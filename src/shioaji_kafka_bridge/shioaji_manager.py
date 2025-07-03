# src/shioaji_kafka_bridge/shioaji_manager.py

import logging
import time
import threading
import shioaji as sj
from shioaji import TickFOPv1, Exchange

from . import config
from .exceptions import APILoginFetchError

logger = logging.getLogger(__name__)

class ShioajiManager:
    """Manages the Shioaji API lifecycle, connection, and subscriptions."""

    def __init__(self, tick_callback, subscription_success_callback=None):
        self._api = None
        self._subscribed = False
        self._pending_operation = None
        self._reconnection_lock = threading.Lock()
        self.tick_callback = tick_callback  # Callback to execute when a tick arrives
        self.subscription_success_callback = subscription_success_callback

        # Initialize the first API object
        self._create_new_api_instance()

    def _create_new_api_instance(self):
        """Creates and configures a new Shioaji API instance."""
        logger.info("Creating a new Shioaji API instance...")
        self._api = sj.Shioaji(simulation=True)
        # Register callbacks on the new instance
        self._api.on_tick_fop_v1()(self._on_tick)
        self._api.quote.on_event(self._on_event)
        self._api.on_session_down(self._handle_session_down)

    @property
    def subscribed(self):
        return self._subscribed

    def _on_tick(self, exchange: Exchange, tick: TickFOPv1):
        """Internal callback for when a tick is received from Shioaji."""
        self.tick_callback(tick)

    def _on_event(self, resp_code: int, event_code: int, info: str, event: str):
        """Internal callback for Shioaji quote events."""
        logger.debug("[Shioaji Event %d: %s] %s", event_code, event, info)
        if event_code == 16:  # Subscription/Unsubscription success
            if self._pending_operation == "subscribe_tick":
                logger.info("Tick Subscription Confirmed.")
                self._subscribed = True
                if self.subscription_success_callback:
                    self.subscription_success_callback()

            elif self._pending_operation == "unsubscribe_tick":
                logger.info("Tick Unsubscription Confirmed.")
                self._subscribed = False
            self._pending_operation = None

    def _handle_session_down(self, reason: str = "API Disconnect"):
        """Callback for when Shioaji session goes down."""
        logger.error("Session down event triggered by Shioaji: %s", reason)
        self.reconnect(reason=f"Shioaji session down: {reason}")

    def connect_and_subscribe(self):
        """Logs into Shioaji, verifies contract, and subscribes to ticks."""
        logger.info("Attempting to login and subscribe to TXF ticks...")
        try:
            logger.info("Logging in to Shioaji...")
            self._api.login(api_key=config.SHIOAJI_API_KEY, secret_key=config.SHIOAJI_SECRET_KEY)
            
            # Retry mechanism for contract fetching
            for i in range(1, 11):
                try:
                    _ = self._api.Contracts.Futures.TXF.TXFR1  # Access the TXF contract
                    break
                except (AttributeError, KeyError):
                    logger.debug("TXF contract not ready, retrying... (%d/10)", i)
                    time.sleep(1)
            else:
                raise RuntimeError("TXF contract not available after 10 retries.")
            
            logger.info("Login successful and TXF contract is ready.")

            if not self._subscribed:
                self.subscribe_ticks()
            else:
                logger.info("Already subscribed, no action needed.")
        
        except Exception as e:
            logger.error("Failed during login or subscription process: %s", e)
            raise APILoginFetchError(f"Login or subscription failed: {e}") from e

    def subscribe_ticks(self):
        """Sends a request to subscribe to TXF ticks."""
        try:
            logger.info("Sending tick subscription request...")
            self._pending_operation = "subscribe_tick"
            self._api.quote.subscribe(
                self._api.Contracts.Futures.TXF.TXFR1,
                quote_type=sj.constant.QuoteType.Tick,
                version=sj.constant.QuoteVersion.v1,
            )
        except Exception as e:
            self._pending_operation = None
            logger.error("Tick subscription request failed: %s", e)

    def unsubscribe_ticks(self):
        """Sends a request to unsubscribe from ticks."""
        if not self._subscribed:
            logger.info("Not currently subscribed, skipping unsubscription.")
            return
        try:
            logger.info("Sending tick unsubscription request...")
            self._pending_operation = "unsubscribe_tick"
            self._api.quote.unsubscribe(self._api.Contracts.Futures.TXF.TXFR1)
        except Exception as e:
            self._pending_operation = None
            logger.warning("Tick unsubscription request failed: %s", e)
            
    def reconnect(self, reason: str):
        """Handles the full session reconnection logic."""
        if not self._reconnection_lock.acquire(blocking=False):
            logger.warning("Reconnection is already in progress. Skipping.")
            return

        try:
            logger.warning("=" * 60)
            logger.warning("Starting session reconnection process due to: %s", reason)
            logger.warning("=" * 60)
            
            # Reset state
            self._subscribed = False
            self._pending_operation = None

            # Cleanly destroy the old API object
            if self._api:
                try:
                    self._api.logout()
                    logger.info("Old API object logged out.")
                except Exception as e:
                    logger.warning("Exception during old API logout (this is often ok): %s", e)
            
            # Create a fresh instance
            self._create_new_api_instance()
            
            # Attempt to log back in and subscribe
            self.connect_and_subscribe()

        except APILoginFetchError as e:
            logger.error("Session recovery failed during login/subscribe. Monitor will retry. Error: %s", e)
        except Exception as e:
            logger.exception("An unexpected error occurred during reconnect.")
        finally:
            self._reconnection_lock.release()
            logger.info("Reconnection process finished.")

    def logout(self):
        """Logs out from the Shioaji API."""
        try:
            logger.info("Logging out from Shioaji API...")
            self._api.logout()
            logger.info("Shioaji API logged out.")
        except Exception as e:
            logger.error("Failed to log out from Shioaji API: %s", e)