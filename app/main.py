from fastapi import FastAPI, Request, Depends, Form, Path, Response, Cookie, HTTPException, UploadFile, status, Query, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload
from app.database import SessionLocal, engine, get_db
from app.models import Base, Event, User, Child, Adult, Booking, AdultBooking, GalleryImage, ChatConversation, ChatMessage, AgentSession, AgentStatus
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
from starlette.middleware.sessions import SessionMiddleware
from typing import List, Dict
import smtplib
from email.mime.text import MIMEText
import uuid
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from authlib.integrations.starlette_client import OAuth
import requests
from sqlalchemy import text
import logging
import json
import traceback

app = FastAPI()
# Use absolute path for templates to ensure correct resolution in Docker and local dev
templates = Jinja2Templates(directory="app/templates")

# Add session middleware for OAuth
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SECRET_KEY", "dev-secret-key"))

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
            'scope': 'public_profile email'  # Changed order - public_profile first
        },
    )

if config.google_oauth_enabled:
    oauth.register(
        name='google',
        client_id=config.GOOGLE_CLIENT_ID,
        client_secret=config.GOOGLE_CLIENT_SECRET,
        authorize_url='https://accounts.google.com/o/oauth2/v2/auth',
        access_token_url='https://oauth2.googleapis.com/token',
        jwks_uri='https://www.googleapis.com/oauth2/v3/certs',
        client_kwargs={
            'scope': 'openid email profile'
        },
    )

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# User Context Middleware - MUST be added early!
class UserContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        logging.debug(f"UserContextMiddleware: Processing request {request.method} {request.url}")
        db = SessionLocal()
        user = None
        session = request.cookies.get(SESSION_COOKIE)
        
        # Log all cookies for debugging
        all_cookies = dict(request.cookies)
        logging.debug(f"All cookies received: {all_cookies}")
        logging.debug(f"Session cookie ({SESSION_COOKIE}): {session[:50] + '...' if session and len(session) > 50 else session}")
        
        if session:
            try:
                data = serializer.loads(session, max_age=SESSION_MAX_AGE)
                user = db.query(User).filter(User.id == data["user_id"]).first()
                logging.debug(f"User successfully loaded from session: ID={user.id}, Email={user.email}" if user else "No user found with session user_id")
            except Exception as e:
                logging.error(f"Error loading session: {e}")
                user = None
        else:
            logging.debug("No session cookie found")
        request.state.user = user
        response = await call_next(request)
        db.close()
        return response

app.add_middleware(UserContextMiddleware)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

# Create tables on startup
Base.metadata.create_all(bind=engine)

# Serve static files (for uploaded images)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
SESSION_COOKIE = "session"
SESSION_MAX_AGE = 60 * 60 * 24 * 30  # 30 days
serializer = URLSafeTimedSerializer(SECRET_KEY)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Simple in-memory session store for OAuth flows
oauth_sessions: Dict[str, int] = {}

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
        elif existing_user.auth_provider == 'google':
            return templates.TemplateResponse("signup.html", {"request": request, "error": "This email is already registered with Google. Please use 'Continue with Google' to log in.", "csrf_token": csrf_token})
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
    
    # Check if this is a Google-only user
    if user.auth_provider == 'google' and not user.hashed_password:
        csrf_token = generate_csrf_token()
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "This account was created with Google. Please use 'Continue with Google' to log in.",
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
    session_token = create_session_cookie(user.id, max_age)
    response.set_cookie(SESSION_COOKIE, session_token, max_age=max_age, httponly=True, samesite="lax", secure=False, path="/")
    print(f"Regular login - Session cookie set: {SESSION_COOKIE}={session_token[:20]}...")
    return response

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/", status_code=HTTP_303_SEE_OTHER)
    response.delete_cookie(SESSION_COOKIE)
    return response

@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    # Test database connection and configuration
    try:
        db.execute(text("SELECT 1"))
        database_status = "connected"
    except Exception as e:
        database_status = f"error: {e}"
    
    # Test OAuth configurations
    facebook_config = {
        "enabled": config.facebook_oauth_enabled,
        "client_id": config.FACEBOOK_CLIENT_ID[:10] + "..." if config.FACEBOOK_CLIENT_ID else None,
        "has_secret": bool(config.FACEBOOK_CLIENT_SECRET)
    }
    
    google_config = {
        "enabled": config.google_oauth_enabled,
        "client_id": config.GOOGLE_CLIENT_ID[:10] + "..." if config.GOOGLE_CLIENT_ID else None,
        "has_secret": bool(config.GOOGLE_CLIENT_SECRET)
    }
    
    return {
        "status": "ok",
        "database": database_status,
        "facebook_oauth": facebook_config,
        "google_oauth": google_config
    }

@app.get("/debug/session")
async def debug_session(request: Request, db: Session = Depends(get_db)):
    """Debug endpoint to check session status and cookies"""
    # Get all cookies
    all_cookies = dict(request.cookies)
    
    # Check for session cookie specifically
    session_cookie = request.cookies.get(SESSION_COOKIE)
    
    # Try to decode session
    user_from_session = None
    session_valid = False
    if session_cookie:
        try:
            data = serializer.loads(session_cookie, max_age=SESSION_MAX_AGE)
            user_from_session = db.query(User).filter(User.id == data["user_id"]).first()
            session_valid = True
        except Exception as e:
            session_valid = f"Error: {e}"
    
    # Check request.state.user (set by middleware)
    user_from_middleware = getattr(request.state, 'user', 'Not set')
    
    return {
        "all_cookies": all_cookies,
        "session_cookie_name": SESSION_COOKIE,
        "session_cookie_value": session_cookie[:20] + "..." if session_cookie else None,
        "session_valid": session_valid,
        "user_from_session": {
            "id": user_from_session.id if user_from_session else None,
            "email": user_from_session.email if user_from_session else None
        } if user_from_session else None,
        "user_from_middleware": {
            "id": user_from_middleware.id if hasattr(user_from_middleware, 'id') else None,
            "email": user_from_middleware.email if hasattr(user_from_middleware, 'email') else None
        } if user_from_middleware and user_from_middleware != 'Not set' else str(user_from_middleware)
    }

# Facebook OAuth Routes
@app.get("/auth/facebook")
async def facebook_login(request: Request):
    print("Initiating Facebook login process")
    if not config.facebook_oauth_enabled:
        print("Facebook OAuth is not enabled")
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Facebook login is not configured. Please set FACEBOOK_CLIENT_ID and FACEBOOK_CLIENT_SECRET environment variables.",
            "csrf_token": generate_csrf_token()
        })
    
    try:
        facebook = oauth.create_client('facebook')
        redirect_uri = config.FACEBOOK_REDIRECT_URI
        print(f"Redirecting to Facebook with URI: {redirect_uri}")
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
    print("Received Facebook OAuth callback")
    if not config.facebook_oauth_enabled:
        print("Facebook OAuth is not enabled")
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Facebook login is not configured.",
            "csrf_token": generate_csrf_token()
        })
    
    try:
        facebook = oauth.create_client('facebook') 
        
        # Check for OAuth errors in the callback
        if request.query_params.get('error'):
            error_description = request.query_params.get('error_description', 'Facebook login failed')
            print(f"Facebook OAuth error from callback: {request.query_params.get('error')}: {error_description}")
            return templates.TemplateResponse("login.html", {
                "request": request,
                "error": "Facebook login was cancelled or failed. Please try again.",
                "csrf_token": generate_csrf_token()
            })
        
        token = await facebook.authorize_access_token(request)
        print(f"Facebook OAuth token received successfully: {token}")
        
        # Get user info from Facebook
        user_response = await facebook.get('https://graph.facebook.com/me?fields=id,email,first_name,last_name,picture', token=token)
        facebook_user = user_response.json()
        print(f"Facebook user data received: {facebook_user}")
        
        if not facebook_user.get('email'):
            print("Facebook account does not have a verified email address")
            return templates.TemplateResponse("login.html", {
                "request": request,
                "error": "Facebook account must have a verified email address.",
                "csrf_token": generate_csrf_token()
            })
        
        # Check if user exists by Facebook ID (handle missing columns gracefully)
        try:
            user = db.query(User).filter(User.facebook_id == facebook_user['id']).first()
            print(f"User found by Facebook ID: {user}")
        except Exception as e:
            if "does not exist" in str(e):
                # Database hasn't been migrated yet, fall back to email-only lookup
                print("Database schema does not support Facebook ID, falling back to email lookup")
                user = None
            else:
                raise
        
        if not user:
            # Check if user exists by email (to link accounts)
            user = db.query(User).filter(User.email == facebook_user['email']).first()
            if user:
                print(f"User found by email: {user}")
                # Link existing account to Facebook (if schema supports it)
                try:
                    user.facebook_id = facebook_user['id']
                    user.first_name = facebook_user.get('first_name')
                    user.last_name = facebook_user.get('last_name')
                    user.profile_picture_url = facebook_user.get('picture', {}).get('data', {}).get('url')
                    if hasattr(user, 'auth_provider') and user.auth_provider == 'email':
                        user.auth_provider = 'both'  # User has both email and Facebook auth
                    print("Linked existing account to Facebook")
                except AttributeError:
                    # Schema doesn't have Facebook fields yet - just log the user in
                    print("Warning: Facebook fields not available in database schema. User logged in with existing account.")
            else:
                print("No existing user found, creating new user")
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
                    print("New user created with Facebook fields")
                except TypeError:
                    # Schema doesn't have Facebook fields yet - create basic user
                    user = User(
                        email=facebook_user['email'],
                        email_confirmed=True  # Facebook emails are considered verified
                    )
                    print("Warning: Created user without Facebook fields. Please run database migration.")
                db.add(user)
        else:
            print("Updating existing Facebook user info")
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
        print(f"User created/updated successfully: ID={user.id}, Email={user.email}")
        
        # Create session token and store it server-side
        session_token = create_session_cookie(user.id)
        oauth_session_id = str(uuid.uuid4())
        oauth_sessions[oauth_session_id] = user.id
        print(f"Created OAuth session: {oauth_session_id} for user {user.id}")
        
        # Redirect to a completion endpoint that will set the final session cookie
        return RedirectResponse(url=f"/auth/complete?session_id={oauth_session_id}", status_code=HTTP_303_SEE_OTHER)
        
    except Exception as e:
        print(f"Facebook OAuth error: {e}")
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Facebook login failed. Please try again.",
            "csrf_token": generate_csrf_token()
        })

# Google OAuth Routes
@app.get("/auth/google")
async def google_login(request: Request):
    print("Initiating Google login process")
    if not config.google_oauth_enabled:
        print("Google OAuth is not enabled")
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Google login is not configured. Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables.",
            "csrf_token": generate_csrf_token()
        })
    
    try:
        google = oauth.create_client('google')
        redirect_uri = config.GOOGLE_REDIRECT_URI
        print(f"Redirecting to Google with URI: {redirect_uri}")
        return await google.authorize_redirect(request, redirect_uri)
    except Exception as e:
        print(f"Google OAuth initialization error: {e}")
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Google login is temporarily unavailable. Please try again later or use email login.",
            "csrf_token": generate_csrf_token()
        })

@app.get("/auth/google/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    print("Received Google OAuth callback")
    if not config.google_oauth_enabled:
        print("Google OAuth is not enabled")
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Google login is not configured.",
            "csrf_token": generate_csrf_token()
        })
    
    try:
        google = oauth.create_client('google')
        
        # Check for OAuth errors in the callback
        if request.query_params.get('error'):
            error_description = request.query_params.get('error_description', 'Google login failed')
            print(f"Google OAuth error from callback: {request.query_params.get('error')}: {error_description}")
            return templates.TemplateResponse("login.html", {
                "request": request,
                "error": "Google login was cancelled or failed. Please try again.",
                "csrf_token": generate_csrf_token()
            })
        
        token = await google.authorize_access_token(request)
        print(f"Google OAuth token received successfully: {token}")
        
        # Get user info from Google (already parsed in token response)
        google_user = token.get('userinfo')
        if not google_user:
            # Fallback: try to parse ID token manually
            google_user = await google.parse_id_token(request, token['id_token'])
        print(f"Google user data received: {google_user}")
        
        if not google_user.get('email'):
            print("Google account does not have a verified email address")
            return templates.TemplateResponse("login.html", {
                "request": request,
                "error": "Google account must have a verified email address.",
                "csrf_token": generate_csrf_token()
            })
        
        # Check if user exists by Google ID
        try:
            user = db.query(User).filter(User.google_id == google_user['sub']).first()
            print(f"User found by Google ID: {user}")
        except Exception as e:
            if "does not exist" in str(e):
                print("Database schema does not support Google ID, falling back to email lookup")
                user = None
            else:
                raise
        
        if not user:
            # Check if user exists by email (to link accounts)
            user = db.query(User).filter(User.email == google_user['email']).first()
            if user:
                print(f"User found by email: {user}")
                # Link existing account to Google
                try:
                    user.google_id = google_user['sub']
                    user.first_name = google_user.get('given_name')
                    user.last_name = google_user.get('family_name')
                    user.profile_picture_url = google_user.get('picture')
                    if hasattr(user, 'auth_provider') and user.auth_provider == 'email':
                        user.auth_provider = 'both'  # User has both email and Google auth
                    print("Linked existing account to Google")
                except AttributeError:
                    print("Warning: Google fields not available in database schema. User logged in with existing account.")
            else:
                print("No existing user found, creating new user")
                # Create new user
                try:
                    user = User(
                        email=google_user['email'],
                        google_id=google_user['sub'],
                        first_name=google_user.get('given_name'),
                        last_name=google_user.get('family_name'),
                        profile_picture_url=google_user.get('picture'),
                        auth_provider='google',
                        email_confirmed=True  # Google emails are considered verified
                    )
                    print("New user created with Google fields")
                except TypeError:
                    # Schema doesn't have Google fields yet - create basic user
                    user = User(
                        email=google_user['email'],
                        email_confirmed=True  # Google emails are considered verified
                    )
                    print("Warning: Created user without Google fields. Please run database migration.")
                db.add(user)
        else:
            print("Updating existing Google user info")
            # Update existing Google user info
            try:
                user.first_name = google_user.get('given_name')
                user.last_name = google_user.get('family_name')
                user.profile_picture_url = google_user.get('picture')
            except AttributeError:
                print("Warning: Google fields not available for update. Please run database migration.")
        
        db.commit()
        db.refresh(user)
        print(f"User created/updated successfully: ID={user.id}, Email={user.email}")
        
        # Create session token and store it server-side
        session_token = create_session_cookie(user.id)
        oauth_session_id = str(uuid.uuid4())
        oauth_sessions[oauth_session_id] = user.id
        print(f"Created OAuth session: {oauth_session_id} for user {user.id}")
        
        # Redirect to a completion endpoint that will set the final session cookie
        return RedirectResponse(url=f"/auth/complete?session_id={oauth_session_id}", status_code=HTTP_303_SEE_OTHER)
        
    except Exception as e:
        print(f"Google OAuth error: {e}")
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Google login failed. Please try again.",
            "csrf_token": generate_csrf_token()
        })

@app.get("/auth/complete")
async def auth_complete(request: Request, session_id: str = Query(...)):
    """Complete the OAuth flow by setting the session cookie"""
    print(f"Completing OAuth flow for session_id: {session_id}")
    
    # Get user ID from OAuth session store
    user_id = oauth_sessions.get(session_id)
    if not user_id:
        print(f"Invalid or expired OAuth session: {session_id}")
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Login session expired. Please try again.",
            "csrf_token": generate_csrf_token()
        })
    
    # Clean up the OAuth session
    del oauth_sessions[session_id]
    print(f"Cleaned up OAuth session: {session_id}")
    
    # Create the final session cookie
    session_token = create_session_cookie(user_id)
    response = RedirectResponse(url="/", status_code=HTTP_303_SEE_OTHER)
    
    # Clear any existing session cookies first
    response.delete_cookie(SESSION_COOKIE, path="/")
    
    # Set the new session cookie
    response.set_cookie(
        SESSION_COOKIE, 
        session_token, 
        max_age=SESSION_MAX_AGE, 
        httponly=True, 
        samesite="lax",
        secure=False,
        path="/"
    )
    print(f"Set final session cookie for user {user_id}: {session_token[:20]}...")
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
    # Basic Information (Stage 1)
    title: str = Form(...),
    subtitle: str = Form(None),
    event_type: str = Form(None),
    status: str = Form("draft"),
    short_description: str = Form(None),
    description: str = Form(None),
    start_date: str = Form(...),  # datetime-local from form
    end_date: str = Form(None),
    timezone: str = Form("UTC"),
    is_recurring: bool = Form(False),
    
    # Details & Location (Stage 2)
    event_format: str = Form(None),
    max_participants: str = Form(None),
    min_age: str = Form(None),
    max_age: str = Form(None),
    venue_name: str = Form(None),
    address: str = Form(None),
    city: str = Form(None),
    state: str = Form(None),
    zip_code: str = Form(None),
    country: str = Form(None),
    meeting_id: str = Form(None),
    meeting_password: str = Form(None),
    what_to_bring: str = Form(None),
    dress_code: str = Form(None),
    language: str = Form("english"),
    accessibility_info: str = Form(None),
    parking_info: str = Form(None),
    
    # Media & Content (Stage 3)
    video_url: str = Form(None),
    event_agenda: str = Form(None),
    speaker_info: str = Form(None),
    rich_description: str = Form(None),
    
    # Ticketing & Pricing (Stage 4)
    cost: str = Form(None),
    is_free: bool = Form(False),
    requires_registration: bool = Form(True),
    early_bird_discount: str = Form(None),  # Changed to str to handle empty strings
    group_discount: str = Form(None),       # Changed to str to handle empty strings  
    member_discount: str = Form(None),      # Changed to str to handle empty strings
    registration_deadline: str = Form(None),
    
    # External Links & Publishing (Stage 5)
    website_url: str = Form(None),
    booking_url: str = Form(None),
    facebook_url: str = Form(None),
    instagram_url: str = Form(None),
    twitter_url: str = Form(None),
    linkedin_url: str = Form(None),
    youtube_url: str = Form(None),
    tiktok_url: str = Form(None),
    venue_website: str = Form(None),
    partner_url: str = Form(None),
    contact_name: str = Form(None),
    contact_email: str = Form(None),
    contact_phone: str = Form(None),
    emergency_contact: str = Form(None),
    terms_url: str = Form(None),
    privacy_policy_url: str = Form(None),
    featured_event: bool = Form(False),
    send_notifications: bool = Form(True),
    seo_keywords: str = Form(None),
    
    # File uploads
    featured_image: UploadFile = File(None),
    image_file: UploadFile = File(None),  # Keep for backward compatibility
    csrf_token: str = Form(None),
    
    # Draft/Status control
    save_as_draft: str = Form("true")
):
    # CSRF check
    if not csrf_token or not verify_csrf_token(csrf_token):
        return templates.TemplateResponse("create_event.html", {
            "request": request, 
            "success": False, 
            "current_user": user, 
            "error": "Invalid or missing CSRF token.", 
            "csrf_token": generate_csrf_token()
        })
    
    try:
        # Helper function to safely parse float values
        def safe_float_parse(value):
            """Safely parse a float value, returning None for empty/invalid inputs"""
            if not value or value.strip() == "":
                return None
            try:
                return float(value)
            except (ValueError, TypeError):
                return None
        
        # Helper function to safely parse integer values
        def safe_int_parse(value):
            """Safely parse an integer value, returning None for empty/invalid inputs"""
            if not value or value.strip() == "":
                return None
            try:
                return int(value)
            except (ValueError, TypeError):
                return None
        
        # Parse start date (required)
        start_datetime = datetime.strptime(start_date, "%Y-%m-%dT%H:%M")
        
        # Parse end date (optional)
        end_datetime = None
        if end_date:
            end_datetime = datetime.strptime(end_date, "%Y-%m-%dT%H:%M")
        
        # Parse registration deadline (optional)
        registration_deadline_datetime = None
        if registration_deadline:
            registration_deadline_datetime = datetime.strptime(registration_deadline, "%Y-%m-%dT%H:%M")
        
        # Handle image upload
        final_image_url = None
        image_to_process = featured_image if featured_image and featured_image.filename else image_file
        
        if image_to_process and image_to_process.filename:
            # Validate image file
            if not image_to_process.content_type.startswith("image/"):
                return templates.TemplateResponse("create_event.html", {
                    "request": request, 
                    "success": False, 
                    "current_user": user, 
                    "error": "Only image files are allowed.", 
                    "csrf_token": generate_csrf_token()
                })
            
            # Save image
            ext = image_to_process.filename.split('.')[-1]
            unique_name = f"{uuid.uuid4().hex}.{ext}"
            
            # Ensure directory exists
            import os
            os.makedirs("app/static/event_images", exist_ok=True)
            
            save_path = f"app/static/event_images/{unique_name}"
            with open(save_path, "wb") as buffer:
                shutil.copyfileobj(image_to_process.file, buffer)
            final_image_url = f"/static/event_images/{unique_name}"
        
        # Determine final status based on draft preference
        is_draft = save_as_draft.lower() == "true"
        final_status = "draft" if is_draft else "published"
        
        # Create new event with all comprehensive fields
        new_event = Event(
            # Basic Information
            title=title,
            subtitle=subtitle,
            event_type=event_type,
            status=final_status,
            short_description=short_description,
            description=description,
            date=start_datetime,  # Map to existing 'date' field
            end_date=end_datetime,
            timezone=timezone,
            is_recurring=is_recurring,
            
            # Details & Location
            event_format=event_format,
            max_participants=safe_int_parse(max_participants),
            min_age=safe_int_parse(min_age),
            max_age=safe_int_parse(max_age),
            venue_name=venue_name,
            address=address,
            city=city,
            state=state,
            zip_code=zip_code,
            country=country,
            meeting_id=meeting_id,
            meeting_password=meeting_password,
            what_to_bring=what_to_bring,
            dress_code=dress_code,
            language=language,
            accessibility_info=accessibility_info,
            parking_info=parking_info,
            
            # Media & Content
            image_url=final_image_url,
            video_url=video_url,
            event_agenda=event_agenda,
            speaker_info=speaker_info,
            rich_description=rich_description,
            
            # Ticketing & Pricing
            cost=safe_float_parse(cost),
            is_free=is_free,
            requires_registration=requires_registration,
            early_bird_discount=safe_float_parse(early_bird_discount),
            group_discount=safe_float_parse(group_discount),
            member_discount=safe_float_parse(member_discount),
            registration_deadline=registration_deadline_datetime,
            
            # External Links & Publishing
            website_url=website_url,
            booking_url=booking_url,
            facebook_url=facebook_url,
            instagram_url=instagram_url,
            twitter_url=twitter_url,
            linkedin_url=linkedin_url,
            youtube_url=youtube_url,
            tiktok_url=tiktok_url,
            venue_website=venue_website,
            partner_url=partner_url,
            contact_name=contact_name,
            contact_email=contact_email,
            contact_phone=contact_phone,
            emergency_contact=emergency_contact,
            terms_url=terms_url,
            privacy_policy_url=privacy_policy_url,
            featured_event=featured_event,
            send_notifications=send_notifications,
            seo_keywords=seo_keywords,
            
            # System fields
            created_by=user.id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(new_event)
        db.commit()
        db.refresh(new_event)
        
        # Redirect based on status
        if final_status == "draft":
            return RedirectResponse(url=f"/admin/events?draft_saved={new_event.id}", status_code=HTTP_303_SEE_OTHER)
        else:
            return RedirectResponse(url=f"/event/{new_event.id}?published=true", status_code=HTTP_303_SEE_OTHER)
        
    except ValueError as e:
        return templates.TemplateResponse("create_event.html", {
            "request": request, 
            "success": False, 
            "current_user": user, 
            "error": f"Invalid date format: {str(e)}", 
            "csrf_token": generate_csrf_token()
        })
    except Exception as e:
        return templates.TemplateResponse("create_event.html", {
            "request": request, 
            "success": False, 
            "current_user": user, 
            "error": f"Error creating event: {str(e)}", 
            "csrf_token": generate_csrf_token()
        })

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
async def startup_tasks():
    print("🚀 Starting LifeLearners application...")
    print("=" * 60)
    
    # Database status
    print("\n📊 DATABASE CONFIGURATION")
    print("-" * 30)
    print(f"🔍 Database URL: {config.DATABASE_URL[:50]}...")
    
    # Check Facebook OAuth configuration with debug info
    print("\n🔐 OAUTH CONFIGURATION")
    print("-" * 30)
    print(f"🔍 Facebook Client ID: {config.FACEBOOK_CLIENT_ID[:10]}..." if config.FACEBOOK_CLIENT_ID else "🔍 Facebook Client ID: NOT SET")
    print(f"🔍 Facebook Secret: {'SET' if config.FACEBOOK_CLIENT_SECRET else 'NOT SET'}")
    print(f"🔍 Facebook OAuth Enabled: {config.facebook_oauth_enabled}")
    
    if config.facebook_oauth_enabled:
        print("✅ Facebook OAuth is configured")
    else:
        print("⚠️  Facebook OAuth is not configured (missing FACEBOOK_CLIENT_ID or FACEBOOK_CLIENT_SECRET)")
    
    # Check Google OAuth configuration with debug info
    print(f"🔍 Google Client ID: {config.GOOGLE_CLIENT_ID[:10]}..." if config.GOOGLE_CLIENT_ID else "🔍 Google Client ID: NOT SET")
    print(f"🔍 Google Secret: {'SET' if config.GOOGLE_CLIENT_SECRET else 'NOT SET'}")
    print(f"🔍 Google OAuth Enabled: {config.google_oauth_enabled}")
    
    if config.google_oauth_enabled:
        print("✅ Google OAuth is configured")
    else:
        print("⚠️  Google OAuth is not configured (missing GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET)")
    
    # AI System Configuration
    print("\n🤖 AI SYSTEM CONFIGURATION")
    print("-" * 30)
    ollama_endpoint = os.getenv("OLLAMA_ENDPOINT", "http://host.docker.internal:11434")
    current_model = os.getenv("CURRENT_AI_MODEL", "mock_assistant")
    
    print(f"🔍 Ollama Endpoint: {ollama_endpoint}")
    print(f"🔍 Current AI Model: {current_model}")
    print(f"🔍 OpenAI API Key: {'SET' if os.getenv('OPENAI_API_KEY') else 'NOT SET'}")
    print(f"🔍 Anthropic API Key: {'SET' if os.getenv('ANTHROPIC_API_KEY') else 'NOT SET'}")
    
    # Test AI system connectivity
    print("\n🔬 AI SYSTEM CONNECTIVITY TEST")
    print("-" * 30)
    try:
        from app.ai_providers import ai_manager
        
        # Get available models
        available_models = ai_manager.get_available_models()
        print(f"📋 Available AI models: {len(available_models)}")
        for model_key, model_config in available_models.items():
            status = "✅ ENABLED" if model_config.enabled else "❌ DISABLED"
            print(f"   - {model_key} ({model_config.provider}): {status}")
        
        # Test current provider
        print(f"\n🧪 Testing current provider: {current_model}")
        try:
            current_provider = ai_manager.get_current_provider()
            print(f"✅ Current provider initialized: {current_provider.__class__.__name__}")
            
            # For Ollama, test connectivity (quick check only during startup)
            if hasattr(current_provider, 'base_url') and 'ollama' in current_provider.base_url:
                print(f"🔗 Testing Ollama connectivity to {current_provider.base_url}...")
                
                # Quick connectivity test with short timeout
                import httpx
                try:
                    async with httpx.AsyncClient(timeout=5) as client:
                        response = await client.get(f"{current_provider.base_url}/api/tags")
                        if response.status_code == 200:
                            models_data = response.json()
                            model_count = len(models_data.get("models", []))
                            print(f"✅ Ollama connection successful - {model_count} models available")
                            if current_provider.model in [m["name"] for m in models_data.get("models", [])]:
                                print(f"✅ Target model '{current_provider.model}' is available")
                            else:
                                print(f"⚠️  Target model '{current_provider.model}' not found in available models")
                        else:
                            print(f"⚠️  Ollama responded with status {response.status_code}")
                except httpx.ConnectError:
                    print(f"⚠️  Cannot connect to Ollama at {current_provider.base_url}")
                    print("💡 This is normal if Ollama is on the host system and containers are starting")
                    print("💡 AI features will attempt to connect when first used")
                except Exception as e:
                    print(f"⚠️  Ollama connectivity test error: {e}")
            
        except Exception as provider_error:
            print(f"⚠️  Could not initialize current provider: {provider_error}")
            print("💡 AI system will fall back to available providers when needed")
            
    except Exception as ai_error:
        print(f"⚠️  AI system initialization error: {ai_error}")
        print("💡 AI features may not be available until this is resolved")
    
    # Payment system status
    print("\n💳 PAYMENT SYSTEM CONFIGURATION")
    print("-" * 30)
    print(f"🔍 Payments Enabled: {config.ENABLE_PAYMENTS}")
    print(f"🔍 Stripe Publishable Key: {'SET' if config.STRIPE_PUBLISHABLE_KEY else 'NOT SET'}")
    print(f"🔍 Stripe Secret Key: {'SET' if config.STRIPE_SECRET_KEY else 'NOT SET'}")
    print(f"🔍 Stripe Test Mode: {config.stripe_is_test_mode}")
    
    create_test_users()
    
    print("\n🎉 LifeLearners startup complete!")
    print("=" * 60)

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
    # Get all bookings for this user (via their children and adults)
    children = db.query(Child).filter(Child.user_id == user.id).all()
    adults = db.query(Adult).filter(Adult.user_id == user.id).all()
    bookings = db.query(Booking).join(Child).filter(Child.user_id == user.id).join(Event).all()
    adult_bookings = db.query(AdultBooking).join(Adult).filter(Adult.user_id == user.id).join(Event).all()
    from datetime import datetime
    now = datetime.utcnow()
    return templates.TemplateResponse("profile.html", {"request": request, "user": user, "children": children, "adults": adults, "bookings": bookings, "adult_bookings": adult_bookings, "success": None, "error": None, "now": now})

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
    
    # Get the booking with event details
    booking = db.query(Booking).join(Child).join(Event).filter(
        Booking.id == booking_id, 
        Child.user_id == user.id
    ).first()
    
    if not booking:
        children = db.query(Child).filter(Child.user_id == user.id).all()
        bookings = db.query(Booking).join(Child).filter(Child.user_id == user.id).join(Event).all()
        return templates.TemplateResponse("profile.html", {"request": request, "user": user, "children": children, "bookings": bookings, "success": None, "error": "Booking not found.", "csrf_token": generate_csrf_token()})
    
    # Check if booking is already cancelled
    if booking.booking_status == "cancelled":
        children = db.query(Child).filter(Child.user_id == user.id).all()
        bookings = db.query(Booking).join(Child).filter(Child.user_id == user.id).join(Event).all()
        return templates.TemplateResponse("profile.html", {"request": request, "user": user, "children": children, "bookings": bookings, "success": None, "error": "This booking is already cancelled.", "csrf_token": generate_csrf_token()})
    
    # Check if cancellation request is already pending
    if booking.booking_status == "cancellation_requested":
        children = db.query(Child).filter(Child.user_id == user.id).all()
        bookings = db.query(Booking).join(Child).filter(Child.user_id == user.id).join(Event).all()
        return templates.TemplateResponse("profile.html", {"request": request, "user": user, "children": children, "bookings": bookings, "success": None, "error": "Cancellation request is already pending for this booking.", "csrf_token": generate_csrf_token()})
    
    # Handle different scenarios based on payment status and event cost
    if booking.event.cost and booking.event.cost > 0:
        # Paid event - handle based on payment status
        if booking.payment_status == 'paid':
            # Paid booking - create cancellation request for admin approval
            booking.booking_status = "cancellation_requested"
            booking.cancellation_requested_at = datetime.utcnow()
            booking.cancellation_reason = "Customer requested cancellation"
            
            db.commit()
            
            # Send notification email to admin (optional)
            try:
                admin_email_body = f"""
                Cancellation Request Received
                
                Event: {booking.event.title}
                Date: {booking.event.date.strftime('%B %d, %Y at %I:%M %p')}
                Customer: {user.email}
                Child: {booking.child.name}
                Amount Paid: ${booking.event.cost:.2f}
                
                Please review this cancellation request and process any necessary refunds.
                """
                # You can implement admin notification here
                # send_email("admin@lifelearners.org.nz", "Cancellation Request", admin_email_body)
            except Exception as e:
                print(f"Failed to send admin notification: {e}")
            
            success = f"Cancellation request submitted for {booking.child.name}'s booking to '{booking.event.title}'. An admin will review your request and process any refunds if approved."
            
        elif booking.payment_status == 'pending':
            # Pending payment - can cancel immediately
            booking.booking_status = "cancelled"
            booking.cancelled_at = datetime.utcnow()
            booking.cancellation_reason = "Customer cancelled before payment"
            db.commit()
            success = f"Booking cancelled for {booking.child.name} to '{booking.event.title}'."
            
        elif booking.payment_status == 'failed':
            # Failed payment - can cancel immediately
            booking.booking_status = "cancelled"
            booking.cancelled_at = datetime.utcnow()
            booking.cancellation_reason = "Customer cancelled after payment failed"
            db.commit()
            success = f"Booking cancelled for {booking.child.name} to '{booking.event.title}'."
            
        else:
            # Unpaid booking - can cancel immediately
            booking.booking_status = "cancelled"
            booking.cancelled_at = datetime.utcnow()
            booking.cancellation_reason = "Customer cancelled unpaid booking"
            db.commit()
            success = f"Booking cancelled for {booking.child.name} to '{booking.event.title}'."
            
    else:
        # Free event - can cancel immediately
        booking.booking_status = "cancelled"
        booking.cancelled_at = datetime.utcnow()
        booking.cancellation_reason = "Customer cancelled free event booking"
        db.commit()
        success = f"Booking cancelled for {booking.child.name} to '{booking.event.title}'."
    
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
    adults = db.query(Adult).filter(Adult.user_id == user.id).all()
    
    # Get already booked children and adults for this event
    booked_child_ids = set(
        booking.child_id for booking in db.query(Booking).filter(
            Booking.event_id == event_id,
            Booking.child_id.in_([child.id for child in children]),
            Booking.booking_status != "cancelled"
        ).all()
    )
    
    booked_adult_ids = set(
        booking.adult_id for booking in db.query(AdultBooking).filter(
            AdultBooking.event_id == event_id,
            AdultBooking.adult_id.in_([adult.id for adult in adults]),
            AdultBooking.booking_status != "cancelled"
        ).all()
    )
    
    return templates.TemplateResponse("booking.html", {
        "request": request, 
        "event": event, 
        "user": user, 
        "children": children, 
        "adults": adults, 
        "booked_child_ids": booked_child_ids,
        "booked_adult_ids": booked_adult_ids,
        "success": None, 
        "error": None, 
        "csrf_token": generate_csrf_token()
    })

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
    new_child_needs_adult: List[bool] = Form([]),
    adult_ids: List[int] = Form([]),
    new_adult_names: List[str] = Form([]),
    new_adult_relationships: List[str] = Form([]),
    new_adult_phones: List[str] = Form([]),
    new_adult_emails: List[str] = Form([]),
    new_adult_allergies: List[str] = Form([]),
    new_adult_roles: List[str] = Form([]),
    new_adult_can_supervise: List[bool] = Form([]),
    new_adult_volunteer: List[bool] = Form([]),
    csrf_token: str = Form(None)
):
    # Get all form data to handle dynamic adult role fields early
    form_data = await request.form()
    
    if not user:
        return RedirectResponse(url="/login", status_code=HTTP_303_SEE_OTHER)
    if not csrf_token or not verify_csrf_token(csrf_token):
        event = db.query(Event).filter(Event.id == event_id).first()
        children = db.query(Child).filter(Child.user_id == user.id).all()
        adults = db.query(Adult).filter(Adult.user_id == user.id).all()
        
        # Get already booked children and adults for this event
        booked_child_ids = set(
            booking.child_id for booking in db.query(Booking).filter(
                Booking.event_id == event_id,
                Booking.child_id.in_([child.id for child in children]),
                Booking.booking_status != "cancelled"
            ).all()
        )
        
        booked_adult_ids = set(
            booking.adult_id for booking in db.query(AdultBooking).filter(
                AdultBooking.event_id == event_id,
                AdultBooking.adult_id.in_([adult.id for adult in adults]),
                AdultBooking.booking_status != "cancelled"
            ).all()
        )
        
        return templates.TemplateResponse("booking.html", {
            "request": request, 
            "event": event, 
            "user": user, 
            "children": children, 
            "adults": adults, 
            "booked_child_ids": booked_child_ids,
            "booked_adult_ids": booked_adult_ids,
            "success": None, 
            "error": "Invalid or missing CSRF token.", 
            "csrf_token": generate_csrf_token()
        })
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        return HTMLResponse(content="<h1>Event not found</h1>", status_code=404)
    error = None
    success = None
    booked_children = []
    duplicate_children = []
    booked_adults = []
    duplicate_adults = []
    already_booked_children = []
    already_booked_adults = []
    
    # Book existing children
    for cid in child_ids:
        child = db.query(Child).filter(Child.id == cid, Child.user_id == user.id).first()
        if child:
            # Check if this child is already booked for this event
            existing_booking = db.query(Booking).filter(
                Booking.event_id == event.id,
                Booking.child_id == child.id,
                Booking.booking_status != "cancelled"
            ).first()
            
            if existing_booking:
                already_booked_children.append(child.name)
            else:
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
            # Still book the existing child if not already selected and not already booked for this event
            if existing_child.id not in child_ids:
                # Check if this child is already booked for this event
                existing_booking = db.query(Booking).filter(
                    Booking.event_id == event.id,
                    Booking.child_id == existing_child.id,
                    Booking.booking_status != "cancelled"
                ).first()
                
                if existing_booking:
                    already_booked_children.append(existing_child.name)
                else:
                    booking = Booking(event_id=event.id, child_id=existing_child.id)
                    db.add(booking)
                    booked_children.append(existing_child.name)
            continue
        
        age = int(new_child_ages[i]) if i < len(new_child_ages) and new_child_ages[i] else None
        allergies = new_child_allergies[i] if i < len(new_child_allergies) else None
        notes = new_child_notes[i] if i < len(new_child_notes) else None
        needs_adult = i < len(new_child_needs_adult) and new_child_needs_adult[i]
        
        child = Child(user_id=user.id, name=name.strip(), age=age, allergies=allergies, notes=notes, needs_assisting_adult=needs_adult)
        db.add(child)
        db.commit()
        db.refresh(child)
        
        # Check if this child is already booked for this event (shouldn't happen for new child, but safety check)
        existing_booking = db.query(Booking).filter(
            Booking.event_id == event.id,
            Booking.child_id == child.id,
            Booking.booking_status != "cancelled"
        ).first()
        
        if not existing_booking:
            booking = Booking(event_id=event.id, child_id=child.id)
            db.add(booking)
            booked_children.append(child.name)
    
    # Book existing adults
    for aid in adult_ids:
        adult = db.query(Adult).filter(Adult.id == aid, Adult.user_id == user.id).first()
        if adult:
            # Check if this adult is already booked for this event
            existing_booking = db.query(AdultBooking).filter(
                AdultBooking.event_id == event.id,
                AdultBooking.adult_id == adult.id,
                AdultBooking.booking_status != "cancelled"
            ).first()
            
            if existing_booking:
                already_booked_adults.append(adult.name)
            else:
                # Get the role for this adult from the form data
                role = form_data.get(f"adult_role_{aid}", "attendee")
                adult_booking = AdultBooking(event_id=event.id, adult_id=adult.id, role=role)
                db.add(adult_booking)
                booked_adults.append(adult.name)
    
    # Add and book new adults with duplicate detection
    for i, name in enumerate(new_adult_names):
        if not name.strip():
            continue
        
        # Check for duplicate adults (case-insensitive name matching)
        existing_adult = db.query(Adult).filter(
            Adult.user_id == user.id,
            Adult.name.ilike(name.strip())
        ).first()
        
        if existing_adult:
            duplicate_adults.append(name.strip())
            # Still book the existing adult if not already selected and not already booked for this event
            if existing_adult.id not in adult_ids:
                # Check if this adult is already booked for this event
                existing_booking = db.query(AdultBooking).filter(
                    AdultBooking.event_id == event.id,
                    AdultBooking.adult_id == existing_adult.id,
                    AdultBooking.booking_status != "cancelled"
                ).first()
                
                if existing_booking:
                    already_booked_adults.append(existing_adult.name)
                else:
                    role = new_adult_roles[i] if i < len(new_adult_roles) else "attendee"
                    adult_booking = AdultBooking(event_id=event.id, adult_id=existing_adult.id, role=role)
                    db.add(adult_booking)
                    booked_adults.append(existing_adult.name)
            continue
        
        relationship = new_adult_relationships[i] if i < len(new_adult_relationships) else None
        phone = new_adult_phones[i] if i < len(new_adult_phones) else None
        email = new_adult_emails[i] if i < len(new_adult_emails) else None
        allergies = new_adult_allergies[i] if i < len(new_adult_allergies) else None
        role = new_adult_roles[i] if i < len(new_adult_roles) else "attendee"
        can_supervise = i < len(new_adult_can_supervise) and new_adult_can_supervise[i]
        willing_volunteer = i < len(new_adult_volunteer) and new_adult_volunteer[i]
        
        adult = Adult(
            user_id=user.id, 
            name=name.strip(), 
            relationship_to_family=relationship,
            phone=phone,
            email=email,
            allergies=allergies,
            can_supervise_children=can_supervise,
            willing_to_volunteer=willing_volunteer
        )
        db.add(adult)
        db.commit()
        db.refresh(adult)
        
        # Check if this adult is already booked for this event (shouldn't happen for new adult, but safety check)
        existing_booking = db.query(AdultBooking).filter(
            AdultBooking.event_id == event.id,
            AdultBooking.adult_id == adult.id,
            AdultBooking.booking_status != "cancelled"
        ).first()
        
        if not existing_booking:
            adult_booking = AdultBooking(event_id=event.id, adult_id=adult.id, role=role)
            db.add(adult_booking)
            booked_adults.append(adult.name)
    
    # Check if event requires payment
    if event.cost and event.cost > 0:
        # Calculate total cost for newly booked participants only
        total_new_participants = len(booked_children) + len(booked_adults)
        if total_new_participants > 0:
            total_cost_dollars = event.cost * total_new_participants
            total_cost_cents = int(total_cost_dollars * 100)
        else:
            total_cost_cents = 0
        
        # Only proceed with payment if there are new bookings
        if total_new_participants > 0:
            # Create payment intent or checkout session
            payment_service = get_payment_service()
            booking_details = {
                'event_id': event.id,
                'event_title': event.title,
                'child_count': len(booked_children),
                'adult_count': len(booked_adults),
                'total_participants': total_new_participants
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
            # No new bookings to charge for, but we still need to mark any existing bookings as appropriate
            pass
    else:
        # Free event - mark as paid
        for booking in db.query(Booking).filter(
            Booking.event_id == event.id,
            Booking.child_id.in_([b.child_id for b in db.query(Booking).filter(Booking.event_id == event.id)])
        ):
            booking.payment_status = 'paid'
    
    db.commit()
    children = db.query(Child).filter(Child.user_id == user.id).all()
    adults = db.query(Adult).filter(Adult.user_id == user.id).all()
    
    # Get updated already booked children and adults for this event after processing
    booked_child_ids_final = set(
        booking.child_id for booking in db.query(Booking).filter(
            Booking.event_id == event_id,
            Booking.child_id.in_([child.id for child in children]),
            Booking.booking_status != "cancelled"
        ).all()
    )
    
    booked_adult_ids_final = set(
        booking.adult_id for booking in db.query(AdultBooking).filter(
            AdultBooking.event_id == event_id,
            AdultBooking.adult_id.in_([adult.id for adult in adults]),
            AdultBooking.booking_status != "cancelled"
        ).all()
    )
    
    if booked_children or booked_adults or already_booked_children or already_booked_adults:
        success_parts = []
        if booked_children:
            success_parts.append(f"New bookings - Children: {', '.join(booked_children)}")
        if booked_adults:
            success_parts.append(f"New bookings - Adults: {', '.join(booked_adults)}")
        
        # Add information about duplicates
        if already_booked_children or already_booked_adults:
            duplicate_parts = []
            if already_booked_children:
                duplicate_parts.append(f"Children: {', '.join(already_booked_children)}")
            if already_booked_adults:
                duplicate_parts.append(f"Adults: {', '.join(already_booked_adults)}")
            success_parts.append(f"Already booked - {' | '.join(duplicate_parts)}")
        
        if duplicate_children or duplicate_adults:
            existing_parts = []
            if duplicate_children:
                existing_parts.append(f"Children: {', '.join(duplicate_children)}")
            if duplicate_adults:
                existing_parts.append(f"Adults: {', '.join(duplicate_adults)}")
            success_parts.append(f"(Note: {' | '.join(existing_parts)} already existed and were used instead)")
        
        if success_parts:
            success = ' | '.join(success_parts)
        
        if booked_children or booked_adults:
            if event.cost and event.cost > 0:
                success += " - Redirecting to payment..."
        elif already_booked_children or already_booked_adults:
            success += " - No payment required (already registered)"
    else:
        error = "No participants selected or added."
    
    return templates.TemplateResponse("booking.html", {
        "request": request, 
        "event": event, 
        "user": user, 
        "children": children, 
        "adults": adults, 
        "booked_child_ids": booked_child_ids_final,
        "booked_adult_ids": booked_adult_ids_final,
        "success": success, 
        "error": error, 
        "csrf_token": generate_csrf_token()
    })

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
async def admin_events(request: Request, user: User = Depends(require_admin), db: Session = Depends(get_db), draft_saved: int = Query(None), updated: int = Query(None)):
    events = db.query(Event).order_by(Event.date.desc()).all()
    
    # Check for success messages
    success_message = None
    if draft_saved:
        draft_event = db.query(Event).filter(Event.id == draft_saved).first()
        if draft_event:
            success_message = f"✅ Draft event '{draft_event.title}' saved successfully! You can continue editing it later."
    elif updated:
        updated_event = db.query(Event).filter(Event.id == updated).first()
        if updated_event:
            success_message = f"✅ Event '{updated_event.title}' updated successfully!"
    
    return templates.TemplateResponse("admin_events.html", {
        "request": request,
        "current_user": user,
        "events": events,
        "success_message": success_message,
        "csrf_token": generate_csrf_token()
    })

@app.get("/admin/events/{event_id}/edit", response_class=HTMLResponse)
async def edit_event_form(request: Request, event_id: int, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    return templates.TemplateResponse("edit_event.html", {
        "request": request,
        "current_user": user,
        "event": event,
        "csrf_token": generate_csrf_token()
    })

@app.post("/admin/events/{event_id}/edit", response_class=HTMLResponse)
async def edit_event_post(
    request: Request,
    event_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
    # All the same fields as create event
    title: str = Form(...),
    subtitle: str = Form(""),
    event_type: str = Form(""),
    status: str = Form("draft"),
    short_description: str = Form(""),
    description: str = Form(""),
    start_date: str = Form(...),
    end_date: str = Form(""),
    timezone: str = Form("Pacific/Auckland"),
    is_recurring: bool = Form(False),
    event_format: str = Form(""),
    max_participants: str = Form(""),
    min_age: str = Form(""),
    max_age: str = Form(""),
    venue_name: str = Form(""),
    address: str = Form(""),
    city: str = Form(""),
    state: str = Form(""),
    zip_code: str = Form(""),
    country: str = Form("New Zealand"),
    meeting_id: str = Form(""),
    meeting_password: str = Form(""),
    what_to_bring: str = Form(""),
    dress_code: str = Form(""),
    language: str = Form("english"),
    accessibility_info: str = Form(""),
    parking_info: str = Form(""),
    video_url: str = Form(""),
    event_agenda: str = Form(""),
    speaker_info: str = Form(""),
    rich_description: str = Form(""),
    cost: str = Form(""),
    is_free: bool = Form(False),
    requires_registration: bool = Form(True),
    early_bird_discount: str = Form(""),
    group_discount: str = Form(""),
    member_discount: str = Form(""),
    registration_deadline: str = Form(""),
    website_url: str = Form(""),
    booking_url: str = Form(""),
    facebook_url: str = Form(""),
    instagram_url: str = Form(""),
    twitter_url: str = Form(""),
    linkedin_url: str = Form(""),
    youtube_url: str = Form(""),
    tiktok_url: str = Form(""),
    venue_website: str = Form(""),
    partner_url: str = Form(""),
    contact_name: str = Form(""),
    contact_email: str = Form(""),
    contact_phone: str = Form(""),
    emergency_contact: str = Form(""),
    terms_url: str = Form(""),
    privacy_policy_url: str = Form(""),
    featured_event: bool = Form(False),
    send_notifications: bool = Form(True),
    seo_keywords: str = Form(""),
    featured_image: UploadFile = File(None),
    csrf_token: str = Form(None)
):
    # CSRF check
    if not csrf_token or not verify_csrf_token(csrf_token):
        return templates.TemplateResponse("edit_event.html", {
            "request": request,
            "current_user": user,
            "error": "Invalid or missing CSRF token.",
            "csrf_token": generate_csrf_token()
        })

    try:
        # Get the existing event
        event = db.query(Event).filter(Event.id == event_id).first()
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")

        # Helper functions for safe parsing
        def safe_float_parse(value):
            if not value or value.strip() == "":
                return None
            try:
                return float(value)
            except (ValueError, TypeError):
                return None

        def safe_int_parse(value):
            if not value or value.strip() == "":
                return None
            try:
                return int(value)
            except (ValueError, TypeError):
                return None

        # Parse dates
        start_datetime = datetime.strptime(start_date, "%Y-%m-%dT%H:%M")
        end_datetime = None
        if end_date:
            end_datetime = datetime.strptime(end_date, "%Y-%m-%dT%H:%M")
        
        registration_deadline_datetime = None
        if registration_deadline:
            registration_deadline_datetime = datetime.strptime(registration_deadline, "%Y-%m-%dT%H:%M")

        # Handle image upload
        final_image_url = event.image_url  # Keep existing image by default
        if featured_image and featured_image.filename:
            if not featured_image.content_type.startswith("image/"):
                return templates.TemplateResponse("edit_event.html", {
                    "request": request,
                    "current_user": user,
                    "event": event,
                    "error": "Only image files are allowed.",
                    "csrf_token": generate_csrf_token()
                })

            ext = featured_image.filename.split('.')[-1]
            unique_name = f"{uuid.uuid4().hex}.{ext}"
            
            import os
            os.makedirs("app/static/event_images", exist_ok=True)
            
            save_path = f"app/static/event_images/{unique_name}"
            with open(save_path, "wb") as buffer:
                shutil.copyfileobj(featured_image.file, buffer)
            final_image_url = f"/static/event_images/{unique_name}"

        # Update all fields
        event.title = title
        event.subtitle = subtitle
        event.event_type = event_type
        event.status = status
        event.short_description = short_description
        event.description = description
        event.date = start_datetime
        event.end_date = end_datetime
        event.timezone = timezone
        event.is_recurring = is_recurring
        event.event_format = event_format
        event.max_participants = safe_int_parse(max_participants)
        event.min_age = safe_int_parse(min_age)
        event.max_age = safe_int_parse(max_age)
        event.venue_name = venue_name
        event.address = address
        event.city = city
        event.state = state
        event.zip_code = zip_code
        event.country = country
        event.meeting_id = meeting_id
        event.meeting_password = meeting_password
        event.what_to_bring = what_to_bring
        event.dress_code = dress_code
        event.language = language
        event.accessibility_info = accessibility_info
        event.parking_info = parking_info
        event.image_url = final_image_url
        event.video_url = video_url
        event.event_agenda = event_agenda
        event.speaker_info = speaker_info
        event.rich_description = rich_description
        event.cost = safe_float_parse(cost)
        event.is_free = is_free
        event.requires_registration = requires_registration
        event.early_bird_discount = safe_float_parse(early_bird_discount)
        event.group_discount = safe_float_parse(group_discount)
        event.member_discount = safe_float_parse(member_discount)
        event.registration_deadline = registration_deadline_datetime
        event.website_url = website_url
        event.booking_url = booking_url
        event.facebook_url = facebook_url
        event.instagram_url = instagram_url
        event.twitter_url = twitter_url
        event.linkedin_url = linkedin_url
        event.youtube_url = youtube_url
        event.tiktok_url = tiktok_url
        event.venue_website = venue_website
        event.partner_url = partner_url
        event.contact_name = contact_name
        event.contact_email = contact_email
        event.contact_phone = contact_phone
        event.emergency_contact = emergency_contact
        event.terms_url = terms_url
        event.privacy_policy_url = privacy_policy_url
        event.featured_event = featured_event
        event.send_notifications = send_notifications
        event.seo_keywords = seo_keywords
        event.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(event)

        return RedirectResponse(url=f"/admin/events?updated={event.id}", status_code=HTTP_303_SEE_OTHER)

    except ValueError as e:
        return templates.TemplateResponse("edit_event.html", {
            "request": request,
            "current_user": user,
            "event": event,
            "error": f"Invalid date format: {str(e)}",
            "csrf_token": generate_csrf_token()
        })
    except Exception as e:
        return templates.TemplateResponse("edit_event.html", {
            "request": request,
            "current_user": user,
            "event": event,
            "error": f"Error updating event: {str(e)}",
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

# Middleware will be added after OAuth setup

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

# ============================================================================
# FAMILY MANAGEMENT ROUTES
# ============================================================================

@app.get("/family", response_class=HTMLResponse)
async def family_get(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    children = db.query(Child).filter(Child.user_id == user.id).all()
    adults = db.query(Adult).filter(Adult.user_id == user.id).all()
    return templates.TemplateResponse("family.html", {"request": request, "user": user, "children": children, "adults": adults, "success": None, "error": None, "csrf_token": generate_csrf_token()})

@app.post("/family/children/add", response_class=HTMLResponse)
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
    date_of_birth: str = Form(None),
    school_year: str = Form(None),
    emergency_contact_name: str = Form(None),
    emergency_contact_phone: str = Form(None),
    emergency_contact_relationship: str = Form(None),
    medical_conditions: str = Form(None),
    csrf_token: str = Form(None)
):
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    if not csrf_token or not verify_csrf_token(csrf_token):
        children = db.query(Child).filter(Child.user_id == user.id).all()
        adults = db.query(Adult).filter(Adult.user_id == user.id).all()
        return templates.TemplateResponse("family.html", {"request": request, "user": user, "children": children, "adults": adults, "success": None, "error": "Invalid or missing CSRF token.", "csrf_token": generate_csrf_token()})
    
    # Check for duplicate children
    existing_child = db.query(Child).filter(
        Child.user_id == user.id,
        Child.name.ilike(name.strip())
    ).first()
    
    if existing_child:
        children = db.query(Child).filter(Child.user_id == user.id).all()
        adults = db.query(Adult).filter(Adult.user_id == user.id).all()
        return templates.TemplateResponse("family.html", {"request": request, "user": user, "children": children, "adults": adults, "success": None, "error": f"A child named '{name.strip()}' already exists.", "csrf_token": generate_csrf_token()})
    
    # Parse date_of_birth if provided
    dob = None
    if date_of_birth:
        try:
            from datetime import datetime
            dob = datetime.strptime(date_of_birth, '%Y-%m-%d')
        except ValueError:
            pass
    
    child = Child(
        user_id=user.id,
        name=name.strip(),
        age=age,
        date_of_birth=dob,
        school_year=school_year,
        allergies=allergies,
        medical_conditions=medical_conditions,
        notes=notes,
        needs_assisting_adult=needs_assisting_adult,
        emergency_contact_name=emergency_contact_name,
        emergency_contact_phone=emergency_contact_phone,
        emergency_contact_relationship=emergency_contact_relationship,
        other_info=other_info
    )
    db.add(child)
    db.commit()
    
    children = db.query(Child).filter(Child.user_id == user.id).all()
    adults = db.query(Adult).filter(Adult.user_id == user.id).all()
    return templates.TemplateResponse("family.html", {"request": request, "user": user, "children": children, "adults": adults, "success": f"Child '{name.strip()}' added successfully!", "error": None, "csrf_token": generate_csrf_token()})

@app.post("/family/children/{child_id}/edit", response_class=HTMLResponse)
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
        adults = db.query(Adult).filter(Adult.user_id == user.id).all()
        return templates.TemplateResponse("family.html", {"request": request, "user": user, "children": children, "adults": adults, "success": None, "error": "Invalid or missing CSRF token.", "csrf_token": generate_csrf_token()})
    
    child = db.query(Child).filter(Child.id == child_id, Child.user_id == user.id).first()
    if not child:
        children = db.query(Child).filter(Child.user_id == user.id).all()
        adults = db.query(Adult).filter(Adult.user_id == user.id).all()
        return templates.TemplateResponse("family.html", {"request": request, "user": user, "children": children, "adults": adults, "success": None, "error": "Child not found.", "csrf_token": generate_csrf_token()})
    
    # Check for duplicate names (excluding current child)
    existing_child = db.query(Child).filter(
        Child.user_id == user.id,
        Child.name.ilike(name.strip()),
        Child.id != child_id
    ).first()
    
    if existing_child:
        children = db.query(Child).filter(Child.user_id == user.id).all()
        adults = db.query(Adult).filter(Adult.user_id == user.id).all()
        return templates.TemplateResponse("family.html", {"request": request, "user": user, "children": children, "adults": adults, "success": None, "error": f"A child named '{name.strip()}' already exists.", "csrf_token": generate_csrf_token()})
    
    child.name = name.strip()
    child.age = age
    child.allergies = allergies
    child.notes = notes
    child.needs_assisting_adult = needs_assisting_adult
    child.other_info = other_info
    db.commit()
    
    children = db.query(Child).filter(Child.user_id == user.id).all()
    adults = db.query(Adult).filter(Adult.user_id == user.id).all()
    return templates.TemplateResponse("family.html", {"request": request, "user": user, "children": children, "adults": adults, "success": f"Child '{name.strip()}' updated successfully!", "error": None, "csrf_token": generate_csrf_token()})

@app.post("/family/children/{child_id}/delete", response_class=HTMLResponse)
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
        adults = db.query(Adult).filter(Adult.user_id == user.id).all()
        return templates.TemplateResponse("family.html", {"request": request, "user": user, "children": children, "adults": adults, "success": None, "error": "Invalid or missing CSRF token.", "csrf_token": generate_csrf_token()})
    
    child = db.query(Child).filter(Child.id == child_id, Child.user_id == user.id).first()
    if not child:
        children = db.query(Child).filter(Child.user_id == user.id).all()
        adults = db.query(Adult).filter(Adult.user_id == user.id).all()
        return templates.TemplateResponse("family.html", {"request": request, "user": user, "children": children, "adults": adults, "success": None, "error": "Child not found.", "csrf_token": generate_csrf_token()})
    
    child_name = child.name
    # Delete associated bookings first
    db.query(Booking).filter(Booking.child_id == child_id).delete()
    db.delete(child)
    db.commit()
    
    children = db.query(Child).filter(Child.user_id == user.id).all()
    adults = db.query(Adult).filter(Adult.user_id == user.id).all()
    return templates.TemplateResponse("family.html", {"request": request, "user": user, "children": children, "adults": adults, "success": f"Child '{child_name}' deleted successfully!", "error": None, "csrf_token": generate_csrf_token()})

# ============================================================================
# ADULT MANAGEMENT ROUTES
# ============================================================================

@app.post("/family/adults/add", response_class=HTMLResponse)
async def add_adult(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    name: str = Form(...),
    relationship_to_family: str = Form(None),
    phone: str = Form(None),
    email: str = Form(None),
    date_of_birth: str = Form(None),
    allergies: str = Form(None),
    medical_conditions: str = Form(None),
    emergency_contact_name: str = Form(None),
    emergency_contact_phone: str = Form(None),
    emergency_contact_relationship: str = Form(None),
    supervision_qualifications: str = Form(None),
    volunteer_skills: str = Form(None),
    notes: str = Form(None),
    can_supervise_children: bool = Form(False),
    willing_to_volunteer: bool = Form(False),
    csrf_token: str = Form(None)
):
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    if not csrf_token or not verify_csrf_token(csrf_token):
        children = db.query(Child).filter(Child.user_id == user.id).all()
        adults = db.query(Adult).filter(Adult.user_id == user.id).all()
        return templates.TemplateResponse("family.html", {"request": request, "user": user, "children": children, "adults": adults, "success": None, "error": "Invalid or missing CSRF token.", "csrf_token": generate_csrf_token()})
    
    # Check for duplicate adults
    existing_adult = db.query(Adult).filter(
        Adult.user_id == user.id,
        Adult.name.ilike(name.strip())
    ).first()
    
    if existing_adult:
        children = db.query(Child).filter(Child.user_id == user.id).all()
        adults = db.query(Adult).filter(Adult.user_id == user.id).all()
        return templates.TemplateResponse("family.html", {"request": request, "user": user, "children": children, "adults": adults, "success": None, "error": f"An adult named '{name.strip()}' already exists.", "csrf_token": generate_csrf_token()})
    
    # Parse date_of_birth if provided
    dob = None
    if date_of_birth:
        try:
            from datetime import datetime
            dob = datetime.strptime(date_of_birth, '%Y-%m-%d')
        except ValueError:
            pass
    
    adult = Adult(
        user_id=user.id,
        name=name.strip(),
        relationship_to_family=relationship_to_family,
        phone=phone,
        email=email,
        date_of_birth=dob,
        allergies=allergies,
        medical_conditions=medical_conditions,
        emergency_contact_name=emergency_contact_name,
        emergency_contact_phone=emergency_contact_phone,
        emergency_contact_relationship=emergency_contact_relationship,
        supervision_qualifications=supervision_qualifications,
        volunteer_skills=volunteer_skills,
        notes=notes,
        can_supervise_children=can_supervise_children,
        willing_to_volunteer=willing_to_volunteer
    )
    db.add(adult)
    db.commit()
    
    children = db.query(Child).filter(Child.user_id == user.id).all()
    adults = db.query(Adult).filter(Adult.user_id == user.id).all()
    return templates.TemplateResponse("family.html", {"request": request, "user": user, "children": children, "adults": adults, "success": f"Adult '{name.strip()}' added successfully!", "error": None, "csrf_token": generate_csrf_token()})

@app.post("/family/adults/{adult_id}/edit", response_class=HTMLResponse)
async def edit_adult(
    request: Request,
    adult_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    name: str = Form(...),
    relationship_to_family: str = Form(None),
    phone: str = Form(None),
    email: str = Form(None),
    allergies: str = Form(None),
    medical_conditions: str = Form(None),
    supervision_qualifications: str = Form(None),
    notes: str = Form(None),
    can_supervise_children: bool = Form(False),
    willing_to_volunteer: bool = Form(False),
    csrf_token: str = Form(None)
):
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    if not csrf_token or not verify_csrf_token(csrf_token):
        children = db.query(Child).filter(Child.user_id == user.id).all()
        adults = db.query(Adult).filter(Adult.user_id == user.id).all()
        return templates.TemplateResponse("family.html", {"request": request, "user": user, "children": children, "adults": adults, "success": None, "error": "Invalid or missing CSRF token.", "csrf_token": generate_csrf_token()})
    
    adult = db.query(Adult).filter(Adult.id == adult_id, Adult.user_id == user.id).first()
    if not adult:
        children = db.query(Child).filter(Child.user_id == user.id).all()
        adults = db.query(Adult).filter(Adult.user_id == user.id).all()
        return templates.TemplateResponse("family.html", {"request": request, "user": user, "children": children, "adults": adults, "success": None, "error": "Adult not found.", "csrf_token": generate_csrf_token()})
    
    # Check for duplicate names (excluding current adult)
    existing_adult = db.query(Adult).filter(
        Adult.user_id == user.id,
        Adult.name.ilike(name.strip()),
        Adult.id != adult_id
    ).first()
    
    if existing_adult:
        children = db.query(Child).filter(Child.user_id == user.id).all()
        adults = db.query(Adult).filter(Adult.user_id == user.id).all()
        return templates.TemplateResponse("family.html", {"request": request, "user": user, "children": children, "adults": adults, "success": None, "error": f"An adult named '{name.strip()}' already exists.", "csrf_token": generate_csrf_token()})
    
    adult.name = name.strip()
    adult.relationship_to_family = relationship_to_family
    adult.phone = phone
    adult.email = email
    adult.allergies = allergies
    adult.medical_conditions = medical_conditions
    adult.supervision_qualifications = supervision_qualifications
    adult.notes = notes
    adult.can_supervise_children = can_supervise_children
    adult.willing_to_volunteer = willing_to_volunteer
    db.commit()
    
    children = db.query(Child).filter(Child.user_id == user.id).all()
    adults = db.query(Adult).filter(Adult.user_id == user.id).all()
    return templates.TemplateResponse("family.html", {"request": request, "user": user, "children": children, "adults": adults, "success": f"Adult '{name.strip()}' updated successfully!", "error": None, "csrf_token": generate_csrf_token()})

@app.post("/family/adults/{adult_id}/delete", response_class=HTMLResponse)
async def delete_adult(
    request: Request,
    adult_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    csrf_token: str = Form(None)
):
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    if not csrf_token or not verify_csrf_token(csrf_token):
        children = db.query(Child).filter(Child.user_id == user.id).all()
        adults = db.query(Adult).filter(Adult.user_id == user.id).all()
        return templates.TemplateResponse("family.html", {"request": request, "user": user, "children": children, "adults": adults, "success": None, "error": "Invalid or missing CSRF token.", "csrf_token": generate_csrf_token()})
    
    adult = db.query(Adult).filter(Adult.id == adult_id, Adult.user_id == user.id).first()
    if not adult:
        children = db.query(Child).filter(Child.user_id == user.id).all()
        adults = db.query(Adult).filter(Adult.user_id == user.id).all()
        return templates.TemplateResponse("family.html", {"request": request, "user": user, "children": children, "adults": adults, "success": None, "error": "Adult not found.", "csrf_token": generate_csrf_token()})
    
    adult_name = adult.name
    # Delete associated adult bookings first
    db.query(AdultBooking).filter(AdultBooking.adult_id == adult_id).delete()
    db.delete(adult)
    db.commit()
    
    children = db.query(Child).filter(Child.user_id == user.id).all()
    adults = db.query(Adult).filter(Adult.user_id == user.id).all()
    return templates.TemplateResponse("family.html", {"request": request, "user": user, "children": children, "adults": adults, "success": f"Adult '{adult_name}' deleted successfully!", "error": None, "csrf_token": generate_csrf_token()})

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
        joinedload(Event.bookings).joinedload(Booking.child).joinedload(Child.user),
        joinedload(Event.adult_bookings).joinedload(AdultBooking.adult).joinedload(Adult.user)
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
        joinedload(Event.bookings).joinedload(Booking.child).joinedload(Child.user),
        joinedload(Event.adult_bookings).joinedload(AdultBooking.adult).joinedload(Adult.user)
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
        joinedload(Event.bookings).joinedload(Booking.child).joinedload(Child.user),
        joinedload(Event.adult_bookings).joinedload(AdultBooking.adult).joinedload(Adult.user)
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

# ============================================================================
# AI MODULE INTEGRATION - Phase 3 Complete! 🚀
# ============================================================================
# The monolithic AI endpoints (previously ~1590 lines) have been replaced
# with our new modular AI service architecture from app/ai/
# ============================================================================

from app.ai.router import ai_router

# Include the AI router with all endpoints
app.include_router(ai_router, prefix="/api/ai")

# Add the main AI create event page route at root level
@app.get("/ai-create-event", response_class=HTMLResponse)
async def ai_create_event_main_page(
    request: Request,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Main AI event creation page accessible at /ai-create-event"""
    return templates.TemplateResponse("ai_create_event.html", {
        "request": request,
        "current_user": user,
        "csrf_token": generate_csrf_token()
    })

# ===== AI ADMIN ENDPOINTS =====
# These are at root level to be consistent with other admin routes

@app.get("/admin/ai-models", response_class=HTMLResponse)
async def admin_ai_models(request: Request, user: User = Depends(require_admin)):
    """Show AI model configuration page"""
    from app.ai.services import ModelService
    model_service = ModelService()
    return model_service.get_available_models(request, user)

@app.post("/admin/ai-models/set-current")
async def set_current_ai_model(
    request: Request,
    model_key: str = Form(...),
    csrf_token: str = Form(...),
    user: User = Depends(require_admin)
):
    """Set the current AI model"""
    try:
        from app.ai.services import ModelService
        model_service = ModelService()
        return await model_service.set_current_model(model_key, user, csrf_token)
        
    except Exception as e:
        logging.error(f"Failed to set AI model: {e}")
        return {
            "success": False,
            "message": f"Failed to set AI model: {str(e)}"
        }

@app.post("/admin/ai-models/{model_key}/test")
async def test_ai_model(
    model_key: str,
    request: Request,
    csrf_token: str = Form(...),
    user: User = Depends(get_current_user)
):
    """Test an AI model with chat and function calling capabilities"""
    try:
        from app.ai.services import ModelService
        model_service = ModelService()
        return await model_service.test_model(model_key, user, csrf_token)
        
    except Exception as e:
        logging.error(f"Failed to test AI model: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "Model testing failed"
        }

@app.post("/admin/ai-models/refresh-ollama")
async def refresh_ollama_models(
    request: Request,
    csrf_token: str = Form(...),
    user: User = Depends(require_admin)
):
    """Refresh available Ollama models"""
    try:
        from app.ai.services import ModelService
        model_service = ModelService()
        return await model_service.refresh_ollama_models(user, csrf_token)
    except Exception as e:
        logging.error(f"Failed to refresh Ollama models: {e}")
        return {
            "success": False,
            "message": f"Failed to refresh models: {str(e)}"
        }

@app.get("/admin/cancellation-requests", response_class=HTMLResponse)
async def admin_cancellation_requests(request: Request, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Admin page to view and manage all cancellation requests"""
    
    # Get all bookings with cancellation requests
    cancellation_requests = db.query(Booking).filter(
        Booking.booking_status == "cancellation_requested"
    ).join(Event).join(Child).join(User).order_by(Booking.cancellation_requested_at.desc()).all()
    
    # Get adult booking cancellation requests too
    adult_cancellation_requests = db.query(AdultBooking).filter(
        AdultBooking.booking_status == "cancellation_requested"
    ).join(Event).join(Adult).join(User).order_by(AdultBooking.cancellation_requested_at.desc()).all()
    
    # Calculate statistics
    total_requests = len(cancellation_requests) + len(adult_cancellation_requests)
    paid_requests = len([b for b in cancellation_requests if b.payment_status == 'paid']) + \
                   len([b for b in adult_cancellation_requests if b.payment_status == 'paid'])
    total_refund_amount = sum(b.event.cost or 0 for b in cancellation_requests if b.payment_status == 'paid') + \
                         sum(b.event.cost or 0 for b in adult_cancellation_requests if b.payment_status == 'paid')
    
    stats = {
        "total_requests": total_requests,
        "paid_requests": paid_requests,
        "total_refund_amount": total_refund_amount
    }
    
    return templates.TemplateResponse("admin_cancellation_requests.html", {
        "request": request,
        "current_user": user,
        "cancellation_requests": cancellation_requests,
        "adult_cancellation_requests": adult_cancellation_requests,
        "stats": stats,
        "csrf_token": generate_csrf_token()
    })

@app.post("/admin/bookings/{booking_id}/approve-cancellation", response_class=HTMLResponse)
async def approve_booking_cancellation(
    request: Request,
    booking_id: int,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    refund_amount: float = Form(None),
    refund_reason: str = Form(None),
    csrf_token: str = Form(None)
):
    """Approve a booking cancellation and process refund if needed"""
    if not csrf_token or not verify_csrf_token(csrf_token):
        raise HTTPException(status_code=400, detail="Invalid CSRF token")
    
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    if booking.booking_status != "cancellation_requested":
        raise HTTPException(status_code=400, detail="Booking is not pending cancellation")
    
    # Process refund if payment was made
    if booking.payment_status == 'paid' and booking.event.cost and booking.event.cost > 0:
        # Calculate refund amount (default to full amount if not specified)
        refund_amount = refund_amount or float(booking.event.cost)
        
        # Process refund through payment service
        payment_service = get_payment_service()
        if booking.stripe_payment_id:
            refund_result = payment_service.process_refund(
                payment_intent_id=booking.stripe_payment_id,
                amount_cents=int(refund_amount * 100),
                reason=refund_reason or "Customer cancellation approved"
            )
            
            if refund_result['success']:
                booking.refund_processed = True
                booking.refund_amount = refund_amount
                booking.refund_processed_at = datetime.utcnow()
            else:
                # Log refund failure but still approve cancellation
                print(f"Refund failed for booking {booking_id}: {refund_result.get('error')}")
        else:
            # Manual refund tracking
            booking.refund_processed = True
            booking.refund_amount = refund_amount
            booking.refund_processed_at = datetime.utcnow()
    
    # Approve the cancellation
    booking.booking_status = "cancelled"
    booking.cancelled_at = datetime.utcnow()
    booking.cancellation_approved_by = user.id
    booking.cancellation_approved_at = datetime.utcnow()
    
    db.commit()
    
    # Send notification email to customer
    try:
        refund_info = ""
        if booking.refund_processed:
            refund_info = f"""
Refund Amount: ${booking.refund_amount:.2f}
Refund Reason: {refund_reason or "Customer cancellation approved"}

Your refund will be processed within 5-10 business days.
"""
        
        customer_email_body = f"""
Your cancellation request has been approved.

Event: {booking.event.title}
Date: {booking.event.date.strftime('%B %d, %Y at %I:%M %p')}
Child: {booking.child.name}

{refund_info}
Thank you for your understanding.
"""
        send_email(booking.child.user.email, f"Cancellation Approved - {booking.event.title}", customer_email_body)
    except Exception as e:
        print(f"Failed to send customer notification: {e}")
    
    return RedirectResponse(url="/admin/cancellation-requests", status_code=HTTP_303_SEE_OTHER)

@app.post("/admin/bookings/{booking_id}/deny-cancellation", response_class=HTMLResponse)
async def deny_booking_cancellation(
    request: Request,
    booking_id: int,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    denial_reason: str = Form(...),
    csrf_token: str = Form(None)
):
    """Deny a booking cancellation request"""
    if not csrf_token or not verify_csrf_token(csrf_token):
        raise HTTPException(status_code=400, detail="Invalid CSRF token")
    
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    if booking.booking_status != "cancellation_requested":
        raise HTTPException(status_code=400, detail="Booking is not pending cancellation")
    
    # Revert to confirmed status
    booking.booking_status = "confirmed"
    booking.cancellation_requested_at = None
    booking.cancellation_reason = None
    
    db.commit()
    
    # Send notification email to customer
    try:
        customer_email_body = f"""
        Your cancellation request has been denied.
        
        Event: {booking.event.title}
        Date: {booking.event.date.strftime('%B %d, %Y at %I:%M %p')}
        Child: {booking.child.name}
        
        Reason: {denial_reason}
        
        Your booking remains confirmed. Please contact us if you have any questions.
        """
        send_email(booking.child.user.email, f"Cancellation Denied - {booking.event.title}", customer_email_body)
    except Exception as e:
        print(f"Failed to send customer notification: {e}")
    
    return RedirectResponse(url="/admin/cancellation-requests", status_code=HTTP_303_SEE_OTHER)

@app.post("/admin/adult-bookings/{booking_id}/approve-cancellation", response_class=HTMLResponse)
async def approve_adult_booking_cancellation(
    request: Request,
    booking_id: int,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    refund_amount: float = Form(None),
    refund_reason: str = Form(None),
    csrf_token: str = Form(None)
):
    """Approve an adult booking cancellation and process refund if needed"""
    if not csrf_token or not verify_csrf_token(csrf_token):
        raise HTTPException(status_code=400, detail="Invalid CSRF token")
    
    booking = db.query(AdultBooking).filter(AdultBooking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Adult booking not found")
    
    if booking.booking_status != "cancellation_requested":
        raise HTTPException(status_code=400, detail="Adult booking is not pending cancellation")
    
    # Process refund if payment was made
    if booking.payment_status == 'paid' and booking.event.cost and booking.event.cost > 0:
        # Calculate refund amount (default to full amount if not specified)
        refund_amount = refund_amount or float(booking.event.cost)
        
        # Process refund through payment service
        payment_service = get_payment_service()
        if booking.stripe_payment_id:
            refund_result = payment_service.process_refund(
                payment_intent_id=booking.stripe_payment_id,
                amount_cents=int(refund_amount * 100),
                reason=refund_reason or "Customer cancellation approved"
            )
            
            if refund_result['success']:
                booking.refund_processed = True
                booking.refund_amount = refund_amount
                booking.refund_processed_at = datetime.utcnow()
            else:
                # Log refund failure but still approve cancellation
                print(f"Refund failed for adult booking {booking_id}: {refund_result.get('error')}")
        else:
            # Manual refund tracking
            booking.refund_processed = True
            booking.refund_amount = refund_amount
            booking.refund_processed_at = datetime.utcnow()
    
    # Approve the cancellation
    booking.booking_status = "cancelled"
    booking.cancelled_at = datetime.utcnow()
    booking.cancellation_approved_by = user.id
    booking.cancellation_approved_at = datetime.utcnow()
    
    db.commit()
    
    # Send notification email to customer
    try:
        refund_info = ""
        if booking.refund_processed:
            refund_info = f"""
Refund Amount: ${booking.refund_amount:.2f}
Refund Reason: {refund_reason or "Customer cancellation approved"}

Your refund will be processed within 5-10 business days.
"""
        
        customer_email_body = f"""
Your cancellation request has been approved.

Event: {booking.event.title}
Date: {booking.event.date.strftime('%B %d, %Y at %I:%M %p')}
Adult: {booking.adult.name}

{refund_info}
Thank you for your understanding.
"""
        send_email(booking.adult.user.email, f"Cancellation Approved - {booking.event.title}", customer_email_body)
    except Exception as e:
        print(f"Failed to send customer notification: {e}")
    
    return RedirectResponse(url="/admin/cancellation-requests", status_code=HTTP_303_SEE_OTHER)

@app.post("/admin/adult-bookings/{booking_id}/deny-cancellation", response_class=HTMLResponse)
async def deny_adult_booking_cancellation(
    request: Request,
    booking_id: int,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    denial_reason: str = Form(...),
    csrf_token: str = Form(None)
):
    """Deny an adult booking cancellation request"""
    if not csrf_token or not verify_csrf_token(csrf_token):
        raise HTTPException(status_code=400, detail="Invalid CSRF token")
    
    booking = db.query(AdultBooking).filter(AdultBooking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Adult booking not found")
    
    if booking.booking_status != "cancellation_requested":
        raise HTTPException(status_code=400, detail="Adult booking is not pending cancellation")
    
    # Revert to confirmed status
    booking.booking_status = "confirmed"
    booking.cancellation_requested_at = None
    booking.cancellation_reason = None
    
    db.commit()
    
    # Send notification email to customer
    try:
        customer_email_body = f"""
        Your cancellation request has been denied.
        
        Event: {booking.event.title}
        Date: {booking.event.date.strftime('%B %d, %Y at %I:%M %p')}
        Adult: {booking.adult.name}
        
        Reason: {denial_reason}
        
        Your booking remains confirmed. Please contact us if you have any questions.
        """
        send_email(booking.adult.user.email, f"Cancellation Denied - {booking.event.title}", customer_email_body)
    except Exception as e:
        print(f"Failed to send customer notification: {e}")
    
    return RedirectResponse(url="/admin/cancellation-requests", status_code=HTTP_303_SEE_OTHER)


