# 🎓 LifeLearners.org.nz - Homeschool Event Management Platform

**Empowering New Zealand's homeschool community with seamless event booking, payments, and community building.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.68+-green.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-13+-blue.svg)](https://www.postgresql.org/)

## 📸 Screenshots

### Homepage - Welcoming Community Hub
![LifeLearners Homepage](docs/screenshots/lifelearners-home.jpg)
*Beautiful homepage with hero section, upcoming events preview, and clear call-to-actions*

### Interactive Events Map
![LifeLearners Events Map](docs/screenshots/lifelearners-events-map.jpg)
*Interactive map view showing event markers across New Zealand with clustering and detailed popups*

### Event Discovery & Booking
*[Screenshot of the events page showing both list and map views, filters, and detailed event cards]*

### Multi-Child Booking System
*[Screenshot of the booking form showing multiple children selection with allergy/dietary requirements]*

### Admin Dashboard
*[Screenshot of the comprehensive admin dashboard with analytics, calendar view, and event management]*

### Payment Integration
*[Screenshot of the Stripe payment flow with secure checkout and confirmation]*

## 🌟 Why LifeLearners?

New Zealand's homeschool community needs a **modern, trustworthy platform** that makes discovering and booking educational events effortless. LifeLearners delivers:

- **🗺️ Visual Discovery** - Interactive map showing events across New Zealand
- **👨‍👩‍👧‍👦 Family-Focused** - Multi-child booking with allergy management
- **💳 Secure Payments** - Stripe integration with instant confirmations
- **📱 Mobile-First** - Beautiful responsive design that works everywhere
- **🔒 Parent-Safe** - OAuth login, CSRF protection, and data privacy
- **📈 Growth-Ready** - Built to scale from local groups to national platform

## ✨ Key Features

### For Parents
- **📍 Interactive Event Map** - Discover local events visually with clustering and detailed popups
- **🔍 Smart Filtering** - Find workshops, field trips, free events, and more
- **👶 Multi-Child Booking** - Book for multiple children with individual requirements
- **🚨 Allergy Management** - Prominent allergy/dietary requirement tracking
- **💳 Seamless Payments** - Secure Stripe checkout with instant confirmations
- **🔐 OAuth Login** - Quick signup with Facebook or Google
- **📧 Email Notifications** - Booking confirmations and event reminders
- **📱 Mobile Optimized** - Perfect experience on phones and tablets

### For Administrators
- **📊 Comprehensive Dashboard** - Revenue analytics, booking trends, and key metrics
- **📅 Calendar Management** - Visual event scheduling with drag-and-drop
- **👥 Parent & Child Management** - Detailed profiles with allergy tracking
- **💰 Payment Tracking** - Monitor all transactions and payment statuses
- **📷 Photo Gallery** - Upload and manage event photos
- **📈 Analytics & Reports** - Track growth, popular events, and revenue
- **⚡ Real-time Updates** - Live booking counts and capacity management

### For Event Organizers
- **🎯 Easy Event Creation** - Rich forms with location, pricing, and capacity
- **📋 Attendee Management** - View bookings, special requirements, and contact info
- **💬 Communication Tools** - Direct messaging with parents
- **📊 Event Analytics** - Track popularity and gather feedback

## 🛠️ Technology Stack

### Backend
- **FastAPI** (Python) - High-performance async web framework
- **PostgreSQL** - Robust relational database with JSONB support
- **SQLAlchemy** - Powerful ORM with async support
- **Alembic** - Database migrations and versioning

### Frontend
- **Jinja2 Templates** - Server-side rendering for optimal SEO
- **Modern CSS Grid/Flexbox** - Responsive layouts without frameworks
- **Leaflet.js** - Interactive maps with clustering (no API keys needed)
- **Progressive Enhancement** - Works without JavaScript

### Infrastructure & Security
- **Docker** - Containerized deployment
- **NGINX** - High-performance reverse proxy
- **Redis** - Session storage and caching
- **Stripe** - PCI-compliant payment processing
- **OAuth 2.0** - Secure social authentication
- **CSRF Protection** - Form security
- **bcrypt** - Password hashing
- **Rate Limiting** - API protection

### Development & Monitoring
- **pytest** - Comprehensive testing suite
- **Black** - Code formatting
- **mypy** - Type checking
- **Sentry** - Error tracking
- **Prometheus** - Metrics collection

## 🚀 Quick Start

### Option 1: Docker (Recommended)
```bash
# Clone the repository
git clone https://github.com/yourusername/homeschool-platform.git
cd homeschool-platform

# Start all services
docker-compose up -d

# Load test data (optional)
docker-compose exec web python scripts/generate_test_data.py

# Visit the application
open http://localhost:8000
```

### Option 2: Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env.local
# Edit .env.local with your configuration

# Run database migrations
alembic upgrade head

# Start the application
uvicorn app.main:app --reload

# Visit the application
open http://localhost:8000
```

### Testing Email
The Docker setup includes MailHog for testing emails:
- **MailHog Interface**: http://localhost:8025
- All emails are captured locally (no external sending)

## 📋 Environment Configuration

Create a `.env.local` file with:

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost/homeschool_db

# Security
SECRET_KEY=your-secret-key-here
CSRF_SECRET_KEY=your-csrf-secret-here

# Stripe (use test keys for development)
STRIPE_PUBLIC_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# OAuth (optional)
FACEBOOK_CLIENT_ID=your-facebook-app-id
FACEBOOK_CLIENT_SECRET=your-facebook-app-secret
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Email (for production)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

## 🧪 Test Data

The platform includes a comprehensive test data generator:

```bash
# Generate realistic test data
python scripts/generate_test_data.py

# Creates:
# - 40 events across New Zealand
# - 20 parent accounts with children
# - 280+ bookings with mixed payment statuses
# - $6,000+ in test revenue for analytics
```

## 📊 Current Status

### ✅ Recently Completed Major Milestones

- **🗺️ Interactive Event Map** - Visual discovery with clustering and detailed popups
- **💳 Complete Payment System** - Stripe integration with webhooks and confirmations  
- **🔐 OAuth Integration** - Facebook and Google social login
- **👨‍👩‍👧‍👦 Multi-Child Booking** - Family-focused booking with allergy management
- **📊 Admin Dashboard** - Comprehensive analytics and calendar management
- **📷 Photo Gallery System** - Event photo uploads with admin moderation
- **🔒 Security Features** - CSRF protection, rate limiting, secure headers
- **📱 Mobile Optimization** - Responsive design with touch-friendly interface
- **🐳 Docker Containerization** - Production-ready deployment setup

### 📈 Platform Metrics (Test Data)
- **40** Diverse events across workshop, field trip, and social categories
- **25** Active users (20 parents + 5 admins)
- **39** Children with detailed profiles and allergy tracking
- **282** Total bookings with realistic payment distribution
- **$6,985** Test revenue demonstrating payment system functionality

## 🎯 Roadmap to National Scale

This platform is designed to scale from local homeschool groups to serve **all 11,000+ homeschooling families across New Zealand**. See our detailed scaling plans:

- **[ARCHITECTURE_DESIGN.md](ARCHITECTURE_DESIGN.md)** - Technical architecture for national scale
- **[SCALING_STRATEGY.md](SCALING_STRATEGY.md)** - Phase-by-phase growth plan with costs
- **[UX_PRIORITY_ROADMAP.md](UX_PRIORITY_ROADMAP.md)** - User experience improvements

### Next Phase Features
- **🎥 Video Course Platform** - Upload and stream educational content
- **💬 Community Chat** - Real-time messaging between families
- **📚 Resource Sharing** - Curriculum and material exchange
- **🏆 Achievement System** - Gamification for learning milestones
- **📱 Mobile App** - Native iOS/Android applications

## 🤝 Contributing

We welcome contributions from the homeschool community!

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'Add amazing feature'`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

### Development Setup
```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
pytest

# Format code
black .

# Type checking
mypy app/
```

## 📞 Support & Community

- **Email**: info@lifelearners.org.nz
- **GitHub Issues**: Report bugs and request features
- **Documentation**: Comprehensive guides in `/docs`
- **Community**: Join our homeschool parent network

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **New Zealand Homeschool Community** - For inspiration and feedback
- **Stripe** - For secure payment processing
- **Leaflet** - For beautiful, free mapping
- **FastAPI** - For the excellent Python web framework
- **OpenStreetMap** - For free, privacy-friendly maps

---

**Built with ❤️ for New Zealand's homeschool families**

*Empowering education, one event at a time.* 