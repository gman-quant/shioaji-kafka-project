# src/main.py

import sys
import signal
import threading
import logging
from datetime import datetime

from shioaji_kafka_bridge import config, utils
from shioaji_kafka_bridge.bridge_service import BridgeService
from shioaji_kafka_bridge.exceptions import KafkaProducerError


def main():
    """Main entry point for the Shioaji Kafka Bridge application."""
    
    # 1. Setup Logging
    utils.setup_logging()
    logger = logging.getLogger(__name__)

    # 2a. Check for essential configurations
    if not config.SHIOAJI_API_KEY or not config.SHIOAJI_SECRET_KEY:
        logger.critical("Missing SHIOAJI_API_KEY or SHIOAJI_SECRET_KEY. Please set them in .env file.")
        sys.exit(1)

    # 2b. Check Market Status
    try:
        is_open = utils.is_trading_time(datetime.now())
        initial_status = "[ Market Status: OPEN ]" if is_open else "[ Market Status: CLOSED ]"
        logger.info("=" * 60)
        logger.info(f"{initial_status}")
        logger.info("=" * 60)
    except Exception as e:
        logger.error(f"Could not determine initial market status: {e}")

    # 3. Setup graceful shutdown
    stop_event = threading.Event()
    service = None

    def shutdown_handler(signum, frame):
        logger.info("Shutdown signal received. Signum: %s", signum)
        stop_event.set()
        # The main thread will handle the cleanup via service.stop()
        
    signal.signal(signal.SIGINT, shutdown_handler)  # Handle Ctrl+C
    signal.signal(signal.SIGTERM, shutdown_handler) # Handle `kill` command

    # 4. Initialize and run the service
    try:
        service = BridgeService(stop_event)
        
        # Run the service's main loop in a background thread
        service_thread = threading.Thread(target=service.run, name="BridgeServiceThread")
        service_thread.start()

        # Keep the main thread alive to listen for shutdown signals
        while service_thread.is_alive():
            service_thread.join(timeout=1.0)

    except KafkaProducerError as e:
        logger.critical("Could not start the service due to a Kafka error: %s", e)
        sys.exit(1)
    except Exception as e:
        logger.critical("An unexpected error occurred during startup: %s", e, exc_info=True)
        sys.exit(1)
    finally:
        if service:
            service.stop()
        logger.info("Application shutdown complete.")

if __name__ == "__main__":
    main()