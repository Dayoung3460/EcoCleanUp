from flask import Flask
from datetime import datetime

app = Flask(__name__)

# Set the secret key for the session encryption
app.secret_key = 'EcoCleanUpSecretKey'


@app.context_processor
def inject_current_year():
    """Inject the current year into all template contexts."""
    return {'current_year': datetime.now().year}

# Set up database connection.
from ecoapp import connect
from ecoapp import db
db.init_db(app, connect.dbuser, connect.dbpass, connect.dbhost, connect.dbname,
           connect.dbport)

from ecoapp import user
from ecoapp import volunteer
from ecoapp import event_leader
from ecoapp import admin