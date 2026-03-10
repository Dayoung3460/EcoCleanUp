"""SQL query constants for admin routes."""

ADMIN_HOME_USERS_SUMMARY = """
SELECT
    COUNT(*) FILTER (WHERE role = 'volunteer') AS volunteer_count,
    COUNT(*) FILTER (WHERE role = 'event_leader') AS event_leader_count,
    COUNT(*) FILTER (WHERE role = 'admin') AS admin_count,
    COUNT(*) FILTER (WHERE status = 'active') AS active_user_count,
    COUNT(*) FILTER (WHERE status = 'inactive') AS inactive_user_count
FROM users;
"""

ADMIN_HOME_TOTAL_EVENTS = "SELECT COUNT(*) AS total_events FROM events;"

ADMIN_HOME_TOTAL_FEEDBACK = "SELECT COUNT(*) AS total_feedback FROM feedback;"

ADMIN_USERS_SELECT = """
SELECT
    u.user_id,
    u.username,
    u.full_name,
    u.email,
    u.role,
    u.status,
    u.created_at
FROM users u
{where_clause}
ORDER BY u.full_name, u.username;
"""

ADMIN_USER_PROFILE_BY_ID = """
SELECT
    user_id,
    username,
    full_name,
    email,
    contact_number,
    home_address,
    environmental_interests,
    profile_image,
    role,
    status,
    created_at
FROM users
WHERE user_id = %s;
"""

ADMIN_USER_ATTENDED_EVENTS_COUNT = """
SELECT COUNT(DISTINCT event_id) AS total
FROM eventregistrations
WHERE volunteer_id = %s
  AND attendance = 'present';
"""

ADMIN_USER_MANAGED_EVENTS_COUNT = """
SELECT COUNT(*) AS total
FROM events
WHERE event_leader_id = %s;
"""

ADMIN_UPDATE_USER_STATUS = "UPDATE users SET status = %s WHERE user_id = %s;"

ADMIN_EVENTS_LIST = """
SELECT
    e.event_id,
    e.event_name,
    e.location,
    e.event_type,
    e.event_date,
    e.start_time,
    e.end_time,
    e.duration,
    e.is_cancelled,
    leader.full_name AS event_leader_name,
    COUNT(er.registration_id) AS registrations,
    COUNT(er.registration_id) FILTER (WHERE er.attendance = 'present') AS present_count
FROM events e
JOIN users leader ON leader.user_id = e.event_leader_id
LEFT JOIN eventregistrations er
  ON er.event_id = e.event_id
 AND er.registration_status = 'active'
GROUP BY e.event_id, leader.full_name
ORDER BY e.event_date DESC, e.start_time DESC NULLS LAST;
"""

ADMIN_EDIT_EVENT_BY_ID = """
SELECT
    e.event_id,
    e.event_name,
    e.location,
    e.event_type,
    e.event_date,
    e.start_time,
    e.end_time,
    e.duration,
    e.description,
    e.supplies,
    e.safety_instructions,
    leader.full_name AS event_leader_name
FROM events e
JOIN users leader ON leader.user_id = e.event_leader_id
WHERE e.event_id = %s
  AND e.is_cancelled = FALSE;
"""

ADMIN_UPDATE_EVENT = """
UPDATE events
SET event_name = %s,
    location = %s,
    event_type = %s,
    event_date = %s,
    start_time = %s,
    end_time = %s,
    duration = %s,
    description = %s,
    supplies = %s,
    safety_instructions = %s
WHERE event_id = %s
  AND is_cancelled = FALSE;
"""

ADMIN_CANCEL_EVENT = """
UPDATE events
SET is_cancelled = TRUE,
    cancelled_at = CURRENT_TIMESTAMP,
    cancelled_by = %s
WHERE event_id = %s
  AND is_cancelled = FALSE;
"""

ADMIN_PLATFORM_EVENTS_SUMMARY = """
SELECT
    COUNT(*) AS total_events,
    COUNT(*) FILTER (WHERE event_date >= CURRENT_DATE) AS upcoming_events,
    COUNT(*) FILTER (WHERE event_date < CURRENT_DATE) AS past_events
FROM events;
"""

ADMIN_PLATFORM_USERS_SUMMARY = """
SELECT
    COUNT(*) FILTER (WHERE role = 'volunteer') AS total_volunteers,
    COUNT(*) FILTER (WHERE role = 'event_leader') AS total_event_leaders,
    COUNT(*) FILTER (WHERE role = 'admin') AS total_admins,
    COUNT(*) FILTER (WHERE status = 'active') AS total_active_users,
    COUNT(*) FILTER (WHERE status = 'inactive') AS total_inactive_users
FROM users;
"""

ADMIN_PLATFORM_FEEDBACK_SUMMARY = """
SELECT
    COUNT(*) AS total_feedback_submissions,
    ROUND(AVG(rating)::numeric, 2) AS avg_event_rating
FROM feedback;
"""

ADMIN_PLATFORM_REGISTRATIONS_SUMMARY = """
SELECT
    COUNT(*) AS total_registrations,
    COUNT(*) FILTER (WHERE attendance = 'present') AS total_attendance_present,
    COUNT(*) FILTER (WHERE attendance = 'absent') AS total_attendance_absent,
    COUNT(*) FILTER (WHERE attendance = 'pending') AS total_attendance_pending
FROM eventregistrations
WHERE registration_status = 'active';
"""

ADMIN_EVENT_REPORT_ROWS = """
SELECT
    e.event_id,
    e.event_name,
    e.event_date,
    e.location,
    e.event_type,
    leader.full_name AS event_leader_name,
    COALESCE(er_sum.registrations, 0) AS registrations,
    COALESCE(er_sum.attendees, 0) AS attendees,
    COALESCE(er_sum.absentees, 0) AS absentees,
    COALESCE(eo.bags_collected, 0) AS bags_collected,
    COALESCE(eo.recyclables_sorted, 0) AS recyclables_sorted,
    COALESCE(eo.other_achievements, '') AS other_achievements,
    f_sum.avg_rating AS avg_rating,
    COALESCE(f_sum.feedback_count, 0) AS feedback_count
FROM events e
JOIN users leader ON leader.user_id = e.event_leader_id
LEFT JOIN (
    SELECT
        event_id,
        COUNT(*) AS registrations,
        COUNT(*) FILTER (WHERE attendance = 'present') AS attendees,
        COUNT(*) FILTER (WHERE attendance = 'absent') AS absentees
    FROM eventregistrations
    WHERE registration_status = 'active'
    GROUP BY event_id
) er_sum ON er_sum.event_id = e.event_id
LEFT JOIN eventoutcomes eo ON eo.event_id = e.event_id
LEFT JOIN (
    SELECT
        event_id,
        ROUND(AVG(rating)::numeric, 2) AS avg_rating,
        COUNT(*) AS feedback_count
    FROM feedback
    GROUP BY event_id
) f_sum ON f_sum.event_id = e.event_id
ORDER BY e.event_date DESC, e.start_time DESC NULLS LAST;
"""
