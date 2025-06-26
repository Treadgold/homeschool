from fastapi import FastAPI, Request, Depends, Form, Path, Response, Cookie, HTTPException, UploadFile, status, Query, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload
from app.database import SessionLocal, engine
from app.models import Base, Event, User, Child, Booking, GalleryImage
from app.config import config
from app.payment_service import get_payment_service
from starlette.status import HTTP_303_SEE_OTHER
from datetime import datetime, timedelta
from passlib.context import CryptContext
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
import os
from fastapi.staticfiles import StaticFiles
import shutil
import uuid
from sqlalchemy.exc import IntegrityError
from starlette.middleware.base import BaseHTTPMiddleware
from typing import List
import smtplib
from email.mime.text import MIMEText
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from authlib.integrations.starlette_client import OAuth
import requests

app = FastAPI()
# Use absolute path for templates to ensure correct resolution in Docker and local dev
templates = Jinja2Templates(directory="app/templates")

# Initialize OAuth
oauth = OAuth()
if config.facebook_oauth_enabled:
    oauth.register(
        name='facebook',
        client_id=config.FACEBOOK_CLIENT_ID,
        client_secret=config.FACEBOOK_CLIENT_SECRET,
        authorize_url='https://www.facebook.com/dialog/oauth',
        access_token_url='https://graph.facebook.com/oauth/access_token',
        client_kwargs={
            'scope': 'email public_profile'
        },
    )

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

# Custom rate limit exceeded handler for HTML responses
async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    return HTMLResponse(
        content=f"""
        <html>
        <head>
            <title>Rate Limit Exceeded - LifeLearners.org.nz</title>
            <style>
                body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
                .error {{ color: #e53e3e; font-size: 1.2em; margin-bottom: 20px; }}
                .message {{ color: #4a5568; margin-bottom: 30px; }}
                .back-link {{ color: #2b6cb0; text-decoration: none; }}
                .back-link:hover {{ text-decoration: underline; }}
            </style>
        </head>
        <body>
            <div class="error">⚠️ Rate Limit Exceeded</div>
            <div class="message">
                You've made too many requests. Please wait a moment before trying again.
            </div>
            <a href="/" class="back-link">← Back to Home</a>
        </body>
        </html>
        """,
        status_code=429
    )

app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# Create tables on startup
Base.metadata.create_all(bind=engine)

# Serve static files (for uploaded images)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
SESSION_COOKIE = "session"
SESSION_MAX_AGE = 60 * 60 * 24 * 30  # 30 days
serializer = URLSafeTimedSerializer(SECRET_KEY)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SMTP_HOST = os.getenv("SMTP_HOST", "mailhog")
SMTP_PORT = int(os.getenv("SMTP_PORT", 1025))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
SITE_URL = os.getenv("SITE_URL", "http://localhost:8000")

def get_password_hash(password):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def create_session_cookie(user_id, max_age=SESSION_MAX_AGE):
    return serializer.dumps({"user_id": user_id})

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(request: Request, db: Session = Depends(get_db), session: str = Cookie(None)):
    if not session:
        return None
    try:
        data = serializer.loads(session, max_age=SESSION_MAX_AGE)
        user = db.query(User).filter(User.id == data["user_id"]).first()
        return user
    except (BadSignature, SignatureExpired):
        return None

def create_email_token(email: str) -> str:
    return serializer.dumps({"email": email}, salt="email-confirm")

def verify_email_token(token: str) -> str:
    try:
        data = serializer.loads(token, salt="email-confirm", max_age=86400)  # 24 hours
        return data["email"]
    except:
        return None

# CSRF token generation and validation
def generate_csrf_token() -> str:
    """Generate a CSRF token for forms"""
    return serializer.dumps({"csrf": "token"}, salt="csrf")

def verify_csrf_token(token: str) -> bool:
    """Verify a CSRF token"""
    try:
        serializer.loads(token, salt="csrf", max_age=3600)  # 1 hour expiry
        return True
    except:
        return False

@app.get("/", response_class=HTMLResponse)
async def landing(request: Request):
    return templates.TemplateResponse("landing.html", {"request": request})

@app.get("/events", response_class=HTMLResponse)
async def events_page(request: Request, db: Session = Depends(get_db)):
    events = db.query(Event).all()
    from datetime import datetime
    now = datetime.utcnow()
    return templates.TemplateResponse("events.html", {"request": request, "events": events, "now": now})

@app.get("/load-message", response_class=HTMLResponse)
async def load_message():
    return "<p>This is a dynamically loaded message using HTMX!</p>"

@app.get("/signup", response_class=HTMLResponse)
async def signup_form(request: Request):
    csrf_token = generate_csrf_token()
    return templates.TemplateResponse("signup.html", {"request": request, "error": None, "csrf_token": csrf_token})

@app.post("/signup", response_class=HTMLResponse)
@limiter.limit("5/minute")
async def signup(request: Request, db: Session = Depends(get_db), email: str = Form(...), password: str = Form(...), honeypot: str = Form(""), csrf_token: str = Form(None)):
    # CSRF check
    if not csrf_token or not verify_csrf_token(csrf_token):
        csrf_token = generate_csrf_token()
        return templates.TemplateResponse("signup.html", {"request": request, "error": "Invalid or missing CSRF token.", "csrf_token": csrf_token})
    # Honeypot check
    if honeypot:
        csrf_token = generate_csrf_token()
        return templates.TemplateResponse("signup.html", {"request": request, "error": "Bot detected.", "csrf_token": csrf_token})
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        csrf_token = generate_csrf_token()
        if existing_user.auth_provider == 'facebook':
            return templates.TemplateResponse("signup.html", {"request": request, "error": "This email is already registered with Facebook. Please use 'Continue with Facebook' to log in.", "csrf_token": csrf_token})
        else:
            return templates.TemplateResponse("signup.html", {"request": request, "error": "Email already registered.", "csrf_token": csrf_token})
    
    user = User(email=email, hashed_password=get_password_hash(password), email_confirmed=False, auth_provider='email')
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Generate confirmation token and send confirmation email
    token = create_email_token(email)
    confirm_url = f"{SITE_URL}/confirm-email/{token}"
    email_body = f"""
    Welcome to LifeLearners!
    
    Please confirm your email address by clicking the link below:
    {confirm_url}
    
    This link will expire in 24 hours.
    
    If you did not sign up for LifeLearners, you can safely ignore this email.
    """
    try:
        send_email(email, "Welcome to LifeLearners - Please Confirm Your Email", email_body)
    except Exception as e:
        print("Email send failed:", e)
        csrf_token = generate_csrf_token()
        return templates.TemplateResponse("signup.html", {
            "request": request, 
            "error": "Failed to send confirmation email. Please try again later.",
            "csrf_token": csrf_token
        })
    
    return templates.TemplateResponse("signup_success.html", {
        "request": request,
        "email": email
    })

@app.get("/confirm-email/{token}", response_class=HTMLResponse)
@limiter.limit("10/minute")
async def confirm_email(request: Request, token: str, db: Session = Depends(get_db)):
    email = verify_email_token(token)
    if not email:
        return templates.TemplateResponse("email_confirmation.html", {
            "request": request,
            "success": False,
            "message": "Invalid or expired confirmation link."
        })
    
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return templates.TemplateResponse("email_confirmation.html", {
            "request": request,
            "success": False,
            "message": "User not found."
        })
    
    if user.email_confirmed:
        return templates.TemplateResponse("email_confirmation.html", {
            "request": request,
            "success": True,
            "message": "Email already confirmed. You can now log in."
        })
    
    user.email_confirmed = True
    db.commit()
    
    return templates.TemplateResponse("email_confirmation.html", {
        "request": request,
        "success": True,
        "message": "Email confirmed successfully! You can now log in."
    })

@app.get("/login", response_class=HTMLResponse)
async def login_form(request: Request):
    csrf_token = generate_csrf_token()
    return templates.TemplateResponse("login.html", {"request": request, "error": None, "csrf_token": csrf_token})

@app.post("/login", response_class=HTMLResponse)
@limiter.limit("10/minute")
async def login(request: Request, db: Session = Depends(get_db), email: str = Form(...), password: str = Form(...), keep_logged_in: str = Form(None), csrf_token: str = Form(None)):
    # CSRF check
    if not csrf_token or not verify_csrf_token(csrf_token):
        csrf_token = generate_csrf_token()
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid or missing CSRF token.", "csrf_token": csrf_token})
    user = db.query(User).filter(User.email == email).first()
    if not user:
        csrf_token = generate_csrf_token()
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid credentials.", "csrf_token": csrf_token})
    
    # Check if this is a Facebook-only user
    if user.auth_provider == 'facebook' and not user.hashed_password:
        csrf_token = generate_csrf_token()
        return templates.TemplateResponse("login.html", {
            "request": request, 
            "error": "This account was created with Facebook. Please use 'Continue with Facebook' to log in.",
            "csrf_token": csrf_token
        })
    
    if not verify_password(password, user.hashed_password):
        csrf_token = generate_csrf_token()
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid credentials.", "csrf_token": csrf_token})
    
    if not user.email_confirmed:
        csrf_token = generate_csrf_token()
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Please confirm your email address before logging in. Check your inbox for the confirmation link.",
            "email": email,
            "csrf_token": csrf_token
        })
    
    response = RedirectResponse(url="/", status_code=HTTP_303_SEE_OTHER)
    max_age = SESSION_MAX_AGE if keep_logged_in else 60 * 60 * 2  # 2 hours if not 'keep me logged in'
    response.set_cookie(SESSION_COOKIE, create_session_cookie(user.id, max_age), max_age=max_age, httponly=True, samesite="lax")
    return response

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/", status_code=HTTP_303_SEE_OTHER)
    response.delete_cookie(SESSION_COOKIE)
    return response

@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """Health check endpoint to verify database connectivity and schema status"""
    try:
        # Basic database connectivity check
        db.execute("SELECT 1")
        
        # Check if Facebook OAuth columns exist
        facebook_columns_exist = True
        try:
            result = db.execute("SELECT facebook_id FROM users LIMIT 1")
        except Exception:
            facebook_columns_exist = False
        
        return {
            "status": "healthy",
            "database": "connected",
            "facebook_oauth_schema": "ready" if facebook_columns_exist else "migration_needed",
            "facebook_oauth_config": "configured" if config.facebook_oauth_enabled else "not_configured"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "error",
            "error": str(e)
        }

# Facebook OAuth Routes
@app.get("/auth/facebook")
async def facebook_login(request: Request):
    if not config.facebook_oauth_enabled:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Facebook login is not configured. Please set FACEBOOK_CLIENT_ID and FACEBOOK_CLIENT_SECRET environment variables.",
            "csrf_token": generate_csrf_token()
        })
    
    try:
        facebook = oauth.create_client('facebook')
        redirect_uri = config.FACEBOOK_REDIRECT_URI
        return await facebook.authorize_redirect(request, redirect_uri)
    except Exception as e:
        print(f"Facebook OAuth initialization error: {e}")
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Facebook login is temporarily unavailable. Please try again later or use email login.",
            "csrf_token": generate_csrf_token()
        })

@app.get("/auth/facebook/callback")
async def facebook_callback(request: Request, db: Session = Depends(get_db)):
    if not config.facebook_oauth_enabled:
        raise HTTPException(status_code=404, detail="Facebook login not configured")
    
    try:
        facebook = oauth.create_client('facebook') 
        token = await facebook.authorize_access_token(request)
        
        # Get user info from Facebook
        user_response = await facebook.get('https://graph.facebook.com/me?fields=id,email,first_name,last_name,picture', token=token)
        facebook_user = user_response.json()
        
        if not facebook_user.get('email'):
            return templates.TemplateResponse("login.html", {
                "request": request,
                "error": "Facebook account must have a verified email address.",
                "csrf_token": generate_csrf_token()
            })
        
        # Check if user exists by Facebook ID (handle missing columns gracefully)
        try:
            user = db.query(User).filter(User.facebook_id == facebook_user['id']).first()
        except Exception as e:
            if "does not exist" in str(e):
                # Database hasn't been migrated yet, fall back to email-only lookup
                user = None
            else:
                raise
        
        if not user:
            # Check if user exists by email (to link accounts)
            user = db.query(User).filter(User.email == facebook_user['email']).first()
            if user:
                # Link existing account to Facebook (if schema supports it)
                try:
                    user.facebook_id = facebook_user['id']
                    user.first_name = facebook_user.get('first_name')
                    user.last_name = facebook_user.get('last_name')
                    user.profile_picture_url = facebook_user.get('picture', {}).get('data', {}).get('url')
                    if hasattr(user, 'auth_provider') and user.auth_provider == 'email':
                        user.auth_provider = 'both'  # User has both email and Facebook auth
                except AttributeError:
                    # Schema doesn't have Facebook fields yet - just log the user in
                    print("Warning: Facebook fields not available in database schema. User logged in with existing account.")
            else:
                # Create new user
                try:
                    user = User(
                        email=facebook_user['email'],
                        facebook_id=facebook_user['id'],
                        first_name=facebook_user.get('first_name'),
                        last_name=facebook_user.get('last_name'),
                        profile_picture_url=facebook_user.get('picture', {}).get('data', {}).get('url'),
                        auth_provider='facebook',
                        email_confirmed=True  # Facebook emails are considered verified
                    )
                except TypeError:
                    # Schema doesn't have Facebook fields yet - create basic user
                    user = User(
                        email=facebook_user['email'],
                        email_confirmed=True  # Facebook emails are considered verified
                    )
                    print("Warning: Created user without Facebook fields. Please run database migration.")
                db.add(user)
        else:
            # Update existing Facebook user info (if schema supports it)
            try:
                user.first_name = facebook_user.get('first_name')
                user.last_name = facebook_user.get('last_name')
                user.profile_picture_url = facebook_user.get('picture', {}).get('data', {}).get('url')
            except AttributeError:
                # Schema doesn't have Facebook fields yet
                print("Warning: Facebook fields not available for update. Please run database migration.")
        
        db.commit()
        db.refresh(user)
        
        # Create session
        response = RedirectResponse(url="/", status_code=HTTP_303_SEE_OTHER)
        response.set_cookie(
            SESSION_COOKIE, 
            create_session_cookie(user.id), 
            max_age=SESSION_MAX_AGE, 
            httponly=True, 
            samesite="lax"
        )
        return response
        
    except Exception as e:
        print(f"Facebook OAuth error: {e}")
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Facebook login failed. Please try again.",
            "csrf_token": generate_csrf_token()
        })

def require_admin(user=Depends(get_current_user)):
    if not user or not user.is_admin:
        raise HTTPException(status_code=403, detail="Admins only")
    return user

@app.get("/admin/events/new", response_class=HTMLResponse)
async def create_event_form(request: Request, user: User = Depends(require_admin)):
    return templates.TemplateResponse("create_event.html", {"request": request, "success": False, "current_user": user, "csrf_token": generate_csrf_token()})

@app.post("/admin/events/new")
async def create_event(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
    title: str = Form(...),
    description: str = Form(None),
    date: str = Form(...),
    location: str = Form(None),
    max_pupils: int = Form(None),
    min_age: int = Form(None),
    max_age: int = Form(None),
    cost: float = Form(None),
    image_url: str = Form(None),
    image_file: UploadFile = None,
    csrf_token: str = Form(None)
):
    if not csrf_token or not verify_csrf_token(csrf_token):
        return templates.TemplateResponse("create_event.html", {"request": request, "success": False, "current_user": user, "error": "Invalid or missing CSRF token.", "csrf_token": generate_csrf_token()})
    event_date = datetime.strptime(date, "%Y-%m-%dT%H:%M")
    final_image_url = image_url
    if image_file is not None and image_file.filename:
        # Only allow image files
        if not image_file.content_type.startswith("image/"):
            return templates.TemplateResponse("create_event.html", {"request": request, "success": False, "current_user": user, "error": "Only image files are allowed.", "csrf_token": generate_csrf_token()})
        ext = image_file.filename.split('.')[-1]
        unique_name = f"{uuid.uuid4().hex}.{ext}"
        save_path = f"app/static/event_images/{unique_name}"
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(image_file.file, buffer)
        final_image_url = f"/static/event_images/{unique_name}"
    new_event = Event(
        title=title,
        description=description,
        date=event_date,
        location=location,
        max_pupils=max_pupils,
        min_age=min_age,
        max_age=max_age,
        cost=cost,
        image_url=final_image_url
    )
    db.add(new_event)
    db.commit()
    db.refresh(new_event)
    return RedirectResponse(url=f"/event/{new_event.id}", status_code=HTTP_303_SEE_OTHER)

@app.get("/event/{event_id}", response_class=HTMLResponse)
async def event_detail(request: Request, event_id: int = Path(...), db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        return HTMLResponse(content="<h1>Event not found</h1>", status_code=404)
    return templates.TemplateResponse("event_detail.html", {"request": request, "event": event})

@app.get("/admin/users", response_class=HTMLResponse)
async def admin_users(request: Request, db: Session = Depends(get_db), user: User = Depends(require_admin)):
    users = db.query(User).all()
    return templates.TemplateResponse("admin_users.html", {"request": request, "users": users, "current_user": user, "csrf_token": generate_csrf_token()})

@app.post("/admin/users/promote", response_class=HTMLResponse)
async def promote_user(request: Request, db: Session = Depends(get_db), user_id: int = Form(...), csrf_token: str = Form(None), user: User = Depends(require_admin)):
    if not csrf_token or not verify_csrf_token(csrf_token):
        users = db.query(User).all()
        return templates.TemplateResponse("admin_users.html", {"request": request, "users": users, "current_user": user, "error": "Invalid or missing CSRF token.", "csrf_token": generate_csrf_token()})
    promotee = db.query(User).filter(User.id == user_id).first()
    if promotee and not promotee.is_admin:
        promotee.is_admin = True
        db.commit()
    return RedirectResponse(url="/admin/users", status_code=HTTP_303_SEE_OTHER)

@app.on_event("startup")
def startup_tasks():
    print("🚀 Starting LifeLearners application...")
    
    # Check Facebook OAuth configuration
    if config.facebook_oauth_enabled:
        print("✅ Facebook OAuth is configured")
    else:
        print("⚠️  Facebook OAuth is not configured (missing FACEBOOK_CLIENT_ID or FACEBOOK_CLIENT_SECRET)")
    
    create_test_users()

def create_test_users():
    from app.models import User
    from app.database import SessionLocal
    from sqlalchemy.exc import ProgrammingError
    
    test_users = [
        {
            "email": os.getenv("TEST_USER_EMAIL"),
            "password": os.getenv("TEST_USER_PASSWORD"),
            "is_admin": False,
        },
        {
            "email": os.getenv("TEST_ADMIN_EMAIL"),
            "password": os.getenv("TEST_ADMIN_PASSWORD"),
            "is_admin": True,
        },
    ]
    
    db = SessionLocal()
    try:
        for u in test_users:
            if u["email"] and u["password"]:
                try:
                    user = db.query(User).filter(User.email == u["email"]).first()
                    if not user:
                        from app.main import get_password_hash
                        # Create user with auth_provider for newer schema, fallback for older schema
                        try:
                            user = User(
                                email=u["email"], 
                                hashed_password=get_password_hash(u["password"]), 
                                is_admin=u["is_admin"],
                                auth_provider='email'
                            )
                        except TypeError:
                            # Fallback for older schema without auth_provider
                            user = User(
                                email=u["email"], 
                                hashed_password=get_password_hash(u["password"]), 
                                is_admin=u["is_admin"]
                            )
                        db.add(user)
                except ProgrammingError as e:
                    # Handle missing columns gracefully (e.g., before migration)
                    if "does not exist" in str(e):
                        print(f"Warning: Database schema appears to be outdated. Skipping test user creation.")
                        print(f"Please run 'alembic upgrade head' to update the database schema.")
                        break
                    else:
                        raise
        db.commit()
    except Exception as e:
        print(f"Error during test user creation: {e}")
        db.rollback()
    finally:
        db.close()

@app.get("/profile", response_class=HTMLResponse)
async def profile_get(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    # Get all bookings for this user (via their children)
    children = db.query(Child).filter(Child.user_id == user.id).all()
    bookings = db.query(Booking).join(Child).filter(Child.user_id == user.id).join(Event).all()
    from datetime import datetime
    now = datetime.utcnow()
    return templates.TemplateResponse("profile.html", {"request": request, "user": user, "children": children, "bookings": bookings, "success": None, "error": None, "now": now})

@app.post("/profile", response_class=HTMLResponse)
async def profile_post(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    email: str = Form(...),
    password: str = Form(None),
    password_confirm: str = Form(None),
    csrf_token: str = Form(None)
):
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    if not csrf_token or not verify_csrf_token(csrf_token):
        return templates.TemplateResponse("profile.html", {"request": request, "user": user, "success": None, "error": "Invalid or missing CSRF token.", "csrf_token": generate_csrf_token()})
    error = None
    success = None
    if email and email != user.email:
        user.email = email
        try:
            db.commit()
            success = "Email updated."
        except IntegrityError:
            db.rollback()
            error = "Email already in use."
    if password:
        if password != password_confirm:
            error = "Passwords do not match."
        elif len(password) < 6:
            error = "Password must be at least 6 characters."
        else:
            user.hashed_password = get_password_hash(password)
            db.commit()
            success = (success + " Password updated.") if success else "Password updated."
    db.refresh(user)
    from datetime import datetime
    now = datetime.utcnow()
    children = db.query(Child).filter(Child.user_id == user.id).all()
    bookings = db.query(Booking).join(Child).filter(Child.user_id == user.id).join(Event).all()
    return templates.TemplateResponse("profile.html", {"request": request, "user": user, "children": children, "bookings": bookings, "success": success, "error": error, "csrf_token": generate_csrf_token(), "now": now})

@app.post("/cancel-booking", response_class=HTMLResponse)
async def cancel_booking(request: Request, booking_id: int = Form(...), csrf_token: str = Form(None), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    if not csrf_token or not verify_csrf_token(csrf_token):
        children = db.query(Child).filter(Child.user_id == user.id).all()
        bookings = db.query(Booking).join(Child).filter(Child.user_id == user.id).join(Event).all()
        return templates.TemplateResponse("profile.html", {"request": request, "user": user, "children": children, "bookings": bookings, "success": None, "error": "Invalid or missing CSRF token.", "csrf_token": generate_csrf_token()})
    booking = db.query(Booking).join(Child).filter(Booking.id == booking_id, Child.user_id == user.id).first()
    if booking:
        db.delete(booking)
        db.commit()
        success = "Booking cancelled."
    else:
        success = None
    # Reload profile page with updated bookings
    children = db.query(Child).filter(Child.user_id == user.id).all()
    bookings = db.query(Booking).join(Child).filter(Child.user_id == user.id).join(Event).all()
    from datetime import datetime
    now = datetime.utcnow()
    return templates.TemplateResponse("profile.html", {"request": request, "user": user, "children": children, "bookings": bookings, "success": success, "error": None, "csrf_token": generate_csrf_token(), "now": now})

@app.get("/event/{event_id}/book", response_class=HTMLResponse)
async def book_event_get(request: Request, event_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/login", status_code=HTTP_303_SEE_OTHER)
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        return HTMLResponse(content="<h1>Event not found</h1>", status_code=404)
    children = db.query(Child).filter(Child.user_id == user.id).all()
    return templates.TemplateResponse("booking.html", {"request": request, "event": event, "user": user, "children": children, "success": None, "error": None, "csrf_token": generate_csrf_token()})

@app.post("/event/{event_id}/book", response_class=HTMLResponse)
async def book_event_post(
    request: Request,
    event_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    child_ids: List[int] = Form([]),
    new_child_names: List[str] = Form([]),
    new_child_ages: List[str] = Form([]),
    new_child_allergies: List[str] = Form([]),
    new_child_notes: List[str] = Form([]),
    csrf_token: str = Form(None)
):
    if not user:
        return RedirectResponse(url="/login", status_code=HTTP_303_SEE_OTHER)
    if not csrf_token or not verify_csrf_token(csrf_token):
        event = db.query(Event).filter(Event.id == event_id).first()
        children = db.query(Child).filter(Child.user_id == user.id).all()
        return templates.TemplateResponse("booking.html", {"request": request, "event": event, "user": user, "children": children, "success": None, "error": "Invalid or missing CSRF token.", "csrf_token": generate_csrf_token()})
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        return HTMLResponse(content="<h1>Event not found</h1>", status_code=404)
    error = None
    success = None
    booked_children = []
    duplicate_children = []
    
    # Book existing children
    for cid in child_ids:
        child = db.query(Child).filter(Child.id == cid, Child.user_id == user.id).first()
        if child:
            booking = Booking(event_id=event.id, child_id=child.id)
            db.add(booking)
            booked_children.append(child.name)
    
    # Add and book new children with duplicate detection
    for i, name in enumerate(new_child_names):
        if not name.strip():
            continue
        
        # Check for duplicate children (case-insensitive name matching)
        existing_child = db.query(Child).filter(
            Child.user_id == user.id,
            Child.name.ilike(name.strip())
        ).first()
        
        if existing_child:
            duplicate_children.append(name.strip())
            # Still book the existing child if not already selected
            if existing_child.id not in child_ids:
                booking = Booking(event_id=event.id, child_id=existing_child.id)
                db.add(booking)
                booked_children.append(existing_child.name)
            continue
        
        age = int(new_child_ages[i]) if i < len(new_child_ages) and new_child_ages[i] else None
        allergies = new_child_allergies[i] if i < len(new_child_allergies) else None
        notes = new_child_notes[i] if i < len(new_child_notes) else None
        
        child = Child(user_id=user.id, name=name.strip(), age=age, allergies=allergies, notes=notes)
        db.add(child)
        db.commit()
        db.refresh(child)
        booking = Booking(event_id=event.id, child_id=child.id)
        db.add(booking)
        booked_children.append(child.name)
    
    # Check if event requires payment
    if event.cost and event.cost > 0:
        # Calculate total cost
        total_children = len(child_ids) + len([name for name in new_child_names if name.strip()])
        total_cost_dollars = event.cost * total_children
        total_cost_cents = int(total_cost_dollars * 100)
        
        # Create payment intent or checkout session
        payment_service = get_payment_service()
        booking_details = {
            'event_id': event.id,
            'event_title': event.title,
            'child_count': total_children
        }
        
        # For this example, we'll use Stripe Checkout (easier for initial implementation)
        payment_result = payment_service.create_checkout_session(
            amount_cents=total_cost_cents,
            booking_details=booking_details,
            customer_email=user.email,
            success_url=f"{config.SITE_URL}/payment/success?event_id={event.id}",
            cancel_url=f"{config.SITE_URL}/event/{event.id}/book"
        )
        
        if payment_result['success']:
            # Store temporary booking info in session or database
            # For now, we'll commit the bookings but mark them as pending payment
            for booking in db.query(Booking).filter(
                Booking.event_id == event.id,
                Booking.child_id.in_([b.child_id for b in db.query(Booking).filter(Booking.event_id == event.id)])
            ):
                booking.payment_status = 'pending'
            
            db.commit()
            
            # Redirect to Stripe Checkout
            return RedirectResponse(url=payment_result['checkout_url'], status_code=HTTP_303_SEE_OTHER)
        else:
            error = f"Payment setup failed: {payment_result.get('error', 'Unknown error')}"
    else:
        # Free event - mark as paid
        for booking in db.query(Booking).filter(
            Booking.event_id == event.id,
            Booking.child_id.in_([b.child_id for b in db.query(Booking).filter(Booking.event_id == event.id)])
        ):
            booking.payment_status = 'paid'
    
    db.commit()
    children = db.query(Child).filter(Child.user_id == user.id).all()
    
    if booked_children:
        success = f"Booked: {', '.join(booked_children)}"
        if duplicate_children:
            success += f" (Note: {', '.join(duplicate_children)} already existed and were used instead)"
        if event.cost and event.cost > 0:
            success += " - Redirecting to payment..."
    else:
        error = "No children selected or added."
    
    return templates.TemplateResponse("booking.html", {"request": request, "event": event, "user": user, "children": children, "success": success, "error": error, "csrf_token": generate_csrf_token()})

@app.get("/resend-confirmation", response_class=HTMLResponse)
async def resend_confirmation_form(request: Request, email: str = Query(None)):
    csrf_token = generate_csrf_token()
    return templates.TemplateResponse("resend_confirmation.html", {"request": request, "error": None, "success": None, "email": email, "csrf_token": csrf_token})

@app.post("/resend-confirmation", response_class=HTMLResponse)
@limiter.limit("3/minute")
async def resend_confirmation(request: Request, db: Session = Depends(get_db), email: str = Form(...), csrf_token: str = Form(None)):
    # CSRF check
    if not csrf_token or not verify_csrf_token(csrf_token):
        csrf_token = generate_csrf_token()
        return templates.TemplateResponse("resend_confirmation.html", {"request": request, "error": "Invalid or missing CSRF token.", "success": None, "csrf_token": csrf_token})
    user = db.query(User).filter(User.email == email).first()
    if not user:
        csrf_token = generate_csrf_token()
        return templates.TemplateResponse("resend_confirmation.html", {
            "request": request,
            "error": "Email not found.",
            "success": None,
            "csrf_token": csrf_token
        })
    
    if user.email_confirmed:
        csrf_token = generate_csrf_token()
        return templates.TemplateResponse("resend_confirmation.html", {
            "request": request,
            "error": "Email already confirmed. You can log in.",
            "success": None,
            "csrf_token": csrf_token
        })
    
    token = create_email_token(email)
    confirm_url = f"{SITE_URL}/confirm-email/{token}"
    email_body = f"""
    Welcome to LifeLearners!
    
    Please confirm your email address by clicking the link below:
    {confirm_url}
    
    This link will expire in 24 hours.
    
    If you did not sign up for LifeLearners, you can safely ignore this email.
    """
    try:
        send_email(email, "LifeLearners - Email Confirmation", email_body)
    except Exception as e:
        print("Email send failed:", e)
        csrf_token = generate_csrf_token()
        return templates.TemplateResponse("resend_confirmation.html", {
            "request": request,
            "error": "Failed to send confirmation email. Please try again later.",
            "success": None,
            "csrf_token": csrf_token
        })
    
    return templates.TemplateResponse("resend_confirmation.html", {
        "request": request,
        "error": None,
        "success": "Confirmation email sent! Please check your inbox.",
        "csrf_token": generate_csrf_token()
    })

# Admin Routes
@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    # Calculate statistics
    total_users = db.query(User).count()
    total_events = db.query(Event).count()
    total_bookings = db.query(Booking).count()
    
    # Calculate total revenue from paid bookings
    paid_bookings = db.query(Booking).filter(Booking.payment_status == 'paid').all()
    total_revenue = sum(booking.event.cost or 0 for booking in paid_bookings)
    
    stats = {
        "total_users": total_users,
        "total_events": total_events,
        "total_bookings": total_bookings,
        "total_revenue": total_revenue
    }
    
    # Get recent activity (last 10 bookings)
    recent_activity = db.query(Booking).order_by(Booking.timestamp.desc()).limit(10).all()
    
    return templates.TemplateResponse("admin_dashboard.html", {
        "request": request,
        "current_user": user,
        "stats": stats,
        "recent_activity": recent_activity
    })

@app.get("/admin/events", response_class=HTMLResponse)
async def admin_events(request: Request, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    events = db.query(Event).order_by(Event.date.desc()).all()
    return templates.TemplateResponse("admin_events.html", {
        "request": request,
        "current_user": user,
        "events": events,
        "csrf_token": generate_csrf_token()
    })

@app.post("/admin/events/{event_id}/delete", response_class=HTMLResponse)
async def delete_event(
    request: Request,
    event_id: int,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    csrf_token: str = Form(None)
):
    if not csrf_token or not verify_csrf_token(csrf_token):
        raise HTTPException(status_code=400, detail="Invalid CSRF token")
    
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Delete associated bookings first
    db.query(Booking).filter(Booking.event_id == event_id).delete()
    db.delete(event)
    db.commit()
    
    return RedirectResponse(url="/admin/events", status_code=HTTP_303_SEE_OTHER)

@app.get("/admin/payments", response_class=HTMLResponse)
async def admin_payments(request: Request, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    # Get all bookings with payment information
    bookings = db.query(Booking).join(Event).join(Child).join(User).order_by(Booking.timestamp.desc()).all()
    
    # Calculate payment statistics
    paid_bookings = [b for b in bookings if b.payment_status == 'paid']
    total_revenue = sum(b.event.cost or 0 for b in paid_bookings)
    total_payments = len(paid_bookings)
    total_refunds = len([b for b in bookings if b.payment_status == 'refunded'])
    pending_payments = len([b for b in bookings if b.payment_status == 'pending'])
    
    stats = {
        "total_revenue": total_revenue,
        "total_payments": total_payments,
        "total_refunds": sum(b.event.cost or 0 for b in bookings if b.payment_status == 'refunded'),
        "pending_payments": pending_payments
    }
    
    return templates.TemplateResponse("admin_payments.html", {
        "request": request,
        "current_user": user,
        "bookings": bookings,
        "stats": stats,
        "csrf_token": generate_csrf_token()
    })

@app.post("/admin/payments/{booking_id}/refund", response_class=HTMLResponse)
async def process_refund(
    request: Request,
    booking_id: int,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    csrf_token: str = Form(None)
):
    if not csrf_token or not verify_csrf_token(csrf_token):
        raise HTTPException(status_code=400, detail="Invalid CSRF token")
    
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    if booking.payment_status != 'paid':
        raise HTTPException(status_code=400, detail="Booking is not paid")
    
    # Update payment status to refunded
    booking.payment_status = 'refunded'
    db.commit()
    
    return RedirectResponse(url="/admin/payments", status_code=HTTP_303_SEE_OTHER)

@app.post("/admin/payments/manual-refund", response_class=HTMLResponse)
async def manual_refund(
    request: Request,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    booking_id: int = Form(...),
    refund_amount: float = Form(...),
    refund_reason: str = Form(...),
    csrf_token: str = Form(None)
):
    if not csrf_token or not verify_csrf_token(csrf_token):
        raise HTTPException(status_code=400, detail="Invalid CSRF token")
    
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    # Process manual refund logic here
    # This would typically integrate with Stripe API
    booking.payment_status = 'refunded'
    db.commit()
    
    return RedirectResponse(url="/admin/payments", status_code=HTTP_303_SEE_OTHER)

@app.get("/admin/stats", response_class=HTMLResponse)
async def admin_stats(request: Request, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    # Calculate comprehensive statistics
    total_users = db.query(User).count()
    total_events = db.query(Event).count()
    total_bookings = db.query(Booking).count()
    
    # Calculate revenue
    paid_bookings = db.query(Booking).filter(Booking.payment_status == 'paid').all()
    total_revenue = sum(booking.event.cost or 0 for booking in paid_bookings)
    
    # Calculate growth percentages (simplified - you'd want to compare with previous periods)
    user_growth = 5.2  # Placeholder
    event_growth = 12.5  # Placeholder
    booking_growth = 8.7  # Placeholder
    revenue_growth = 15.3  # Placeholder
    
    # Calculate performance metrics
    avg_bookings_per_event = total_bookings / total_events if total_events > 0 else 0
    avg_revenue_per_event = total_revenue / total_events if total_events > 0 else 0
    conversion_rate = (total_bookings / total_users * 100) if total_users > 0 else 0
    
    # Calculate average children per user
    total_children = db.query(Child).count()
    avg_children_per_user = total_children / total_users if total_users > 0 else 0
    
    # Additional child statistics
    users_with_children = db.query(User).join(Child).distinct().count()
    users_without_children = total_users - users_with_children
    children_with_allergies = db.query(Child).filter(Child.allergies.isnot(None)).count()
    children_needing_assistance = db.query(Child).filter(Child.needs_assisting_adult == True).count()
    
    # Age distribution of children
    age_groups = {
        "0-2": db.query(Child).filter(Child.age <= 2).count(),
        "3-5": db.query(Child).filter(Child.age >= 3, Child.age <= 5).count(),
        "6-8": db.query(Child).filter(Child.age >= 6, Child.age <= 8).count(),
        "9-12": db.query(Child).filter(Child.age >= 9, Child.age <= 12).count(),
        "13+": db.query(Child).filter(Child.age >= 13).count()
    }
    
    stats = {
        "total_users": total_users,
        "total_events": total_events,
        "total_bookings": total_bookings,
        "total_revenue": total_revenue,
        "user_growth": user_growth,
        "event_growth": event_growth,
        "booking_growth": booking_growth,
        "revenue_growth": revenue_growth,
        "avg_bookings_per_event": avg_bookings_per_event,
        "avg_revenue_per_event": avg_revenue_per_event,
        "conversion_rate": conversion_rate,
        "avg_children_per_user": avg_children_per_user,
        "total_children": total_children,
        "users_with_children": users_with_children,
        "users_without_children": users_without_children,
        "children_with_allergies": children_with_allergies,
        "children_needing_assistance": children_needing_assistance,
        "age_groups": age_groups
    }
    
    # Get top performing events
    top_events = db.query(Event).all()
    for event in top_events:
        event.total_revenue = sum(booking.event.cost or 0 for booking in event.bookings if booking.payment_status == 'paid')
    
    top_events = sorted(top_events, key=lambda x: x.total_revenue, reverse=True)[:5]
    
    # Get recent activity
    recent_activity = db.query(Booking).order_by(Booking.timestamp.desc()).limit(10).all()
    
    return templates.TemplateResponse("admin_stats.html", {
        "request": request,
        "current_user": user,
        "stats": stats,
        "top_events": top_events,
        "recent_activity": recent_activity
    })

@app.get("/admin/stripe", response_class=HTMLResponse)
async def admin_stripe(request: Request, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    # Mock Stripe configuration data
    stripe_config = {
        "status": "connected",  # or "disconnected", "testing"
        "balance": {
            "available": 1250.75,
            "pending": 350.25
        },
        "webhooks_enabled": True,
        "webhook_url": "https://lifelearners.org.nz/webhook/stripe",
        "webhook_secret": "whsec_...",
        "publishable_key": "pk_test_...",
        "secret_key": "sk_test_...",
        "webhook_endpoint": "https://lifelearners.org.nz/webhook/stripe",
        "currency": "nzd",
        "test_mode": True,
        "enabled_methods": ["card", "bank_transfer"]
    }
    
    # Mock Stripe statistics
    stripe_stats = {
        "successful_payments": 45,
        "failed_payments": 3,
        "refunds_processed": 2,
        "dispute_rate": 0.5
    }
    
    # Mock webhook logs
    webhook_logs = [
        {
            "event_type": "payment_intent.succeeded",
            "timestamp": datetime.now() - timedelta(minutes=5),
            "description": "Payment completed for Event: Science Workshop",
            "status": "success",
            "error_message": None
        },
        {
            "event_type": "payment_intent.payment_failed",
            "timestamp": datetime.now() - timedelta(minutes=15),
            "description": "Payment failed for Event: Art Class",
            "status": "error",
            "error_message": "Card declined"
        }
    ]
    
    return templates.TemplateResponse("admin_stripe.html", {
        "request": request,
        "current_user": user,
        "stripe_config": stripe_config,
        "stripe_stats": stripe_stats,
        "webhook_logs": webhook_logs,
        "csrf_token": generate_csrf_token()
    })

@app.post("/admin/stripe/webhook-config")
async def update_webhook_config(
    request: Request,
    user: User = Depends(require_admin),
    data: dict = None
):
    # This would update webhook configuration
    # For now, just return success
    return {"success": True}

@app.post("/admin/stripe/test-webhook")
async def test_webhook(
    request: Request,
    user: User = Depends(require_admin),
    data: dict = None
):
    # This would send a test webhook
    # For now, just return success
    return {"success": True}

@app.post("/admin/stripe/update-config", response_class=HTMLResponse)
async def update_stripe_config(
    request: Request,
    user: User = Depends(require_admin),
    publishable_key: str = Form(None),
    secret_key: str = Form(None),
    webhook_endpoint: str = Form(None),
    currency: str = Form("nzd"),
    test_mode: bool = Form(False),
    csrf_token: str = Form(None)
):
    if not csrf_token or not verify_csrf_token(csrf_token):
        raise HTTPException(status_code=400, detail="Invalid CSRF token")
    
    # This would update Stripe configuration
    # For now, just redirect back
    return RedirectResponse(url="/admin/stripe", status_code=HTTP_303_SEE_OTHER)

# Payment Success and Webhook Routes
@app.get("/payment/success", response_class=HTMLResponse)
async def payment_success(
    request: Request, 
    event_id: int = Query(None),
    session_id: str = Query(None),
    mock: str = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    if not user:
        return RedirectResponse(url="/login", status_code=HTTP_303_SEE_OTHER)
    
    # Handle successful payment - mark bookings as paid
    # This works even without webhooks since Stripe redirects here after successful payment
    if event_id:
        recent_bookings = db.query(Booking).filter(
            Booking.event_id == event_id,
            Booking.child.has(Child.user_id == user.id),
            Booking.payment_status == 'pending'
        ).all()
        
        for booking in recent_bookings:
            booking.payment_status = 'paid'
            # Use session_id if available, otherwise use mock for development
            booking.stripe_payment_id = session_id or 'checkout_session_completed'
        
        db.commit()
    
    event = db.query(Event).filter(Event.id == event_id).first() if event_id else None
    
    return templates.TemplateResponse("payment_success.html", {
        "request": request,
        "user": user,
        "event": event,
        "mock_mode": bool(mock)
    })

@app.get("/payment/cancel", response_class=HTMLResponse)  
async def payment_cancel(request: Request, event_id: int = Query(None)):
    return templates.TemplateResponse("payment_cancel.html", {
        "request": request,
        "event_id": event_id
    })

@app.post("/webhook/stripe")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')
    
    payment_service = get_payment_service()
    webhook_result = payment_service.handle_webhook_event(payload, sig_header)
    
    if not webhook_result['success']:
        raise HTTPException(status_code=400, detail=webhook_result['error'])
    
    event_type = webhook_result['event_type']
    event_data = webhook_result['data']
    
    # Handle different webhook events
    if event_type == 'payment_intent.succeeded':
        payment_intent = event_data['object']
        metadata = payment_intent.get('metadata', {})
        
        if metadata.get('booking_type') == 'event_booking':
            event_id = metadata.get('event_id')
            user_email = metadata.get('user_email')
            
            if event_id and user_email:
                # Find user and update booking status
                user = db.query(User).filter(User.email == user_email).first()
                if user:
                    bookings = db.query(Booking).filter(
                        Booking.event_id == event_id,
                        Booking.child.has(Child.user_id == user.id),
                        Booking.payment_status == 'pending'
                    ).all()
                    
                    for booking in bookings:
                        booking.payment_status = 'paid'
                        booking.stripe_payment_id = payment_intent['id']
                    
                    db.commit()
    
    elif event_type == 'payment_intent.payment_failed':
        payment_intent = event_data['object']
        metadata = payment_intent.get('metadata', {})
        
        if metadata.get('booking_type') == 'event_booking':
            event_id = metadata.get('event_id')
            user_email = metadata.get('user_email')
            
            if event_id and user_email:
                user = db.query(User).filter(User.email == user_email).first()
                if user:
                    bookings = db.query(Booking).filter(
                        Booking.event_id == event_id,
                        Booking.child.has(Child.user_id == user.id),
                        Booking.payment_status == 'pending'
                    ).all()
                    
                    for booking in bookings:
                        booking.payment_status = 'failed'
                    
                    db.commit()
    
    return {"status": "success"}

class UserContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        db = SessionLocal()
        user = None
        session = request.cookies.get(SESSION_COOKIE)
        if session:
            try:
                data = serializer.loads(session, max_age=SESSION_MAX_AGE)
                user = db.query(User).filter(User.id == data["user_id"]).first()
            except Exception:
                user = None
        request.state.user = user
        response = await call_next(request)
        db.close()
        return response

app.add_middleware(UserContextMiddleware)

# Simple email sender
def send_email(to_email, subject, body):
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = "noreply@lifelearners.org.nz"
    msg["To"] = to_email
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        if SMTP_USER and SMTP_PASS:
            server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(msg["From"], [to_email], msg.as_string())

@app.get("/children", response_class=HTMLResponse)
async def children_get(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    children = db.query(Child).filter(Child.user_id == user.id).all()
    return templates.TemplateResponse("children.html", {"request": request, "user": user, "children": children, "success": None, "error": None, "csrf_token": generate_csrf_token()})

@app.post("/children/add", response_class=HTMLResponse)
async def add_child(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    name: str = Form(...),
    age: int = Form(...),
    allergies: str = Form(None),
    notes: str = Form(None),
    needs_assisting_adult: bool = Form(False),
    other_info: str = Form(None),
    csrf_token: str = Form(None)
):
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    if not csrf_token or not verify_csrf_token(csrf_token):
        children = db.query(Child).filter(Child.user_id == user.id).all()
        return templates.TemplateResponse("children.html", {"request": request, "user": user, "children": children, "success": None, "error": "Invalid or missing CSRF token.", "csrf_token": generate_csrf_token()})
    
    # Check for duplicate children
    existing_child = db.query(Child).filter(
        Child.user_id == user.id,
        Child.name.ilike(name.strip())
    ).first()
    
    if existing_child:
        children = db.query(Child).filter(Child.user_id == user.id).all()
        return templates.TemplateResponse("children.html", {"request": request, "user": user, "children": children, "success": None, "error": f"A child named '{name.strip()}' already exists.", "csrf_token": generate_csrf_token()})
    
    child = Child(
        user_id=user.id,
        name=name.strip(),
        age=age,
        allergies=allergies,
        notes=notes,
        needs_assisting_adult=needs_assisting_adult,
        other_info=other_info
    )
    db.add(child)
    db.commit()
    
    children = db.query(Child).filter(Child.user_id == user.id).all()
    return templates.TemplateResponse("children.html", {"request": request, "user": user, "children": children, "success": f"Child '{name.strip()}' added successfully!", "error": None, "csrf_token": generate_csrf_token()})

@app.post("/children/{child_id}/edit", response_class=HTMLResponse)
async def edit_child(
    request: Request,
    child_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    name: str = Form(...),
    age: int = Form(...),
    allergies: str = Form(None),
    notes: str = Form(None),
    needs_assisting_adult: bool = Form(False),
    other_info: str = Form(None),
    csrf_token: str = Form(None)
):
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    if not csrf_token or not verify_csrf_token(csrf_token):
        children = db.query(Child).filter(Child.user_id == user.id).all()
        return templates.TemplateResponse("children.html", {"request": request, "user": user, "children": children, "success": None, "error": "Invalid or missing CSRF token.", "csrf_token": generate_csrf_token()})
    
    child = db.query(Child).filter(Child.id == child_id, Child.user_id == user.id).first()
    if not child:
        children = db.query(Child).filter(Child.user_id == user.id).all()
        return templates.TemplateResponse("children.html", {"request": request, "user": user, "children": children, "success": None, "error": "Child not found.", "csrf_token": generate_csrf_token()})
    
    # Check for duplicate names (excluding current child)
    existing_child = db.query(Child).filter(
        Child.user_id == user.id,
        Child.name.ilike(name.strip()),
        Child.id != child_id
    ).first()
    
    if existing_child:
        children = db.query(Child).filter(Child.user_id == user.id).all()
        return templates.TemplateResponse("children.html", {"request": request, "user": user, "children": children, "success": None, "error": f"A child named '{name.strip()}' already exists.", "csrf_token": generate_csrf_token()})
    
    child.name = name.strip()
    child.age = age
    child.allergies = allergies
    child.notes = notes
    child.needs_assisting_adult = needs_assisting_adult
    child.other_info = other_info
    db.commit()
    
    children = db.query(Child).filter(Child.user_id == user.id).all()
    return templates.TemplateResponse("children.html", {"request": request, "user": user, "children": children, "success": f"Child '{name.strip()}' updated successfully!", "error": None, "csrf_token": generate_csrf_token()})

@app.post("/children/{child_id}/delete", response_class=HTMLResponse)
async def delete_child(
    request: Request,
    child_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    csrf_token: str = Form(None)
):
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    if not csrf_token or not verify_csrf_token(csrf_token):
        children = db.query(Child).filter(Child.user_id == user.id).all()
        return templates.TemplateResponse("children.html", {"request": request, "user": user, "children": children, "success": None, "error": "Invalid or missing CSRF token.", "csrf_token": generate_csrf_token()})
    
    child = db.query(Child).filter(Child.id == child_id, Child.user_id == user.id).first()
    if not child:
        children = db.query(Child).filter(Child.user_id == user.id).all()
        return templates.TemplateResponse("children.html", {"request": request, "user": user, "children": children, "success": None, "error": "Child not found.", "csrf_token": generate_csrf_token()})
    
    child_name = child.name
    # Delete associated bookings first
    db.query(Booking).filter(Booking.child_id == child_id).delete()
    db.delete(child)
    db.commit()
    
    children = db.query(Child).filter(Child.user_id == user.id).all()
    return templates.TemplateResponse("children.html", {"request": request, "user": user, "children": children, "success": f"Child '{child_name}' deleted successfully!", "error": None, "csrf_token": generate_csrf_token()})

@app.get("/gallery", response_class=HTMLResponse)
async def gallery_page(request: Request, db: Session = Depends(get_db)):
    images = db.query(GalleryImage).order_by(GalleryImage.upload_date.desc()).all()
    return templates.TemplateResponse("gallery.html", {"request": request, "images": images})

@app.get("/admin/gallery", response_class=HTMLResponse)
async def admin_gallery_page(request: Request, db: Session = Depends(get_db), user: User = Depends(require_admin)):
    images = db.query(GalleryImage).order_by(GalleryImage.upload_date.desc()).all()
    return templates.TemplateResponse("admin_gallery.html", {"request": request, "images": images, "current_user": user, "csrf_token": generate_csrf_token()})

@app.post("/admin/gallery/upload", response_class=HTMLResponse)
async def upload_gallery_image(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
    title: str = Form(None),
    description: str = Form(None),
    image_file: UploadFile = File(...),
    csrf_token: str = Form(None)
):
    if not csrf_token or not verify_csrf_token(csrf_token):
        images = db.query(GalleryImage).order_by(GalleryImage.upload_date.desc()).all()
        return templates.TemplateResponse("admin_gallery.html", {"request": request, "images": images, "current_user": user, "error": "Invalid or missing CSRF token.", "csrf_token": generate_csrf_token()})
    if not image_file.content_type.startswith("image/"):
        images = db.query(GalleryImage).order_by(GalleryImage.upload_date.desc()).all()
        return templates.TemplateResponse("admin_gallery.html", {"request": request, "images": images, "current_user": user, "error": "Only image files are allowed.", "csrf_token": generate_csrf_token()})
    ext = image_file.filename.split('.')[-1]
    unique_name = f"{uuid.uuid4().hex}.{ext}"
    save_path = f"app/static/gallery/{unique_name}"
    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(image_file.file, buffer)
    new_image = GalleryImage(filename=unique_name, title=title, description=description)
    db.add(new_image)
    db.commit()
    return RedirectResponse(url="/admin/gallery", status_code=HTTP_303_SEE_OTHER)

@app.post("/admin/gallery/{image_id}/delete", response_class=HTMLResponse)
async def delete_gallery_image(
    request: Request,
    image_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
    csrf_token: str = Form(None)
):
    if not csrf_token or not verify_csrf_token(csrf_token):
        images = db.query(GalleryImage).order_by(GalleryImage.upload_date.desc()).all()
        return templates.TemplateResponse("admin_gallery.html", {"request": request, "images": images, "current_user": user, "error": "Invalid or missing CSRF token.", "csrf_token": generate_csrf_token()})
    image = db.query(GalleryImage).filter(GalleryImage.id == image_id).first()
    if image:
        try:
            os.remove(f"app/static/gallery/{image.filename}")
        except Exception:
            pass
        db.delete(image)
        db.commit()
    return RedirectResponse(url="/admin/gallery", status_code=HTTP_303_SEE_OTHER)

@app.post("/admin/gallery/{image_id}/edit", response_class=HTMLResponse)
async def edit_gallery_image(
    request: Request,
    image_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
    title: str = Form(...),
    description: str = Form(...),
    csrf_token: str = Form(None)
):
    if not csrf_token or not verify_csrf_token(csrf_token):
        images = db.query(GalleryImage).order_by(GalleryImage.upload_date.desc()).all()
        return templates.TemplateResponse("admin_gallery.html", {"request": request, "images": images, "current_user": user, "error": "Invalid or missing CSRF token.", "csrf_token": generate_csrf_token()})
    image = db.query(GalleryImage).filter(GalleryImage.id == image_id).first()
    if image:
        image.title = title
        image.description = description
        db.commit()
    return RedirectResponse(url="/admin/gallery", status_code=HTTP_303_SEE_OTHER)

@app.get("/admin/events/all", response_class=HTMLResponse)
async def admin_all_events(request: Request, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    # Get all events with their bookings and related data
    events = db.query(Event).options(
        joinedload(Event.bookings).joinedload(Booking.child).joinedload(Child.user)
    ).order_by(Event.date.desc()).all()
    
    from datetime import datetime, timedelta
    now = datetime.utcnow()
    
    return templates.TemplateResponse("admin_all_events.html", {
        "request": request, 
        "events": events, 
        "current_user": user,
        "now": now,
        "timedelta": timedelta,
        "csrf_token": generate_csrf_token()
    })

@app.get("/admin/events/calendar", response_class=HTMLResponse)
async def admin_events_calendar(request: Request, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    # Get all events with their bookings
    events = db.query(Event).options(
        joinedload(Event.bookings).joinedload(Booking.child).joinedload(Child.user)
    ).order_by(Event.date).all()
    
    from datetime import datetime
    now = datetime.utcnow()
    
    # Serialize events for JSON
    serialized_events = []
    for event in events:
        event_dict = {
            'id': event.id,
            'title': event.title,
            'description': event.description,
            'date': event.date.isoformat() if event.date else None,
            'location': event.location,
            'event_type': event.event_type,
            'cost': float(event.cost) if event.cost else None,
            'max_pupils': event.max_pupils,
            'recommended_age': event.recommended_age,
            'bookings': []
        }
        
        # Serialize bookings
        for booking in event.bookings:
            booking_dict = {
                'id': booking.id,
                'child': {
                    'id': booking.child.id,
                    'name': booking.child.name,
                    'age': booking.child.age,
                    'allergies': booking.child.allergies,
                    'needs_assisting_adult': booking.child.needs_assisting_adult,
                    'notes': booking.child.notes,
                    'user': {
                        'id': booking.child.user.id,
                        'email': booking.child.user.email
                    }
                }
            }
            event_dict['bookings'].append(booking_dict)
        
        serialized_events.append(event_dict)
    
    return templates.TemplateResponse("admin_events_calendar.html", {
        "request": request, 
        "events": serialized_events, 
        "current_user": user,
        "now": now,
        "csrf_token": generate_csrf_token()
    })

@app.get("/admin/events/{event_id}/bookings", response_class=HTMLResponse)
async def admin_event_bookings(request: Request, event_id: int, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    # Get the specific event with all its bookings
    event = db.query(Event).options(
        joinedload(Event.bookings).joinedload(Booking.child).joinedload(Child.user)
    ).filter(Event.id == event_id).first()
    
    if not event:
        return RedirectResponse(url="/admin/events/all", status_code=status.HTTP_303_SEE_OTHER)
    
    from datetime import datetime, timedelta
    now = datetime.utcnow()
    
    return templates.TemplateResponse("admin_event_bookings.html", {
        "request": request, 
        "event": event, 
        "current_user": user,
        "now": now,
        "timedelta": timedelta,
        "csrf_token": generate_csrf_token()
    })
