#!/usr/bin/env python3
"""
User Adoption and Feedback Database Models
==========================================
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from enum import Enum
from sqlalchemy import (
    Column, String, Integer, DateTime, Boolean, Text, 
    ForeignKey, JSON, Float, Index, UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from pydantic import BaseModel, Field

Base = declarative_base()

class OnboardingStatus(str, Enum):
    """Onboarding status enumeration"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    ABANDONED = "abandoned"

class FeedbackType(str, Enum):
    """Feedback type enumeration"""
    GENERAL = "general"
    FEATURE_REQUEST = "feature_request"
    BUG_REPORT = "bug_report"
    USABILITY = "usability"
    PERFORMANCE = "performance"
    TRAINING = "training"
    SATISFACTION = "satisfaction"

class FeedbackPriority(str, Enum):
    """Feedback priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AdoptionMetricType(str, Enum):
    """Adoption metric types"""
    LOGIN = "login"
    QUERY_EXECUTION = "query_execution"
    DASHBOARD_VIEW = "dashboard_view"
    DASHBOARD_CREATE = "dashboard_create"
    ALERT_CREATE = "alert_create"
    REPORT_EXPORT = "report_export"
    FEATURE_USE = "feature_use"
    HELP_ACCESS = "help_access"
    SESSION_DURATION = "session_duration"

# Database Models

class UserProfile(Base):
    """Extended user profile for adoption tracking"""
    __tablename__ = "user_profiles"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    department = Column(String(100))
    role = Column(String(100))
    user_type = Column(String(50), default="end_user")  # end_user, admin, power_user
    
    # Onboarding tracking
    onboarding_status = Column(String(20), default=OnboardingStatus.NOT_STARTED)
    onboarding_started_at = Column(DateTime)
    onboarding_completed_at = Column(DateTime)
    onboarding_progress = Column(Float, default=0.0)  # 0.0 to 1.0
    
    # Adoption metrics
    first_login_at = Column(DateTime)
    last_login_at = Column(DateTime)
    total_logins = Column(Integer, default=0)
    total_queries = Column(Integer, default=0)
    total_dashboards = Column(Integer, default=0)
    total_alerts = Column(Integer, default=0)
    total_exports = Column(Integer, default=0)
    
    # Engagement scores
    adoption_score = Column(Float, default=0.0)  # Overall adoption score
    engagement_level = Column(String(20), default="new")  # new, beginner, intermediate, advanced, expert
    last_activity_at = Column(DateTime)
    
    # Preferences and settings
    preferred_features = Column(JSON)
    notification_preferences = Column(JSON)
    training_completed = Column(JSON)  # List of completed training modules
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    onboarding_steps = relationship("OnboardingStep", back_populates="user_profile")
    feedback_submissions = relationship("FeedbackSubmission", back_populates="user_profile")
    adoption_metrics = relationship("AdoptionMetric", back_populates="user_profile")
    
    __table_args__ = (
        Index('idx_user_adoption_score', 'adoption_score'),
        Index('idx_user_last_activity', 'last_activity_at'),
        Index('idx_user_engagement', 'engagement_level'),
    )

class OnboardingStep(Base):
    """Individual onboarding step tracking"""
    __tablename__ = "onboarding_steps"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_profile_id = Column(UUID(as_uuid=True), ForeignKey("user_profiles.id"), nullable=False)
    step_id = Column(String(100), nullable=False)  # e.g., "first_query", "create_dashboard"
    step_name = Column(String(255), nullable=False)
    step_order = Column(Integer, nullable=False)
    
    # Step status
    status = Column(String(20), default=OnboardingStatus.NOT_STARTED)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    attempts = Column(Integer, default=0)
    
    # Step data
    step_data = Column(JSON)  # Additional data about the step
    completion_time_seconds = Column(Integer)
    help_accessed = Column(Boolean, default=False)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user_profile = relationship("UserProfile", back_populates="onboarding_steps")
    
    __table_args__ = (
        Index('idx_onboarding_user_step', 'user_profile_id', 'step_id'),
        Index('idx_onboarding_status', 'status'),
        UniqueConstraint('user_profile_id', 'step_id', name='uq_user_step'),
    )

class FeedbackSubmission(Base):
    """User feedback submissions"""
    __tablename__ = "feedback_submissions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_profile_id = Column(UUID(as_uuid=True), ForeignKey("user_profiles.id"), nullable=False)
    
    # Feedback classification
    feedback_type = Column(String(50), nullable=False)
    category = Column(String(100))
    priority = Column(String(20), default=FeedbackPriority.MEDIUM)
    
    # Feedback content
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    rating = Column(Integer)  # 1-5 star rating
    tags = Column(JSON)  # List of tags
    
    # Context information
    page_url = Column(String(500))
    feature_context = Column(String(255))
    session_data = Column(JSON)
    browser_info = Column(JSON)
    
    # Feedback metadata
    is_anonymous = Column(Boolean, default=False)
    contact_requested = Column(Boolean, default=False)
    
    # Processing status
    status = Column(String(50), default="submitted")  # submitted, reviewed, in_progress, resolved, closed
    assigned_to = Column(String(255))
    internal_notes = Column(Text)
    resolution_notes = Column(Text)
    resolved_at = Column(DateTime)
    
    # Engagement metrics
    helpfulness_votes = Column(Integer, default=0)
    follow_up_responses = Column(Integer, default=0)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user_profile = relationship("UserProfile", back_populates="feedback_submissions")
    follow_ups = relationship("FeedbackFollowUp", back_populates="feedback_submission")
    
    __table_args__ = (
        Index('idx_feedback_type_status', 'feedback_type', 'status'),
        Index('idx_feedback_created', 'created_at'),
        Index('idx_feedback_priority', 'priority'),
        Index('idx_feedback_rating', 'rating'),
    )

class FeedbackFollowUp(Base):
    """Follow-up responses to feedback submissions"""
    __tablename__ = "feedback_follow_ups"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    feedback_submission_id = Column(UUID(as_uuid=True), ForeignKey("feedback_submissions.id"), nullable=False)
    
    # Follow-up content
    response_type = Column(String(50), default="response")  # response, question, update
    message = Column(Text, nullable=False)
    responder_id = Column(String(255))  # User ID of responder
    responder_type = Column(String(50), default="admin")  # admin, user, system
    
    # Response metadata
    is_public = Column(Boolean, default=True)
    requires_action = Column(Boolean, default=False)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    feedback_submission = relationship("FeedbackSubmission", back_populates="follow_ups")
    
    __table_args__ = (
        Index('idx_followup_feedback', 'feedback_submission_id'),
        Index('idx_followup_created', 'created_at'),
    )

class AdoptionMetric(Base):
    """User adoption and usage metrics"""
    __tablename__ = "adoption_metrics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_profile_id = Column(UUID(as_uuid=True), ForeignKey("user_profiles.id"), nullable=False)
    
    # Metric details
    metric_type = Column(String(50), nullable=False)
    metric_name = Column(String(255), nullable=False)
    metric_value = Column(Float, nullable=False)
    metric_unit = Column(String(50))  # count, seconds, bytes, etc.
    
    # Context information
    feature_name = Column(String(255))
    page_context = Column(String(255))
    session_id = Column(String(255))
    
    # Additional metric data
    metric_data = Column(JSON)  # Additional structured data
    
    # Time dimensions
    recorded_at = Column(DateTime, default=datetime.utcnow)
    date_dimension = Column(DateTime)  # For aggregation (date only)
    hour_dimension = Column(Integer)   # Hour of day (0-23)
    day_of_week = Column(Integer)      # Day of week (0-6)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user_profile = relationship("UserProfile", back_populates="adoption_metrics")
    
    __table_args__ = (
        Index('idx_metric_user_type', 'user_profile_id', 'metric_type'),
        Index('idx_metric_recorded', 'recorded_at'),
        Index('idx_metric_date_dim', 'date_dimension'),
        Index('idx_metric_feature', 'feature_name'),
    )

class SurveyTemplate(Base):
    """Survey templates for automated feedback collection"""
    __tablename__ = "survey_templates"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    survey_type = Column(String(50), nullable=False)  # onboarding, periodic, feature, exit
    
    # Survey configuration
    questions = Column(JSON, nullable=False)  # Survey questions structure
    targeting_rules = Column(JSON)  # Who should receive this survey
    trigger_conditions = Column(JSON)  # When to trigger the survey
    
    # Survey settings
    is_active = Column(Boolean, default=True)
    max_responses = Column(Integer)
    expiration_date = Column(DateTime)
    frequency_limit = Column(Integer)  # Days between surveys for same user
    
    # Display settings
    display_settings = Column(JSON)
    notification_settings = Column(JSON)
    
    # Metadata
    created_by = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    survey_responses = relationship("SurveyResponse", back_populates="survey_template")
    
    __table_args__ = (
        Index('idx_survey_type_active', 'survey_type', 'is_active'),
        Index('idx_survey_created', 'created_at'),
    )

class SurveyResponse(Base):
    """Individual survey responses"""
    __tablename__ = "survey_responses"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    survey_template_id = Column(UUID(as_uuid=True), ForeignKey("survey_templates.id"), nullable=False)
    user_profile_id = Column(UUID(as_uuid=True), ForeignKey("user_profiles.id"), nullable=False)
    
    # Response data
    responses = Column(JSON, nullable=False)  # User's answers
    completion_status = Column(String(50), default="completed")  # completed, partial, abandoned
    completion_percentage = Column(Float, default=0.0)
    
    # Response metadata
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    time_spent_seconds = Column(Integer)
    
    # Context information
    trigger_context = Column(JSON)
    session_data = Column(JSON)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    survey_template = relationship("SurveyTemplate", back_populates="survey_responses")
    user_profile = relationship("UserProfile")
    
    __table_args__ = (
        Index('idx_response_survey_user', 'survey_template_id', 'user_profile_id'),
        Index('idx_response_completed', 'completed_at'),
        Index('idx_response_status', 'completion_status'),
    )

# Pydantic Models for API

class UserProfileCreate(BaseModel):
    """Create user profile request"""
    user_id: str
    email: str
    full_name: str
    department: Optional[str] = None
    role: Optional[str] = None
    user_type: str = "end_user"

class UserProfileUpdate(BaseModel):
    """Update user profile request"""
    email: Optional[str] = None
    full_name: Optional[str] = None
    department: Optional[str] = None
    role: Optional[str] = None
    user_type: Optional[str] = None
    notification_preferences: Optional[Dict[str, Any]] = None

class UserProfileResponse(BaseModel):
    """User profile response"""
    id: uuid.UUID
    user_id: str
    email: str
    full_name: str
    department: Optional[str]
    role: Optional[str]
    user_type: str
    onboarding_status: str
    onboarding_progress: float
    adoption_score: float
    engagement_level: str
    last_activity_at: Optional[datetime]
    total_logins: int
    total_queries: int
    total_dashboards: int
    total_alerts: int
    
    class Config:
        orm_mode = True

class OnboardingStepUpdate(BaseModel):
    """Update onboarding step"""
    status: OnboardingStatus
    step_data: Optional[Dict[str, Any]] = None
    help_accessed: bool = False

class FeedbackSubmissionCreate(BaseModel):
    """Create feedback submission"""
    feedback_type: FeedbackType
    category: Optional[str] = None
    priority: FeedbackPriority = FeedbackPriority.MEDIUM
    title: str = Field(..., max_length=255)
    description: str
    rating: Optional[int] = Field(None, ge=1, le=5)
    tags: Optional[List[str]] = None
    page_url: Optional[str] = None
    feature_context: Optional[str] = None
    is_anonymous: bool = False
    contact_requested: bool = False

class FeedbackSubmissionResponse(BaseModel):
    """Feedback submission response"""
    id: uuid.UUID
    feedback_type: str
    category: Optional[str]
    priority: str
    title: str
    description: str
    rating: Optional[int]
    status: str
    created_at: datetime
    
    class Config:
        orm_mode = True

class AdoptionMetricCreate(BaseModel):
    """Create adoption metric"""
    metric_type: AdoptionMetricType
    metric_name: str
    metric_value: float
    metric_unit: Optional[str] = None
    feature_name: Optional[str] = None
    page_context: Optional[str] = None
    session_id: Optional[str] = None
    metric_data: Optional[Dict[str, Any]] = None

class SurveyTemplateCreate(BaseModel):
    """Create survey template"""
    name: str
    description: Optional[str] = None
    survey_type: str
    questions: List[Dict[str, Any]]
    targeting_rules: Optional[Dict[str, Any]] = None
    trigger_conditions: Optional[Dict[str, Any]] = None
    max_responses: Optional[int] = None
    expiration_date: Optional[datetime] = None
    frequency_limit: int = 30  # 30 days default

class SurveyResponseCreate(BaseModel):
    """Create survey response"""
    survey_template_id: uuid.UUID
    responses: Dict[str, Any]
    completion_status: str = "completed"
    trigger_context: Optional[Dict[str, Any]] = None