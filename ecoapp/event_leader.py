"""Event-leader routes for managing events, volunteers, outcomes, and reminders."""

from datetime import date

from flask import flash, redirect, render_template, request, session, url_for

from ecoapp import app
from ecoapp import db
from ecoapp.queries import event_leader_queries as queries
from ecoapp.utils import (
    EVENT_TEXT_LIMITS,
    _safe_int,
    parse_event_form,
    split_events_by_tab,
    validate_event_form,
)
from ecoapp.user import roles_required

@app.route('/event-leader/home')
@roles_required('event_leader')
def event_leader_home():
    """Render the event leader dashboard with key summary counts."""
    leader_id = session['user_id']

    with db.get_cursor() as cursor:
        cursor.execute(queries.LEADER_HOME_COUNTS, (leader_id,))
        counts = cursor.fetchone()

        cursor.execute(queries.LEADER_HOME_VOLUNTEER_SIGNUPS, (leader_id,))
        volunteer_signups = cursor.fetchone()['total']

        cursor.execute(queries.LEADER_HOME_FEEDBACK_COUNT, (leader_id,))
        feedback_count = cursor.fetchone()['total']

    return render_template(
        'private/event_leader_home.html',
        counts=counts,
        volunteer_signups=volunteer_signups,
        feedback_count=feedback_count,
    )


@app.route('/event-leader/events')
@roles_required('event_leader')
def leader_events():
    """Display the leader's events grouped by today, upcoming, past, or cancelled tabs."""
    leader_id = session['user_id']
    selected_tab = request.args.get('tab', 'today')
    if selected_tab not in ('today', 'upcoming', 'past', 'cancelled'):
        selected_tab = 'today'

    with db.get_cursor() as cursor:
        cursor.execute(queries.LEADER_EVENTS_LIST, (leader_id,))
        events = cursor.fetchall()

    event_groups = split_events_by_tab(events, today=date.today())
    today_events = event_groups['today']
    upcoming_events = event_groups['upcoming']
    past_events = event_groups['past']
    cancelled_events = event_groups['cancelled']

    if selected_tab == 'today':
        visible_events = today_events
    elif selected_tab == 'past':
        visible_events = past_events
    elif selected_tab == 'cancelled':
        visible_events = cancelled_events
    else:
        visible_events = upcoming_events

    return render_template(
        'private/leader_events.html',
        events=visible_events,
        selected_tab=selected_tab,
        today_count=len(today_events),
        upcoming_count=len(upcoming_events),
        past_count=len(past_events),
        cancelled_count=len(cancelled_events),
        current_date=date.today().isoformat(),
    )

@app.route('/event-leader/events/create', methods=['POST'])
@roles_required('event_leader')
def create_event():
    """
    Create a new leader-owned event after validating required inputs.
    Time and duration values are validated to prevent invalid schedules.
    """
    event_data = parse_event_form(request.form)
    event_validation_error = validate_event_form(event_data, require_future_date=True)
    if event_validation_error:
        flash(event_validation_error, 'danger')
        return redirect(url_for('leader_events'))

    with db.get_cursor() as cursor:
        cursor.execute(
            queries.LEADER_CREATE_EVENT,
            (
                event_data['event_name'],
                session['user_id'],
                event_data['location'],
                event_data['event_type'],
                event_data['event_date'],
                event_data['start_time'],
                event_data['end_time'],
                event_data['duration'],
                event_data['description'],
                event_data['supplies'],
                event_data['safety_instructions'],
            ),
        )

    flash('Event created successfully.', 'success')
    return redirect(url_for('leader_events'))

@app.route('/event-leader/events/<int:event_id>/update', methods=['POST'])
@roles_required('event_leader')
def update_event(event_id):
    """Validate input and update an event owned by the current leader."""
    leader_id = session['user_id']

    event_data = parse_event_form(request.form)
    event_validation_error = validate_event_form(event_data)
    if event_validation_error:
        flash(event_validation_error, 'danger')
        return redirect(url_for('show_event_edit_form', event_id=event_id))

    with db.get_cursor() as cursor:
        cursor.execute(
            queries.LEADER_UPDATE_EVENT,
            (
                event_data['event_name'],
                event_data['location'],
                event_data['event_type'],
                event_data['event_date'],
                event_data['start_time'],
                event_data['end_time'],
                event_data['duration'],
                event_data['description'],
                event_data['supplies'],
                event_data['safety_instructions'],
                event_id,
                leader_id,
            ),
        )

        if cursor.rowcount == 0:
            flash('Event not found or access denied.', 'danger')
            return redirect(url_for('leader_events'))

    flash('Event updated successfully.', 'success')
    return redirect(url_for('leader_events'))


@app.route('/event-leader/events/<int:event_id>/edit')
@roles_required('event_leader')
def show_event_edit_form(event_id):
    """Render the edit form for a specific event owned by the leader."""
    with db.get_cursor() as cursor:
        cursor.execute(queries.LEADER_EDIT_EVENT_BY_ID, (event_id, session['user_id']))
        event = cursor.fetchone()

    if event is None:
        flash('Event not found or access denied.', 'danger')
        return redirect(url_for('leader_events'))

    # Keep min=today for today/future events to prevent accidental backdating, 
    # and remove min for past events to support natural past date corrections.
    edit_date_min = date.today().isoformat() if event['event_date'] >= date.today() else None

    return render_template(
        'private/event_edit.html',
        event=event,
        edit_date_min=edit_date_min,
        current_date=date.today().isoformat(),
    )


@app.route('/event-leader/events/<int:event_id>/cancel', methods=['POST'])
@roles_required('event_leader')
def cancel_event(event_id):
    """Cancel an event owned by the current leader if it is still active."""
    with db.get_cursor() as cursor:
        cursor.execute(queries.LEADER_CANCEL_EVENT, (session['user_id'], event_id, session['user_id']))
        if cursor.rowcount == 0:
            flash('Event not found, already cancelled, or access denied.', 'danger')
            return redirect(url_for('leader_events'))

    flash('Event cancelled successfully.', 'warning')
    return redirect(url_for('leader_events'))


@app.route('/event-leader/events/<int:event_id>/volunteers')
@roles_required('event_leader', 'admin')
def view_event_volunteers(event_id):
    """Show registered volunteers and outcomes for an event viewable by leader or admin."""
    user_role = session['role']
    source = request.args.get('source', '').strip()

    if user_role == 'admin' and source == 'admin_event_report':
        back_url = url_for('admin_event_report')
    elif user_role == 'admin':
        back_url = url_for('admin_events')
    else:
        back_url = url_for('leader_events')

    with db.get_cursor() as cursor:
        if user_role == 'event_leader':
            cursor.execute(queries.LEADER_EVENT_BY_ID_FOR_OWNER, (event_id, session['user_id']))
        else:
            cursor.execute(queries.LEADER_EVENT_BY_ID_FOR_ADMIN, (event_id,))

        event = cursor.fetchone()
        if event is None:
            flash('Event not found or access denied.', 'danger')
            return redirect(url_for('event_leader_home' if user_role == 'event_leader' else 'admin_events'))

        cursor.execute(queries.LEADER_EVENT_VOLUNTEERS, (event_id,))
        volunteers = cursor.fetchall()

        cursor.execute(queries.LEADER_EVENT_OUTCOME_BY_EVENT_ID, (event_id,))
        outcome = cursor.fetchone()

        present_attendees = sum(1 for v in volunteers if v['attendance'] == 'present')

    return render_template(
        'private/event_volunteers.html',
        event=event,
        volunteers=volunteers,
        outcome=outcome,
        present_attendees=present_attendees,
        is_admin=(user_role == 'admin'),
        back_url=back_url,
    )


@app.route('/event-leader/events/<int:event_id>/volunteers/remove/<int:volunteer_id>', methods=['POST'])
@roles_required('event_leader')
def remove_volunteer(event_id, volunteer_id):
    """Remove an active volunteer registration from a leader-owned event."""
    with db.get_cursor() as cursor:
        cursor.execute(queries.LEADER_EVENT_OWNERSHIP_CHECK, (event_id, session['user_id']))
        if cursor.fetchone() is None:
            flash('Event not found or access denied.', 'danger')
            return redirect(url_for('leader_events'))

        cursor.execute(queries.LEADER_REMOVE_VOLUNTEER, (event_id, volunteer_id))

    flash('Volunteer removed from event.', 'warning')
    return redirect(url_for('view_event_volunteers', event_id=event_id))


@app.route('/event-leader/events/<int:event_id>/attendance', methods=['POST'])
@roles_required('event_leader')
def update_attendance(event_id):
    """Update attendance statuses for active registrations in a leader-owned event."""
    # convert the form data into a dictionary.
    # flat=True: if there are multiple values for the same key, only return the first one.
    attendance_map = request.form.to_dict(flat=True)
    # eg., print(attendance_map) -> {'attendance_29': 'present'}

    with db.get_cursor() as cursor:
        cursor.execute(queries.LEADER_EVENT_OWNERSHIP_CHECK, (event_id, session['user_id']))
        if cursor.fetchone() is None:
            flash('Event not found or access denied.', 'danger')
            return redirect(url_for('leader_events'))

        for key, value in attendance_map.items():
            if not key.startswith('attendance_'):
                continue
            registration_id = _safe_int(key.replace('attendance_', ''), -1)
            if registration_id <= 0:
                continue
            if value not in ('pending', 'present', 'absent'):
                continue

            cursor.execute(queries.LEADER_UPDATE_ATTENDANCE, (value, registration_id, event_id))

    flash('Attendance updated successfully.', 'success')
    return redirect(url_for('view_event_volunteers', event_id=event_id))


@app.route('/event-leader/events/<int:event_id>/outcomes', methods=['POST'])
@roles_required('event_leader')
def save_event_outcomes(event_id):
    """Save or update event outcome metrics for a leader-owned event."""
    num_attendees = _safe_int(request.form.get('num_attendees', 0), 0)
    bags_collected = _safe_int(request.form.get('bags_collected', 0), 0)
    recyclables_sorted = _safe_int(request.form.get('recyclables_sorted', 0), 0)
    other_achievements = request.form.get('other_achievements', '').strip() or None

    if num_attendees < 0 or bags_collected < 0 or recyclables_sorted < 0:
        flash('Outcome values cannot be negative.', 'danger')
        return redirect(url_for('view_event_volunteers', event_id=event_id))

    recorded_by = session['user_id']

    with db.get_cursor() as cursor:
        cursor.execute(queries.LEADER_EVENT_OWNERSHIP_CHECK, (event_id, session['user_id']))
        if cursor.fetchone() is None:
            flash('Event not found or access denied.', 'danger')
            return redirect(url_for('leader_events'))

        cursor.execute(queries.LEADER_PRESENT_ATTENDEES_COUNT, (event_id,))
        present_result = cursor.fetchone()
        present_attendees = present_result['present_count'] if present_result else 0

        cursor.execute(
            queries.LEADER_UPSERT_EVENT_OUTCOME,
            (
                event_id,
                num_attendees,
                bags_collected,
                recyclables_sorted,
                other_achievements,
                recorded_by,
            ),
        )

    if num_attendees != present_attendees:
        flash(
            f"Outcomes saved. Note: Number of Attendees ({num_attendees}) does not match "
            f"attendance Present count ({present_attendees}).",
            'warning',
        )
    else:
        flash('Event outcomes saved.', 'success')
    return redirect(url_for('view_event_volunteers', event_id=event_id))


@app.route('/event-leader/feedback')
@roles_required('event_leader', 'admin')
def review_feedback():
    """Display feedback submissions for leader-owned events or all events for admins."""
    event_query = request.args.get('event', '').strip()
    rating_raw = request.args.get('rating', '').strip()
    rating_filter = _safe_int(rating_raw, 0)
    if rating_filter not in (1, 2, 3, 4, 5):
        rating_filter = 0

    with db.get_cursor() as cursor:
        params = []

        if session['role'] == 'event_leader':
            where_clauses = ['e.event_leader_id = %s']
            params.append(session['user_id'])
        else:
            where_clauses = ['TRUE']

        if event_query:
            where_clauses.append('e.event_name ILIKE %s')
            params.append(f'%{event_query}%')

        if rating_filter:
            where_clauses.append('f.rating = %s')
            params.append(rating_filter)

        query = queries.LEADER_FEEDBACK_ROWS_BASE.format(where_clause=' AND '.join(where_clauses))
        cursor.execute(query, tuple(params))
        feedback_rows = cursor.fetchall()

    return render_template(
        'private/review_feedback.html',
        feedback_rows=feedback_rows,
        is_admin=(session['role'] == 'admin'),
        selected_event_query=event_query,
        selected_rating=rating_filter,
    )


@app.route('/event-leader/reports')
@roles_required('event_leader')
def leader_event_report():
    """Generate event-level report rows for the current event leader."""
    with db.get_cursor() as cursor:
        cursor.execute(queries.LEADER_EVENT_REPORT_ROWS, (session['user_id'],))
        report_rows = cursor.fetchall()

    return render_template('private/leader_event_report.html', report_rows=report_rows)


@app.route('/event-leader/participation-history')
@roles_required('event_leader')
def leader_participation_history():
    """Render detailed and summary volunteer participation history for this leader's events."""
    with db.get_cursor() as cursor:
        cursor.execute(queries.LEADER_PARTICIPATION_HISTORY_ROWS, (session['user_id'],))
        history_rows = cursor.fetchall()

        cursor.execute(queries.LEADER_PARTICIPATION_SUMMARY_ROWS, (session['user_id'],))
        volunteer_summaries = cursor.fetchall()

    return render_template(
        'private/leader_participation_history.html',
        history_rows=history_rows,
        volunteer_summaries=volunteer_summaries,
    )


@app.route('/event-leader/events/<int:event_id>/send-reminder', methods=['POST'])
@roles_required('event_leader')
def send_event_reminder(event_id):
    """Send and store a reminder message for all active registrations of an upcoming event."""
    reminder_message = request.form.get('reminder_message', '').strip()
    if not reminder_message:
        flash('Reminder message is required.', 'danger')
        return redirect(url_for('leader_events'))
    if len(reminder_message) > EVENT_TEXT_LIMITS['reminder_message']:
        flash(
            f"Reminder message cannot exceed {EVENT_TEXT_LIMITS['reminder_message']} characters.",
            'danger',
        )
        return redirect(url_for('leader_events'))

    with db.get_cursor() as cursor:
        cursor.execute(queries.LEADER_REMINDER_TARGET, (event_id, session['user_id']))
        reminder_target = cursor.fetchone()

        if reminder_target is None:
            flash('Event not found, not upcoming, or access denied.', 'danger')
            return redirect(url_for('leader_events'))

        cursor.execute(queries.LEADER_SEND_REMINDER, (reminder_message, session['user_id'], event_id))

    flash(
        f"Reminder sent for '{reminder_target['event_name']}' to {reminder_target['volunteer_count']} registered volunteers.",
        'info',
    )
    return redirect(url_for('leader_events'))
