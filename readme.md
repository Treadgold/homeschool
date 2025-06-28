# 🏠 LifeLearners.org.nz - Complete Homeschool Event Management Platform

> **The Ultimate All-in-One Solution for Homeschool Communities in New Zealand**

Transform your homeschool community with our comprehensive event management platform. LifeLearners.org.nz is a modern, secure, and feature-rich web application designed specifically for homeschool families, event organizers, and community leaders across New Zealand.

## 🎯 Why Choose LifeLearners?

### For Homeschool Families
- **Seamless Event Discovery** - Browse upcoming events with rich details, photos, and real-time availability
- **Multi-Child Management** - Register multiple children with individual profiles, allergies, and special needs
- **Smart Booking System** - Book events with instant confirmation and easy cancellation
- **Family Dashboard** - Manage all your bookings, children's profiles, and event history in one place
- **Mobile-First Design** - Access everything on any device, anywhere
- **Secure Payment Processing** - Integrated Stripe payment system with instant confirmations

### For Event Organizers & Admins
- **Complete Event Management** - Create, edit, and manage events with rich content and image uploads
- **Advanced Admin Dashboard** - Real-time statistics, user management, and financial tracking
- **Integrated Payment System** - Full Stripe payment processing with refund capabilities
- **Photo Gallery Management** - Upload and manage community photos with titles and descriptions
- **Comprehensive Analytics** - Track attendance, revenue, user engagement, and event performance
- **Calendar View** - Visual calendar interface for managing all events

## ✨ Feature Showcase

### 🎪 **Event Management System**
- **Rich Event Creation** - Add titles, descriptions, dates, locations, capacity limits, age ranges, and costs
- **Image Upload Support** - Attach event photos with automatic optimization and secure storage
- **Multi-Part Events** - Support for series and multi-session events
- **Real-Time Capacity Tracking** - Automatic booking limits and availability updates
- **Event Categories** - Organize events by type (Science, Arts, Outdoor, etc.)
- **Location Details** - Comprehensive venue information and directions
- **Admin Calendar View** - Visual calendar interface with color-coded event status indicators

### 👨‍👩‍👧‍👦 **Family & Child Management**
- **Child Profiles** - Store names, ages, allergies, special needs, and additional notes
- **Assisting Adult Tracking** - Flag children who need additional support
- **Allergy & Medical Information** - Critical health and safety data for event organizers
- **Family Dashboard** - Centralized view of all children and their bookings
- **Profile Updates** - Easy editing of child information and preferences
- **Multi-Child Booking** - Book multiple children for events simultaneously

### 💳 **Payment & Financial Management**
- **Full Stripe Integration** - Secure payment processing with multiple payment methods
- **Checkout Session Management** - Seamless Stripe Checkout experience
- **Payment Status Tracking** - Real-time payment confirmation and status updates
- **Webhook Processing** - Automatic payment confirmation via Stripe webhooks
- **Refund Processing** - Admin-controlled refund system with reason tracking
- **Financial Dashboard** - Revenue tracking, payment analytics, and financial reporting
- **Mock Payment Mode** - Development-friendly payment simulation
- **NZD Currency Support** - Optimized for New Zealand pricing

### 📊 **Advanced Analytics & Reporting**
- **Real-Time Statistics** - Live dashboard with key metrics and trends
- **Event Performance Analytics** - Track attendance, capacity utilization, and popularity
- **User Engagement Metrics** - Monitor registration trends and user activity
- **Financial Reporting** - Revenue analysis, payment tracking, and financial insights
- **Booking Management** - Detailed participant lists and booking analytics
- **Export Capabilities** - Comprehensive admin tools for data management

### 🖼️ **Photo Gallery System**
- **Community Photo Sharing** - Upload and display event photos with titles and descriptions
- **Admin Gallery Management** - Full control over photo uploads, editing, and deletion
- **Responsive Gallery Grid** - Beautiful, mobile-friendly photo display
- **Upload Date Tracking** - Automatic timestamping of all gallery content
- **Image Optimization** - Secure file handling with UUID-based naming

### 🔐 **Security & User Management**
- **Multi-Provider Authentication** - Email, Facebook, and Google OAuth integration
- **Email Confirmation System** - Required email verification for account activation
- **Rate Limiting Protection** - Intelligent request throttling on sensitive endpoints
- **CSRF Protection** - Form security with token validation
- **Admin User Management** - Promote users to admin status with full system access
- **Password Security** - Bcrypt hashing with salt for maximum security

### 📧 **Communication System**
- **Automated Email Notifications** - Booking confirmations, event reminders, and updates
- **Email Confirmation System** - Secure token-based email verification
- **Resend Confirmation** - User-friendly email re-sending functionality
- **SMTP Integration** - Professional email delivery with custom branding
- **Development Email Testing** - MailHog integration for local development
- **Multi-Provider OAuth** - Social login integration with Facebook and Google

## 🛠 Technology Stack

### **Modern Backend Architecture**
- **FastAPI** - High-performance, modern Python web framework with async support
- **SQLAlchemy ORM** - Robust database abstraction and query building
- **PostgreSQL/SQLite** - Production PostgreSQL with SQLite for development
- **Alembic** - Database migration management with version control

### **Security & Authentication**
- **Bcrypt** - Industry-standard password hashing with salt
- **Session Management** - Secure HTTP-only cookies with encryption
- **SlowAPI Rate Limiting** - IP-based request throttling with configurable limits
- **CSRF Protection** - Token-based form security across all endpoints
- **OAuth Integration** - Facebook and Google OAuth with Authlib

### **Payment & Financial**
- **Stripe API** - World-class payment processing integration
- **Webhook Handling** - Real-time payment event processing
- **Refund Management** - Automated and manual refund capabilities
- **Multi-Currency Support** - NZD primary with international expansion ready

### **File Management & Media**
- **Secure File Uploads** - Image validation, optimization, and secure storage
- **Static File Serving** - Efficient delivery of images, CSS, and JavaScript
- **UUID-based Filenames** - Secure, collision-resistant file naming
- **Gallery Management** - Complete photo management system

### **Development & Deployment**
- **Docker & Docker Compose** - Containerized deployment with multi-service orchestration
- **Uvicorn** - High-performance ASGI server with hot reloading
- **Environment Configuration** - Flexible configuration management
- **MailHog** - Email testing in development environment

## 📁 Project Architecture

```
homeschool/
├── app/
│   ├── main.py              # FastAPI application with all routes and business logic (1900+ lines)
│   ├── models.py            # SQLAlchemy database models and relationships
│   ├── database.py          # Database connection and session management
│   ├── config.py            # Environment configuration and settings
│   ├── payment_service.py   # Stripe integration and payment processing
│   ├── static/              # Static assets and uploaded content
│   │   ├── event_images/    # Event photos with secure storage
│   │   ├── gallery/         # Community photo gallery
│   │   └── style.css        # Modern, responsive styling
│   └── templates/           # Jinja2 HTML templates (27 template files)
│       ├── base.html        # Base template with navigation and layout
│       ├── landing.html     # Homepage with hero section
│       ├── admin_*.html     # Comprehensive admin interface templates
│       ├── auth/            # Authentication and user management
│       └── events/          # Event-related templates
├── alembic/                 # Database migration management
│   ├── versions/            # Migration files with version control
│   └── env.py              # Alembic environment configuration
├── requirements.txt         # Python dependencies and versions
├── docker-compose.yml       # Multi-container orchestration
├── Dockerfile              # Application container definition
├── PAYMENT_SETUP_GUIDE.md   # Comprehensive payment setup documentation
├── FACEBOOK_SETUP_GUIDE.md  # Facebook OAuth setup guide
└── readme.md               # This comprehensive documentation
```

## 🚀 Quick Start Guide

### **Prerequisites**
- Docker and Docker Compose
- Git

### **1. Clone & Setup**
```bash
git clone <repository-url>
cd homeschool
```

### **2. Environment Configuration**
Create a `.env` file in the project root:
```bash
# Security Configuration
SECRET_KEY=your-super-secret-key-here

# Database Configuration
DATABASE_URL=postgresql://user:pass@db:5432/homeschool

# Email Configuration
SMTP_HOST=mailhog
SMTP_PORT=1025
SMTP_USER=
SMTP_PASS=
SITE_URL=http://localhost:8000

# Payment Configuration (Optional for development)
ENABLE_PAYMENTS=true
STRIPE_PUBLISHABLE_KEY=pk_test_your_stripe_key
STRIPE_SECRET_KEY=sk_test_your_stripe_secret
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret
STRIPE_CURRENCY=nzd

# OAuth Configuration (Optional)
FACEBOOK_CLIENT_ID=your_facebook_client_id
FACEBOOK_CLIENT_SECRET=your_facebook_client_secret
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret

# Test Users (auto-created on startup)
TEST_USER_EMAIL=testuser@example.com
TEST_USER_PASSWORD=testuser123
TEST_ADMIN_EMAIL=testadmin@example.com
TEST_ADMIN_PASSWORD=testadmin123
```

### **3. Launch the Application**
```bash
# Build and start all services
docker-compose up --build

# Access the application:
# 🌐 Main App: http://localhost:8000
# 📧 Email Testing: http://localhost:8025 (MailHog)
```

### **4. Database Setup**
```bash
# Run database migrations
docker-compose exec web alembic upgrade head
```

### **5. Explore the Features**
- **🏠 Homepage**: http://localhost:8000 - Landing page with hero section
- **📅 Events**: http://localhost:8000/events - Browse all events
- **👤 Signup**: http://localhost:8000/signup - Create new account
- **🔐 Login**: http://localhost:8000/login - User authentication
- **👶 Profile**: http://localhost:8000/profile - Manage account and children
- **📊 Admin Dashboard**: http://localhost:8000/admin - Admin overview
- **🖼️ Photo Gallery**: http://localhost:8000/gallery - Community photos
- **💳 Payment Admin**: http://localhost:8000/admin/payments - Payment management
- **📅 Event Calendar**: http://localhost:8000/admin/events/calendar - Visual calendar

## 📊 Database Schema

### **Core Models & Relationships**
- **User** - Authentication, profile information, admin status, OAuth integration
- **Event** - Event details, capacity, pricing, location, categories, multi-part support
- **Child** - Family member information, allergies, special needs, assisting adult flags
- **Booking** - Event registrations with payment status and volunteer info
- **GalleryImage** - Community photos with titles, descriptions, and upload tracking

### **Key Features**
- OAuth integration fields (Facebook ID, Google ID, auth provider)
- Payment tracking (Stripe payment IDs, payment status)
- Comprehensive child information (allergies, special needs, assisting adults)
- Event categorization and multi-part event support
- Gallery management with metadata

## 💻 Development Features

### **Payment System**
- **Development Mode**: Mock payment service for testing without Stripe keys
- **Test Mode**: Full Stripe integration with test keys
- **Production Mode**: Live payment processing
- **Webhook Support**: Automatic payment confirmation
- **Refund Processing**: Admin-controlled refund system

### **Authentication Options**
- **Email/Password**: Traditional authentication with email confirmation
- **Facebook OAuth**: Social login integration
- **Google OAuth**: Google account integration
- **Admin Management**: Promote users to admin status

### **Development Tools**
- **MailHog**: Email testing in development
- **Hot Reload**: Automatic code reload during development
- **Database Migrations**: Version-controlled schema changes
- **Health Checks**: Application monitoring endpoints

## 📋 Recent Updates & Completions

### **✅ Recently Completed Features**
- ✅ **Full Stripe Payment Integration** - Complete payment processing system
- ✅ **Admin Calendar View** - Visual calendar interface for event management
- ✅ **Enhanced Booking Management** - Detailed participant tracking and management
- ✅ **OAuth Integration** - Facebook and Google social login
- ✅ **Gallery System** - Complete photo gallery with admin management
- ✅ **Rate Limiting & Security** - Comprehensive security measures
- ✅ **Payment Webhook Handling** - Automatic payment confirmation
- ✅ **Multi-Child Booking** - Book multiple children simultaneously
- ✅ **Admin Analytics** - Comprehensive statistics and reporting

### **🔄 Current Focus Areas**
- Payment system testing and optimization
- User experience improvements
- Performance optimization
- Security enhancements

## 🎯 Getting Started for Developers

1. **Quick Start**: Use the Docker setup for immediate development
2. **Payment Testing**: Review `PAYMENT_SETUP_GUIDE.md` for Stripe integration
3. **OAuth Setup**: Check `FACEBOOK_SETUP_GUIDE.md` for social login configuration
4. **Database Changes**: Use Alembic for schema migrations
5. **Testing**: Use test user accounts created automatically on startup

## 📚 Documentation

- **Payment Setup**: `PAYMENT_SETUP_GUIDE.md` - Comprehensive payment integration guide
- **Facebook OAuth**: `FACEBOOK_SETUP_GUIDE.md` - Social login setup
- **Todo List**: `todo-list.md` - Development roadmap and task tracking
- **Environment**: `.env.example` - Configuration template

## 🔧 Configuration

The application supports flexible configuration through environment variables:
- **Database**: PostgreSQL for production, SQLite for development
- **Payments**: Optional Stripe integration with mock mode
- **Email**: SMTP configuration with MailHog for testing
- **OAuth**: Optional Facebook and Google integration
- **Security**: Configurable rate limiting and CSRF protection

## 🚀 Production Deployment

The application is production-ready with:
- Docker containerization
- Database migrations
- Security hardening
- Payment processing
- Email system
- Monitoring and health checks

For production deployment, update the environment variables for your production environment and ensure proper security configurations are in place.

## 🤝 Community & Support

### **Getting Help**
- **Documentation** - Comprehensive guides and tutorials
- **Issue Tracking** - Bug reports and feature requests
- **Community Forum** - User discussions and support
- **Email Support** - Direct support for technical issues

### **Contributing**
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### **Development Guidelines**
- Follow PEP 8 style guidelines
- Add tests for new features
- Update documentation as needed
- Ensure all migrations are backward compatible

## 📈 Roadmap & Future Features

### **Coming Soon**
- **Advanced Payment Features** - Subscription payments, payment plans
- **Calendar Integration** - Google Calendar, Outlook sync
- **SMS Notifications** - Text message alerts and reminders
- **Waitlist Management** - Automatic waitlist promotion
- **Event Reviews** - User ratings and feedback system
- **API Development** - RESTful API for mobile apps and integrations

### **Advanced Analytics**
- **Predictive Analytics** - Event popularity forecasting
- **Geographic Analysis** - Location-based insights
- **User Behavior Tracking** - Engagement and retention metrics
- **Financial Forecasting** - Revenue prediction and planning

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🎉 Ready to Transform Your Homeschool Community?

LifeLearners.org.nz is more than just an event booking system - it's a complete community management platform designed specifically for homeschool families in New Zealand. With our comprehensive feature set, modern technology stack, and focus on security and user experience, we're helping homeschool communities thrive.

**Get started today and see the difference LifeLearners can make for your community!**

---

*Built with ❤️ for the New Zealand homeschool community*