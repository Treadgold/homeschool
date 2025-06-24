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

app = FastAPI()
# Use absolute path for templates to ensure correct resolution in Docker and local dev
templates = Jinja2Templates(directory="app/templates")

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
    return templates.TemplateResponse("signup.html", {"request": request, "error": None})

@app.post("/signup", response_class=HTMLResponse)
async def signup(request: Request, db: Session = Depends(get_db), email: str = Form(...), password: str = Form(...), honeypot: str = Form("")):
    # Honeypot check
    if honeypot:
        return templates.TemplateResponse("signup.html", {"request": request, "error": "Bot detected."})
    if db.query(User).filter(User.email == email).first():
        return templates.TemplateResponse("signup.html", {"request": request, "error": "Email already registered."})
    
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
        return templates.TemplateResponse("signup.html", {
            "request": request, 
            "error": "Failed to send confirmation email. Please try again later."
        })
    
    return templates.TemplateResponse("signup_success.html", {
        "request": request,
        "email": email
    })

@app.get("/confirm-email/{token}", response_class=HTMLResponse)
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
    return templates.TemplateResponse("login.html", {"request": request, "error": None})

@app.post("/login", response_class=HTMLResponse)
async def login(request: Request, db: Session = Depends(get_db), email: str = Form(...), password: str = Form(...), keep_logged_in: str = Form(None)):
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid credentials."})
    
    if not user.email_confirmed:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Please confirm your email address before logging in. Check your inbox for the confirmation link."
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
    return templates.TemplateResponse("create_event.html", {"request": request, "success": False, "current_user": user})

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
    image_file: UploadFile = None
):
    event_date = datetime.strptime(date, "%Y-%m-%dT%H:%M")
    final_image_url = image_url
    if image_file is not None and image_file.filename:
        # Only allow image files
        if not image_file.content_type.startswith("image/"):
            return templates.TemplateResponse("create_event.html", {"request": request, "success": False, "current_user": user, "error": "Only image files are allowed."})
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
    return templates.TemplateResponse("admin_users.html", {"request": request, "users": users, "current_user": user})

@app.post("/admin/users/promote", response_class=HTMLResponse)
async def promote_user(request: Request, db: Session = Depends(get_db), user_id: int = Form(...), user: User = Depends(require_admin)):
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
    password_confirm: str = Form(None)
):
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
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
    return templates.TemplateResponse("profile.html", {"request": request, "user": user, "success": success, "error": error})

@app.post("/cancel-booking", response_class=HTMLResponse)
async def cancel_booking(request: Request, booking_id: int = Form(...), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
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
    return templates.TemplateResponse("profile.html", {"request": request, "user": user, "children": children, "bookings": bookings, "success": success, "error": None})

@app.get("/event/{event_id}/book", response_class=HTMLResponse)
async def book_event_get(request: Request, event_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/login", status_code=HTTP_303_SEE_OTHER)
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        return HTMLResponse(content="<h1>Event not found</h1>", status_code=404)
    children = db.query(Child).filter(Child.user_id == user.id).all()
    return templates.TemplateResponse("booking.html", {"request": request, "event": event, "user": user, "children": children, "success": None, "error": None})

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
):
    if not user:
        return RedirectResponse(url="/login", status_code=HTTP_303_SEE_OTHER)
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
    return templates.TemplateResponse("booking.html", {"request": request, "event": event, "user": user, "children": children, "success": success, "error": error})

@app.get("/resend-confirmation", response_class=HTMLResponse)
async def resend_confirmation_form(request: Request):
    return templates.TemplateResponse("resend_confirmation.html", {"request": request, "error": None, "success": None})

@app.post("/resend-confirmation", response_class=HTMLResponse)
async def resend_confirmation(request: Request, db: Session = Depends(get_db), email: str = Form(...)):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return templates.TemplateResponse("resend_confirmation.html", {
            "request": request,
            "error": "Email not found.",
            "success": None
        })
    
    if user.email_confirmed:
        return templates.TemplateResponse("resend_confirmation.html", {
            "request": request,
            "error": "Email already confirmed. You can log in.",
            "success": None
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
        return templates.TemplateResponse("resend_confirmation.html", {
            "request": request,
            "error": "Failed to send confirmation email. Please try again later.",
            "success": None
        })
    
    return templates.TemplateResponse("resend_confirmation.html", {
        "request": request,
        "error": None,
        "success": "Confirmation email sent! Please check your inbox."
    })

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
