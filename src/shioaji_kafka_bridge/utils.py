# src/shioaji_kafka_bridge/utils.py

import logging
import socket
from datetime import datetime, timedelta
from . import config

# Defines the fields within a Tick object that should be converted to float.
FIELDS_TO_FLOAT = (
    'open', 'underlying_price', 'avg_price', 'close', 'high',
    'low', 'amount', 'total_amount', 'price_chg', 'pct_chg'
)

def setup_logging():
    """Configures the root logger for the application."""
    log_format = '[%(asctime)s] [%(threadName)-20s] [%(levelname)-8s] %(message)s (%(filename)s:%(lineno)d)'
    logging.basicConfig(level=logging.INFO, format=log_format, datefmt='%Y-%m-%d %H:%M:%S')

def tick_to_dict(tick) -> dict:
    """
    Converts a Shioaji Tick object to a dictionary, safely handling
    type conversions and ensuring timezone information is present.
    """
    tick_dict = tick.to_dict()
    tick_dict['datetime'] = tick_dict['datetime'].replace(tzinfo=config.TW_TZ) # Optionally set timezone if needed
    for field in FIELDS_TO_FLOAT:
        tick_dict[field] = float(tick_dict[field])
    return tick_dict

def is_trading_time(dt_now: datetime = None, day_off_date: datetime.date = None) -> bool:
    """
    Checks if the current time is within allowed trading sessions,
    considering day/night sessions, buffer time, weekends, and holidays.
    """
    if day_off_date and dt_now.date() == day_off_date:
        return False

    dt_now = dt_now or datetime.now()
    if dt_now.tzinfo is not None:
        dt_now = dt_now.replace(tzinfo=None)
        
    buffer = timedelta(seconds=2 * config.MONITOR_INTERVAL) # 20s to buffer around session open/close

    # Note: Use a fixed date to prevent issues with date changes during overnight sessions
    dummy_date = dt_now.date()
    
    day_open    = (datetime.combine(dummy_date, config.DAY_SESSION_START)   - buffer).time()
    day_close   = (datetime.combine(dummy_date, config.DAY_SESSION_END)     + buffer).time()
    night_open  = (datetime.combine(dummy_date, config.NIGHT_SESSION_START) - buffer).time()
    night_close = (datetime.combine(dummy_date, config.NIGHT_SESSION_END)   + buffer).time()

    time_now = dt_now.time()
    weekday = dt_now.weekday()  # Monday ~ Sunday = 0 ~ 6

    if weekday == 6:  # Sunday is always a non-trading day
        return False
    
    if weekday == 5 and time_now >= night_close and night_open > night_close: # Saturday after night session close
        return False

    if weekday == 0 and time_now < day_open: # Monday before day session open
        return False

    is_in_day_session = day_open <= time_now < day_close
    is_in_night_session = (
        night_open <= time_now < night_close
        if night_open < night_close  # same-day night session
        else time_now >= night_open or time_now < night_close  # overnight session
    )

    return is_in_day_session or is_in_night_session

def get_current_warning_threshold(dt_now: datetime) -> int:
    """
    Determines the appropriate slow tick warning threshold based on the current time.
    
    Args:
        dt_now: The current timezone-aware datetime.

    Returns:
        The warning threshold in seconds for the current session.
    """
    now_time = dt_now.time()
    # Day session is defined as the time between the day session start and before the night session start.
    if config.DAY_SESSION_START <= now_time < config.NIGHT_SESSION_START:
        return config.DAY_SESSION_SLOW_TICK_THRESHOLD
    else:
        return config.NIGHT_SESSION_SLOW_TICK_THRESHOLD