"""Shared utility helpers used across EcoCleanUp modules."""

from datetime import date


def _safe_int(value, default=0):
    """Convert a value to int and return default if conversion fails."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _to_minutes(time_value):
    """Convert a time value to total minutes, or None for empty input."""
    if not time_value:
        return None

    if hasattr(time_value, 'hour') and hasattr(time_value, 'minute'):
        hours = int(time_value.hour)
        minutes = int(time_value.minute)
    else:
        parts = str(time_value).strip().split(':')
        if len(parts) < 2:
            raise ValueError('Invalid time format.')

        hours = int(parts[0])
        minutes = int(parts[1])

    if hours < 0 or hours > 23 or minutes < 0 or minutes > 59:
        raise ValueError('Invalid time value.')

    return (hours * 60) + minutes


EVENT_TEXT_LIMITS = {
    "event_name": 100,
    "location": 255,
    "event_type": 50,
    "description": 2000,
    "supplies": 1000,
    "safety_instructions": 1000,
    "reminder_message": 500,
}


def event_text_length_error(
    event_name,
    location,
    event_type=None,
    description=None,
    supplies=None,
    safety_instructions=None,
):
    """
    Validate event text fields against configured maximum lengths.
    Return a user-facing error message when any field exceeds its limit.
    """
    field_specs = [
        ("Event name", event_name, EVENT_TEXT_LIMITS["event_name"]),
        ("Location", location, EVENT_TEXT_LIMITS["location"]),
        ("Event type", event_type, EVENT_TEXT_LIMITS["event_type"]),
        ("Description", description, EVENT_TEXT_LIMITS["description"]),
        ("Supplies", supplies, EVENT_TEXT_LIMITS["supplies"]),
        ("Safety instructions", safety_instructions, EVENT_TEXT_LIMITS["safety_instructions"]),
    ]

    for label, value, max_length in field_specs:
        if value and len(value) > max_length:
            return f"{label} cannot exceed {max_length} characters."

    return None


def parse_event_form(form_data):
    """Extract and normalise event form inputs from request form data."""
    duration_raw = form_data.get('duration', '').strip()
    return {
        'event_name': form_data.get('event_name', '').strip(),
        'location': form_data.get('location', '').strip(),
        'event_type': form_data.get('event_type', '').strip() or None,
        'event_date': form_data.get('event_date', '').strip(),
        'start_time': form_data.get('start_time', '').strip() or None,
        'end_time': form_data.get('end_time', '').strip() or None,
        'duration_raw': duration_raw,
        'duration': _safe_int(duration_raw, 0),
        'description': form_data.get('description', '').strip() or None,
        'supplies': form_data.get('supplies', '').strip() or None,
        'safety_instructions': form_data.get('safety_instructions', '').strip() or None,
    }


def validate_event_form(event_data, require_future_date=False):
    """Validate shared event form rules and return an error message when invalid."""
    required_values = (
        event_data['event_name'],
        event_data['location'],
        event_data['event_date'],
        event_data['start_time'],
        event_data['duration_raw'],
        event_data['supplies'],
        event_data['safety_instructions'],
    )
    if not all(required_values):
        return (
            'Please complete all required fields: event name, location, date, '
            'start time, duration, supplies, and safety instructions.'
        )

    text_length_error = event_text_length_error(
        event_name=event_data['event_name'],
        location=event_data['location'],
        event_type=event_data['event_type'],
        description=event_data['description'],
        supplies=event_data['supplies'],
        safety_instructions=event_data['safety_instructions'],
    )
    if text_length_error:
        return text_length_error

    try:
        event_date_value = date.fromisoformat(event_data['event_date'])
    except ValueError:
        return 'Invalid event date.'

    if require_future_date and event_date_value < date.today():
        return 'Event date cannot be in the past.'

    if event_data['duration'] <= 0:
        return 'Duration must be a positive number.'

    try:
        start_minutes = _to_minutes(event_data['start_time'])
        end_minutes = _to_minutes(event_data['end_time'])
    except (ValueError, AttributeError):
        return 'Invalid time format.'

    if start_minutes is not None and end_minutes is not None and end_minutes < start_minutes:
        return 'End time must be after start time.'

    if start_minutes is not None and (start_minutes + event_data['duration']) >= (24 * 60):
        return 'Calculated end time exceeds 24:00.'

    return None


def split_events_by_tab(events, today=None):
    """Group events into today, upcoming, past, and cancelled collections."""
    today_value = today or date.today()
    cancelled_events = [event for event in events if event['is_cancelled']]
    today_events = [
        event
        for event in events
        if not event['is_cancelled'] and event['event_date'] == today_value
    ]
    upcoming_events = [
        event
        for event in events
        if not event['is_cancelled'] and event['event_date'] > today_value
    ]
    past_events = [
        event
        for event in events
        if not event['is_cancelled'] and event['event_date'] < today_value
    ]

    return {
        'today': today_events,
        'upcoming': upcoming_events,
        'past': past_events,
        'cancelled': cancelled_events,
    }
