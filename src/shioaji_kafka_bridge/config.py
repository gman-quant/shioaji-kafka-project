# src/shioaji_kafka_bridge/config.py

import os
from datetime import time as dt_time
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

# ==================== Load Environment Variables ====================
load_dotenv()

# ==================== Shioaji API Credentials ====================
API_KEY = os.environ.get("SHIOAJI_API_KEY")
SECRET_KEY = os.environ.get("SHIOAJI_SECRET_KEY")

# ==================== Kafka Config ====================
KAFKA_BROKER = os.environ.get("KAFKA_BROKER")
KAFKA_TOPIC = os.environ.get("KAFKA_TOPIC")

# ==================== Monitor Settings ====================
MONITOR_INTERVAL    =  30  # Seconds between health checks
TIMEOUT_SECONDS     = 360  # Max allowed tick silence before triggering a check
MAX_TIMEOUT_RETRIES =   3  # Retries before assuming non-trading day and pausing

# ==================== Trading Hours (Asia/Taipei) ====================
TRADING_BUFFER_MIN  = 1  # Minutes to buffer around session open/close
DAY_SESSION_START   = dt_time( 8, 30)
DAY_SESSION_END     = dt_time(13, 45)
NIGHT_SESSION_START = dt_time(14, 50)
NIGHT_SESSION_END   = dt_time( 5,  0)
TW_TZ = ZoneInfo("Asia/Taipei")

# ==================== Tick Field Mapping ====================
FIELDS_TO_FLOAT = (
    'open', 'underlying_price', 'avg_price', 'close', 'high',
    'low', 'amount', 'total_amount', 'price_chg', 'pct_chg'
)