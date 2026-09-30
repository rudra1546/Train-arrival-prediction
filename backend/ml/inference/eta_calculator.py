"""
ETA Calculation module for SIH 26028 Dynamic ETA Prediction Service.
Calculates absolute scheduled arrival datetimes and dynamic ETAs respecting journey start date,
multi-day journey arrival days, and delay-induced midnight crossings.
"""

from datetime import datetime, date, timedelta, time
from typing import Tuple, Union
import re

from ml.inference.schemas import InvalidJourneyDateError


def parse_journey_date(date_str: str) -> date:
    """
    Validate and parse journey start date string (YYYY-MM-DD).
    Raises InvalidJourneyDateError on failure.
    """
    if not isinstance(date_str, str):
        raise InvalidJourneyDateError(str(date_str), "Date must be a string")
    
    date_str = date_str.strip()
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        raise InvalidJourneyDateError(date_str, "Date format must be strictly YYYY-MM-DD")
    
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError as e:
        raise InvalidJourneyDateError(date_str, str(e))


def parse_time_to_minutes(time_val: Union[str, int, float, None]) -> int:
    """
    Convert time representation to minutes from midnight (0..1439).
    Supports 'HH:MM' string or integer minutes.
    """
    if time_val is None:
        return 0
    if isinstance(time_val, (int, float)):
        return int(time_val) % 1440
    if isinstance(time_val, str):
        parts = time_val.strip().split(":")
        if len(parts) == 2:
            try:
                hh, mm = int(parts[0]), int(parts[1])
                return (hh * 60 + mm) % 1440
            except ValueError:
                return 0
    return 0


def compute_scheduled_arrival(
    journey_date: Union[str, date],
    arrival_day: int,
    arrival_time_or_minutes: Union[str, int, float, None]
) -> datetime:
    """
    Calculate the exact scheduled arrival datetime at a target station.
    
    Parameters:
    -----------
    journey_date : str or date
        Journey start date (YYYY-MM-DD).
    arrival_day : int
        Timetable arrival day offset (1-indexed: Day 1 = start date, Day 2 = next date, etc.).
    arrival_time_or_minutes : str or int
        Scheduled arrival time string 'HH:MM' or integer minutes from midnight (0..1439).
        
    Returns:
    --------
    datetime : Scheduled arrival timestamp
    """
    if isinstance(journey_date, str):
        j_date = parse_journey_date(journey_date)
    elif isinstance(journey_date, date):
        j_date = journey_date
    else:
        raise InvalidJourneyDateError(str(journey_date), "Unsupported date object")

    # arrival_day is 1-indexed (Day 1 -> offset 0 days; Day 2 -> offset 1 day)
    day_offset = max(0, int(arrival_day) - 1) if arrival_day is not None else 0
    target_date = j_date + timedelta(days=day_offset)

    arr_min = parse_time_to_minutes(arrival_time_or_minutes)
    hh = arr_min // 60
    mm = arr_min % 60

    return datetime.combine(target_date, time(hour=hh, minute=mm, second=0))


def compute_predicted_eta(
    scheduled_arrival_dt: datetime,
    predicted_delay_minutes: float
) -> datetime:
    """
    Calculate dynamic expected time of arrival (ETA) given scheduled arrival
    datetime and predicted delay in minutes.
    
    Accurately handles:
    - Normal positive delays (e.g. +45 min)
    - Early arrivals with negative delay (e.g. -10 min)
    - Delays that push arrival across midnight into the following day
    """
    delay_delta = timedelta(minutes=float(predicted_delay_minutes))
    return scheduled_arrival_dt + delay_delta


def format_timestamp(dt: datetime) -> str:
    """Standardize timestamp format for output API/schema (YYYY-MM-DD HH:MM:SS)."""
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def calculate_station_eta(
    journey_date: Union[str, date],
    arrival_day: int,
    arrival_time_or_minutes: Union[str, int, float, None],
    predicted_delay_minutes: float
) -> Tuple[str, str]:
    """
    Convenience method calculating both scheduled arrival and dynamic ETA.
    
    Returns:
    --------
    Tuple[str, str] : (scheduled_arrival_str, predicted_eta_str)
    """
    sched_dt = compute_scheduled_arrival(journey_date, arrival_day, arrival_time_or_minutes)
    eta_dt = compute_predicted_eta(sched_dt, predicted_delay_minutes)
    return format_timestamp(sched_dt), format_timestamp(eta_dt)
