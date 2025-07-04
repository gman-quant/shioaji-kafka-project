# src/shioaji_kafka_bridge/kafka_handler.py

import logging
import time
import orjson
from datetime import datetime, timedelta, timezone

from confluent_kafka import Producer, Consumer, TopicPartition
from . import config, utils
from .exceptions import KafkaProducerError

logger = logging.getLogger(__name__)

high_throughput_config = {
    'bootstrap.servers': config.KAFKA_BROKER,
    # --- Optimization parameters ---
    # Increase batching wait time and size to allow the producer to bundle more messages.
    'linger.ms': 20,          # Wait up to 20ms to form a batch.
    'batch.size': 32768,      # Send batch immediately if it reaches 32KB.
    # Enable compression to significantly reduce network traffic.
    'compression.type': 'snappy', # Or 'zstd'.
    # --- Resource & Reliability parameters ---
    # Provide a larger buffer to handle traffic spikes.
    'queue.buffering.max.kbytes': 65536,  # 64MB.
    # Maintain default reliability level.
    'acks': 1
}

def create_producer() -> Producer:
    """Initializes and returns a Kafka Producer."""
    try:
        producer = Producer(high_throughput_config)
        logger.info("Kafka Producer initialized. Broker: %s", config.KAFKA_BROKER)
        return producer
    except Exception as e:
        raise KafkaProducerError(f"Kafka Producer initialization failed: {e}") from e

def send_tick_to_kafka(producer: Producer, tick):
    """Serializes a tick and sends it to the configured Kafka topic."""
    try:
        msg_bytes = orjson.dumps(utils.tick_to_dict(tick))
        producer.produce(config.KAFKA_TOPIC, value=msg_bytes)
        producer.poll(0)
    except Exception as e:
        logger.error("Kafka send failed: %s", e)
        
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
            'group.id': f'temp-tick-check-{time.time()}',
            'auto.offset.reset': 'earliest',
        })
        
        metadata = consumer.list_topics(config.KAFKA_TOPIC, timeout=10)
        if not metadata.topics.get(config.KAFKA_TOPIC):
            logger.warning("Topic '%s' does not exist. Assuming no recent ticks.", config.KAFKA_TOPIC)
            return False

        # --- 【核心修改】使用 offsets_for_times ---
        # 1. 建立一個 TopicPartition 列表，每個都帶有我們要查詢的時間戳
        partitions_to_query = [
            TopicPartition(config.KAFKA_TOPIC, p, start_utc_ms) 
            for p in metadata.topics[config.KAFKA_TOPIC].partitions
        ]
        
        # 2. 讓 Kafka 直接告訴我們每個 partition 在該時間之後的 offset
        # 這個呼叫效率非常高，因為它是在 Broker 端完成的
        offsets = consumer.offsets_for_times(partitions_to_query, timeout=10.0)

        # 3. 檢查回傳的結果
        for p in offsets:
            # 如果 offset 不是 -1，代表找到了在該時間點之後的訊息
            if p.offset != -1:
                logger.info(
                    "Found a message in partition %d with offset %d after session start. Assuming trading is active.",
                    p.partition, p.offset
                )
                return True

        logger.info("No messages found in any partition after the session start time.")
        return False
        
    except Exception as e:
        logger.error("Failed to check Kafka for opening ticks due to an exception: %s", e)
        # 【核心修改】修改錯誤處理的策略
        # Fail safe: If we can't check Kafka, assume it's a connection issue, not a holiday.
        # This keeps the main monitoring loop trying to reconnect.
        return True
    finally:
        if consumer:
            consumer.close()