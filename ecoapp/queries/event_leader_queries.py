"""SQL query constants for event leader routes."""

LEADER_HOME_COUNTS = """
SELECT
    COUNT(*) FILTER (WHERE event_date >= CURRENT_DATE) AS upcoming_events,
    COUNT(*) FILTER (WHERE event_date < CURRENT_DATE) AS past_events,
    COUNT(*) AS my_events
FROM events
WHERE event_leader_id = %s;
"""

LEADER_HOME_VOLUNTEER_SIGNUPS = """
SELECT COUNT(*) AS total
FROM eventregistrations er
JOIN events e ON e.event_id = er.event_id
WHERE e.event_leader_id = %s
  AND er.registration_status = 'active';
"""

LEADER_HOME_FEEDBACK_COUNT = """
SELECT COUNT(*) AS total
FROM feedback f
JOIN events e ON e.event_id = f.event_id
WHERE e.event_leader_id = %s;
"""

LEADER_EVENTS_LIST = """
SELECT
    e.event_id,
    e.event_name,
    e.location,
    e.event_type,
    e.event_date,
    e.start_time,
    e.end_time,
    e.is_cancelled,
    CASE WHEN e.event_date < CURRENT_DATE THEN TRUE ELSE FALSE END AS is_past,
    e.duration,
    e.description,
    e.supplies,
    e.safety_instructions,
    COUNT(er.registration_id) AS registrations,
    COUNT(er.registration_id) FILTER (WHERE er.attendance = 'present') AS present_count
FROM events e
LEFT JOIN eventregistrations er
  ON er.event_id = e.event_id
 AND er.registration_status = 'active'
WHERE e.event_leader_id = %s
GROUP BY e.event_id
ORDER BY e.event_date DESC, e.start_time DESC NULLS LAST;
"""

LEADER_CREATE_EVENT = """
INSERT INTO events (
    event_name, event_leader_id, location, event_type, event_date,
    start_time, end_time, duration, description, supplies, safety_instructions
)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
"""

LEADER_UPDATE_EVENT = """
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
  AND event_leader_id = %s;
"""

LEADER_EDIT_EVENT_BY_ID = """
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
  AND e.event_leader_id = %s;
"""

LEADER_CANCEL_EVENT = """
UPDATE events
SET is_cancelled = TRUE,
    cancelled_at = CURRENT_TIMESTAMP,
    cancelled_by = %s
WHERE event_id = %s
  AND event_leader_id = %s
  AND is_cancelled = FALSE;
"""

LEADER_EVENT_BY_ID_FOR_OWNER = """
SELECT
    e.event_id,
    e.event_name,
    e.event_date,
    e.start_time,
    e.end_time,
    leader.full_name AS event_leader_name
FROM events e
JOIN users leader ON leader.user_id = e.event_leader_id
WHERE e.event_id = %s AND e.event_leader_id = %s;
"""

LEADER_EVENT_BY_ID_FOR_ADMIN = """
SELECT
    e.event_id,
    e.event_name,
    e.event_date,
    e.start_time,
    e.end_time,
    leader.full_name AS event_leader_name
FROM events e
JOIN users leader ON leader.user_id = e.event_leader_id
WHERE e.event_id = %s;
"""

LEADER_EVENT_VOLUNTEERS = """
SELECT
    er.registration_id,
    er.volunteer_id,
    er.attendance,
    er.registered_at,
    u.full_name,
    u.username,
    u.email,
    u.contact_number
FROM eventregistrations er
JOIN users u ON u.user_id = er.volunteer_id
WHERE er.event_id = %s
  AND er.registration_status = 'active'
ORDER BY u.full_name;
"""

LEADER_EVENT_OUTCOME_BY_EVENT_ID = """
SELECT
    num_attendees,
    bags_collected,
    recyclables_sorted,
    other_achievements
FROM eventoutcomes
WHERE event_id = %s;
"""

LEADER_EVENT_OWNERSHIP_CHECK = """
SELECT event_id FROM events WHERE event_id = %s AND event_leader_id = %s;
"""

LEADER_REMOVE_VOLUNTEER = """
UPDATE eventregistrations
SET registration_status = 'removed',
    attendance = 'pending'
WHERE event_id = %s
  AND volunteer_id = %s
  AND registration_status = 'active';
"""

LEADER_UPDATE_ATTENDANCE = """
UPDATE eventregistrations
SET attendance = %s
WHERE registration_id = %s
  AND event_id = %s
  AND registration_status = 'active';
"""

LEADER_PRESENT_ATTENDEES_COUNT = """
SELECT COUNT(*) AS present_count
FROM eventregistrations
WHERE event_id = %s
  AND attendance = 'present'
  AND registration_status = 'active';
"""

LEADER_UPSERT_EVENT_OUTCOME = """
INSERT INTO eventoutcomes (
    event_id, num_attendees, bags_collected, recyclables_sorted,
    other_achievements, recorded_by, recorded_at
)
VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
ON CONFLICT (event_id)
DO UPDATE SET
    num_attendees = EXCLUDED.num_attendees,
    bags_collected = EXCLUDED.bags_collected,
    recyclables_sorted = EXCLUDED.recyclables_sorted,
    other_achievements = EXCLUDED.other_achievements,
    recorded_by = EXCLUDED.recorded_by,
    recorded_at = CURRENT_TIMESTAMP;
"""

LEADER_FEEDBACK_ROWS_BASE = """
SELECT
    f.feedback_id,
    f.event_id,
    e.event_name,
    e.event_date,
    u.full_name AS volunteer_name,
    f.rating,
    f.comments,
    f.submitted_at
FROM feedback f
JOIN events e ON e.event_id = f.event_id
JOIN users u ON u.user_id = f.volunteer_id
WHERE {where_clause}
ORDER BY f.submitted_at DESC;
"""

LEADER_EVENT_REPORT_ROWS = """
SELECT
    e.event_id,
    e.event_name,
    e.event_date,
    e.location,
    e.event_type,
    COALESCE(er_sum.registrations, 0) AS registrations,
    COALESCE(er_sum.attendees, 0) AS attendees,
    COALESCE(er_sum.absentees, 0) AS absentees,
    COALESCE(eo.bags_collected, 0) AS bags_collected,
    COALESCE(eo.recyclables_sorted, 0) AS recyclables_sorted,
    COALESCE(eo.other_achievements, '') AS other_achievements,
    f_sum.avg_rating AS avg_rating,
    COALESCE(f_sum.feedback_count, 0) AS feedback_count
FROM events e
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
WHERE e.event_leader_id = %s
ORDER BY e.event_date DESC, e.start_time DESC NULLS LAST;
"""

LEADER_PARTICIPATION_HISTORY_ROWS = """
SELECT
    u.user_id AS volunteer_id,
    u.full_name AS volunteer_name,
    u.username AS volunteer_username,
    e.event_id,
    e.event_name,
    e.event_date,
    e.start_time,
    e.end_time,
    er.attendance,
    er.registered_at,
    eo.num_attendees,
    eo.bags_collected,
    eo.recyclables_sorted,
    eo.other_achievements
FROM eventregistrations er
JOIN events e ON e.event_id = er.event_id
JOIN users u ON u.user_id = er.volunteer_id
LEFT JOIN eventoutcomes eo ON eo.event_id = e.event_id
WHERE e.event_leader_id = %s
  AND er.registration_status = 'active'
ORDER BY u.full_name, e.event_date DESC, e.start_time DESC NULLS LAST;
"""

LEADER_PARTICIPATION_SUMMARY_ROWS = """
SELECT
    u.user_id AS volunteer_id,
    u.full_name AS volunteer_name,
    u.username AS volunteer_username,
    COUNT(*) AS total_events,
    COUNT(*) FILTER (WHERE er.attendance = 'present') AS present_count,
    COUNT(*) FILTER (WHERE er.attendance = 'absent') AS absent_count,
    COUNT(*) FILTER (WHERE er.attendance = 'pending') AS pending_count,
    MAX(e.event_date) AS latest_event_date
FROM eventregistrations er
JOIN events e ON e.event_id = er.event_id
JOIN users u ON u.user_id = er.volunteer_id
WHERE e.event_leader_id = %s
  AND er.registration_status = 'active'
GROUP BY u.user_id, u.full_name, u.username
ORDER BY u.full_name;
"""

LEADER_REMINDER_TARGET = """
SELECT e.event_name, COUNT(er.registration_id) AS volunteer_count
FROM events e
LEFT JOIN eventregistrations er
  ON er.event_id = e.event_id
 AND er.registration_status = 'active'
WHERE e.event_id = %s
  AND e.event_leader_id = %s
  AND e.is_cancelled = FALSE
  AND e.event_date >= CURRENT_DATE
GROUP BY e.event_id;
"""

LEADER_SEND_REMINDER = """
UPDATE eventregistrations
SET leader_reminder_message = %s,
    leader_reminder_sent_at = CURRENT_TIMESTAMP,
    leader_reminder_sent_by = %s
WHERE event_id = %s
  AND registration_status = 'active';
"""
