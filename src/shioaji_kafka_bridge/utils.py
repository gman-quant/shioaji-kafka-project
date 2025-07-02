# src/shioaji_kafka_bridge/utils.py

import logging
import socket
from datetime import datetime, timedelta
from . import config

def setup_logging():
    """Configures the root logger for the application."""
    log_format = '[%(asctime)s] [%(threadName)-20s] [%(levelname)-8s] %(message)s (%(filename)s:%(lineno)d)'
    logging.basicConfig(level=logging.INFO, format=log_format, datefmt='%Y-%m-%d %H:%M:%S')

def tick_to_dict(tick) -> dict:
    """Converts a Shioaji Tick object to a dictionary with float conversions."""
    tick_dict = tick.to_dict()
    tick_dict['datetime'] = tick_dict['datetime'].replace(tzinfo=config.TW_TZ) # Optionally set timezone if needed
    for field in config.FIELDS_TO_FLOAT:
        tick_dict[field] = float(tick_dict[field])
    return tick_dict

def is_internet_available(host="8.8.8.8", port=53, timeout=2) -> bool:
    """Checks for an active internet connection."""
    try:
        socket.setdefaulttimeout(timeout)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((host, port))
        return True
    except OSError:
        return False

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
        
    buffer = timedelta(minutes=config.TRADING_BUFFER_MIN)

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