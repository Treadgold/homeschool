#!/usr/bin/env python3
"""
Test Data Generator for LifeLearners Homeschool Platform

This script generates realistic test data including:
- 40+ diverse events over 2 months
- Various event types and pricing
- Test users and children
- Sample bookings for payment testing

Run: python scripts/generate_test_data.py
Or: docker-compose exec web python scripts/generate_test_data.py
"""

import sys
import os
import random
from datetime import datetime, timedelta
from decimal import Decimal

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'app'))

from sqlalchemy.orm import Session
from database import SessionLocal, engine
from models import Base, Event, User, Child, Booking
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Test data constants
EVENT_TYPES = [
    "Science Workshop", "Art Class", "Music Lesson", "Drama Workshop", 
    "Mathematics Tutoring", "History Exploration", "Nature Study", 
    "Coding Club", "Creative Writing", "Sports Day", "Field Trip",
    "Language Learning", "Cooking Class", "Gardening Workshop",
    "Astronomy Night", "Chemistry Lab", "Physics Fun", "Biology Study"
]

LOCATIONS = [
    "Community Centre, Auckland", "Public Library, Wellington", 
    "Science Museum, Christchurch", "Local Park, Hamilton",
    "Art Gallery, Dunedin", "Botanical Gardens, Palmerston North",
    "Beach House, Tauranga", "Mountain Lodge, Queenstown",
    "Historic Site, Rotorua", "City Hall, Napier",
    "Sports Complex, New Plymouth", "Farm Visit, Cambridge",
    "Maori Cultural Centre, Waitangi", "Observatory, Lake Tekapo"
]

DESCRIPTIONS = [
    "Hands-on learning experience with expert guidance and all materials provided.",
    "Interactive session designed to inspire creativity and critical thinking.",
    "Small group setting with personalized attention for each child.",
    "Fun and educational activity suitable for the whole family.",
    "Practical skills development in a supportive environment.",
    "Explore new concepts through games, experiments, and discovery.",
    "Build confidence while learning essential life skills.",
    "Connect with like-minded families in your community.",
    "Professional instruction with age-appropriate activities.",
    "Outdoor adventure combining education with physical activity."
]

# Generate realistic New Zealand names
FIRST_NAMES = [
    "Emma", "Olivia", "Charlotte", "Sophie", "Amelia", "Grace", "Isla", "Zoe", "Lily", "Ruby",
    "Liam", "Oliver", "James", "William", "Lucas", "Mason", "Ethan", "Alexander", "Jack", "Noah"
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Wilson", "Moore",
    "Taylor", "Anderson", "Thomas", "Jackson", "White", "Harris", "Martin", "Thompson", "Young", "King"
]

def get_password_hash(password):
    return pwd_context.hash(password)

def clear_existing_test_data(db: Session):
    """Clear existing test data to start fresh"""
    print("🧹 Clearing existing test data...")
    
    try:
        # Delete in correct order to respect foreign keys
        db.query(Booking).delete()
        db.query(Child).delete()
        
        # Delete test users (keep any admin users that aren't test users)
        test_emails = [f"parent{i+1}@example.com" for i in range(20)]
        test_emails.append("admin@lifelearners.org.nz")
        
        for email in test_emails:
            user = db.query(User).filter(User.email == email).first()
            if user:
                db.delete(user)
        
        # Delete all events (assuming all events are test events)
        db.query(Event).delete()
        
        db.commit()
        print("✅ Cleared existing test data")
        
    except Exception as e:
        print(f"⚠️  Warning: Could not clear existing data: {e}")
        db.rollback()

def create_test_users(db: Session, num_users: int = 20):
    """Create test user accounts with children"""
    print(f"Creating {num_users} test users...")
    
    users = []
    for i in range(num_users):
        email = f"parent{i+1}@example.com"
        first_name = random.choice(FIRST_NAMES)
        last_name = random.choice(LAST_NAMES)
        
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            users.append(existing_user)
            continue
            
        user = User(
            email=email,
            hashed_password=get_password_hash("password123"),
            first_name=first_name,
            last_name=last_name,
            email_confirmed=True,
            is_admin=False,
            auth_provider='email'  # Explicitly set auth provider
        )
        db.add(user)
        db.flush()  # Get the user ID
        
        # Create 1-3 children per user
        num_children = random.randint(1, 3)
        for j in range(num_children):
            child_name = random.choice(FIRST_NAMES)
            age = random.randint(5, 16)
            
            # Some children have allergies or special needs
            allergies = None
            if random.random() < 0.3:  # 30% chance of allergies
                allergies = random.choice([
                    "Dairy", "Nuts", "Shellfish", "Eggs", "Gluten",
                    "Dairy, Nuts", "Seasonal allergies"
                ])
            
            notes = None
            if random.random() < 0.2:  # 20% chance of special notes
                notes = random.choice([
                    "Very shy, needs gentle encouragement",
                    "Highly energetic, loves hands-on activities",
                    "Advanced reader, may need additional challenges",
                    "Works best in small groups",
                    "Has ADHD, may need movement breaks"
                ])
            
            needs_assisting_adult = random.random() < 0.1  # 10% need assistance
            
            child = Child(
                user_id=user.id,
                name=child_name,
                age=age,
                allergies=allergies,
                notes=notes,
                needs_assisting_adult=needs_assisting_adult
            )
            db.add(child)
        
        users.append(user)
    
    db.commit()
    print(f"✅ Created {len(users)} users with children")
    return users

def create_test_events(db: Session, num_events: int = 40):
    """Create diverse test events over the next 2 months"""
    print(f"Creating {num_events} test events...")
    
    events = []
    start_date = datetime.now()
    end_date = start_date + timedelta(days=60)
    
    for i in range(num_events):
        # Random date within the next 2 months
        random_days = random.randint(1, 60)
        event_date = start_date + timedelta(days=random_days)
        
        # Random time during the day (9 AM to 4 PM)
        hour = random.randint(9, 16)
        minute = random.choice([0, 15, 30, 45])
        event_date = event_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        event_type = random.choice(EVENT_TYPES)
        location = random.choice(LOCATIONS)
        description = random.choice(DESCRIPTIONS)
        
        # Varied pricing structure
        if random.random() < 0.3:  # 30% free events
            cost = None
        else:  # 70% paid events with realistic NZ pricing
            cost = random.choice([
                15.00, 20.00, 25.00, 30.00, 35.00, 40.00, 45.00, 50.00,
                60.00, 75.00, 100.00  # Higher for special workshops
            ])
        
        # Capacity based on event type
        if "Field Trip" in event_type or "Sports Day" in event_type:
            max_pupils = random.randint(20, 50)
        elif "Tutoring" in event_type or "Music Lesson" in event_type:
            max_pupils = random.randint(3, 8)
        else:
            max_pupils = random.randint(8, 20)
        
        # Age ranges
        min_age = random.randint(5, 10)
        max_age = min_age + random.randint(3, 8)
        
        event = Event(
            title=event_type,
            description=f"{description} Perfect for children aged {min_age}-{max_age}. {location}.",
            date=event_date,
            location=location,
            max_pupils=max_pupils,
            min_age=min_age,
            max_age=max_age,
            cost=cost
        )
        
        db.add(event)
        events.append(event)
    
    db.commit()
    print(f"✅ Created {len(events)} events")
    return events

def create_test_bookings(db: Session, users: list, events: list):
    """Create realistic bookings for payment testing"""
    print("Creating test bookings...")
    
    bookings = []
    
    for event in events:
        # Random number of bookings per event (20-80% capacity)
        booking_percentage = random.uniform(0.2, 0.8)
        num_bookings = int(event.max_pupils * booking_percentage)
        
        # Select random users for this event
        available_users = users.copy()
        random.shuffle(available_users)
        
        for i in range(min(num_bookings, len(available_users))):
            user = available_users[i]
            
            # Get user's children
            children = db.query(Child).filter(Child.user_id == user.id).all()
            if not children:
                continue
            
            # Filter children by age for this event
            eligible_children = [
                child for child in children 
                if event.min_age <= child.age <= event.max_age
            ]
            
            if not eligible_children:
                continue
            
            # Book 1-2 eligible children (randomly)
            num_children_to_book = min(
                random.randint(1, 2), 
                len(eligible_children)
            )
            
            children_to_book = random.sample(eligible_children, num_children_to_book)
            
            for child in children_to_book:
                # Determine payment status based on event cost
                if event.cost is None or event.cost == 0:
                    payment_status = 'unpaid'  # Free event
                    stripe_payment_id = None
                else:
                    # Mix of payment statuses for testing
                    payment_status = random.choices(
                        ['paid', 'pending', 'failed', 'unpaid'],
                        weights=[70, 15, 10, 5],  # Most paid, some pending/failed
                        k=1
                    )[0]
                    
                    if payment_status == 'paid':
                        stripe_payment_id = f"pi_test_{random.randint(100000, 999999)}"
                    else:
                        stripe_payment_id = None
                
                # Some bookings involve volunteering
                volunteer = random.random() < 0.15  # 15% volunteer
                volunteer_role = None
                if volunteer:
                    volunteer_role = random.choice([
                        "Setup/Cleanup", "Assistant", "Photography", 
                        "First Aid", "Registration", "Activity Helper"
                    ])
                
                booking = Booking(
                    event_id=event.id,
                    child_id=child.id,
                    timestamp=datetime.now() - timedelta(
                        days=random.randint(0, 30)  # Bookings made over last 30 days
                    ),
                    volunteer=volunteer,
                    volunteer_role=volunteer_role,
                    payment_status=payment_status,
                    stripe_payment_id=stripe_payment_id
                )
                
                db.add(booking)
                bookings.append(booking)
    
    db.commit()
    print(f"✅ Created {len(bookings)} bookings")
    return bookings

def create_admin_user(db: Session):
    """Create an admin user for testing"""
    admin_email = "admin@lifelearners.org.nz"
    
    # Check if admin already exists
    existing_admin = db.query(User).filter(User.email == admin_email).first()
    if existing_admin:
        existing_admin.is_admin = True
        existing_admin.email_confirmed = True
        if not existing_admin.auth_provider:
            existing_admin.auth_provider = 'email'
        db.commit()
        print(f"✅ Updated existing admin user: {admin_email}")
        return existing_admin
    
    admin = User(
        email=admin_email,
        hashed_password=get_password_hash("admin123"),
        first_name="Admin",
        last_name="User",
        email_confirmed=True,
        is_admin=True,
        auth_provider='email'
    )
    db.add(admin)
    db.commit()
    print(f"✅ Created admin user: {admin_email} (password: admin123)")
    return admin

def print_summary_stats(db: Session):
    """Print summary of generated data"""
    print("\n" + "="*50)
    print("📊 TEST DATA SUMMARY")
    print("="*50)
    
    # Count users
    total_users = db.query(User).count()
    admin_users = db.query(User).filter(User.is_admin == True).count()
    regular_users = total_users - admin_users
    
    # Count children
    total_children = db.query(Child).count()
    children_with_allergies = db.query(Child).filter(Child.allergies.isnot(None)).count()
    children_need_assistance = db.query(Child).filter(Child.needs_assisting_adult == True).count()
    
    # Count events
    total_events = db.query(Event).count()
    free_events = db.query(Event).filter(Event.cost.is_(None)).count()
    paid_events = total_events - free_events
    
    # Count bookings by payment status
    total_bookings = db.query(Booking).count()
    paid_bookings = db.query(Booking).filter(Booking.payment_status == 'paid').count()
    pending_bookings = db.query(Booking).filter(Booking.payment_status == 'pending').count()
    failed_bookings = db.query(Booking).filter(Booking.payment_status == 'failed').count()
    
    # Calculate revenue
    from sqlalchemy import func
    revenue_result = db.query(
        func.sum(Event.cost)
    ).join(Booking).filter(
        Booking.payment_status == 'paid'
    ).scalar()
    
    total_revenue = revenue_result or 0
    
    print(f"👥 Users: {total_users} total ({regular_users} parents, {admin_users} admins)")
    print(f"👶 Children: {total_children} total")
    print(f"   - {children_with_allergies} with allergies")
    print(f"   - {children_need_assistance} need assistance")
    print(f"📅 Events: {total_events} total ({free_events} free, {paid_events} paid)")
    print(f"🎫 Bookings: {total_bookings} total")
    print(f"   - {paid_bookings} paid")
    print(f"   - {pending_bookings} pending")
    print(f"   - {failed_bookings} failed")
    print(f"💰 Revenue: ${total_revenue:.2f} from paid bookings")
    
    print("\n🧪 TEST ACCOUNTS:")
    print("Admin: admin@lifelearners.org.nz (password: admin123)")
    print("Parents: parent1@example.com to parent20@example.com (password: password123)")
    
    print("\n🎯 NEXT STEPS:")
    print("1. App is running at: http://localhost:8000")
    print("2. Login as admin to view dashboard and analytics")
    print("3. Login as parents to test booking flow")
    print("4. Test Stripe payments with test card: 4242 4242 4242 4242")
    print("5. MailHog UI available at: http://localhost:8025")
    print("="*50)

def main():
    """Generate all test data"""
    print("🚀 Generating test data for LifeLearners platform...")
    print("This will create realistic homeschool events, users, and bookings")
    print("🐘 Using PostgreSQL database from Docker environment")
    print("-" * 60)
    
    # Create database tables
    Base.metadata.create_all(bind=engine)
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Clear existing test data
        clear_existing_test_data(db)
        
        # Generate test data
        admin = create_admin_user(db)
        users = create_test_users(db, num_users=20)
        events = create_test_events(db, num_events=40)
        bookings = create_test_bookings(db, users, events)
        
        # Print summary
        print_summary_stats(db)
        
    except Exception as e:
        print(f"❌ Error generating test data: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main() 