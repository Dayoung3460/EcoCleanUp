"""SQL query constants for shared user routes."""

USER_VOLUNTEER_LOGIN_REMINDERS = """
SELECT
    e.event_name,
    e.event_date,
    e.start_time,
    e.location,
    er.leader_reminder_message
FROM eventregistrations er
JOIN events e ON e.event_id = er.event_id
WHERE er.volunteer_id = %s
  AND er.registration_status = 'active'
  AND e.is_cancelled = FALSE
  AND e.event_date >= CURRENT_DATE
ORDER BY e.event_date, e.start_time NULLS LAST;
"""

USER_PUBLIC_HOME_IMPACT_STATS = """
SELECT
    (
        SELECT COUNT(*)
        FROM events
        WHERE is_cancelled = FALSE
          AND event_date >= CURRENT_DATE
    ) AS upcoming_events,
    (SELECT COUNT(*) FROM users WHERE role = 'volunteer') AS total_volunteers,
    (
        SELECT COUNT(*)
        FROM feedback
    ) AS total_feedback_submissions,
    (
        SELECT COALESCE(SUM(bags_collected), 0)
        FROM eventoutcomes
    ) AS total_bags_collected;
"""

USER_LOGIN_ACCOUNT_BY_USERNAME = """
SELECT user_id, username, password_hash, role, status
FROM users
WHERE username = %s;
"""

USER_SIGNUP_USERNAME_EXISTS = "SELECT user_id FROM users WHERE username = %s;"

USER_SIGNUP_EMAIL_EXISTS = "SELECT user_id FROM users WHERE email = %s;"

USER_SIGNUP_INSERT = """
INSERT INTO users (
    username, email, password_hash, role, status,
    full_name, home_address, contact_number, environmental_interests, profile_image
)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
"""

USER_PROFILE_BY_ID = """
SELECT
    username, email, role, status,
    full_name, home_address, contact_number,
    environmental_interests, profile_image
FROM users
WHERE user_id = %s;
"""

USER_PROFILE_IMAGE_BY_ID = "SELECT profile_image FROM users WHERE user_id = %s;"

USER_PROFILE_UPDATE = """
UPDATE users
SET full_name = %s,
    home_address = %s,
    contact_number = %s,
    environmental_interests = %s,
    profile_image = %s
WHERE user_id = %s;
"""

USER_PASSWORD_HASH_BY_ID = "SELECT password_hash FROM users WHERE user_id = %s;"

USER_PASSWORD_UPDATE = "UPDATE users SET password_hash = %s WHERE user_id = %s;"
