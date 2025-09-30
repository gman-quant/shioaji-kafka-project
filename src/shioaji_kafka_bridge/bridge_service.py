# src/shioaji_kafka_bridge/bridge_service.py

import logging
import threading
import time
from datetime import datetime

import orjson

from . import config, utils, kafka_handler
from .exceptions import APILoginFetchError
from .shioaji_manager import ShioajiManager


logger = logging.getLogger(__name__)

class BridgeService:
    """
    The core service that orchestrates the Shioaji to Kafka bridge.
    It manages the application state and the main monitoring loop.
    """
    def __init__(self, stop_event: threading.Event):
        self._stop_event = stop_event
        self.last_tick_time = time.time()
        self.day_off_date = None
        self._producer = kafka_handler.create_producer()
        self._shioaji_manager = ShioajiManager(
            tick_callback = self._handle_new_tick,
            subscription_success_callback = self._on_subscription_success
        )
    
    def _handle_new_tick(self, tick):
        """Got tick from Shioaji API, send to Kafka."""
        try:
            msg_bytes = orjson.dumps(utils.tick_to_dict(tick))
            self._producer.produce(config.KAFKA_TOPIC, value=msg_bytes)
            self.last_tick_time = time.time()
        except Exception as e:
            logger.error(f"Error producing tick to Kafka: {e}")

    def _on_subscription_success(self):
        """Callback function for when ShioajiManager confirms a subscription."""
        logger.debug("Subscription success event received by service, resetting tick timer.")
        self.last_tick_time = time.time()

    def run(self):
        """Starts the main monitoring loop of the bridge service."""
        logger.info("Bridge service started. Initializing session...")
        
        try:
            # Initial connection attempt
            if utils.is_trading_time(datetime.now(), self.day_off_date):
                self._shioaji_manager.connect_and_subscribe()
        except APILoginFetchError:
            logger.critical("Initial startup failed. The monitor will attempt to recover.")
        
        self._monitor_loop()

    def _monitor_loop(self):
        """
        The main loop for monitoring connection health and trading times.
        This loop is the heart of the service's resilience.
        """
        logger.info("Monitoring loop started.")
        
        # --- State variables for monitoring ---
        timeout_retries = 0
        # Tracks the escalation level of slow tick warnings.
        slow_tick_warning_level = 0
        
        # Get initial market status to prevent logging a transition on startup
        try:
            dt_now = datetime.now(config.TW_TZ)
            was_trading = utils.is_trading_time(dt_now, self.day_off_date)
        except Exception as e:
            logger.error(f"Could not determine initial trading status for monitor loop: {e}")
            was_trading = False 

        while not self._stop_event.wait(config.MONITOR_INTERVAL):
            # self._send_test() # check connection with KAFKA
            self._producer.poll(0)

            dt_now = datetime.now(config.TW_TZ)
            is_currently_trading = utils.is_trading_time(dt_now, self.day_off_date)

            # --- Block 1: Handle Market Status Transitions (Logging only) ---
            if is_currently_trading != was_trading:
                status_msg = "[ Market Status: OPEN ]" if is_currently_trading else "[ Market Status: CLOSED ]"
                logger.info("=" * 60)
                logger.info(f"{status_msg}")
                logger.info("=" * 60)
                was_trading = is_currently_trading

            # --- Block 2: Handle Non-Trading Hours ---
            # This is the authoritative block for the non-trading state.
            if not is_currently_trading:
                if self._shioaji_manager.subscribed:
                    logger.info("Market is closed. Unsubscribing from ticks.")
                    self._shioaji_manager.unsubscribe_ticks()
                
                # Crucial: Reset all session-specific counters to ensure a clean start.
                timeout_retries = 0
                slow_tick_warning_level = 0
                continue
            else:
                # Reset day_off_date if we are back in trading hours
                self.day_off_date = None
            
            # --- From here, we are confirmed to be IN TRADING HOURS ---

            # --- Block 3: Ensure Subscription ---
            if not self._shioaji_manager.subscribed:
                logger.debug("Not subscribed during trading hours. Attempting to connect...")
                try:
                    self._shioaji_manager.connect_and_subscribe()
                except APILoginFetchError as e:
                    logger.error("Failed to connect during monitor cycle. Will retry. Reason: %s", e)
                continue

            # --- Block 4: Tick Health Check ---
            current_warning_threshold = utils.get_current_warning_threshold(dt_now)
            no_tick_duration = time.time() - self.last_tick_time

            # 4a. Major Timeout: A critical failure state.
            if no_tick_duration > config.TIMEOUT_SECONDS:
                slow_tick_warning_level = 0
                timeout_retries += 1
                
                if timeout_retries > config.MAX_TIMEOUT_RETRIES:
                    # Reached max attempts, now determine the root cause (holiday vs connection)
                    logger.error("[CRITICAL]: Max retries exceeded. Checking Kafka ticks.")
                    if not kafka_handler.has_opening_kafka_ticks():
                        logger.info("No recent Kafka ticks.")
                        logger.info("Holiday suspected. Entering sleep mode.")
                        self.day_off_date = dt_now.date()
                        self._shioaji_manager.unsubscribe_ticks()
                        timeout_retries = 0 # Reset retries after handling holiday
                        continue  # Exit current loop iteration
                    else:
                        # Kafka has ticks, so it's a connection issue, not a holiday.
                        logger.info("Kafka shows recent ticks.")
                
                else: # Still within retry attempts, simply reattempting connection
                    logger.error(
                        "[CRITICAL]: No new tick for %.0fs. Reattempting (%d/%d).",
                        no_tick_duration, timeout_retries, config.MAX_TIMEOUT_RETRIES
                    )

                # Always force reconnection if critical timeout persists.
                logger.error("Connection issue suspected. Forcing reconnection.")
                self._shioaji_manager.reconnect(reason="Tick Timeout")

            # 4b. Escalating Slow Tick Warning.
            # Threshold increases by 60s for each warning level.
            elif no_tick_duration > current_warning_threshold + (60 * slow_tick_warning_level):
                logger.warning("[SLOW]: No new tick for %.0fs.", no_tick_duration)
                slow_tick_warning_level += 1

            # 4c. Recovery from Slow Tick Warning.
            elif no_tick_duration < current_warning_threshold and slow_tick_warning_level > 0:
                logger.info("[RECOVERED]: Tick flow normal.")
                slow_tick_warning_level = 0

    def stop(self):
        """Gracefully shuts down the service."""
        logger.info("Preparing to shut down Bridge service...")
        
        if self._shioaji_manager:
            self._shioaji_manager.unsubscribe_ticks()
            time.sleep(2) # Give it a moment to process unsubscription
            self._shioaji_manager.logout()

        if self._producer:
            logger.info("Flushing Kafka producer...")
            self._producer.flush(timeout=15)
            logger.info("Kafka producer flushed.")
            
        logger.info("Bridge service stopped.")
