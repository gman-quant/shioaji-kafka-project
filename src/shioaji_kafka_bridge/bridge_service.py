# src/shioaji_kafka_bridge/bridge_service.py

import logging
import time
import threading
from datetime import datetime

from . import config, utils, kafka_handler
from .shioaji_manager import ShioajiManager
from .exceptions import APILoginFetchError

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
        """Callback function passed to ShioajiManager."""
        kafka_handler.send_tick_to_kafka(self._producer, tick)
        self.last_tick_time = time.time()

    def _on_subscription_success(self):
        """Callback function for when ShioajiManager confirms a subscription."""
        logger.info("Subscription success event received by service, resetting tick timer.")
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
        """The main loop for monitoring connection health and trading times."""
        logger.info("Monitoring loop started.")
        timeout_retries = 0
        # --- Add a state variable for the warning if no tick ---
        tick_flow_warning_active = False
        
        # Get initial market status 
        try:
            dt_now = datetime.now(config.TW_TZ)
            was_trading = utils.is_trading_time(dt_now, self.day_off_date)
        except Exception as e:
            logger.error(f"Could not determine initial trading status for monitor loop: {e}")
            was_trading = False 

        while not self._stop_event.wait(config.MONITOR_INTERVAL):
            dt_now = datetime.now(config.TW_TZ)
            is_currently_trading = utils.is_trading_time(dt_now, self.day_off_date)

            # Market status change detection
            if is_currently_trading != was_trading:
                status_msg = "[ Market Status: OPEN ]" if is_currently_trading else "[ Market Status: CLOSED ]"
                logger.info("=" * 60)
                logger.info(status_msg)
                logger.info("=" * 60)
                
                was_trading = is_currently_trading
                self.last_tick_time = time.time() 
                timeout_retries = 0
                tick_flow_warning_active = False # Reset warning on status change

            if not is_currently_trading:
                if self._shioaji_manager.subscribed:
                    logger.info("Unsubscribing from ticks.")
                    self._shioaji_manager.unsubscribe_ticks()
                timeout_retries = 0
                continue
            
            # --- We are in trading hours from here ---

            if not self._shioaji_manager.subscribed:
                logger.warning("Not subscribed during trading hours.")
                try:
                    self._shioaji_manager.connect_and_subscribe()
                except APILoginFetchError as e:
                    logger.error("Failed to connect during monitor cycle. Will retry. Reason: %s", e)
                continue

            # --- Tick Health Check ---
            no_tick_duration = time.time() - self.last_tick_time

            # 1. Major Timeout: Handles reconnection or holiday detection
            if no_tick_duration > config.TIMEOUT_SECONDS:
                tick_flow_warning_active = False # Reset warning flag
                
                timeout_retries += 1
                logger.warning(
                    "Tick timeout: No new tick for %.0f seconds. (count %d/%d).",
                    no_tick_duration, timeout_retries, config.MAX_TIMEOUT_RETRIES
                )
                
                if timeout_retries >= config.MAX_TIMEOUT_RETRIES:
                    if not kafka_handler.has_opening_kafka_ticks_optimized():
                        logger.warning("No ticks in Kafka either. Assuming it's a non-trading day.")
                        self.day_off_date = dt_now.date()
                        self._shioaji_manager.unsubscribe_ticks()
                        timeout_retries = 0
                        continue
                    else:
                        logger.info("Kafka has recent ticks. This is likely a connection issue, not a holiday.")
                
                logger.error("Assuming connection issue. Forcing reconnection.")
                self._shioaji_manager.reconnect(reason="Tick Timeout")

            # 2. Minor Timeout Warning: Log a warning if tick flow is slow
            elif no_tick_duration > 2 * config.MONITOR_INTERVAL:
                logger.warning("No new tick for %.0f seconds.", no_tick_duration)
                tick_flow_warning_active = True # Set state to "warning"

            # 3. Recovery Message: Log a recovery message only if it was previously in a warning state
            else:
                if tick_flow_warning_active:
                    logger.info("Tick data flow has recovered.")
                    tick_flow_warning_active = False # Reset state to "normal"


    def stop(self):
        """Gracefully shuts down the service."""
        logger.info("Shutdown signal received. Cleaning up...")
        
        if self._shioaji_manager:
            self._shioaji_manager.unsubscribe_ticks()
            time.sleep(2) # Give it a moment to process unsubscription
            self._shioaji_manager.logout()

        if self._producer:
            logger.info("Flushing Kafka producer...")
            self._producer.flush(timeout=15)
            logger.info("Kafka producer flushed.")
            
        logger.info("Bridge service stopped.")
