import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./homeschool.db")
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    
    # Email
    SMTP_HOST: str = os.getenv("SMTP_HOST", "mailhog")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "1025"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASS: str = os.getenv("SMTP_PASS", "")
    
    # Site Configuration
    SITE_URL: str = os.getenv("SITE_URL", "http://localhost:8000")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    # Facebook OAuth Configuration
    FACEBOOK_CLIENT_ID: str = os.getenv("FACEBOOK_CLIENT_ID", "")
    FACEBOOK_CLIENT_SECRET: str = os.getenv("FACEBOOK_CLIENT_SECRET", "")
    FACEBOOK_REDIRECT_URI: str = f"{SITE_URL}/auth/facebook/callback"
    
    # Google OAuth Configuration
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_REDIRECT_URI: str = f"{SITE_URL}/auth/google/callback"
    
    # Stripe Configuration
    STRIPE_PUBLISHABLE_KEY: str = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
    STRIPE_SECRET_KEY: str = os.getenv("STRIPE_SECRET_KEY", "")
    STRIPE_WEBHOOK_SECRET: str = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    STRIPE_CURRENCY: str = os.getenv("STRIPE_CURRENCY", "nzd")
    
    # Payment Configuration
    ENABLE_PAYMENTS: bool = os.getenv("ENABLE_PAYMENTS", "false").lower() == "true"
    PAYMENT_SUCCESS_URL: str = f"{SITE_URL}/payment/success"
    PAYMENT_CANCEL_URL: str = f"{SITE_URL}/payment/cancel"
    
    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT.lower() in ("development", "dev", "local")
    
    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() in ("production", "prod")
    
    @property
    def stripe_is_test_mode(self) -> bool:
        return self.STRIPE_PUBLISHABLE_KEY.startswith("pk_test_") if self.STRIPE_PUBLISHABLE_KEY else True
    
    @property
    def facebook_oauth_enabled(self) -> bool:
        return bool(self.FACEBOOK_CLIENT_ID and self.FACEBOOK_CLIENT_SECRET)
    
    @property
    def google_oauth_enabled(self) -> bool:
        return bool(self.GOOGLE_CLIENT_ID and self.GOOGLE_CLIENT_SECRET)

config = Config() 