# EcoCleanUp
Live URL:
`https://2dayoungkim1171294.pythonanywhere.com/home`

## 1) Project Setup (Local / for macOS users)

### Prerequisites
- Python 3.11+ (or your installed Python 3 version)
- PostgreSQL
- `pip3`

### Step 1: Clone the repository
```bash
git clone https://github.com/Dayoung3460/EcoCleanUp.git

cd EcoCleanUp
```

### Step 2: Create and activate a virtual environment
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Step 3: Install dependencies
```bash
pip3 install -r requirements.txt
```

### Step 4: Configure database connection
Create `ecoapp/connect.py` on your own machine and add your local PostgreSQL details.

Example:
```python
dbhost = "localhost"
dbport = "5432"
dbname = "ecocleanup"
dbuser = "your_username"
dbpass = "your_password"
```

### Step 5: Create schema and seed data
Run the SQL files in this order:
1. `create_database.sql`
2. `populate_database.sql`

### Step 6: Run the app
```bash
python3 run.py
```

Open your browser and go to:
`http://127.0.0.1:5000`

## 2) How to Use the Application

### Login and role access
- All users log in through the same login page.
- Available roles:
  - **Volunteer**
  - **Event Leader**
  - **Admin**

### Volunteer signup
- New users can sign up as volunteers.

### Typical workflow
1. Sign up (volunteer) or log in with an existing account.
2. Browse upcoming events.
3. Register for an event.
4. Attend event and submit feedback.

## 3) Deployment (PythonAnywhere)

1. Create a new PostgreSQL database in PythonAnywhere.
2. Upload or clone this repository on PythonAnywhere.
3. Create or update `ecoapp/connect.py` with PythonAnywhere database credentials.
4. Run SQL scripts (`create_database.sql`, then `populate_database.sql`) against the PythonAnywhere PostgreSQL database.
5. Configure the PythonAnywhere web app (WSGI) to serve the Flask app.
6. Reload the web app and test login for each role.

## 4) Test Data

### Sample login accounts
- Volunteer: `maya_green`
- Event Leader: `leader_hana`
- Admin: `admin_nora`

### Password pattern
Use:
`Welcome1!<username>`

Examples:
- `maya_green` → `Welcome1!maya_green`
- `leader_hana` → `Welcome1!leader_hana`
- `admin_nora` → `Welcome1!admin_nora`
