"""Shared authentication, authorization, and profile routes for all user roles."""

from functools import wraps
import os
import re
import time

from flask import (
    flash,
    redirect,
    render_template,
    request,
    session, # loggedin, user_id, username, role
    url_for,
)

from flask_bcrypt import Bcrypt
from werkzeug.utils import secure_filename

from ecoapp import app
from ecoapp import db
from ecoapp.queries import user_queries as queries

flask_bcrypt = Bcrypt(app)

DEFAULT_USER_ROLE = "volunteer"
DEFAULT_USER_STATUS = "active"
ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif", "svg"}
DEFAULT_PROFILE_IMAGE = "default-profile.svg" # static/profile_images/default-profile.svg

MAX_FULL_NAME_LENGTH = 100
MIN_CONTACT_NUMBER_DIGITS = 7
MAX_CONTACT_NUMBER_DIGITS = 20
FULL_NAME_ALLOWED_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ' -]+")
MAX_HOME_ADDRESS_LENGTH = 255
MAX_ENVIRONMENTAL_INTERESTS_LENGTH = 255


def user_home_url():
    """Return the correct home URL based on the current logged-in user's role."""
    if "loggedin" in session:
        role = session.get("role")
        if role == "volunteer":
            return url_for("volunteer_home")
        if role == "event_leader":
            return url_for("event_leader_home")
        if role == "admin":
            return url_for("admin_home")
        return url_for("logout")
    return url_for("home")


def clear_auth_session():
    """Remove authentication-related keys from session state."""
    for key in ("loggedin", "user_id", "username", "role"):
        session.pop(key, None)


# view_func: route handler function(eg,. profile, update_profile, change_password)
def login_required(view_func):
    """Ensure a user is logged in before allowing access to a view function."""
    # preserve the original function's metadata
    @wraps(view_func)
    # *args: accept any number of positional arguments as a tuple. **kwargs: accept any number of keyword arguments as a dictionary.
    def wrapped(*args, **kwargs):
        """Redirect unauthenticated users to login, otherwise call the wrapped view."""
        if "loggedin" not in session:
            return redirect(url_for("login"))
        # if user is logged in, call the original view function
        return view_func(*args, **kwargs)

    return wrapped


def roles_required(*allowed_roles):
    """Restrict access to users whose role is included in allowed_roles."""
    # view_func: route handler function(eg,. volunteer_home, event_leader_home, admin_home)
    def decorator(view_func):
        """Wrap a view function with role-based authorization checks."""
        @wraps(view_func)
        def wrapped(*args, **kwargs):
            """Block unauthenticated users and deny requests with disallowed roles."""
            if "loggedin" not in session:
                return redirect(url_for("login"))
            if session.get("role") not in allowed_roles:
                # return tuple of (response body, http status code)
                # 403 Forbidden - refuses to authorize it.
                return render_template("private/access_denied.html"), 403
            return view_func(*args, **kwargs)

        return wrapped

    return decorator

# requirement: Passwords must be at least 8 characters long with a mix of character types.
def is_valid_password(password):
    """Return True when a password satisfies the required strength rules."""
    if len(password) < 8:
        return False
    if not re.search(r"[A-Z]", password):
        return False
    if not re.search(r"[a-z]", password):
        return False
    if not re.search(r"[0-9]", password):
        return False
    if not re.search(r"[^A-Za-z0-9]", password):
        return False
    return True


def password_error_message(password):
    """Return a validation message when a password is invalid, otherwise None."""
    if is_valid_password(password):
        return None
    return (
        "Password must be at least 8 characters and include uppercase, lowercase, "
        "number, and special character."
    )


def is_valid_full_name(full_name):
    """
    Validate full names with letters plus optional spaces, apostrophes, and hyphens.
    Digits and symbols such as ! or ? are rejected.
    """
    if not full_name or len(full_name) > MAX_FULL_NAME_LENGTH:
        return False

    if not FULL_NAME_ALLOWED_RE.fullmatch(full_name):
        return False

    connectors = {" ", "-", "'"}
    if full_name[0] in connectors or full_name[-1] in connectors:
        return False

    has_letter = False
    previous_was_connector = False
    for char in full_name:
        if char.isalpha():
            has_letter = True
            previous_was_connector = False
        elif char in connectors:
            if previous_was_connector:
                return False
            previous_was_connector = True
        else:
            return False

    return has_letter


def full_name_error_message(full_name):
    """Return a user-facing validation message for full_name, or None when valid."""
    if not full_name:
        return "Full name is required."
    if len(full_name) > MAX_FULL_NAME_LENGTH:
        return f"Full name cannot exceed {MAX_FULL_NAME_LENGTH} characters."
    if not is_valid_full_name(full_name):
        return "Full name can contain letters, spaces, apostrophes, and hyphens only."
    return None


def normalise_contact_number(contact_number):
    """normalise phone formatting by removing spaces and hyphens before storage."""
    return contact_number.replace(" ", "").replace("-", "")


def is_valid_contact_number(contact_number):
    """
    Validate contact numbers using digits with optional spaces or hyphens.
    Letters and other symbols are rejected.
    """
    if not contact_number:
        return False
    if not re.fullmatch(r"[0-9 -]+", contact_number):
        return False

    normalised = normalise_contact_number(contact_number)
    if not normalised.isdigit():
        return False

    return MIN_CONTACT_NUMBER_DIGITS <= len(normalised) <= MAX_CONTACT_NUMBER_DIGITS


def contact_number_error_message(contact_number):
    """Return a user-facing validation message for contact_number, or None when valid."""
    if not contact_number:
        return "Contact number is required."
    if not re.fullmatch(r"[0-9 -]+", contact_number):
        return "Contact number can only include digits, spaces, and hyphens."

    normalised = normalise_contact_number(contact_number)
    if not normalised.isdigit():
        return "Contact number can only include digits, spaces, and hyphens."
    if not (MIN_CONTACT_NUMBER_DIGITS <= len(normalised) <= MAX_CONTACT_NUMBER_DIGITS):
        return (
            f"Contact number must contain {MIN_CONTACT_NUMBER_DIGITS} to "
            f"{MAX_CONTACT_NUMBER_DIGITS} digits."
        )
    return None


def home_address_error_message(home_address):
    """Return a user-facing validation message for home_address, or None when valid."""
    if not home_address:
        return "Home address is required."
    if len(home_address) > MAX_HOME_ADDRESS_LENGTH:
        return f"Home address cannot exceed {MAX_HOME_ADDRESS_LENGTH} characters."
    return None


def environmental_interests_error_message(environmental_interests):
    """Return a validation message for environmental_interests, or None when valid."""
    if not environmental_interests:
        return "Environmental interests are required."
    if len(environmental_interests) > MAX_ENVIRONMENTAL_INTERESTS_LENGTH:
        return (
            "Environmental interests cannot exceed "
            f"{MAX_ENVIRONMENTAL_INTERESTS_LENGTH} characters."
        )
    return None


def allowed_file(filename):
    """Check whether a filename has an allowed profile image extension."""
    if not filename or "." not in filename:
        return False
    # rsplit(".", 1) → split from the right, max 1 split
    return filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS

def save_profile_image(file_storage):
    """Validate and save an uploaded profile image, returning the stored filename."""
    if file_storage is None or file_storage.filename == "":
        return None

    if not allowed_file(file_storage.filename):
        return None

    # app.root_path: "ecoapp"
    # upload_folder: ".../ecoapp/static/profile_images"
    upload_folder = os.path.join(app.root_path, "static", "profile_images")
    # exist_ok=True: If the directory already exists, do not raise an error
    os.makedirs(upload_folder, exist_ok=True)

    safe_name = secure_filename(file_storage.filename)
    # Unique file name with timestamp prefix
    file_name = f"{int(time.time())}_{safe_name}"
    destination = os.path.join(upload_folder, file_name)
    # file_storage is a FileStorage object, which has a save() method that saves the file to the specified location.
    file_storage.save(destination)
    return file_name


def profile_image_path(image_name):
    """
    Build the absolute path for a stored profile image filename.
    All profile images are saved under static/profile_images.
    """
    return os.path.join(app.root_path, "static", "profile_images", image_name)


def remove_profile_image_file(image_name):
    """Delete a stored profile image file unless it is the default placeholder."""
    if not image_name or image_name == DEFAULT_PROFILE_IMAGE:
        return

    image_path = profile_image_path(image_name)
    if os.path.exists(image_path):
        os.remove(image_path)


# requirement: Volunteers must receive reminders (via notification popup on login) of any upcoming event they have registered for.
def send_volunteer_login_reminders(volunteer_id):
    """Flash upcoming event reminders and leader notices for a volunteer on login."""
    # with: context manager that automatically manages the database cursor, ensuring it is properly closed after use, even if an error occurs.
    with db.get_cursor() as cursor:
        cursor.execute(queries.USER_VOLUNTEER_LOGIN_REMINDERS, (volunteer_id,))
        reminders = cursor.fetchall()

    if not reminders:
        return

    reminder_parts = []
    leader_notice_parts = []
    for event in reminders:
        start_time = event["start_time"].strftime("%H:%M") if event["start_time"] else "TBA"
        reminder_parts.append(
            f"{event['event_name']} ({event['event_date']} {start_time}, {event['location']})"
        )

        leader_message = (event.get("leader_reminder_message") or "").strip()
        if leader_message:
            leader_notice_parts.append(
                f"{event['event_name']}: {leader_message}"
            )

    if reminder_parts:
        # Keep reminders in a dedicated category so they can be shown in a popup modal.
        flash("Upcoming events: " + " | ".join(reminder_parts), "reminder")

    if leader_notice_parts:
        flash("Leader reminders: " + " | ".join(leader_notice_parts), "reminder")


def public_home_impact_stats():
    """Return platform metrics shown on the public home page impact section."""
    with db.get_cursor() as cursor:
        cursor.execute(queries.USER_PUBLIC_HOME_IMPACT_STATS)
        return cursor.fetchone()


@app.route("/")
def root():
    """Redirect the root URL to the appropriate role-aware home destination."""
    return redirect(user_home_url())


@app.route("/home")
def home():
    """Render the public home page or redirect logged-in users to their dashboard."""
    if "loggedin" in session:
        return redirect(user_home_url())
    # why not return redirect(url_for("home"))?
    # Because it will cause an infinite redirect loop.
    # url_for("home") will generate the URL for the home() function, which is "/home".
    impact_stats = public_home_impact_stats()
    return render_template("public/home.html", impact_stats=impact_stats)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Authenticate users, initialize session data, and route them to role home pages."""
    if "loggedin" in session:
        return redirect(user_home_url())

    if request.method == "POST" and "username" in request.form and "password" in request.form:
        username = request.form["username"].strip()
        # no strip() for password, because leading/trailing spaces may be intentional
        password = request.form["password"]

        with db.get_cursor() as cursor:
            cursor.execute(queries.USER_LOGIN_ACCOUNT_BY_USERNAME, (username,))
            account = cursor.fetchone()

        if account is None:
            return render_template("public/login.html", username=username, username_invalid=True)

        if account["status"] != "active":
            return render_template(
                "public/login.html",
                username=username,
                account_inactive=True,
            )

        # checks if the provided password matches the stored password hash for the account.
        if not flask_bcrypt.check_password_hash(account["password_hash"], password):
            return render_template("public/login.html", username=username, password_invalid=True)

        session["loggedin"] = True
        session["user_id"] = account["user_id"]
        session["username"] = account["username"]
        session["role"] = account["role"]

        if account["role"] == "volunteer":
            send_volunteer_login_reminders(account["user_id"])

        return redirect(user_home_url())

    return render_template("public/login.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    """Register a new volunteer account after validating input and uniqueness rules."""
    if "loggedin" in session:
        return redirect(user_home_url())

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        full_name = request.form.get("full_name", "").strip()
        home_address = request.form.get("home_address", "").strip()
        contact_number = request.form.get("contact_number", "").strip()
        environmental_interests = request.form.get("environmental_interests", "").strip()

        username_error = None
        email_error = None
        password_error = None
        full_name_error = None
        home_address_error = None
        contact_number_error = None
        environmental_interests_error = None
        profile_image_error = None

        if not username:
            username_error = "Username is required."
        elif len(username) > 50:
            username_error = "Username cannot exceed 50 characters."
        # "+" means "one or more of the preceding element"
        elif not re.fullmatch(r"[A-Za-z0-9_]+", username):
            username_error = "Username can only include letters, numbers, and underscore."

        if not email:
            email_error = "Email is required."
        elif len(email) > 100 or not re.fullmatch(r"[^@]+@[^@]+\.[^@]+", email):
            email_error = "Please enter a valid email address."

        password_error = password_error_message(password)
        if confirm_password != password and not password_error:
            password_error = "Password and confirmation do not match."

        full_name_error = full_name_error_message(full_name)

        home_address_error = home_address_error_message(home_address)

        contact_number_error = contact_number_error_message(contact_number)

        environmental_interests_error = environmental_interests_error_message(environmental_interests)

        profile_image_filename = DEFAULT_PROFILE_IMAGE
        if "profile_image" in request.files and request.files["profile_image"].filename:
            # uploaded: werkzeug.datastructures.FileStorage object, represents an uploaded file in Flask
            uploaded = request.files["profile_image"]
            profile_image_filename = save_profile_image(uploaded)
            if profile_image_filename is None:
                profile_image_error = "Profile image must be png, jpg, jpeg, webp, gif, or svg."

        with db.get_cursor() as cursor:
            cursor.execute(queries.USER_SIGNUP_USERNAME_EXISTS, (username,))
            if cursor.fetchone() is not None:
                username_error = "An account already exists with this username."

            cursor.execute(queries.USER_SIGNUP_EMAIL_EXISTS, (email,))
            if cursor.fetchone() is not None:
                email_error = "An account already exists with this email address."

        if (
            username_error
            or email_error
            or password_error
            or full_name_error
            or home_address_error
            or contact_number_error
            or environmental_interests_error
            or profile_image_error
        ):
            return render_template(
                "public/signup.html",
                username=username,
                email=email,
                full_name=full_name,
                home_address=home_address,
                contact_number=contact_number,
                environmental_interests=environmental_interests,
                username_error=username_error,
                email_error=email_error,
                password_error=password_error,
                full_name_error=full_name_error,
                home_address_error=home_address_error,
                contact_number_error=contact_number_error,
                environmental_interests_error=environmental_interests_error,
                profile_image_error=profile_image_error,
            )

        contact_number_for_db = normalise_contact_number(contact_number)
        password_hash = flask_bcrypt.generate_password_hash(password).decode("utf-8")

        with db.get_cursor() as cursor:
            cursor.execute(
                queries.USER_SIGNUP_INSERT,
                (
                    username,
                    email,
                    password_hash,
                    DEFAULT_USER_ROLE,
                    DEFAULT_USER_STATUS,
                    full_name,
                    home_address,
                    contact_number_for_db,
                    environmental_interests,
                    profile_image_filename,
                ),
            )

        flash("Registration successful. You can now log in.", "success")
        return redirect(url_for("login"))

    return render_template("public/signup.html")


@app.route("/profile")
# decorator that checks if user is logged in before allowing access to the profile page.
# passing the profile function to the login_required decorator 
@login_required 
def profile():
    """Display the current user's profile details and resolved profile image."""
    with db.get_cursor() as cursor:
        cursor.execute(queries.USER_PROFILE_BY_ID, (session["user_id"],))
        profile_data = cursor.fetchone()

    if profile_data is not None:
        image_name = profile_data.get("profile_image") or DEFAULT_PROFILE_IMAGE
        image_path = profile_image_path(image_name)
        if not os.path.exists(image_path):
            image_name = DEFAULT_PROFILE_IMAGE
        profile_data["profile_image"] = image_name

    return render_template("private/profile.html", profile=profile_data)


@app.route("/profile/update", methods=["POST"])
@login_required
def update_profile():
    """
    Update editable profile fields and image settings in one request.
    Users can upload a new image or remove the current one back to default.
    """
    full_name = request.form.get("full_name", "").strip()
    home_address = request.form.get("home_address", "").strip()
    contact_number = request.form.get("contact_number", "").strip()
    environmental_interests = request.form.get("environmental_interests", "").strip()
    remove_image_requested = request.form.get("remove_profile_image") == "1"

    if not full_name or not home_address or not contact_number or not environmental_interests:
        flash("Full name, address, contact number, and interests are required.", "danger")
        return redirect(url_for("profile"))

    full_name_error = full_name_error_message(full_name)
    if full_name_error:
        flash(full_name_error, "danger")
        return redirect(url_for("profile"))

    contact_number_error = contact_number_error_message(contact_number)
    if contact_number_error:
        flash(contact_number_error, "danger")
        return redirect(url_for("profile"))
    contact_number_for_db = normalise_contact_number(contact_number)

    home_address_error = home_address_error_message(home_address)
    if home_address_error:
        flash(home_address_error, "danger")
        return redirect(url_for("profile"))

    environmental_interests_error = environmental_interests_error_message(environmental_interests)
    if environmental_interests_error:
        flash(environmental_interests_error, "danger")
        return redirect(url_for("profile"))

    uploaded_image = request.files.get("profile_image")
    has_uploaded_image = uploaded_image is not None and uploaded_image.filename != ""
    if remove_image_requested and has_uploaded_image:
        flash("Choose either image upload or image removal, not both.", "danger")
        return redirect(url_for("profile"))

    profile_image_update = None
    if has_uploaded_image:
        profile_image_update = save_profile_image(uploaded_image)
        if profile_image_update is None:
            flash("Profile image must be png, jpg, jpeg, webp, gif, or svg.", "danger")
            return redirect(url_for("profile"))

    previous_image_name = DEFAULT_PROFILE_IMAGE
    with db.get_cursor() as cursor:
        cursor.execute(queries.USER_PROFILE_IMAGE_BY_ID, (session["user_id"],))
        account = cursor.fetchone()
        if account is None:
            flash("Account not found.", "danger")
            return redirect(url_for("logout"))

        previous_image_name = account.get("profile_image") or DEFAULT_PROFILE_IMAGE
        profile_image_target = previous_image_name

        if remove_image_requested:
            profile_image_target = DEFAULT_PROFILE_IMAGE
        if profile_image_update is not None:
            profile_image_target = profile_image_update

        cursor.execute(
            queries.USER_PROFILE_UPDATE,
            (
                full_name,
                home_address,
                contact_number_for_db,
                environmental_interests,
                profile_image_target,
                session["user_id"],
            ),
        )

    if profile_image_target != previous_image_name:
        remove_profile_image_file(previous_image_name)

    flash("Profile updated successfully.", "success")
    return redirect(url_for("profile"))


@app.route("/profile/change-password", methods=["POST"])
@login_required
def change_password():
    """
    Change the current user's password with full server-side validation.
    The new password must differ from the existing hash and pass policy checks.
    """
    current_password = request.form.get("current_password", "")
    new_password = request.form.get("new_password", "")
    confirm_new_password = request.form.get("confirm_new_password", "")

    with db.get_cursor() as cursor:
        cursor.execute(queries.USER_PASSWORD_HASH_BY_ID, (session["user_id"],))
        account = cursor.fetchone()

    if account is None or not flask_bcrypt.check_password_hash(account["password_hash"], current_password):
        flash("Current password is incorrect.", "danger")
        return redirect(url_for("profile"))

    if new_password != confirm_new_password:
        flash("New password and confirmation do not match.", "danger")
        return redirect(url_for("profile"))

    if flask_bcrypt.check_password_hash(account["password_hash"], new_password):
        flash("New password must be different from your current password.", "danger")
        return redirect(url_for("profile"))

    pwd_error = password_error_message(new_password)
    if pwd_error:
        flash(pwd_error, "danger")
        return redirect(url_for("profile"))

    new_hash = flask_bcrypt.generate_password_hash(new_password).decode("utf-8")
    with db.get_cursor() as cursor:
        cursor.execute(queries.USER_PASSWORD_UPDATE, (new_hash, session["user_id"]))

    flash("Your password has been changed. For security, please log in again.", "success")
    clear_auth_session()
    return redirect(url_for("login"))


@app.route("/logout")
def logout():
    """Clear authentication-related session keys and redirect to the login page."""
    clear_auth_session()

    return redirect(url_for("login"))

@app.route("/debug-session")
def debug_session():
    """Print session data in debug mode and block access in non-debug environments."""
    if not app.debug:
        return "Not available", 403

    print(dict(session))
    return "Check your terminal"
