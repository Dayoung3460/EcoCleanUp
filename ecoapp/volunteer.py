"""Volunteer-facing routes for event discovery, registration, history, and feedback."""

from datetime import date

from flask import flash, redirect, render_template, request, session, url_for

from ecoapp import app
from ecoapp import db
from ecoapp.queries import volunteer_queries as queries
from ecoapp.user import roles_required

MAX_FEEDBACK_COMMENTS_LENGTH = 1000


@app.route('/volunteer/home')
@roles_required('volunteer')
def volunteer_home():
    """Render volunteer dashboard metrics grouped into event and feedback summaries."""
    with db.get_cursor() as cursor:
        cursor.execute(queries.VOLUNTEER_HOME_EVENT_STATS, (session['user_id'],))
        event_stats = cursor.fetchone()

        cursor.execute(queries.VOLUNTEER_HOME_PENDING_FEEDBACK, (session['user_id'],))
        pending_feedback_count = cursor.fetchone()['pending_feedback_count']

        cursor.execute(queries.VOLUNTEER_HOME_FEEDBACK_SUBMITTED, (session['user_id'],))
        feedback_submitted_count = cursor.fetchone()['feedback_submitted_count']

    return render_template(
        'private/volunteer_home.html',
        event_stats=event_stats,
        feedback_stats={
            'pending_feedback_count': pending_feedback_count,
            'feedback_submitted_count': feedback_submitted_count,
        },
    )


@app.route('/events')
@roles_required('volunteer', 'event_leader', 'admin')
def browse_events():
    """List active events with optional date, location, and type filters."""
    filter_date = request.args.get('date', '').strip()
    filter_location = request.args.get('location', '').strip()
    filter_type = request.args.get('event_type', '').strip()

    # Base condition to only show active (not cancelled) events
    conditions = ["e.is_cancelled = FALSE"]
    params = []

    if filter_date:
        conditions.append("e.event_date = %s")
        params.append(filter_date)

    if filter_location:
        # Use ILIKE for case-insensitive partial match
        conditions.append("e.location ILIKE %s")
        params.append(f"%{filter_location}%")

    if filter_type:
        conditions.append("e.event_type ILIKE %s")
        params.append(f"%{filter_type}%")

    where_sql = " AND ".join(conditions)

    with db.get_cursor() as cursor:
        cursor.execute(
            queries.VOLUNTEER_BROWSE_EVENTS.format(where_sql=where_sql),
            tuple(params),
        )
        upcoming_events = cursor.fetchall()

        registered_event_ids = set()
        if session.get('role') == 'volunteer':
            cursor.execute(queries.VOLUNTEER_REGISTERED_EVENT_IDS, (session['user_id'],))
            registered_event_ids = {row['event_id'] for row in cursor.fetchall()}

    return render_template(
        'private/events.html',
        upcoming_events=upcoming_events,
        filter_date=filter_date,
        filter_location=filter_location,
        filter_type=filter_type,
        registered_event_ids=registered_event_ids,
        current_date=date.today(),
    )


@app.route('/volunteer/events/register/<int:event_id>', methods=['POST'])
@roles_required('volunteer')
def register_event(event_id):
    """Register the current volunteer for an eligible upcoming event."""
    volunteer_id = session['user_id']

    with db.get_cursor() as cursor:
        cursor.execute(queries.VOLUNTEER_EVENT_BY_ID, (event_id,))
        event = cursor.fetchone()

        if event is None:
            flash('Event not found.', 'danger')
            return redirect(url_for('browse_events'))

        if event['event_date'] < date.today():
            flash('You cannot register for an event in the past.', 'warning')
            return redirect(url_for('browse_events'))

        cursor.execute(queries.VOLUNTEER_REGISTRATION_BY_EVENT_AND_USER, (event_id, volunteer_id))
        registered_event = cursor.fetchone()
        if registered_event is not None:
            if registered_event['registration_status'] == 'active':
                flash('You are already registered for this event.', 'warning')
                return redirect(url_for('browse_events'))

            cursor.execute(queries.VOLUNTEER_REACTIVATE_REGISTRATION, (registered_event['registration_id'],))

            flash(f"Successfully registered for '{event['event_name']}'.", 'success')
            return redirect(url_for('browse_events'))

        if event['start_time'] is not None and event['end_time'] is not None:
            cursor.execute(
                # overlaps operator checks if the time intervals overlap (partial or full)
                # ::time casts the string to time type 
                queries.VOLUNTEER_CONFLICT_EVENT,
                (
                    volunteer_id,
                    event_id,
                    event['event_date'],
                    event['start_time'],
                    event['end_time'],
                ),
            )
            conflict_event = cursor.fetchone()
            if conflict_event is not None:
                requested_date = event['event_date'].strftime('%Y-%m-%d')
                requested_start = event['start_time'].strftime('%H:%M') if event['start_time'] else 'TBA'
                requested_end = event['end_time'].strftime('%H:%M') if event['end_time'] else 'TBA'
                conflict_date = conflict_event['event_date'].strftime('%Y-%m-%d')
                conflict_start = conflict_event['start_time'].strftime('%H:%M') if conflict_event['start_time'] else 'TBA'
                conflict_end = conflict_event['end_time'].strftime('%H:%M') if conflict_event['end_time'] else 'TBA'
                flash(
                    (
                        f"Registration declined. '{event['event_name']}' ({requested_date} {requested_start}-{requested_end}) "
                        f"overlaps with your existing registration '{conflict_event['event_name']}' "
                        f"({conflict_date} {conflict_start}-{conflict_end}). "
                        "Please choose a different time or cancel the existing one first."
                    ),
                    'warning',
                )
                return redirect(url_for('browse_events'))

        cursor.execute(queries.VOLUNTEER_INSERT_REGISTRATION, (event_id, volunteer_id))

    flash(f"Successfully registered for '{event['event_name']}'.", 'success')
    return redirect(url_for('browse_events'))

@app.route('/volunteer/history')
@roles_required('volunteer')
def volunteer_history_legacy():
    """Redirect old history URL to the new my-events page."""
    return redirect(url_for('volunteer_events'))


@app.route('/volunteer/my-events')
@roles_required('volunteer')
def volunteer_events():
    """Show volunteer-registered events separated into today, upcoming, and past tabs."""
    selected_tab = request.args.get('tab', 'today').strip().lower()
    if selected_tab not in ('today', 'upcoming', 'past'):
        selected_tab = 'today'

    today = date.today()
    with db.get_cursor() as cursor:
        cursor.execute(queries.VOLUNTEER_MY_EVENTS, (session['user_id'],))
        all_rows = cursor.fetchall()

    today_rows = [row for row in all_rows if row['event_date'] == today]
    upcoming_rows = [row for row in all_rows if row['event_date'] > today]
    past_rows = [row for row in all_rows if row['event_date'] < today]

    if selected_tab == 'today':
        history_rows = today_rows
    elif selected_tab == 'upcoming':
        history_rows = upcoming_rows
    else:
        history_rows = past_rows

    return render_template(
        'private/volunteer_history.html',
        history_rows=history_rows,
        today=today,
        selected_tab=selected_tab,
        today_count=len(today_rows),
        upcoming_count=len(upcoming_rows),
        past_count=len(past_rows),
    )


@app.route('/volunteer/feedback/<int:event_id>', methods=['POST'])
@roles_required('volunteer')
def submit_feedback(event_id):
    """Create or update feedback for an attended event by the current volunteer."""
    volunteer_id = session['user_id']
    rating_raw = request.form.get('rating', '').strip()
    comments = request.form.get('comments', '').strip()

    # requirements: Feedback can include a star rating system (1 – 5)
    if not rating_raw.isdigit() or int(rating_raw) < 1 or int(rating_raw) > 5:
        flash('Rating must be a number between 1 and 5.', 'danger')
        return redirect(url_for('volunteer_events', tab='past'))

    rating = int(rating_raw)
    comments = comments or None

    if comments is not None and len(comments) > MAX_FEEDBACK_COMMENTS_LENGTH:
        flash(f'Comments cannot exceed {MAX_FEEDBACK_COMMENTS_LENGTH} characters.', 'danger')
        return redirect(url_for('volunteer_events', tab='past'))

    with db.get_cursor() as cursor:
        cursor.execute(queries.VOLUNTEER_FEEDBACK_PARTICIPATION_CHECK, (event_id, volunteer_id))
        participation = cursor.fetchone()

        if participation is None:
            flash('You can only submit feedback for events you registered for.', 'danger')
            return redirect(url_for('volunteer_events', tab='past'))

        if participation['event_date'] > date.today():
            flash('Feedback can only be submitted after the event date.', 'warning')
            return redirect(url_for('volunteer_events', tab='past'))

        if participation['attendance'] != 'present':
            flash('Feedback can only be submitted for events you have attended.', 'warning')
            return redirect(url_for('volunteer_events', tab='past'))

        # ON CONFLICT clause allows us to either insert new feedback or update existing feedback for the same event and volunteer
        # EXCLUDED: contains the values proposed for insertion in the failed insert attempt
        cursor.execute(queries.VOLUNTEER_UPSERT_FEEDBACK, (event_id, volunteer_id, rating, comments))

    flash('Feedback saved successfully.', 'success')
    return redirect(url_for('volunteer_events', tab='past'))
