from fastapi import FastAPI, Request, Depends, Form, Path, Response, Cookie, HTTPException, UploadFile, status, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app.models import Base, Event, User, Child, Booking
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

app = FastAPI()
# Use absolute path for templates to ensure correct resolution in Docker and local dev
templates = Jinja2Templates(directory="app/templates")

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
    return templates.TemplateResponse("index.html", {"request": request, "events": events})

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
    if db.query(User).filter(User.email == email).first():
        csrf_token = generate_csrf_token()
        return templates.TemplateResponse("signup.html", {"request": request, "error": "Email already registered.", "csrf_token": csrf_token})
    
    user = User(email=email, hashed_password=get_password_hash(password), email_confirmed=False)
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
    if not user or not verify_password(password, user.hashed_password):
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
def create_test_users():
    from app.models import User
    from app.database import SessionLocal
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
    for u in test_users:
        if u["email"] and u["password"]:
            user = db.query(User).filter(User.email == u["email"]).first()
            if not user:
                from app.main import get_password_hash
                user = User(email=u["email"], hashed_password=get_password_hash(u["password"]), is_admin=u["is_admin"])
                db.add(user)
    db.commit()
    db.close()

@app.get("/profile", response_class=HTMLResponse)
async def profile_get(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    # Get all bookings for this user (via their children)
    children = db.query(Child).filter(Child.user_id == user.id).all()
    bookings = db.query(Booking).join(Child).filter(Child.user_id == user.id).join(Event).all()
    return templates.TemplateResponse("profile.html", {"request": request, "user": user, "children": children, "bookings": bookings, "success": None, "error": None})

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
    return templates.TemplateResponse("profile.html", {"request": request, "user": user, "success": success, "error": error, "csrf_token": generate_csrf_token()})

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
    return templates.TemplateResponse("profile.html", {"request": request, "user": user, "children": children, "bookings": bookings, "success": success, "error": None, "csrf_token": generate_csrf_token()})

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
    # Book existing children
    for cid in child_ids:
        child = db.query(Child).filter(Child.id == cid, Child.user_id == user.id).first()
        if child:
            booking = Booking(event_id=event.id, child_id=child.id)
            db.add(booking)
            booked_children.append(child.name)
    # Add and book new children
    for i, name in enumerate(new_child_names):
        if not name.strip():
            continue
        age = int(new_child_ages[i]) if i < len(new_child_ages) and new_child_ages[i] else None
        allergies = new_child_allergies[i] if i < len(new_child_allergies) else None
        notes = new_child_notes[i] if i < len(new_child_notes) else None
        child = Child(user_id=user.id, name=name, age=age, allergies=allergies, notes=notes)
        db.add(child)
        db.commit()
        db.refresh(child)
        booking = Booking(event_id=event.id, child_id=child.id)
        db.add(booking)
        booked_children.append(child.name)
    db.commit()
    children = db.query(Child).filter(Child.user_id == user.id).all()
    if booked_children:
        success = f"Booked: {', '.join(booked_children)}"
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
        "avg_children_per_user": avg_children_per_user
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
