from sqlalchemy import Column, Integer, String, Text, DateTime, Numeric, Boolean, ForeignKey, Float, func, JSON, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import datetime
import enum

Base = declarative_base()

class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    date = Column(DateTime, default=datetime.datetime.utcnow)
    location = Column(String(200), nullable=True)
    max_pupils = Column(Integer, nullable=True)
    min_age = Column(Integer, nullable=True)
    max_age = Column(Integer, nullable=True)
    cost = Column(Float, nullable=True)
    image_url = Column(String(500), nullable=True)
    event_type = Column(String(50), default='homeschool')  # 'homeschool' or 'offsite'
    recommended_age = Column(Integer, nullable=True)
    is_multi_part = Column(Boolean, default=False)
    part_number = Column(Integer, nullable=True)
    location_details = Column(Text, nullable=True)
    bookings = relationship("Booking", back_populates="event")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=True)  # Make nullable for OAuth users
    is_admin = Column(Boolean, default=False)
    email_confirmed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # OAuth fields
    facebook_id = Column(String(50), unique=True, nullable=True, index=True)
    google_id = Column(String(50), unique=True, nullable=True, index=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    profile_picture_url = Column(String(500), nullable=True)
    auth_provider = Column(String(20), default='email')  # 'email', 'facebook', 'google'
    
    children = relationship("Child", back_populates="user")
    chat_conversations = relationship("ChatConversation", back_populates="user")

class Child(Base):
    __tablename__ = "children"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    age = Column(Integer, nullable=False)
    allergies = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    needs_assisting_adult = Column(Boolean, default=False)
    other_info = Column(Text, nullable=True)
    user = relationship("User", back_populates="children")
    bookings = relationship("Booking", back_populates="child")

class Booking(Base):
    __tablename__ = "bookings"
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    child_id = Column(Integer, ForeignKey("children.id"), nullable=False)
    timestamp = Column(DateTime, default=func.now())
    part_number = Column(Integer, nullable=True)
    volunteer = Column(Boolean, default=False)
    volunteer_role = Column(String(100), nullable=True)
    voucher_used = Column(Boolean, default=False)
    payment_status = Column(String(30), default='unpaid')
    stripe_payment_id = Column(String(100), nullable=True)
    event = relationship("Event", back_populates="bookings")
    child = relationship("Child", back_populates="bookings")

class GalleryImage(Base):
    __tablename__ = "gallery_images"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    title = Column(String(200), nullable=True)
    description = Column(Text, nullable=True)
    upload_date = Column(DateTime, default=func.now())

class AgentStatus(enum.Enum):
    """Agent status enumeration"""
    idle = "idle"
    thinking = "thinking"
    using_tool = "using_tool"
    planning = "planning"
    waiting = "waiting"
    error = "error"

class ChatConversation(Base):
    """Persistent chat conversations"""
    __tablename__ = "chat_conversations"
    
    id = Column(String(36), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(200), nullable=True)  # Auto-generated from first message
    status = Column(String(20), default="active")  # active, completed, archived
    agent_context = Column(JSON, nullable=True)  # Agent memory and state
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="chat_conversations")
    messages = relationship("ChatMessage", back_populates="conversation", cascade="all, delete-orphan")

class ChatMessage(Base):
    """Individual messages in conversations"""
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True)
    conversation_id = Column(String(36), ForeignKey("chat_conversations.id"), nullable=False)
    role = Column(String(20), nullable=False)  # user, assistant, system, tool
    content = Column(Text, nullable=False)
    msg_metadata = Column(JSON, nullable=True)  # Tool calls, timing, etc.
    agent_status = Column(Enum(AgentStatus, name="agent_status"), nullable=True)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    conversation = relationship("ChatConversation", back_populates="messages")

    def to_dict(self):
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "role": self.role,
            "content": self.content,
            "msg_metadata": self.msg_metadata,
            "agent_status": self.agent_status.value if self.agent_status else None,
            "created_at": self.created_at.isoformat()
        }

class AgentSession(Base):
    """Agent session state for complex workflows"""
    __tablename__ = "agent_sessions"
    
    id = Column(String(36), primary_key=True)
    conversation_id = Column(String(36), ForeignKey("chat_conversations.id"), nullable=False)
    agent_type = Column(String(50), default="event_creator")  # event_creator, planner, assistant
    current_step = Column(String(100), nullable=True)
    plan = Column(JSON, nullable=True)  # Agent's current plan
    memory = Column(JSON, nullable=True)  # Working memory
    tools_used = Column(JSON, nullable=True)  # History of tool usage
    status = Column(Enum(AgentStatus, name="agent_status"), default=AgentStatus.idle)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    conversation = relationship("ChatConversation") 