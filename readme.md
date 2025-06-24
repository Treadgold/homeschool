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

### For Event Organizers & Admins
- **Complete Event Management** - Create, edit, and manage events with rich content and image uploads
- **Advanced Admin Dashboard** - Real-time statistics, user management, and financial tracking
- **Payment Processing** - Integrated Stripe payment system with refund capabilities
- **Photo Gallery Management** - Upload and manage community photos with titles and descriptions
- **Comprehensive Analytics** - Track attendance, revenue, user engagement, and event performance

## ✨ Feature Showcase

### 🎪 **Event Management System**
- **Rich Event Creation** - Add titles, descriptions, dates, locations, capacity limits, age ranges, and costs
- **Image Upload Support** - Attach event photos with automatic optimization and secure storage
- **Multi-Part Events** - Support for series and multi-session events
- **Real-Time Capacity Tracking** - Automatic booking limits and availability updates
- **Event Categories** - Organize events by type (Science, Arts, Outdoor, etc.)
- **Location Details** - Comprehensive venue information and directions

### 👨‍👩‍👧‍👦 **Family & Child Management**
- **Child Profiles** - Store names, ages, allergies, special needs, and additional notes
- **Assisting Adult Tracking** - Flag children who need additional support
- **Allergy & Medical Information** - Critical health and safety data for event organizers
- **Family Dashboard** - Centralized view of all children and their bookings
- **Profile Updates** - Easy editing of child information and preferences

### 💳 **Payment & Financial Management**
- **Stripe Integration** - Secure payment processing with multiple payment methods
- **Payment Status Tracking** - Real-time payment confirmation and status updates
- **Refund Processing** - Admin-controlled refund system with reason tracking
- **Financial Dashboard** - Revenue tracking, payment analytics, and financial reporting
- **Manual Payment Entry** - Support for cash payments and external transactions

### 📊 **Advanced Analytics & Reporting**
- **Real-Time Statistics** - Live dashboard with key metrics and trends
- **Event Performance Analytics** - Track attendance, capacity utilization, and popularity
- **User Engagement Metrics** - Monitor registration trends and user activity
- **Financial Reporting** - Revenue analysis, payment tracking, and financial insights
- **Export Capabilities** - Download reports in various formats for external analysis

### 🖼️ **Photo Gallery System**
- **Community Photo Sharing** - Upload and display event photos with titles and descriptions
- **Admin Gallery Management** - Full control over photo uploads, editing, and deletion
- **Responsive Gallery Grid** - Beautiful, mobile-friendly photo display
- **Upload Date Tracking** - Automatic timestamping of all gallery content
- **Image Optimization** - Automatic resizing and compression for optimal performance

### 🔐 **Security & User Management**
- **Secure Authentication** - Email confirmation, password hashing, and session management
- **Rate Limiting** - Protection against abuse with intelligent request throttling
- **CSRF Protection** - Form security with token validation
- **Admin User Management** - Promote users to admin status with full system access
- **Email Verification** - Required email confirmation for account activation

### 📧 **Communication System**
- **Automated Email Notifications** - Booking confirmations, event reminders, and updates
- **Email Confirmation System** - Secure token-based email verification
- **Resend Confirmation** - User-friendly email re-sending functionality
- **SMTP Integration** - Professional email delivery with custom branding
- **Development Email Testing** - MailHog integration for local development

## 🛠 Technology Stack

### **Modern Backend Architecture**
- **FastAPI** - High-performance, modern Python web framework
- **SQLAlchemy ORM** - Robust database abstraction and query building
- **PostgreSQL** - Enterprise-grade relational database
- **Alembic** - Database migration management with version control

### **Security & Authentication**
- **Bcrypt** - Industry-standard password hashing with salt
- **Session Management** - Secure HTTP-only cookies with encryption
- **Rate Limiting** - IP-based request throttling with SlowAPI
- **CSRF Protection** - Token-based form security

### **Payment & Financial**
- **Stripe API** - World-class payment processing integration
- **Webhook Handling** - Real-time payment event processing
- **Refund Management** - Automated and manual refund capabilities

### **File Management & Media**
- **Secure File Uploads** - Image validation, optimization, and secure storage
- **Static File Serving** - Efficient delivery of images, CSS, and JavaScript
- **UUID-based Filenames** - Secure, collision-resistant file naming

### **Development & Deployment**
- **Docker & Docker Compose** - Containerized deployment with multi-service orchestration
- **Uvicorn** - High-performance ASGI server
- **Environment Configuration** - Flexible configuration management
- **Development Tools** - MailHog for email testing, hot reloading

## 📁 Project Architecture

```
homeschool/
├── app/
│   ├── main.py              # FastAPI application with all routes and business logic
│   ├── models.py            # SQLAlchemy database models and relationships
│   ├── database.py          # Database connection and session management
│   ├── static/              # Static assets and uploaded content
│   │   ├── event_images/    # Event photos with secure storage
│   │   ├── gallery/         # Community photo gallery
│   │   ├── videos/          # Video content and media
│   │   └── style.css        # Modern, responsive styling
│   └── templates/           # Jinja2 HTML templates
│       ├── base.html        # Base template with navigation and layout
│       ├── landing.html     # Homepage with video hero section
│       ├── admin_*.html     # Comprehensive admin interface templates
│       ├── auth/            # Authentication and user management
│       └── events/          # Event-related templates
├── alembic/                 # Database migration management
│   ├── versions/            # Migration files with version control
│   └── env.py              # Alembic environment configuration
├── requirements.txt         # Python dependencies and versions
├── docker-compose.yml       # Multi-container orchestration
├── Dockerfile              # Application container definition
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
- **🏠 Homepage**: http://localhost:8000
- **📅 Events**: http://localhost:8000/events
- **👤 Signup**: http://localhost:8000/signup
- **🔐 Login**: http://localhost:8000/login
- **📊 Admin Dashboard**: http://localhost:8000/admin
- **🖼️ Photo Gallery**: http://localhost:8000/gallery

## 📊 Database Schema

### **Core Models & Relationships**
- **User** - Authentication, profile information, admin status
- **Event** - Event details, capacity, pricing, location, categories
- **Child** - Family member information, allergies, special needs
- **Booking** - Event registrations with payment status and volunteer info
- **GalleryImage** - Community photos with titles and descriptions

### **Key Features**
- **Multi-Child Support** - Users can register multiple children
- **Flexible Booking System** - Support for paid and free events
- **Payment Integration** - Stripe payment processing with status tracking
- **Admin Hierarchy** - User promotion system for community management
- **Rich Content** - Image uploads, descriptions, and metadata

## 🔒 Security Features

### **Authentication & Authorization**
- **Secure Password Hashing** - Bcrypt with salt for maximum security
- **Email Confirmation** - Required email verification for account activation
- **Session Management** - Encrypted, HTTP-only session cookies
- **Admin Access Control** - Role-based permissions and user promotion

### **Rate Limiting & Protection**
- **Signup Protection** - 5 requests per minute per IP
- **Login Protection** - 10 requests per minute per IP
- **Email Confirmation** - 3 requests per minute per IP
- **CSRF Protection** - Token validation on all forms

### **Data Security**
- **Input Validation** - Comprehensive data validation and sanitization
- **SQL Injection Prevention** - Parameterized queries via SQLAlchemy
- **File Upload Security** - Type validation and secure storage
- **XSS Protection** - Content sanitization and secure templates

## 📧 Email System

### **Automated Communications**
- **Welcome Emails** - New user onboarding with email confirmation
- **Booking Confirmations** - Instant booking confirmation emails
- **Event Reminders** - Automated event reminders and updates
- **Payment Confirmations** - Payment receipt and status updates

### **Admin Notifications**
- **New Booking Alerts** - Real-time notifications for event organizers
- **Capacity Alerts** - Automatic notifications when events reach capacity
- **Payment Notifications** - Instant alerts for successful payments
- **System Monitoring** - Error alerts and system status notifications

## 🎨 User Experience

### **Responsive Design**
- **Mobile-First Approach** - Optimized for all device sizes
- **Touch-Friendly Interface** - Intuitive navigation and interactions
- **Fast Loading** - Optimized images and efficient code delivery
- **Accessibility** - WCAG compliant design principles

### **Modern Interface**
- **Clean, Professional Design** - Beautiful, modern UI components
- **Intuitive Navigation** - Easy-to-use menu system and breadcrumbs
- **Dynamic Interactions** - JavaScript-enhanced user experience
- **Progressive Enhancement** - Core functionality works without JavaScript

## 🚀 Deployment & Production

### **Production Considerations**
- **SSL/TLS Certificates** - Secure HTTPS connections
- **Production Database** - Optimized PostgreSQL configuration
- **Email Service** - Professional SMTP service integration
- **Monitoring & Logging** - Application monitoring and error tracking
- **Backup Strategy** - Automated database and file backups

### **Docker Production Deployment**
```bash
# Build production image
docker build -t lifelearners:latest .

# Run with production settings
docker run -p 8000:8000 --env-file .env.prod lifelearners:latest
```

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