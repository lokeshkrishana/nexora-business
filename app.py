
import os
from datetime import datetime, timezone
from functools import wraps

from flask import (
    Flask,
    render_template,
    redirect,
    url_for,
    flash,
    request,
    jsonify,
)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    login_required,
    logout_user,
    current_user,
)
from flask_wtf import FlaskForm, CSRFProtect
from wtforms import StringField, PasswordField, SelectField, TextAreaField
from wtforms.validators import DataRequired, Email, Length
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError


# --------------------------------------------------
# Application configuration
# --------------------------------------------------

app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-only-change-this-key")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL", "sqlite:///nexora.db"
).replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = (
    os.environ.get("COOKIE_SECURE", "false").lower() == "true"
)

db = SQLAlchemy(app)

csrf = CSRFProtect(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message_category = "info"


# --------------------------------------------------
# Database models
# --------------------------------------------------

class Inquiry(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), nullable=False)
    service = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)

    status = db.Column(db.String(30), nullable=False, default="New")

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


class AdminUser(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(
        db.String(80),
        unique=True,
        nullable=False,
    )

    password_hash = db.Column(db.String(255), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


# --------------------------------------------------
# Login manager
# --------------------------------------------------

@login_manager.user_loader
def load_user(user_id):
    try:
        return db.session.get(AdminUser, int(user_id))
    except (ValueError, TypeError):
        return None


# --------------------------------------------------
# Forms and CSRF protection
# --------------------------------------------------

class ContactForm(FlaskForm):
    name = StringField(
        "Name",
        validators=[
            DataRequired(),
            Length(min=2, max=100),
        ],
    )

    email = StringField(
        "Email",
        validators=[
            DataRequired(),
            Email(),
            Length(max=150),
        ],
    )

    service = SelectField(
        "Service",
        choices=[
            ("Web Development", "Web Development"),
            ("UI/UX Design", "UI/UX Design"),
            ("Business Consulting", "Business Consulting"),
            ("Digital Marketing", "Digital Marketing"),
            ("Other", "Other"),
        ],
        validators=[DataRequired()],
    )

    message = TextAreaField(
        "Message",
        validators=[
            DataRequired(),
            Length(min=10, max=5000),
        ],
    )


class LoginForm(FlaskForm):
    username = StringField(
        "Username",
        validators=[
            DataRequired(),
            Length(max=80),
        ],
    )

    password = PasswordField(
        "Password",
        validators=[DataRequired()],
    )


class StatusForm(FlaskForm):
    status = SelectField(
        "Status",
        choices=[
            ("New", "New"),
            ("In Progress", "In Progress"),
            ("Completed", "Completed"),
        ],
        validators=[DataRequired()],
    )


class DeleteForm(FlaskForm):
    pass


class LogoutForm(FlaskForm):
    pass


# --------------------------------------------------
# Public website
# --------------------------------------------------

@app.route("/")
def home():
    contact_form = ContactForm()

    return render_template(
        "index.html",
        contact_form=contact_form,
    )


@app.route("/contact", methods=["POST"])
def contact():
    form = ContactForm()

    if not form.validate_on_submit():
        flash(
            "Please check your details and try submitting the form again.",
            "error",
        )
        return redirect(url_for("home") + "#contact")

    inquiry = Inquiry(
        name=form.name.data.strip(),
        email=form.email.data.strip(),
        service=form.service.data,
        message=form.message.data.strip(),
        status="New",
    )

    try:
        db.session.add(inquiry)
        db.session.commit()

        flash(
            "Thank you! Your inquiry has been submitted successfully.",
            "success",
        )

    except SQLAlchemyError:
        db.session.rollback()
        app.logger.exception("Failed to save contact inquiry.")

        flash(
            "Sorry, we could not submit your inquiry. Please try again later.",
            "error",
        )

    return redirect(url_for("home") + "#contact")


# --------------------------------------------------
# Admin login
# --------------------------------------------------

@app.route("/admin/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    form = LoginForm()

    if form.validate_on_submit():
        username = form.username.data.strip()

        admin = AdminUser.query.filter_by(
            username=username
        ).first()

        if admin and admin.check_password(form.password.data):
            login_user(admin)

            flash("Login successful.", "success")

            next_page = request.args.get("next")

            # Only allow local application paths.
            if next_page and next_page.startswith("/") and not next_page.startswith("//"):
                return redirect(next_page)

            return redirect(url_for("dashboard"))

        flash("Invalid username or password.", "error")

    return render_template(
        "login.html",
        form=form,
    )


# --------------------------------------------------
# Admin logout
# --------------------------------------------------

@app.route("/admin/logout", methods=["POST"])
@login_required
def logout():
    form = LogoutForm()

    if form.validate_on_submit():
        logout_user()
        flash("You have been logged out.", "success")
        return redirect(url_for("login"))

    flash("Invalid logout request. Please try again.", "error")
    return redirect(url_for("dashboard"))


# --------------------------------------------------
# Admin dashboard
# --------------------------------------------------

@app.route("/admin")
@login_required
def dashboard():
    total = Inquiry.query.count()

    new_count = Inquiry.query.filter_by(
        status="New"
    ).count()

    inquiries = Inquiry.query.order_by(
        Inquiry.created_at.desc()
    ).all()

    return render_template(
        "admin.html",
        inquiries=inquiries,
        total=total,
        new_count=new_count,
        status_form=StatusForm(),
        delete_form=DeleteForm(),
        logout_form=LogoutForm(),
    )


# --------------------------------------------------
# Update inquiry status
# --------------------------------------------------

@app.route(
    "/admin/inquiry/<int:inquiry_id>/status",
    methods=["POST"],
)
@login_required
def update_status(inquiry_id):
    form = StatusForm()

    if not form.validate_on_submit():
        flash("Please select a valid inquiry status.", "error")
        return redirect(url_for("dashboard"))

    inquiry = db.session.get(Inquiry, inquiry_id)

    if inquiry is None:
        flash("Inquiry not found.", "error")
        return redirect(url_for("dashboard"))

    inquiry.status = form.status.data

    try:
        db.session.commit()
        flash("Inquiry status updated.", "success")

    except SQLAlchemyError:
        db.session.rollback()
        app.logger.exception("Failed to update inquiry status.")
        flash("Could not update the inquiry. Please try again.", "error")

    return redirect(url_for("dashboard"))


# --------------------------------------------------
# Delete inquiry
# --------------------------------------------------

@app.route(
    "/admin/inquiry/<int:inquiry_id>/delete",
    methods=["POST"],
)
@login_required
def delete_inquiry(inquiry_id):
    form = DeleteForm()

    if not form.validate_on_submit():
        flash("Invalid request. Please try again.", "error")
        return redirect(url_for("dashboard"))

    inquiry = db.session.get(Inquiry, inquiry_id)

    if inquiry is None:
        flash("Inquiry not found.", "error")
        return redirect(url_for("dashboard"))

    try:
        db.session.delete(inquiry)
        db.session.commit()
        flash("Inquiry deleted successfully.", "success")

    except SQLAlchemyError:
        db.session.rollback()
        app.logger.exception("Failed to delete inquiry.")
        flash("Could not delete the inquiry. Please try again.", "error")

    return redirect(url_for("dashboard"))


# --------------------------------------------------
# Health check
# --------------------------------------------------

@app.route("/health")
def health():
    try:
        db.session.execute(db.select(func.count()).select_from(Inquiry))
        return jsonify({
            "status": "healthy",
            "database": "connected",
        }), 200

    except SQLAlchemyError:
        db.session.rollback()

        return jsonify({
            "status": "unhealthy",
            "database": "disconnected",
        }), 503


# --------------------------------------------------
# Database initialization
# --------------------------------------------------

def initialize_database():
    with app.app_context():
        db.create_all()

        admin_username = os.environ.get("ADMIN_USERNAME")
        admin_password = os.environ.get("ADMIN_PASSWORD")

        if admin_username and admin_password:
            existing_admin = AdminUser.query.filter_by(
                username=admin_username
            ).first()

            if not existing_admin:
                if len(admin_password) < 12:
                    raise RuntimeError(
                        "ADMIN_PASSWORD must contain at least 12 characters."
                    )

                admin = AdminUser(username=admin_username)
                admin.set_password(admin_password)

                db.session.add(admin)
                db.session.commit()


# Initialize database when Flask imports this application.
initialize_database()


# --------------------------------------------------
# Run locally
# --------------------------------------------------

if __name__ == "__main__":
    app.run(
        debug=os.environ.get("FLASK_DEBUG") == "1"
    )
