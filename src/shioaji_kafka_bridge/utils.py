# src/shioaji_kafka_bridge/utils.py

import logging
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
    Determine whether the given datetime falls within valid trading sessions.

    Trading rules considered:
      - Day and night sessions (with configurable start/end times).
      - Buffer time before session start and after session end 
        (to account for slight timing drifts).
      - Weekends (Saturday night close, full Sunday off, Monday pre-open).
      - Holidays (full day off and the following day's day-session pre-open).

    Args:
        dt_now (datetime, optional): The datetime to evaluate. 
                                     Defaults to current local time if None.
        day_off_date (date, optional): Specific holiday date (non-trading day).
                                       If provided, both that date and the 
                                       next day's early morning before 
                                       day-session open are treated as closed.

    Returns:
        bool: True if trading is open, False otherwise.
    """
    dt_now = dt_now or datetime.now()

    # Normalize tz-aware datetime into naive datetime (local reference).
    if dt_now.tzinfo is not None:
        dt_now = dt_now.replace(tzinfo=None)
        
    # Buffer time (e.g., 20s if MONITOR_INTERVAL=10s) around open/close.
    buffer = timedelta(seconds=2 * config.MONITOR_INTERVAL)

    # Fix to current date to avoid issues with overnight sessions spanning midnight.
    dummy_date = dt_now.date()
    
    # Session boundaries (with buffer adjustment).
    day_open    = (datetime.combine(dummy_date, config.DAY_SESSION_START)   - buffer).time()
    day_close   = (datetime.combine(dummy_date, config.DAY_SESSION_END)     + buffer).time()
    night_open  = (datetime.combine(dummy_date, config.NIGHT_SESSION_START) - buffer).time()
    night_close = (datetime.combine(dummy_date, config.NIGHT_SESSION_END)   + buffer).time()

    time_now = dt_now.time()
    weekday = dt_now.weekday()  # Monday=0 ... Sunday=6

    # --- Holiday check ---
    if day_off_date:
        # Entire holiday is closed.
        if dt_now.date() == day_off_date:
            return False
        # Following day: closed until day session opens.
        if dt_now.date() == (day_off_date + timedelta(days=1)) and time_now < day_open:
            return False

    # --- Weekend check ---
    if weekday == 6:  # Full Sunday is non-trading
        return False
    
    if weekday == 5 and time_now >= night_close and night_open > night_close:
        # Saturday after night session ends (markets closed)
        return False

    if weekday == 0 and time_now < day_open:  
        # Monday before day session opens
        return False

    # --- Regular sessions ---
    is_in_day_session = day_open <= time_now < day_close
    is_in_night_session = (
        night_open <= time_now < night_close
        if night_open < night_close  # Same-day night session
        else time_now >= night_open or time_now < night_close  # Overnight night session
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