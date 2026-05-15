from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Boolean
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
    is_warming_up = Column(Integer, default=1) # 1 for True, 0 for False
    trust_score = Column(Integer, default=50) # 0 to 100
    daily_action_count = Column(Integer, default=0)
    last_action_date = Column(String, nullable=True) # YYYY-MM-DD
    profile_pic_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    missions = relationship("Mission", back_populates="account")
    warmup_config = relationship("WarmupConfig", back_populates="account", uselist=False)
    action_logs = relationship("DailyActionLog", back_populates="account")

class WarmupConfig(Base):
    __tablename__ = "warmup_configs"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"))
    niche = Column(String, nullable=True)
    personality = Column(Text, nullable=True)
    languages = Column(String, default="Spanish, English")
    forbidden_topics = Column(Text, nullable=True)
    tone_modifiers = Column(String, default="Professional, Helpful")
    vip_profiles = Column(JSON, nullable=True) # List of LinkedIn IDs
    start_date = Column(DateTime, default=datetime.datetime.utcnow)
    total_days = Column(Integer, default=120)
    current_trust_level = Column(Integer, default=1)
    last_higiene_run = Column(DateTime, nullable=True)

    account = relationship("Account", back_populates="warmup_config")

class DailyActionLog(Base):
    __tablename__ = "daily_action_logs"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"))
    action_type = Column(String) # LIKE, COMMENT, CONNECTION, VISIT, DM
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

    account = relationship("Account", back_populates="action_logs")

class Mission(Base):
    __tablename__ = "missions"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"))
    status = Column(String, default="pending")  # pending, running, completed, failed
    tasks = Column(JSON)  # List of tasks to execute
    source = Column(String, default="manual")  # "manual" | "autopilot" | "autopilot_notification"
    target_profile_id = Column(Integer, ForeignKey("target_profiles.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    executed_at = Column(DateTime, nullable=True)

    account = relationship("Account", back_populates="missions")
    target_profile = relationship("TargetProfile")
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

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"))
    text = Column(String)
    link = Column(String)
    time_ago = Column(String)
    is_unread = Column(Integer, default=1)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

    account = relationship("Account")

class PendingLogin(Base):
    __tablename__ = "pending_logins"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, index=True)
    password_encrypted = Column(String)
    proxy_url = Column(String, nullable=True)
    status = Column(String, default="pending")  # pending, 2fa_email, 2fa_app, success, expired, locked
    code_sent_to = Column(String, nullable=True)
    storage_state = Column(JSON, nullable=True)
    failed_attempts = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    expires_at = Column(DateTime)

class ConcurrencyTestResult(Base):
    __tablename__ = "concurrency_test_results"

    id = Column(Integer, primary_key=True, index=True)
    test_run_id = Column(String, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"))
    account_email = Column(String)
    mission_id = Column(Integer, nullable=True)
    task_type = Column(String)
    result = Column(String)
    duration_ms = Column(Integer)
    error_message = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

class ExecutionLock(Base):
    __tablename__ = "execution_locks"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), unique=True)
    mission_id = Column(Integer)
    acquired_at = Column(DateTime, default=datetime.datetime.utcnow)
    ttl_seconds = Column(Integer, default=600)

class Proxy(Base):
    __tablename__ = "proxies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=True)
    host = Column(String, nullable=False)
    port = Column(Integer, nullable=False)
    username = Column(String, nullable=True)
    password = Column(String, nullable=True)
    protocol = Column(String, default="socks5")
    country = Column(String, nullable=True)
    city = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    is_online = Column(Boolean, default=False)
    last_health_check = Column(DateTime, nullable=True)
    assigned_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    assigned_account = relationship("Account", foreign_keys=[assigned_account_id])

    @property
    def url(self) -> str:
        auth = f"{self.username}:{self.password}@" if self.username else ""
        return f"{self.protocol}://{auth}{self.host}:{self.port}"

    @property
    def short_url(self) -> str:
        return f"{self.protocol}://{self.host}:{self.port}"


class RateLimit(Base):
    __tablename__ = "rate_limits"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"))
    action_type = Column(String)
    action_count = Column(Integer, default=0)
    window_start = Column(DateTime, default=datetime.datetime.utcnow)
