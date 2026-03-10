
-- cascade: delete dependent objects first when dropping tables or types
DROP TABLE IF EXISTS feedback CASCADE;
DROP TABLE IF EXISTS eventoutcomes CASCADE;
DROP TABLE IF EXISTS eventregistrations CASCADE;
DROP TABLE IF EXISTS events CASCADE;
DROP TABLE IF EXISTS users CASCADE;

DROP TYPE IF EXISTS attendance_enum CASCADE;
DROP TYPE IF EXISTS registration_status_enum CASCADE;
DROP TYPE IF EXISTS status_enum CASCADE;
DROP TYPE IF EXISTS role_enum CASCADE;

CREATE TYPE role_enum AS ENUM ('volunteer', 'event_leader', 'admin');
CREATE TYPE status_enum AS ENUM ('active', 'inactive');
CREATE TYPE attendance_enum AS ENUM ('pending', 'present', 'absent');
CREATE TYPE registration_status_enum AS ENUM ('active', 'removed');

CREATE TABLE users (
    user_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    contact_number VARCHAR(20),
    home_address VARCHAR(255),
    profile_image VARCHAR(255),
    environmental_interests VARCHAR(255),
    role role_enum NOT NULL DEFAULT 'volunteer',
    status status_enum DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE events (
    event_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    event_name VARCHAR(100) NOT NULL,
    event_leader_id INTEGER NOT NULL REFERENCES users (user_id),
    location VARCHAR(255) NOT NULL,
    event_type VARCHAR(50),
    event_date DATE NOT NULL,
    start_time TIME,
    end_time TIME,
    duration INTEGER,
    description TEXT,
    supplies TEXT,
    safety_instructions TEXT,
    is_cancelled BOOLEAN NOT NULL DEFAULT FALSE,
    cancelled_at TIMESTAMP,
    cancelled_by INTEGER REFERENCES users (user_id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE eventregistrations (
    registration_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    event_id INTEGER NOT NULL REFERENCES events (event_id) ON DELETE CASCADE,
    volunteer_id INTEGER NOT NULL REFERENCES users (user_id) ON DELETE CASCADE,
    attendance attendance_enum DEFAULT 'pending',
    registration_status registration_status_enum NOT NULL DEFAULT 'active',
    leader_reminder_message TEXT,
    leader_reminder_sent_at TIMESTAMP,
    leader_reminder_sent_by INTEGER REFERENCES users (user_id),
    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (event_id, volunteer_id)
);

CREATE TABLE eventoutcomes (
    outcome_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    event_id INTEGER NOT NULL UNIQUE REFERENCES events (event_id) ON DELETE CASCADE,
    num_attendees INTEGER,
    bags_collected INTEGER,
    recyclables_sorted INTEGER,
    other_achievements TEXT,
    recorded_by INTEGER NOT NULL REFERENCES users (user_id),
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE feedback (
    feedback_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    event_id INTEGER NOT NULL REFERENCES events (event_id) ON DELETE CASCADE,
    volunteer_id INTEGER NOT NULL REFERENCES users (user_id) ON DELETE CASCADE,
    rating INTEGER CHECK (rating BETWEEN 1 AND 5),
    comments TEXT,
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (event_id, volunteer_id)
);

-- indexes for performance optimization
CREATE INDEX idx_users_role ON users (role);
CREATE INDEX idx_users_status ON users (status);
CREATE INDEX idx_events_leader ON events (event_leader_id);
CREATE INDEX idx_events_date ON events (event_date);
CREATE INDEX idx_events_is_cancelled ON events (is_cancelled);
CREATE INDEX idx_eventregistrations_volunteer ON eventregistrations (volunteer_id);
