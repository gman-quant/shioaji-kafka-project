# src/shioaji_kafka_bridge/exceptions.py

class APILoginFetchError(Exception):
    """Custom error raised when an error occurs during Shioaji API login or contract fetching."""
    pass

class KafkaProducerError(Exception):
    """Custom error for Kafka producer initialization failures."""
    pass