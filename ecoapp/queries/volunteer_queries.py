"""SQL query constants for volunteer routes."""

VOLUNTEER_HOME_EVENT_STATS = """
SELECT
    COUNT(*) FILTER (
        WHERE er.registration_status = 'active'
          AND e.event_date >= CURRENT_DATE
    ) AS upcoming_count,
    COUNT(*) FILTER (
        WHERE er.registration_status = 'active'
          AND e.event_date < CURRENT_DATE
          AND er.attendance = 'present'
    ) AS attended_past_count,
    COUNT(*) FILTER (
        WHERE er.registration_status = 'active'
          AND er.attendance = 'pending'
    ) AS attendance_pending_count,
    COUNT(*) FILTER (
        WHERE er.registration_status = 'active'
          AND e.event_date <= CURRENT_DATE
          AND er.attendance = 'absent'
    ) AS absent_count
FROM eventregistrations er
JOIN events e ON e.event_id = er.event_id
WHERE er.volunteer_id = %s;
"""

VOLUNTEER_HOME_PENDING_FEEDBACK = """
SELECT COUNT(*) AS pending_feedback_count
FROM eventregistrations er
JOIN events e ON e.event_id = er.event_id
LEFT JOIN feedback f
    ON f.event_id = er.event_id
    AND f.volunteer_id = er.volunteer_id
WHERE er.volunteer_id = %s
  AND er.registration_status = 'active'
  AND e.event_date <= CURRENT_DATE
  AND er.attendance = 'present'
  AND f.feedback_id IS NULL;
"""

VOLUNTEER_HOME_FEEDBACK_SUBMITTED = """
SELECT COUNT(*) AS feedback_submitted_count FROM feedback WHERE volunteer_id = %s;
"""

VOLUNTEER_BROWSE_EVENTS = """
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
    u.full_name AS event_leader_name
FROM events e
JOIN users u ON u.user_id = e.event_leader_id
WHERE {where_sql}
ORDER BY e.event_date, e.start_time NULLS LAST;
"""

VOLUNTEER_REGISTERED_EVENT_IDS = """
SELECT event_id
FROM eventregistrations
WHERE volunteer_id = %s
  AND registration_status = 'active';
"""

VOLUNTEER_EVENT_BY_ID = """
SELECT event_id, event_name, event_date, start_time, end_time
FROM events
WHERE event_id = %s AND is_cancelled = FALSE;
"""

VOLUNTEER_REGISTRATION_BY_EVENT_AND_USER = """
SELECT registration_id, registration_status
FROM eventregistrations
WHERE event_id = %s AND volunteer_id = %s;
"""

VOLUNTEER_REACTIVATE_REGISTRATION = """
UPDATE eventregistrations
SET registration_status = 'active',
    attendance = 'pending',
    registered_at = CURRENT_TIMESTAMP
WHERE registration_id = %s;
"""

VOLUNTEER_CONFLICT_EVENT = """
SELECT e.event_name, e.event_date, e.start_time, e.end_time
FROM eventregistrations er
JOIN events e ON e.event_id = er.event_id
WHERE er.volunteer_id = %s
  AND er.registration_status = 'active'
  AND e.event_id <> %s
  AND e.event_date = %s
  AND e.start_time IS NOT NULL
  AND e.end_time IS NOT NULL
  AND (e.start_time, e.end_time) OVERLAPS (%s::time, %s::time)
LIMIT 1;
"""

VOLUNTEER_INSERT_REGISTRATION = """
INSERT INTO eventregistrations (event_id, volunteer_id, attendance)
VALUES (%s, %s, 'pending');
"""

VOLUNTEER_MY_EVENTS = """
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
    e.is_cancelled,
    leader.full_name AS event_leader_name,
    er.attendance,
    er.registered_at,
    f.rating,
    f.comments,
    f.submitted_at
FROM eventregistrations er
JOIN events e ON e.event_id = er.event_id
JOIN users leader ON leader.user_id = e.event_leader_id
LEFT JOIN feedback f
    ON f.event_id = er.event_id
    AND f.volunteer_id = er.volunteer_id
WHERE er.volunteer_id = %s
  AND er.registration_status = 'active'
ORDER BY e.event_date ASC, e.start_time ASC NULLS LAST;
"""

VOLUNTEER_FEEDBACK_PARTICIPATION_CHECK = """
SELECT e.event_id, e.event_date, er.attendance
FROM events e
JOIN eventregistrations er ON er.event_id = e.event_id
WHERE e.event_id = %s
  AND er.volunteer_id = %s
  AND er.registration_status = 'active';
"""

VOLUNTEER_UPSERT_FEEDBACK = """
INSERT INTO feedback (event_id, volunteer_id, rating, comments, submitted_at)
VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
ON CONFLICT (event_id, volunteer_id)
DO UPDATE SET
    rating = EXCLUDED.rating,
    comments = EXCLUDED.comments,
    submitted_at = CURRENT_TIMESTAMP;
"""
