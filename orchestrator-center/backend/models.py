from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from database import Base
import datetime

class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    proxy_url = Column(String, nullable=True)
    storage_state = Column(JSON, nullable=True)  # Store playwright storageState JSON
    status = Column(String, default="active")  # active, restricted, invalid
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    missions = relationship("Mission", back_populates="account")

class Mission(Base):
    __tablename__ = "missions"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"))
    status = Column(String, default="pending")  # pending, running, completed, failed
    tasks = Column(JSON)  # List of tasks to execute
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    executed_at = Column(DateTime, nullable=True)

    account = relationship("Account", back_populates="missions")
    logs = relationship("Log", back_populates="mission")

class Log(Base):
    __tablename__ = "logs"

    id = Column(Integer, primary_key=True, index=True)
    mission_id = Column(Integer, ForeignKey("missions.id"))
    message = Column(String)
    level = Column(String, default="info")
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

    mission = relationship("Mission", back_populates="logs")

class TargetProfile(Base):
    __tablename__ = "target_profiles"

    id = Column(Integer, primary_key=True, index=True)
    linkedin_url = Column(String, unique=True, index=True)
    status = Column(String, default="active")  # active, paused
    schedule_start = Column(String, default="09:00")
    schedule_end = Column(String, default="18:00")
    cta_keywords = Column(String, nullable=True) # comma separated
    comment_base = Column(String, nullable=True) # Base comment for AI
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class ProcessedPost(Base):
    __tablename__ = "processed_posts"

    id = Column(Integer, primary_key=True, index=True)
    target_profile_id = Column(Integer, ForeignKey("target_profiles.id"))
    post_url = Column(String, unique=True, index=True)
    processed_at = Column(DateTime, default=datetime.datetime.utcnow)

    target_profile = relationship("TargetProfile")
