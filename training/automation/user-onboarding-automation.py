#!/usr/bin/env python3
"""
User Onboarding Automation System
=================================
Comprehensive automation for user onboarding, training enrollment, and adoption tracking
for the Splunk MCP Integration platform.
"""

import asyncio
import asyncpg
import redis.asyncio as redis
import smtplib
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
from pathlib import Path
import aiohttp
import yaml

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class UserRole(Enum):
    BUSINESS_USER = "business_user"
    TECHNICAL_USER = "technical_user"
    POWER_USER = "power_user"
    CASUAL_USER = "casual_user"
    ADMIN_USER = "admin_user"

class OnboardingStage(Enum):
    ACCOUNT_CREATED = "account_created"
    WELCOME_SENT = "welcome_sent"
    TRAINING_ENROLLED = "training_enrolled"
    FIRST_LOGIN = "first_login"
    FOUNDATION_COMPLETED = "foundation_completed"
    ROLE_TRAINING_COMPLETED = "role_training_completed"
    FIRST_DASHBOARD_CREATED = "first_dashboard_created"
    FULLY_ONBOARDED = "fully_onboarded"

class NotificationChannel(Enum):
    EMAIL = "email"
    SLACK = "slack"
    TEAMS = "teams"
    IN_APP = "in_app"

@dataclass
class OnboardingStep:
    step_id: str
    name: str
    description: str
    required: bool
    estimated_time_minutes: int
    dependencies: List[str]
    completion_criteria: Dict[str, Any]
    
@dataclass
class UserOnboardingProfile:
    user_id: str
    email: str
    full_name: str
    role: UserRole
    department: str
    manager_email: Optional[str]
    start_date: datetime
    current_stage: OnboardingStage
    completed_steps: List[str]
    training_progress: Dict[str, Any]
    last_activity: Optional[datetime]
    onboarding_score: float
    
class OnboardingAutomationSystem:
    """Comprehensive user onboarding automation system"""
    
    def __init__(self, config_path: str = "config/onboarding-config.yaml"):
        self.config = self._load_config(config_path)
        self.db_pool: Optional[asyncpg.Pool] = None
        self.redis_client: Optional[redis.Redis] = None
        self.email_client = None
        self.onboarding_steps = self._initialize_onboarding_steps()
        
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load onboarding configuration"""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning(f"Config file {config_path} not found, using defaults")
            return self._default_config()
    
    def _default_config(self) -> Dict[str, Any]:
        """Default configuration settings"""
        return {
            "database": {
                "url": "postgresql://localhost:5432/splunk_mcp",
                "pool_size": 20
            },
            "redis": {
                "url": "redis://localhost:6379/0"
            },
            "email": {
                "smtp_host": "smtp.company.com",
                "smtp_port": 587,
                "username": "noreply@company.com",
                "from_address": "Splunk MCP Platform <noreply@company.com>"
            },
            "onboarding": {
                "welcome_delay_hours": 1,
                "reminder_intervals_days": [3, 7, 14],
                "completion_timeout_days": 30,
                "manager_notification_enabled": True
            },
            "training": {
                "foundation_training_id": "foundation_training",
                "auto_enroll": True,
                "completion_tracking": True
            },
            "notifications": {
                "enabled_channels": ["email", "in_app"],
                "slack_webhook": None,
                "teams_webhook": None
            }
        }
    
    async def initialize(self):
        """Initialize database connections and clients"""
        # Database connection
        self.db_pool = await asyncpg.create_pool(
            self.config["database"]["url"],
            min_size=5,
            max_size=self.config["database"]["pool_size"]
        )
        
        # Redis connection
        self.redis_client = redis.from_url(self.config["redis"]["url"])
        
        # Initialize database schema
        await self._initialize_database_schema()
        
        logger.info("Onboarding automation system initialized successfully")
    
    async def _initialize_database_schema(self):
        """Initialize required database tables"""
        async with self.db_pool.acquire() as conn:
            # User onboarding profiles table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS user_onboarding_profiles (
                    user_id VARCHAR(255) PRIMARY KEY,
                    email VARCHAR(255) NOT NULL,
                    full_name VARCHAR(255) NOT NULL,
                    role VARCHAR(50) NOT NULL,
                    department VARCHAR(100),
                    manager_email VARCHAR(255),
                    start_date TIMESTAMP NOT NULL,
                    current_stage VARCHAR(50) NOT NULL,
                    completed_steps TEXT[],
                    training_progress JSONB,
                    last_activity TIMESTAMP,
                    onboarding_score FLOAT DEFAULT 0.0,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # Onboarding activities log
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS onboarding_activities (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(255) NOT NULL,
                    activity_type VARCHAR(100) NOT NULL,
                    activity_description TEXT,
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # Notification log
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS onboarding_notifications (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(255) NOT NULL,
                    notification_type VARCHAR(100) NOT NULL,
                    channel VARCHAR(50) NOT NULL,
                    subject VARCHAR(255),
                    content TEXT,
                    sent_at TIMESTAMP DEFAULT NOW(),
                    delivered BOOLEAN DEFAULT FALSE
                )
            """)
    
    def _initialize_onboarding_steps(self) -> List[OnboardingStep]:
        """Initialize comprehensive onboarding steps"""
        return [
            OnboardingStep(
                step_id="account_setup",
                name="Account Setup and Verification",
                description="Complete account setup and email verification",
                required=True,
                estimated_time_minutes=10,
                dependencies=[],
                completion_criteria={"email_verified": True, "profile_completed": True}
            ),
            OnboardingStep(
                step_id="platform_tour",
                name="Platform Interface Tour",
                description="Complete guided tour of platform interface",
                required=True,
                estimated_time_minutes=15,
                dependencies=["account_setup"],
                completion_criteria={"tour_completed": True, "help_accessed": True}
            ),
            OnboardingStep(
                step_id="foundation_training",
                name="Foundation Training",
                description="Complete platform foundation training module",
                required=True,
                estimated_time_minutes=120,
                dependencies=["platform_tour"],
                completion_criteria={"training_completed": True, "assessment_passed": True}
            ),
            OnboardingStep(
                step_id="first_query",
                name="First Natural Language Query",
                description="Execute your first natural language query",
                required=True,
                estimated_time_minutes=10,
                dependencies=["foundation_training"],
                completion_criteria={"query_executed": True, "results_viewed": True}
            ),
            OnboardingStep(
                step_id="dashboard_creation",
                name="Create Your First Dashboard",
                description="Create a personalized dashboard with multiple visualizations",
                required=True,
                estimated_time_minutes=30,
                dependencies=["first_query"],
                completion_criteria={"dashboard_created": True, "visualizations_added": True}
            ),
            OnboardingStep(
                step_id="role_specific_training",
                name="Role-Specific Advanced Training",
                description="Complete training specific to your role and responsibilities",
                required=True,
                estimated_time_minutes=240,
                dependencies=["dashboard_creation"],
                completion_criteria={"role_training_completed": True, "advanced_features_used": True}
            ),
            OnboardingStep(
                step_id="collaboration_features",
                name="Collaboration and Sharing",
                description="Learn to share dashboards and collaborate with team members",
                required=False,
                estimated_time_minutes=20,
                dependencies=["dashboard_creation"],
                completion_criteria={"dashboard_shared": True, "comment_added": True}
            ),
            OnboardingStep(
                step_id="automation_setup",
                name="Report Automation Setup",
                description="Set up automated reports and notifications",
                required=False,
                estimated_time_minutes=25,
                dependencies=["role_specific_training"],
                completion_criteria={"report_scheduled": True, "notifications_configured": True}
            )
        ]
    
    async def start_user_onboarding(self, user_data: Dict[str, Any]) -> UserOnboardingProfile:
        """Initiate comprehensive user onboarding process"""
        
        # Create onboarding profile
        profile = UserOnboardingProfile(
            user_id=user_data["user_id"],
            email=user_data["email"],
            full_name=user_data["full_name"],
            role=UserRole(user_data["role"]),
            department=user_data.get("department"),
            manager_email=user_data.get("manager_email"),
            start_date=datetime.utcnow(),
            current_stage=OnboardingStage.ACCOUNT_CREATED,
            completed_steps=[],
            training_progress={},
            last_activity=None,
            onboarding_score=0.0
        )
        
        # Store in database
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO user_onboarding_profiles (
                    user_id, email, full_name, role, department, manager_email,
                    start_date, current_stage, completed_steps, training_progress,
                    last_activity, onboarding_score
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            """, 
            profile.user_id, profile.email, profile.full_name, profile.role.value,
            profile.department, profile.manager_email, profile.start_date,
            profile.current_stage.value, profile.completed_steps, 
            json.dumps(profile.training_progress), profile.last_activity, profile.onboarding_score
            )
        
        # Log activity
        await self._log_onboarding_activity(
            profile.user_id,
            "onboarding_started",
            f"User onboarding initiated for {profile.full_name}",
            {"role": profile.role.value, "department": profile.department}
        )
        
        # Schedule welcome email
        await self._schedule_welcome_email(profile)
        
        # Auto-enroll in training programs
        if self.config["training"]["auto_enroll"]:
            await self._auto_enroll_training(profile)
        
        # Start progress monitoring
        await self._start_progress_monitoring(profile)
        
        logger.info(f"Started onboarding for user {profile.email} ({profile.role.value})")
        return profile
    
    async def _schedule_welcome_email(self, profile: UserOnboardingProfile):
        """Schedule personalized welcome email"""
        delay_hours = self.config["onboarding"]["welcome_delay_hours"]
        
        # Schedule email task
        await self.redis_client.zadd(
            "scheduled_emails",
            {f"welcome:{profile.user_id}": (datetime.utcnow() + timedelta(hours=delay_hours)).timestamp()}
        )
        
        logger.info(f"Scheduled welcome email for {profile.email} in {delay_hours} hours")
    
    async def _auto_enroll_training(self, profile: UserOnboardingProfile):
        """Automatically enroll user in appropriate training programs"""
        
        # Determine training programs based on role
        training_programs = {
            UserRole.BUSINESS_USER: ["foundation_training", "business_user_mastery"],
            UserRole.TECHNICAL_USER: ["foundation_training", "technical_user_advanced"],
            UserRole.POWER_USER: ["foundation_training", "business_user_mastery", "power_user_analytics"],
            UserRole.CASUAL_USER: ["foundation_training"],
            UserRole.ADMIN_USER: ["foundation_training", "technical_user_advanced", "administrator_excellence"]
        }
        
        programs = training_programs.get(profile.role, ["foundation_training"])
        
        async with self.db_pool.acquire() as conn:
            for program in programs:
                await conn.execute("""
                    INSERT INTO training_enrollments (
                        user_id, program_name, enrolled_at, status, enrollment_type
                    ) VALUES ($1, $2, $3, 'enrolled', 'automatic')
                    ON CONFLICT (user_id, program_name) DO NOTHING
                """, profile.user_id, program, datetime.utcnow())
        
        # Update training progress
        profile.training_progress = {program: {"status": "enrolled", "progress": 0} for program in programs}
        
        await self._log_onboarding_activity(
            profile.user_id,
            "training_enrolled",
            f"Auto-enrolled in {len(programs)} training programs",
            {"programs": programs}
        )
    
    async def _start_progress_monitoring(self, profile: UserOnboardingProfile):
        """Start automated progress monitoring and reminders"""
        
        # Schedule progress check tasks
        reminder_intervals = self.config["onboarding"]["reminder_intervals_days"]
        
        for days in reminder_intervals:
            await self.redis_client.zadd(
                "progress_checks",
                {f"reminder:{profile.user_id}:{days}": (datetime.utcnow() + timedelta(days=days)).timestamp()}
            )
        
        # Schedule completion timeout
        timeout_days = self.config["onboarding"]["completion_timeout_days"]
        await self.redis_client.zadd(
            "onboarding_timeouts",
            {f"timeout:{profile.user_id}": (datetime.utcnow() + timedelta(days=timeout_days)).timestamp()}
        )
    
    async def update_onboarding_progress(self, user_id: str, activity_type: str, 
                                       activity_data: Dict[str, Any]) -> bool:
        """Update user onboarding progress based on platform activity"""
        
        # Get current profile
        profile = await self._get_onboarding_profile(user_id)
        if not profile:
            logger.warning(f"Onboarding profile not found for user {user_id}")
            return False
        
        # Update last activity
        profile.last_activity = datetime.utcnow()
        
        # Process activity and update progress
        progress_updated = await self._process_activity(profile, activity_type, activity_data)
        
        if progress_updated:
            # Recalculate onboarding score
            profile.onboarding_score = self._calculate_onboarding_score(profile)
            
            # Update current stage
            new_stage = self._determine_current_stage(profile)
            if new_stage != profile.current_stage:
                await self._handle_stage_transition(profile, new_stage)
                profile.current_stage = new_stage
            
            # Save updated profile
            await self._save_onboarding_profile(profile)
            
            # Log activity
            await self._log_onboarding_activity(
                user_id, activity_type, f"Progress updated: {activity_type}", activity_data
            )
            
            logger.info(f"Updated onboarding progress for {user_id}: {activity_type}")
            return True
        
        return False
    
    async def _process_activity(self, profile: UserOnboardingProfile, 
                              activity_type: str, activity_data: Dict[str, Any]) -> bool:
        """Process specific activity and update onboarding steps"""
        
        progress_updated = False
        
        # Map activities to onboarding steps
        activity_mappings = {
            "email_verified": "account_setup",
            "profile_completed": "account_setup",
            "tour_completed": "platform_tour",
            "training_module_completed": "foundation_training",
            "assessment_passed": "foundation_training",
            "query_executed": "first_query",
            "dashboard_created": "dashboard_creation",
            "dashboard_shared": "collaboration_features",
            "report_scheduled": "automation_setup"
        }
        
        # Check if activity completes any steps
        for activity, step_id in activity_mappings.items():
            if activity_type == activity or activity in activity_data:
                if step_id not in profile.completed_steps:
                    # Validate step completion criteria
                    step = next((s for s in self.onboarding_steps if s.step_id == step_id), None)
                    if step and self._validate_step_completion(step, profile, activity_data):
                        profile.completed_steps.append(step_id)
                        progress_updated = True
                        
                        # Send completion notification
                        await self._send_step_completion_notification(profile, step)
        
        # Handle training progress updates
        if activity_type == "training_progress_updated":
            program_name = activity_data.get("program_name")
            progress = activity_data.get("progress", 0)
            
            if program_name:
                if program_name not in profile.training_progress:
                    profile.training_progress[program_name] = {}
                
                profile.training_progress[program_name]["progress"] = progress
                
                if progress >= 100:
                    profile.training_progress[program_name]["status"] = "completed"
                    profile.training_progress[program_name]["completed_at"] = datetime.utcnow().isoformat()
                
                progress_updated = True
        
        return progress_updated
    
    def _validate_step_completion(self, step: OnboardingStep, profile: UserOnboardingProfile, 
                                activity_data: Dict[str, Any]) -> bool:
        """Validate if step completion criteria are met"""
        
        # Check dependencies
        for dep in step.dependencies:
            if dep not in profile.completed_steps:
                return False
        
        # Check completion criteria
        for criterion, required_value in step.completion_criteria.items():
            if criterion not in activity_data:
                return False
            if activity_data[criterion] != required_value:
                return False
        
        return True
    
    def _calculate_onboarding_score(self, profile: UserOnboardingProfile) -> float:
        """Calculate comprehensive onboarding score (0-100)"""
        
        total_steps = len(self.onboarding_steps)
        completed_steps = len(profile.completed_steps)
        required_steps = len([s for s in self.onboarding_steps if s.required])
        completed_required = len([s for s in profile.completed_steps 
                                if any(step.step_id == s and step.required for step in self.onboarding_steps)])
        
        # Base score from step completion
        base_score = (completed_steps / total_steps) * 70
        
        # Bonus for required steps
        required_bonus = (completed_required / required_steps) * 20
        
        # Training progress bonus
        training_bonus = 0
        if profile.training_progress:
            total_progress = sum(prog.get("progress", 0) for prog in profile.training_progress.values())
            avg_progress = total_progress / len(profile.training_progress)
            training_bonus = (avg_progress / 100) * 10
        
        total_score = min(100.0, base_score + required_bonus + training_bonus)
        return round(total_score, 1)
    
    def _determine_current_stage(self, profile: UserOnboardingProfile) -> OnboardingStage:
        """Determine current onboarding stage based on completed steps"""
        
        if "automation_setup" in profile.completed_steps:
            return OnboardingStage.FULLY_ONBOARDED
        elif "role_specific_training" in profile.completed_steps:
            return OnboardingStage.ROLE_TRAINING_COMPLETED
        elif "dashboard_creation" in profile.completed_steps:
            return OnboardingStage.FIRST_DASHBOARD_CREATED
        elif "foundation_training" in profile.completed_steps:
            return OnboardingStage.FOUNDATION_COMPLETED
        elif profile.last_activity:
            return OnboardingStage.FIRST_LOGIN
        elif "foundation_training" in [prog for prog in profile.training_progress.keys()]:
            return OnboardingStage.TRAINING_ENROLLED
        elif profile.completed_steps:
            return OnboardingStage.WELCOME_SENT
        else:
            return OnboardingStage.ACCOUNT_CREATED
    
    async def _handle_stage_transition(self, profile: UserOnboardingProfile, new_stage: OnboardingStage):
        """Handle onboarding stage transitions with appropriate actions"""
        
        stage_actions = {
            OnboardingStage.WELCOME_SENT: self._send_welcome_email,
            OnboardingStage.FIRST_LOGIN: self._send_first_login_congratulations,
            OnboardingStage.FOUNDATION_COMPLETED: self._send_foundation_completion_notification,
            OnboardingStage.FIRST_DASHBOARD_CREATED: self._send_dashboard_achievement_notification,
            OnboardingStage.ROLE_TRAINING_COMPLETED: self._send_role_training_completion,
            OnboardingStage.FULLY_ONBOARDED: self._send_onboarding_completion_celebration
        }
        
        action_func = stage_actions.get(new_stage)
        if action_func:
            await action_func(profile)
        
        # Notify manager if enabled
        if self.config["onboarding"]["manager_notification_enabled"] and profile.manager_email:
            await self._send_manager_notification(profile, new_stage)
    
    async def _send_welcome_email(self, profile: UserOnboardingProfile):
        """Send personalized welcome email"""
        
        role_specific_content = {
            UserRole.BUSINESS_USER: {
                "welcome_message": "Transform your data analysis with natural language queries",
                "key_benefits": "Create dashboards, generate reports, and gain insights without technical complexity",
                "first_steps": "Complete Foundation Training (2 hours) and create your first dashboard"
            },
            UserRole.TECHNICAL_USER: {
                "welcome_message": "Enhance your technical capabilities with advanced analytics",
                "key_benefits": "Advanced SPL queries, system monitoring, and seamless integrations",
                "first_steps": "Complete Technical Training (8 hours) and set up system monitoring"
            },
            UserRole.POWER_USER: {
                "welcome_message": "Unlock advanced analytics and machine learning capabilities",
                "key_benefits": "Predictive modeling, custom analytics, and advanced visualizations",
                "first_steps": "Complete Power User Training (12 hours) and start your first ML project"
            },
            UserRole.ADMIN_USER: {
                "welcome_message": "Master platform administration and user enablement",
                "key_benefits": "Complete system control, security management, and user training coordination",
                "first_steps": "Complete Administrator Training (20 hours) and review system configuration"
            }
        }
        
        content = role_specific_content.get(profile.role, role_specific_content[UserRole.BUSINESS_USER])
        
        email_body = f"""
        Dear {profile.full_name},

        Welcome to the Splunk MCP Integration Platform! 

        {content['welcome_message']}

        What you can achieve:
        {content['key_benefits']}

        Your next steps:
        1. {content['first_steps']}
        2. Access your personalized dashboard: https://splunk-mcp.company.com
        3. Join our user community and connect with platform experts

        Training Schedule:
        - Your training programs are ready and waiting
        - Estimated completion time: Based on your role requirements
        - Support available 24/7 through our help system

        Questions? Reply to this email or contact your department champion.

        Welcome aboard!
        The Splunk MCP Team
        """
        
        await self._send_notification(
            profile, NotificationChannel.EMAIL,
            f"Welcome to Splunk MCP - Let's Get Started, {profile.full_name}!",
            email_body
        )
    
    async def _send_step_completion_notification(self, profile: UserOnboardingProfile, step: OnboardingStep):
        """Send step completion notification with next steps guidance"""
        
        # Determine next recommended step
        next_step = self._get_next_recommended_step(profile)
        
        notification_body = f"""
        Congratulations {profile.full_name}!

        You've successfully completed: {step.name}
        
        {step.description}

        Your onboarding progress: {profile.onboarding_score}% complete
        """
        
        if next_step:
            notification_body += f"""
            
            Next recommended step: {next_step.name}
            Estimated time: {next_step.estimated_time_minutes} minutes
            
            Ready to continue? Access your next step: https://splunk-mcp.company.com/onboarding
            """
        
        await self._send_notification(
            profile, NotificationChannel.IN_APP,
            f"Step Complete: {step.name}",
            notification_body
        )
    
    def _get_next_recommended_step(self, profile: UserOnboardingProfile) -> Optional[OnboardingStep]:
        """Get next recommended onboarding step"""
        
        for step in self.onboarding_steps:
            if step.step_id not in profile.completed_steps:
                # Check if dependencies are met
                deps_met = all(dep in profile.completed_steps for dep in step.dependencies)
                if deps_met:
                    return step
        
        return None
    
    async def _send_notification(self, profile: UserOnboardingProfile, channel: NotificationChannel,
                               subject: str, content: str):
        """Send notification through specified channel"""
        
        try:
            if channel == NotificationChannel.EMAIL:
                await self._send_email_notification(profile.email, subject, content)
            elif channel == NotificationChannel.IN_APP:
                await self._send_in_app_notification(profile.user_id, subject, content)
            elif channel == NotificationChannel.SLACK:
                await self._send_slack_notification(profile, subject, content)
            elif channel == NotificationChannel.TEAMS:
                await self._send_teams_notification(profile, subject, content)
            
            # Log notification
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO onboarding_notifications (
                        user_id, notification_type, channel, subject, content, delivered
                    ) VALUES ($1, $2, $3, $4, $5, $6)
                """, profile.user_id, "onboarding", channel.value, subject, content, True)
                
        except Exception as e:
            logger.error(f"Failed to send {channel.value} notification to {profile.email}: {e}")
            
            # Log failed notification
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO onboarding_notifications (
                        user_id, notification_type, channel, subject, content, delivered
                    ) VALUES ($1, $2, $3, $4, $5, $6)
                """, profile.user_id, "onboarding", channel.value, subject, content, False)
    
    async def _send_email_notification(self, email: str, subject: str, content: str):
        """Send email notification"""
        # Email implementation would integrate with SMTP server
        logger.info(f"Email sent to {email}: {subject}")
    
    async def _send_in_app_notification(self, user_id: str, subject: str, content: str):
        """Send in-app notification"""
        await self.redis_client.lpush(
            f"notifications:{user_id}",
            json.dumps({
                "subject": subject,
                "content": content,
                "timestamp": datetime.utcnow().isoformat(),
                "read": False
            })
        )
    
    async def get_onboarding_analytics(self, department: Optional[str] = None) -> Dict[str, Any]:
        """Generate comprehensive onboarding analytics"""
        
        async with self.db_pool.acquire() as conn:
            # Base query conditions
            where_clause = ""
            params = []
            
            if department:
                where_clause = "WHERE department = $1"
                params.append(department)
            
            # Overall statistics
            overall_stats = await conn.fetchrow(f"""
                SELECT 
                    COUNT(*) as total_users,
                    AVG(onboarding_score) as avg_onboarding_score,
                    COUNT(*) FILTER (WHERE current_stage = 'fully_onboarded') as fully_onboarded,
                    COUNT(*) FILTER (WHERE onboarding_score >= 80) as high_performers,
                    AVG(EXTRACT(EPOCH FROM (NOW() - start_date))/86400) as avg_days_since_start
                FROM user_onboarding_profiles
                {where_clause}
            """, *params)
            
            # Stage distribution
            stage_distribution = await conn.fetch(f"""
                SELECT 
                    current_stage,
                    COUNT(*) as user_count,
                    AVG(onboarding_score) as avg_score
                FROM user_onboarding_profiles
                {where_clause}
                GROUP BY current_stage
                ORDER BY user_count DESC
            """, *params)
            
            # Role-based analytics
            role_analytics = await conn.fetch(f"""
                SELECT 
                    role,
                    COUNT(*) as user_count,
                    AVG(onboarding_score) as avg_score,
                    COUNT(*) FILTER (WHERE current_stage = 'fully_onboarded') as completed
                FROM user_onboarding_profiles
                {where_clause}
                GROUP BY role
                ORDER BY user_count DESC
            """, *params)
            
            # Training progress analytics
            training_analytics = await conn.fetch(f"""
                SELECT 
                    te.program_name,
                    COUNT(DISTINCT te.user_id) as enrolled_users,
                    AVG(te.completion_percentage) as avg_completion,
                    COUNT(*) FILTER (WHERE te.status = 'completed') as completed_users
                FROM training_enrollments te
                JOIN user_onboarding_profiles uop ON te.user_id = uop.user_id
                {where_clause.replace('WHERE', 'WHERE') if where_clause else 'WHERE 1=1'}
                GROUP BY te.program_name
                ORDER BY enrolled_users DESC
            """, *params)
            
            # Recent activity trends
            activity_trends = await conn.fetch(f"""
                SELECT 
                    DATE(created_at) as activity_date,
                    activity_type,
                    COUNT(*) as activity_count
                FROM onboarding_activities oa
                JOIN user_onboarding_profiles uop ON oa.user_id = uop.user_id
                {where_clause.replace('WHERE', 'WHERE') if where_clause else 'WHERE 1=1'}
                AND oa.created_at >= NOW() - INTERVAL '30 days'
                GROUP BY DATE(created_at), activity_type
                ORDER BY activity_date DESC, activity_count DESC
            """, *params)
            
            return {
                "report_generated": datetime.utcnow().isoformat(),
                "department_filter": department,
                "overall_statistics": dict(overall_stats) if overall_stats else {},
                "stage_distribution": [dict(row) for row in stage_distribution],
                "role_analytics": [dict(row) for row in role_analytics],
                "training_analytics": [dict(row) for row in training_analytics],
                "activity_trends": [dict(row) for row in activity_trends],
                "success_metrics": {
                    "target_completion_rate": 85.0,
                    "current_completion_rate": float(overall_stats["fully_onboarded"]) / float(overall_stats["total_users"]) * 100 if overall_stats and overall_stats["total_users"] > 0 else 0,
                    "target_onboarding_score": 80.0,
                    "current_avg_score": float(overall_stats["avg_onboarding_score"]) if overall_stats else 0
                }
            }
    
    async def _get_onboarding_profile(self, user_id: str) -> Optional[UserOnboardingProfile]:
        """Retrieve user onboarding profile"""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT * FROM user_onboarding_profiles WHERE user_id = $1
            """, user_id)
            
            if row:
                return UserOnboardingProfile(
                    user_id=row["user_id"],
                    email=row["email"],
                    full_name=row["full_name"],
                    role=UserRole(row["role"]),
                    department=row["department"],
                    manager_email=row["manager_email"],
                    start_date=row["start_date"],
                    current_stage=OnboardingStage(row["current_stage"]),
                    completed_steps=row["completed_steps"] or [],
                    training_progress=json.loads(row["training_progress"]) if row["training_progress"] else {},
                    last_activity=row["last_activity"],
                    onboarding_score=row["onboarding_score"]
                )
        return None
    
    async def _save_onboarding_profile(self, profile: UserOnboardingProfile):
        """Save updated onboarding profile"""
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                UPDATE user_onboarding_profiles SET
                    current_stage = $1,
                    completed_steps = $2,
                    training_progress = $3,
                    last_activity = $4,
                    onboarding_score = $5,
                    updated_at = NOW()
                WHERE user_id = $6
            """, 
            profile.current_stage.value,
            profile.completed_steps,
            json.dumps(profile.training_progress),
            profile.last_activity,
            profile.onboarding_score,
            profile.user_id
            )
    
    async def _log_onboarding_activity(self, user_id: str, activity_type: str, 
                                     description: str, metadata: Dict[str, Any]):
        """Log onboarding activity for analytics"""
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO onboarding_activities (
                    user_id, activity_type, activity_description, metadata
                ) VALUES ($1, $2, $3, $4)
            """, user_id, activity_type, description, json.dumps(metadata))
    
    async def process_scheduled_tasks(self):
        """Process scheduled onboarding tasks (reminders, timeouts, etc.)"""
        current_time = datetime.utcnow().timestamp()
        
        # Process scheduled emails
        scheduled_emails = await self.redis_client.zrangebyscore(
            "scheduled_emails", 0, current_time, withscores=True
        )
        
        for email_task, score in scheduled_emails:
            email_task = email_task.decode()
            if email_task.startswith("welcome:"):
                user_id = email_task.split(":")[1]
                profile = await self._get_onboarding_profile(user_id)
                if profile:
                    await self._send_welcome_email(profile)
                    await self.redis_client.zrem("scheduled_emails", email_task)
        
        # Process progress reminders
        progress_checks = await self.redis_client.zrangebyscore(
            "progress_checks", 0, current_time, withscores=True
        )
        
        for check_task, score in progress_checks:
            check_task = check_task.decode()
            if check_task.startswith("reminder:"):
                parts = check_task.split(":")
                user_id = parts[1]
                days = parts[2]
                
                profile = await self._get_onboarding_profile(user_id)
                if profile and profile.onboarding_score < 50:  # Send reminder if not progressing well
                    await self._send_progress_reminder(profile, int(days))
                
                await self.redis_client.zrem("progress_checks", check_task)
        
        logger.info(f"Processed {len(scheduled_emails)} scheduled emails and {len(progress_checks)} progress checks")
    
    async def _send_progress_reminder(self, profile: UserOnboardingProfile, days: int):
        """Send progress reminder to user"""
        next_step = self._get_next_recommended_step(profile)
        
        reminder_content = f"""
        Hi {profile.full_name},

        You started your Splunk MCP onboarding {days} days ago and you're {profile.onboarding_score}% complete.
        
        Don't let your momentum slow down! Your next step is waiting:
        """
        
        if next_step:
            reminder_content += f"""
            
            Next Step: {next_step.name}
            Time needed: {next_step.estimated_time_minutes} minutes
            
            Continue your journey: https://splunk-mcp.company.com/onboarding
            """
        
        reminder_content += """
        
        Need help? Our support team is here to assist you.
        
        Best regards,
        The Splunk MCP Team
        """
        
        await self._send_notification(
            profile, NotificationChannel.EMAIL,
            f"Continue Your Splunk MCP Journey - {profile.onboarding_score}% Complete",
            reminder_content
        )

# Background task runner
async def run_onboarding_automation():
    """Main background task runner for onboarding automation"""
    
    automation_system = OnboardingAutomationSystem()
    await automation_system.initialize()
    
    logger.info("Onboarding automation system started")
    
    try:
        while True:
            await automation_system.process_scheduled_tasks()
            await asyncio.sleep(300)  # Check every 5 minutes
            
    except KeyboardInterrupt:
        logger.info("Onboarding automation system stopped")
    except Exception as e:
        logger.error(f"Onboarding automation error: {e}")
        raise

# CLI interface
async def main():
    """Main CLI interface for onboarding automation"""
    import argparse
    
    parser = argparse.ArgumentParser(description="User Onboarding Automation System")
    parser.add_argument("--config", default="config/onboarding-config.yaml", help="Configuration file path")
    parser.add_argument("--run-daemon", action="store_true", help="Run as background daemon")
    parser.add_argument("--start-onboarding", help="Start onboarding for user (JSON data)")
    parser.add_argument("--update-progress", help="Update user progress (user_id:activity_type:data)")
    parser.add_argument("--analytics", help="Generate analytics report (optional: department filter)")
    
    args = parser.parse_args()
    
    automation_system = OnboardingAutomationSystem(args.config)
    await automation_system.initialize()
    
    if args.run_daemon:
        await run_onboarding_automation()
    elif args.start_onboarding:
        user_data = json.loads(args.start_onboarding)
        profile = await automation_system.start_user_onboarding(user_data)
        print(f"Started onboarding for {profile.email}")
    elif args.update_progress:
        user_id, activity_type, data = args.update_progress.split(":", 2)
        activity_data = json.loads(data)
        success = await automation_system.update_onboarding_progress(user_id, activity_type, activity_data)
        print(f"Progress update {'successful' if success else 'failed'}")
    elif args.analytics is not None:
        department = args.analytics if args.analytics else None
        analytics = await automation_system.get_onboarding_analytics(department)
        print(json.dumps(analytics, indent=2, default=str))
    else:
        parser.print_help()

if __name__ == "__main__":
    asyncio.run(main())