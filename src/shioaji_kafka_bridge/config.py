# src/shioaji_kafka_bridge/config.py

import os
from datetime import time as dt_time
from zoneinfo import ZoneInfo

from dotenv import load_dotenv


# ==================== Load Environment Variables ====================
load_dotenv()

# ==================== Shioaji API Credentials ====================
SHIOAJI_API_KEY = os.environ.get("SHIOAJI_API_KEY")
SHIOAJI_SECRET_KEY = os.environ.get("SHIOAJI_SECRET_KEY")

# ==================== Kafka Config ====================
KAFKA_BROKER = os.environ.get("KAFKA_BROKER")
KAFKA_TOPIC = os.environ.get("KAFKA_TOPIC")

# ==================== Monitor Settings ====================
# Service monitoring loop interval (seconds)
MONITOR_INTERVAL = 10
# Max tick silence before critical timeout (seconds)
TIMEOUT_SECONDS = 300
# Retries after critical timeout before holiday check
MAX_TIMEOUT_RETRIES = 3
# Defines different slow tick warning thresholds (in seconds) for day and night sessions.
DAY_SESSION_SLOW_TICK_THRESHOLD = 60
NIGHT_SESSION_SLOW_TICK_THRESHOLD = 180

# ==================== Trading Hours (Asia/Taipei) ====================
DAY_SESSION_START   = dt_time( 8, 30)
DAY_SESSION_END     = dt_time(13, 45)
NIGHT_SESSION_START = dt_time(14, 50)
NIGHT_SESSION_END   = dt_time( 5,  0)
TW_TZ = ZoneInfo("Asia/Taipei")
