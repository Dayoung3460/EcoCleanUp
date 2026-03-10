"""Admin routes for user management, event operations, and reporting views."""

import csv
import io
import os
from datetime import date

from flask import Response, flash, redirect, render_template, request, session, url_for
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from ecoapp import app
from ecoapp import db
from ecoapp.queries import admin_queries as queries
from ecoapp.utils import parse_event_form, split_events_by_tab, validate_event_form
from ecoapp.user import DEFAULT_PROFILE_IMAGE, profile_image_path, roles_required


@app.route('/admin/home')
@roles_required('admin')
def admin_home():
    """Render the admin dashboard with user, event, and feedback summary metrics."""
    with db.get_cursor() as cursor:
        cursor.execute(queries.ADMIN_HOME_USERS_SUMMARY)
        users_summary = cursor.fetchone()

        cursor.execute(queries.ADMIN_HOME_TOTAL_EVENTS)
        total_events = cursor.fetchone()['total_events']

        cursor.execute(queries.ADMIN_HOME_TOTAL_FEEDBACK)
        total_feedback = cursor.fetchone()['total_feedback']

    return render_template(
        'private/admin_home.html',
        users_summary=users_summary,
        total_events=total_events,
        total_feedback=total_feedback,
    )


@app.route('/admin/users')
@roles_required('admin')
def admin_users():
    """Display the admin user list with optional search and filter conditions."""
    search = request.args.get('search', '').strip()
    role_filter = request.args.get('role', '').strip()
    status_filter = request.args.get('status', '').strip()

    conditions = []
    params = []

    if search:
        conditions.append("(u.username ILIKE %s OR u.full_name ILIKE %s)")
        params.extend([f"%{search}%", f"%{search}%"])

    if role_filter in ('volunteer', 'event_leader', 'admin'):
        conditions.append("u.role = %s")
        params.append(role_filter)

    if status_filter in ('active', 'inactive'):
        conditions.append("u.status = %s")
        params.append(status_filter)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    with db.get_cursor() as cursor:
        cursor.execute(
            queries.ADMIN_USERS_SELECT.format(where_clause=where_clause),
            tuple(params),
        )
        users = cursor.fetchall()

    return render_template(
        'private/admin_users.html',
        users=users,
        search=search,
        role_filter=role_filter,
        status_filter=status_filter,
    )


@app.route('/admin/users/<int:user_id>/profile')
@roles_required('admin')
def admin_view_user_profile(user_id):
    """Show detailed profile information for a selected user."""
    back_args = {
        'search': request.args.get('search', '').strip(),
        'role': request.args.get('role', '').strip(),
        'status': request.args.get('status', '').strip(),
    }

    with db.get_cursor() as cursor:
        cursor.execute(queries.ADMIN_USER_PROFILE_BY_ID, (user_id,))
        user_profile = cursor.fetchone()

        if user_profile is None:
            flash('User not found.', 'danger')
            return redirect(url_for('admin_users', **back_args))

        if user_profile['role'] == 'volunteer':
            cursor.execute(queries.ADMIN_USER_ATTENDED_EVENTS_COUNT, (user_id,))
            user_profile['attended_events'] = cursor.fetchone()['total']
        elif user_profile['role'] == 'event_leader':
            cursor.execute(queries.ADMIN_USER_MANAGED_EVENTS_COUNT, (user_id,))
            user_profile['managed_events'] = cursor.fetchone()['total']

    image_name = user_profile.get('profile_image') or DEFAULT_PROFILE_IMAGE
    if not os.path.exists(profile_image_path(image_name)):
        image_name = DEFAULT_PROFILE_IMAGE
    user_profile['profile_image'] = image_name

    return render_template(
        'private/admin_user_profile.html',
        user_profile=user_profile,
        back_args=back_args,
    )


@app.route('/admin/users/<int:user_id>/status', methods=['POST'])
@roles_required('admin')
def admin_update_user_status(user_id):
    """Update a user's status and return to the current filtered user list."""
    new_status = request.form.get('status', '').strip()
    
    # The redirect preserves current list filters so admins return to the same
    # filtered user view after submitting the status change form. This prevents
    # losing search and filter context during repeated user management actions.
    redirect_args = {
        'search': request.form.get('search', '').strip(),
        'role': request.form.get('role_filter', '').strip(),
        'status': request.form.get('status_filter', '').strip(),
    }

    if new_status not in ('active', 'inactive'):
        flash('Invalid status value.', 'danger')
        return redirect(url_for('admin_users', **redirect_args))

    if user_id == session.get('user_id') and new_status == 'inactive':
        flash('You cannot deactivate your own admin account.', 'warning')
        return redirect(url_for('admin_users', **redirect_args))

    with db.get_cursor() as cursor:
        cursor.execute(queries.ADMIN_UPDATE_USER_STATUS, (new_status, user_id))
        if cursor.rowcount == 0:
            flash('User not found.', 'danger')
            return redirect(url_for('admin_users', **redirect_args))

    flash('User status updated successfully.', 'success')
    return redirect(url_for('admin_users', **redirect_args))


@app.route('/admin/events')
@roles_required('admin')
def admin_events():
    """Render event lists for admins by selected tab: today, upcoming, past, or cancelled."""
    selected_tab = request.args.get('tab', 'today')
    if selected_tab not in ('today', 'upcoming', 'past', 'cancelled'):
        selected_tab = 'today'

    with db.get_cursor() as cursor:
        cursor.execute(queries.ADMIN_EVENTS_LIST)
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
        'private/admin_events.html',
        events=visible_events,
        selected_tab=selected_tab,
        today_count=len(today_events),
        upcoming_count=len(upcoming_events),
        past_count=len(past_events),
        cancelled_count=len(cancelled_events),
    )


@app.route('/admin/events/<int:event_id>/edit')
@roles_required('admin')
def admin_edit_event_form(event_id):
    """Render the edit form for an active event chosen by the admin."""
    with db.get_cursor() as cursor:
        cursor.execute(queries.ADMIN_EDIT_EVENT_BY_ID, (event_id,))
        event = cursor.fetchone()

    if event is None:
        flash('Event not found or already cancelled.', 'danger')
        return redirect(url_for('admin_events'))

    edit_date_min = date.today().isoformat() if event['event_date'] >= date.today() else None

    return render_template(
        'private/event_edit.html',
        event=event,
        edit_date_min=edit_date_min,
        active_page='admin_events',
        form_endpoint='admin_update_event',
        cancel_endpoint='admin_events',
    )


@app.route('/admin/events/<int:event_id>/update', methods=['POST'])
@roles_required('admin')
def admin_update_event(event_id):
    """Validate submitted data and update an active event record."""
    event_data = parse_event_form(request.form)
    event_validation_error = validate_event_form(event_data)
    if event_validation_error:
        flash(event_validation_error, 'danger')
        return redirect(url_for('admin_edit_event_form', event_id=event_id))

    with db.get_cursor() as cursor:
        cursor.execute(
            queries.ADMIN_UPDATE_EVENT,
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
            ),
        )

        if cursor.rowcount == 0:
            flash('Event not found or already cancelled.', 'danger')
            return redirect(url_for('admin_events'))

    flash('Event updated successfully.', 'success')
    return redirect(url_for('admin_events'))


@app.route('/admin/events/<int:event_id>/cancel', methods=['POST'])
@roles_required('admin')
def admin_cancel_event(event_id):
    """Mark an event as cancelled and track cancellation metadata."""
    with db.get_cursor() as cursor:
        cursor.execute(queries.ADMIN_CANCEL_EVENT, (session['user_id'], event_id))

        if cursor.rowcount == 0:
            flash('Event not found or already cancelled.', 'danger')
            return redirect(url_for('admin_events'))

    flash('Event cancelled successfully.', 'warning')
    return redirect(url_for('admin_events'))


@app.route('/admin/reports/platform')
@roles_required('admin')
def admin_platform_report():
    """Generate platform-level summary metrics for the admin reporting page."""
    with db.get_cursor() as cursor:
        cursor.execute(queries.ADMIN_PLATFORM_EVENTS_SUMMARY)
        events_summary = cursor.fetchone()

        cursor.execute(queries.ADMIN_PLATFORM_USERS_SUMMARY)
        users_summary = cursor.fetchone()

        cursor.execute(queries.ADMIN_PLATFORM_FEEDBACK_SUMMARY)
        feedback_summary = cursor.fetchone()

        cursor.execute(queries.ADMIN_PLATFORM_REGISTRATIONS_SUMMARY)
        registrations_summary = cursor.fetchone()

    return render_template(
        'private/admin_platform_report.html',
        events_summary=events_summary,
        users_summary=users_summary,
        feedback_summary=feedback_summary,
        registrations_summary=registrations_summary,
    )

@app.route('/admin/reports/events')
@roles_required('admin')
def admin_event_report():
    """Generate event-level outcome, attendance, and feedback report data."""
    report_rows = _fetch_admin_event_report_rows()
    return render_template('private/admin_event_report.html', report_rows=report_rows)


def _fetch_admin_event_report_rows():
    """Fetch event report rows used by admin HTML, CSV, and PDF outputs."""
    with db.get_cursor() as cursor:
        cursor.execute(queries.ADMIN_EVENT_REPORT_ROWS)
        report_rows = cursor.fetchall()

    return report_rows


@app.route('/admin/reports/events/export.csv')
@roles_required('admin')
def admin_event_report_export_csv():
    """Download the admin event report as a CSV file."""
    report_rows = _fetch_admin_event_report_rows()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(
        [
            'Event',
            'Date',
            'Event Leader',
            'Registrations',
            'Attendees',
            'Absentees',
            'Bags Collected',
            'Recyclables Sorted',
            'Other Achievements',
            'Average Rating',
            'Feedback Count',
        ]
    )

    for row in report_rows:
        writer.writerow(
            [
                row['event_name'],
                row['event_date'],
                row['event_leader_name'],
                row['registrations'],
                row['attendees'],
                row['absentees'],
                row['bags_collected'],
                row['recyclables_sorted'],
                row['other_achievements'] or '-',
                f"{row['avg_rating']}/5" if row['avg_rating'] is not None else '-',
                row['feedback_count'],
            ]
        )

    filename = f"admin_event_report_{date.today().isoformat()}.csv"
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename={filename}',
        },
    )


@app.route('/admin/reports/events/export.pdf')
@roles_required('admin')
def admin_event_report_export_pdf():
    """Download the admin event report as a PDF file."""
    report_rows = _fetch_admin_event_report_rows()

    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        pdf_buffer,
        pagesize=landscape(letter),
        leftMargin=24,
        rightMargin=24,
        topMargin=24,
        bottomMargin=24,
    )
    styles = getSampleStyleSheet()

    elements = [
        Paragraph('EcoCleanUp Hub - Admin Event Report', styles['Title']),
        Spacer(1, 8),
        Paragraph(
            f"Generated on {date.today().isoformat()}",
            styles['Normal'],
        ),
        Spacer(1, 12),
    ]

    table_data = [
        [
            'Event',
            'Date',
            'Leader',
            'Registrations',
            'Attendees',
            'Absentees',
            'Bags',
            'Recyclables',
            'Avg Rating',
        ]
    ]

    for row in report_rows:
        table_data.append(
            [
                row['event_name'],
                str(row['event_date']),
                row['event_leader_name'],
                row['registrations'],
                row['attendees'],
                row['absentees'],
                row['bags_collected'],
                row['recyclables_sorted'],
                f"{row['avg_rating']}/5" if row['avg_rating'] is not None else '-',
            ]
        )

    report_table = Table(table_data, repeatRows=1)
    report_table.setStyle(
        TableStyle(
            [
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#198754')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('ALIGN', (3, 1), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#adb5bd')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]
        )
    )
    elements.append(report_table)

    doc.build(elements)
    pdf_buffer.seek(0)

    filename = f"admin_event_report_{date.today().isoformat()}.pdf"
    return Response(
        pdf_buffer.getvalue(),
        mimetype='application/pdf',
        headers={
            'Content-Disposition': f'attachment; filename={filename}',
        },
    )
