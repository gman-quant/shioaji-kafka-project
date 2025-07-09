# src/shioaji_kafka_bridge/kafka_handler.py

import logging
from datetime import datetime, timedelta, timezone

from confluent_kafka import Producer, Consumer, TopicPartition

from . import config
from .exceptions import KafkaProducerError


logger = logging.getLogger(__name__)

def get_producer_config() -> dict:
    """
    Returns the configuration dictionary for the Kafka Producer.
    This is a placeholder function to allow for future configuration changes.
    """
    return {
        'bootstrap.servers': config.KAFKA_BROKER,
        # Short linger time ensures low latency and prevents back-pressure.
        'linger.ms': 20,
        # Best balance of speed and reliability. `acks='all'` is too slow for this use case.
        'acks': 1,
        # Max batch size; batches are usually sent by `linger.ms` expiring first.
        'batch.size': 32768,      # 32KB
        # Large buffer to absorb traffic spikes and avoid blocking the producer.
        'queue.buffering.max.kbytes': 65536,  # 64MB
        # Efficient compression to reduce network bandwidth.
        'compression.type': 'zstd',
    }

def create_producer() -> Producer:
    """Initializes and returns a Kafka Producer."""
    try:
        producer = Producer(get_producer_config())
        logger.info("Kafka Producer initialized. Broker: %s", config.KAFKA_BROKER)
        return producer
    except Exception as e:
        raise KafkaProducerError(f"Kafka Producer initialization failed: {e}") from e
        
def has_opening_kafka_ticks() -> bool:
    """
    Checks if any Kafka message exists for the current trading session using offsets_for_times.
    Returns True if a message is found, otherwise False.
    """
    dt_now = datetime.now(tz=config.TW_TZ)
    
    # --- Session start time logic ---
    is_day_session = config.DAY_SESSION_START <= dt_now.time() < config.NIGHT_SESSION_START
    if is_day_session:
        start_time, start_date = config.DAY_SESSION_START, dt_now.date()
    else: # Night session
        start_time = config.NIGHT_SESSION_START
        start_date = dt_now.date() - timedelta(days=1) if dt_now.time() < config.NIGHT_SESSION_END else dt_now.date()
            
    start_dt_tw = datetime.combine(start_date, start_time, tzinfo=config.TW_TZ)
    start_utc_ms = int(start_dt_tw.astimezone(timezone.utc).timestamp() * 1000)

    consumer = None
    try:
        consumer = Consumer({
            'bootstrap.servers': config.KAFKA_BROKER,
            'group.id': 'temp-tick-check',
            'auto.offset.reset': 'earliest',
        })
        
        metadata = consumer.list_topics(config.KAFKA_TOPIC, timeout=10)
        if not metadata.topics.get(config.KAFKA_TOPIC):
            logger.warning("Topic '%s' does not exist. Assuming no recent ticks.", config.KAFKA_TOPIC)
            return False

        # 1. Create a list of TopicPartitions, each with the desired timestamp
        partitions_to_query = [
            TopicPartition(config.KAFKA_TOPIC, p, start_utc_ms) 
            for p in metadata.topics[config.KAFKA_TOPIC].partitions
        ]
        
        # 2. Get offsets for each partition after the specified time from Kafka.
        # This call is efficient as it's processed on the Broker.
        offsets = consumer.offsets_for_times(partitions_to_query, timeout=10.0)

        # 3. Check the returned results
        for p in offsets:
            # If offset is not -1, a message was found after the timestamp
            if p.offset != -1:
                logger.debug(
                    "Found a message in partition %d with offset %d after session start. Assuming trading is active.",
                    p.partition, p.offset
                )
                return True

        logger.debug("No messages found in any partition after the session start time.")
        return False
        
    except Exception as e:
        logger.error("Failed to check Kafka for opening ticks due to an exception: %s", e)
        # Fail-safe: Assume connection issue, not a holiday.
        # This keeps the main monitoring loop attempting to reconnect.
        return True
    finally:
        if consumer:
            consumer.close()