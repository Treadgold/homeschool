# LifeLearners.org.nz - Homeschool Event Booking System

A comprehensive web application for managing and booking homeschool events in New Zealand. Built with modern web technologies to provide a seamless experience for parents, children, and event organizers.

## 🎯 Overview

LifeLearners is a community-driven platform that connects homeschool families across New Zealand through engaging events, workshops, and learning experiences. The system handles user registration, event management, booking processes, and administrative functions with a focus on security and user experience.

## ✨ Features

### For Parents & Families
- **User Registration & Authentication**: Secure signup with email confirmation
- **Profile Management**: Update personal information and manage children's profiles
- **Event Discovery**: Browse upcoming events with detailed information
- **Multi-Child Booking**: Book multiple children for events with individual details
- **Booking Management**: View, modify, and cancel event bookings
- **Child Profiles**: Store allergy information, special needs, and preferences

### For Administrators
- **Event Management**: Create, edit, and manage events with rich details
- **User Administration**: Promote users to admin status and manage accounts
- **Booking Oversight**: Monitor event registrations and participant lists
- **Content Management**: Upload event images and manage event details

### Technical Features
- **Responsive Design**: Mobile-friendly interface with modern CSS
- **Session Management**: Secure cookie-based authentication
- **File Upload**: Event image management with automatic storage
- **Email Integration**: Confirmation emails and notifications via SMTP
- **Database Migrations**: Version-controlled schema changes with Alembic

## 🛠 Technology Stack

### Backend
- **FastAPI** - Modern, fast web framework for building APIs
- **SQLAlchemy** - SQL toolkit and Object-Relational Mapping (ORM)
- **Alembic** - Database migration tool for SQLAlchemy
- **Passlib** - Password hashing and verification (bcrypt)
- **ItsDangerous** - Secure token generation for email confirmation
- **SlowAPI** - Rate limiting and throttling for API endpoints

### Frontend
- **Jinja2** - Template engine for server-side rendering
- **Vanilla JavaScript** - Dynamic UI interactions and form handling
- **CSS3** - Modern styling with responsive design principles

### Database & Storage
- **PostgreSQL** - Primary database (version 15)
- **SQLAlchemy ORM** - Database abstraction and query building

### Authentication & Security
- **Session Cookies** - Secure, HTTP-only session management
- **Password Hashing** - Bcrypt-based password security
- **Email Confirmation** - Token-based email verification system
- **Rate Limiting** - IP-based rate limiting for authentication endpoints (slowapi)

### Development & Deployment
- **Docker** - Containerized application deployment
- **Docker Compose** - Multi-service orchestration
- **Uvicorn** - ASGI server for FastAPI
- **MailHog** - Email testing and development SMTP server

### External Integrations
- **Stripe** - Payment processing (configured but not fully implemented)
- **SMTP** - Email delivery system

## 📁 Project Structure

```
homeschool/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application, routes, and business logic
│   ├── models.py            # SQLAlchemy database models
│   ├── database.py          # Database connection and session management
│   ├── static/              # Static assets (images, videos, CSS)
│   │   ├── event_images/    # Uploaded event images
│   │   └── videos/          # Video content
│   └── templates/           # Jinja2 HTML templates
│       ├── base.html        # Base template with navigation
│       ├── landing.html     # Homepage with video hero
│       ├── events/          # Event-related templates
│       ├── auth/            # Authentication templates
│       └── admin/           # Administrative templates
├── alembic/                 # Database migrations
│   ├── versions/            # Migration files
│   ├── env.py              # Alembic environment configuration
│   └── script.py.mako      # Migration template
├── requirements.txt         # Python dependencies
├── docker-compose.yml       # Multi-container orchestration
├── Dockerfile              # Application container definition
├── alembic.ini             # Alembic configuration
└── readme.md               # This file
```

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- Git

### 1. Clone the Repository
```bash
git clone <repository-url>
cd homeschool
```

### 2. Environment Configuration
Create a `.env` file in the project root:
```bash
# Security
SECRET_KEY=your-super-secret-key-here

# Database
DATABASE_URL=postgresql://user:pass@db:5432/homeschool

# Email Configuration
SMTP_HOST=mailhog
SMTP_PORT=1025
SMTP_USER=
SMTP_PASS=
SITE_URL=http://localhost:8000

# Test Users (auto-created on startup)
TEST_USER_EMAIL=testuser@example.com
TEST_USER_PASSWORD=testuser123
TEST_ADMIN_EMAIL=testadmin@example.com
TEST_ADMIN_PASSWORD=testadmin123
```

### 3. Start the Application
```bash
# Build and start all services
docker-compose up --build

# The application will be available at:
# - Main App: http://localhost:8000
# - Email Testing: http://localhost:8025 (MailHog)
```

### 4. Database Setup
```bash
# Run database migrations
docker-compose exec web alembic upgrade head
```

### 5. Access the Application
- **Homepage**: http://localhost:8000
- **Events**: http://localhost:8000/events
- **Signup**: http://localhost:8000/signup
- **Login**: http://localhost:8000/login
- **Admin Panel**: http://localhost:8000/admin/users

## 🔧 Development

### Local Development Setup
```bash
# Install Python dependencies
pip install -r requirements.txt

# Set up PostgreSQL database
# (Use Docker or local PostgreSQL instance)

# Run migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Database Migrations
```bash
# Create a new migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Rollback migrations
alembic downgrade -1
```

### Code Quality
The project follows Python best practices:
- Type hints where appropriate
- Comprehensive error handling
- Secure authentication patterns
- Clean separation of concerns

## 📊 Database Schema

### Core Models
- **User**: Authentication, profile information, admin status
- **Event**: Event details, capacity, pricing, location
- **Child**: Family member information, allergies, special needs
- **Booking**: Event registrations with payment status

### Key Relationships
- Users can have multiple children
- Children can have multiple bookings
- Events can have multiple bookings
- Admin users can manage all content

## 🔒 Security Features

- **Password Security**: Bcrypt hashing with salt
- **Session Management**: Secure HTTP-only cookies
- **Email Verification**: Token-based confirmation system
- **Rate Limiting**: IP-based rate limiting on authentication endpoints
  - Signup: 5 requests per minute
  - Login: 10 requests per minute
  - Email confirmation: 3 requests per minute
  - Email verification: 10 requests per minute
- **CSRF Protection**: Form-based security measures
- **Input Validation**: Comprehensive data validation
- **SQL Injection Prevention**: Parameterized queries via SQLAlchemy

## 📧 Email System

The application includes a complete email system:
- **Email Confirmation**: Required for account activation
- **Password Reset**: Secure token-based reset process
- **Event Notifications**: Booking confirmations and updates
- **Development Testing**: MailHog integration for local testing

## 🎨 User Interface

- **Responsive Design**: Works on desktop, tablet, and mobile
- **Modern Styling**: Clean, accessible interface
- **Dynamic Interactions**: JavaScript-enhanced user experience
- **Progressive Enhancement**: Core functionality works without JavaScript

## 🚀 Deployment

### Production Considerations
- Use production-grade ASGI server (Gunicorn + Uvicorn)
- Configure proper SMTP settings
- Set up SSL/TLS certificates
- Use environment-specific database configurations
- Implement proper logging and monitoring

### Docker Production
```bash
# Build production image
docker build -t lifelearners:latest .

# Run with production settings
docker run -p 8000:8000 --env-file .env.prod lifelearners:latest
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines
- Follow PEP 8 style guidelines
- Add tests for new features
- Update documentation as needed
- Ensure all migrations are backward compatible

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Check the TODO list for known issues and planned features
- Review the codebase documentation
- Open an issue for bugs or feature requests

## 🔮 Roadmap

See `todo-list.md` for detailed feature roadmap including:
- Payment integration with Stripe
- Advanced admin dashboard
- Waitlist functionality
- SMS notifications
- Calendar integration
- Accessibility improvements