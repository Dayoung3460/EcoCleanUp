"""Database connection helpers for PostgreSQL access within Flask request context."""

from flask import Flask, g
import psycopg2
import psycopg2.extras

connection_params = {}

def init_db(app: Flask, user: str, password: str, host: str, database: str,
            port: int = 5432, autocommit: bool = True):
    """Store DB connection settings and register teardown cleanup for Flask."""

    connection_params['user'] = user
    connection_params['password'] = password
    connection_params['host'] = host
    connection_params['database'] = database
    connection_params['port'] = port
    connection_params['autocommit'] = autocommit
    
    app.teardown_appcontext(close_db)

def get_db():
    """Return a request-scoped database connection, creating it if needed."""
    if 'db' not in g:
        conn = psycopg2.connect(
            user=connection_params['user'],
            password=connection_params['password'],
            host=connection_params['host'],
            dbname=connection_params['database'],
            port=connection_params['port']
        )
        conn.autocommit = connection_params.get('autocommit', True)
        g.db = conn

    return g.db

def get_cursor():
    """Return a RealDictCursor from the current request-scoped DB connection."""
    return get_db().cursor(cursor_factory=psycopg2.extras.RealDictCursor)

def close_db(exception = None):
    """Close and remove the request-scoped database connection from Flask g."""
    db = g.pop('db', None)
    
    if db is not None:
        db.close()
