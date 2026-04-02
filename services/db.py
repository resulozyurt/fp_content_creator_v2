from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Float
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./content_engine.db")

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# --- NEW: User Table for SaaS Architecture ---
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="user") # Options: 'user', 'admin'
    is_active = Column(Boolean, default=True)
    balance = Column(Float, default=0.0) # For future AI API cost tracking
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    articles = relationship("ArticleHistory", back_populates="owner")
    wp_settings = relationship("WPSettings", back_populates="owner")
    activity_logs = relationship("ActivityLog", back_populates="owner")

# --- NEW: Multi-Tenant WordPress Settings ---
class WPSettings(Base):
    __tablename__ = "wp_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    website_name = Column(String, nullable=True) # E.g., "My Tech Blog"
    wp_url = Column(String, nullable=False)
    wp_username = Column(String, nullable=False)
    wp_app_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="wp_settings")

# --- NEW: System Activity Logs (For Admin Panel) ---
class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action_type = Column(String, nullable=False) # E.g., 'ARTICLE_GENERATED', 'LOGIN'
    details = Column(Text, nullable=True) # JSON details
    cost = Column(Float, default=0.0) # Cost of the operation (AI tokens)
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="activity_logs")

# --- UPDATED: Existing Article History (Now Tenant-Isolated) ---
class ArticleHistory(Base):
    __tablename__ = "article_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True) # Nullable for backward compatibility
    keyword = Column(String, index=True)
    language = Column(String)
    country = Column(String)
    process_summary = Column(Text) 
    article_markdown = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="articles")

# --- NEW: Global System Settings ---
class SystemSettings(Base):
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, index=True)
    setting_key = Column(String, unique=True, index=True, nullable=False)
    setting_value = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# Create all tables
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()