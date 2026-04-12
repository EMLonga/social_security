"""
Initialize database with sample data for testing
Run: python init_data.py
"""

from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from database import SessionLocal
from models import (
    User, Community, Event, EventType, DangerLevel,
    SafetyLevel, UserRole
)
from security import hash_password
import random


def init_database():
    """Initialize database with sample data"""
    db = SessionLocal()
    
    try:
        # Clear existing data
        db.query(Event).delete()
        db.query(Community).delete()
        db.query(User).delete()
        db.commit()
        
        print("Creating users...")
        # Create admin user
        admin = User(
            username="admin",
            email="admin@example.com",
            hashed_password=hash_password("admin123"),
            role=UserRole.ADMIN,
            is_active=True
        )
        db.add(admin)
        
        # Create regular users
        user1 = User(
            username="john_doe",
            email="john@example.com",
            hashed_password=hash_password("password123"),
            role=UserRole.USER,
            is_active=True
        )
        user2 = User(
            username="jane_smith",
            email="jane@example.com",
            hashed_password=hash_password("password123"),
            role=UserRole.USER,
            is_active=True
        )
        db.add_all([user1, user2])
        db.commit()
        print(f"✅ Created 3 users (admin, john_doe, jane_smith)")
        
        print("Creating communities...")
        # Create sample communities
        communities_data = [
            {
                "name": "Los Angeles Downtown",
                "state": "CA",
                "city": "Los Angeles",
                "zipcode": "90001",
                "latitude": 34.0522,
                "longitude": -118.2437,
                "population": 500000,
                "area": 50.0,
                "safety_level": SafetyLevel.MEDIUM,
                "trend": "stable"
            },
            {
                "name": "San Francisco Bay",
                "state": "CA",
                "city": "San Francisco",
                "zipcode": "94102",
                "latitude": 37.7749,
                "longitude": -122.4194,
                "population": 300000,
                "area": 30.0,
                "safety_level": SafetyLevel.LOW,
                "trend": "up"
            },
            {
                "name": "New York Manhattan",
                "state": "NY",
                "city": "New York",
                "zipcode": "10001",
                "latitude": 40.7128,
                "longitude": -74.0060,
                "population": 1000000,
                "area": 60.0,
                "safety_level": SafetyLevel.MEDIUM,
                "trend": "down"
            },
            {
                "name": "Chicago Downtown",
                "state": "IL",
                "city": "Chicago",
                "zipcode": "60601",
                "latitude": 41.8781,
                "longitude": -87.6298,
                "population": 400000,
                "area": 45.0,
                "safety_level": SafetyLevel.MEDIUM,
                "trend": "stable"
            },
        ]
        
        communities = []
        for data in communities_data:
            community = Community(**data)
            community.safety_score = random.uniform(40, 90)
            db.add(community)
            communities.append(community)
        
        db.commit()
        print(f"✅ Created {len(communities)} communities")
        
        print("Creating events...")
        # Create sample events
        event_types = [EventType.THEFT, EventType.SHOOTING, EventType.FIRE, EventType.SECURITY]
        danger_levels = [DangerLevel.LOW, DangerLevel.MEDIUM, DangerLevel.HIGH]
        
        event_titles = [
            "Theft reported at downtown parking lot",
            "Traffic accident on main street",
            "Structural fire at abandoned warehouse",
            "Armed robbery at convenience store",
            "Assault in public park",
            "Vehicle break-in reported",
            "House fire evacuation required",
            "Shooting incident near school",
        ]
        
        events = []
        for i, community in enumerate(communities):
            for j in range(5):  # 5 events per community
                event_type = random.choice(event_types)
                danger_level = random.choice(danger_levels)
                
                event = Event(
                    title=f"{event_titles[j % len(event_titles)]} - {community.name}",
                    description=f"Incident occurred in {community.name} area. "
                               f"Emergency services responded to the scene.",
                    event_type=event_type,
                    danger_level=danger_level,
                    community_id=community.id,
                    address=f"{random.randint(1, 9999)} {community.city} Street",
                    latitude=community.latitude + random.uniform(-0.05, 0.05),
                    longitude=community.longitude + random.uniform(-0.05, 0.05),
                    zipcode=community.zipcode,
                    event_time=datetime.now(timezone.utc) - timedelta(days=random.randint(0, 30)),
                    data_source="CrimeReports",
                    like_count=random.randint(0, 100),
                    comment_count=random.randint(0, 20),
                )
                db.add(event)
                events.append(event)
        
        db.commit()
        print(f"✅ Created {len(events)} events")
        
        # Create user interactions
        print("Creating user interactions...")
        for user in [user1, user2]:
            # Add some liked events
            liked_events = random.sample(events, min(5, len(events)))
            user.liked_events = liked_events
            
            # Add some saved events
            saved_events = random.sample(events, min(3, len(events)))
            user.saved_events = saved_events
            
            # Add followed communities
            followed = random.sample(communities, min(2, len(communities)))
            user.followed_communities = followed
        
        db.commit()
        print("✅ Created user interactions (likes, saves, follows)")
        
        print("\n" + "="*50)
        print("✅ Database initialization complete!")
        print("="*50)
        print("\nYou can now login with:")
        print("  Admin: admin / admin123")
        print("  User: john_doe / password123")
        print("  User: jane_smith / password123")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    init_database()
