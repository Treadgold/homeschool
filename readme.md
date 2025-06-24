# Homeschool Event Booking System

A web application for managing and booking homeschool events. Built with FastAPI, SQLAlchemy, Jinja2, and HTMX.

## Features
- User signup, login, and session management
- Admin portal for event and user management
- Event creation, listing, and detail pages
- Secure password hashing and session cookies
- Dockerized for easy local development

## Technology Stack
- **Backend:** FastAPI
- **Frontend:** Jinja2 templates + HTMX
- **Database:** PostgreSQL (via Docker)
- **ORM:** SQLAlchemy + Alembic
- **Auth:** Session cookies (with admin/parent separation)
- **Container:** Docker + Docker Compose

## Directory Structure
```
homeschool/
  ├── app/
  │   ├── main.py           # FastAPI app, routes, and logic
  │   ├── models.py         # SQLAlchemy models
  │   ├── database.py       # DB session and engine
  │   └── templates/        # Jinja2 HTML templates
  ├── alembic/              # DB migrations
  ├── requirements.txt      # Python dependencies
  ├── Dockerfile            # Docker build file
  ├── docker-compose.yml    # Multi-container setup
  └── readme.md             # This file
```

## Setup & Usage

### 1. Clone the repository
```bash
git clone <repo-url>
cd homeschool
```

### 2. Environment Variables
Create a `.env` file (or set these in your environment):
```
SECRET_KEY=your-secret-key
DATABASE_URL=postgresql://user:pass@db:5432/homeschool

# Test user credentials
TEST_USER_EMAIL=testuser@example.com
TEST_USER_PASSWORD=testuser123

# Test admin credentials
TEST_ADMIN_EMAIL=testadmin@example.com
TEST_ADMIN_PASSWORD=testadmin123
```

### 3. Start with Docker
```bash
docker-compose up --build
```
The app will be available at [http://localhost:8000](http://localhost:8000)

### 4. Database Migrations
```bash
docker-compose exec web alembic upgrade head
```

### 5. Access
- Home: `/`
- Signup/Login: `/signup`, `/login`
- Admin: `/admin/users`, `/admin/events/new`

## Development
- Python 3.11+
- Install dependencies: `pip install -r requirements.txt`
- Run locally: `uvicorn app.main:app --reload`

## Testing
- (Add tests in `tests/` and run with `pytest`)

## Contribution
Pull requests are welcome! Please open an issue first to discuss major changes.

## License
MIT