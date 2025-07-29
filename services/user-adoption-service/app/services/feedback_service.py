#!/usr/bin/env python3
"""
Feedback Service
================
Service for processing, analyzing, and managing user feedback
"""

import uuid
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, or_, func, desc
from sqlalchemy.orm import selectinload

from app.models.adoption_models import (
    UserProfile, FeedbackSubmission, FeedbackFollowUp, SurveyTemplate, SurveyResponse,
    FeedbackType, FeedbackPriority
)

class FeedbackService:
    """Service for managing user feedback and surveys"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        
        # Keyword mappings for auto-categorization
        self.category_keywords = {
            "performance": ["slow", "slow down", "loading", "timeout", "lag", "delay", "response time", "performance"],
            "user_interface": ["ui", "interface", "design", "layout", "navigation", "menu", "button", "visual"],
            "functionality": ["feature", "function", "work", "broken", "doesn't work", "not working", "error"],
            "data_accuracy": ["wrong", "incorrect", "inaccurate", "missing", "data", "results", "values"],
            "documentation": ["help", "tutorial", "guide", "documentation", "instructions", "unclear"],
            "integration": ["api", "connect", "sync", "integration", "export", "import", "webhook"],
            "training": ["learn", "training", "tutorial", "onboarding", "help", "guidance"],
            "mobile": ["mobile", "phone", "tablet", "responsive", "app"],
            "accessibility": ["accessibility", "screen reader", "keyboard", "contrast", "font size"],
            "security": ["security", "permission", "access", "login", "authentication", "authorization"]
        }
        
        # Sentiment analysis keywords
        self.positive_keywords = ["good", "great", "excellent", "love", "awesome", "perfect", "amazing", "helpful"]
        self.negative_keywords = ["bad", "terrible", "awful", "hate", "horrible", "useless", "frustrating", "annoying"]
    
    async def auto_categorize_feedback(self, feedback_id: uuid.UUID) -> str:
        """Automatically categorize feedback based on content analysis"""
        
        # Get feedback submission
        result = await self.db.execute(
            select(FeedbackSubmission).where(FeedbackSubmission.id == feedback_id)
        )
        feedback = result.scalar_one_or_none()
        
        if not feedback:
            return "uncategorized"
        
        # Combine title and description for analysis
        content = f"{feedback.title} {feedback.description}".lower()
        
        # Score each category
        category_scores = {}
        for category, keywords in self.category_keywords.items():
            score = 0
            for keyword in keywords:
                score += content.count(keyword)
            if score > 0:
                category_scores[category] = score
        
        # Determine best category
        if category_scores:
            best_category = max(category_scores, key=category_scores.get)
            
            # Update feedback with category
            feedback.category = best_category
            await self.db.commit()
            
            return best_category
        
        return "general"
    
    def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyze sentiment of feedback text"""
        
        text_lower = text.lower()
        
        positive_score = sum(1 for keyword in self.positive_keywords if keyword in text_lower)
        negative_score = sum(1 for keyword in self.negative_keywords if keyword in text_lower)
        
        total_score = positive_score + negative_score
        if total_score == 0:
            return {"sentiment": "neutral", "confidence": 0.0, "positive_score": 0, "negative_score": 0}
        
        sentiment_score = (positive_score - negative_score) / total_score
        
        if sentiment_score > 0.3:
            sentiment = "positive"
        elif sentiment_score < -0.3:
            sentiment = "negative"
        else:
            sentiment = "neutral"
        
        confidence = abs(sentiment_score)
        
        return {
            "sentiment": sentiment,
            "confidence": confidence,
            "positive_score": positive_score,
            "negative_score": negative_score
        }
    
    async def get_feedback_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Get comprehensive feedback analytics"""
        
        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Get feedback submissions in date range
        result = await self.db.execute(
            select(FeedbackSubmission)
            .where(FeedbackSubmission.created_at >= start_date)
            .options(selectinload(FeedbackSubmission.user_profile))
        )
        submissions = result.scalars().all()
        
        # Basic metrics
        total_submissions = len(submissions)
        
        # Sentiment analysis
        sentiment_analysis = {"positive": 0, "negative": 0, "neutral": 0}
        for submission in submissions:
            sentiment = self.analyze_sentiment(f"{submission.title} {submission.description}")
            sentiment_analysis[sentiment["sentiment"]] += 1
        
        # Category distribution
        category_distribution = {}
        for submission in submissions:
            category = submission.category or "uncategorized"
            category_distribution[category] = category_distribution.get(category, 0) + 1
        
        # Priority distribution
        priority_distribution = {}
        for submission in submissions:
            priority = submission.priority
            priority_distribution[priority] = priority_distribution.get(priority, 0) + 1
        
        # Type distribution
        type_distribution = {}
        for submission in submissions:
            feedback_type = submission.feedback_type
            type_distribution[feedback_type] = type_distribution.get(feedback_type, 0) + 1
        
        # Rating analysis
        ratings = [s.rating for s in submissions if s.rating is not None]
        avg_rating = sum(ratings) / len(ratings) if ratings else 0
        rating_distribution = {}
        for rating in ratings:
            rating_distribution[rating] = rating_distribution.get(rating, 0) + 1
        
        # Response time analysis
        response_times = []
        resolution_times = []
        for submission in submissions:
            if submission.follow_ups:
                first_response = min(submission.follow_ups, key=lambda x: x.created_at)
                response_time = (first_response.created_at - submission.created_at).total_seconds() / 3600
                response_times.append(response_time)
            
            if submission.resolved_at:
                resolution_time = (submission.resolved_at - submission.created_at).total_seconds() / 3600
                resolution_times.append(resolution_time)
        
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        avg_resolution_time = sum(resolution_times) / len(resolution_times) if resolution_times else 0
        
        # Trends over time
        daily_trends = {}
        for submission in submissions:
            date_key = submission.created_at.date().isoformat()
            if date_key not in daily_trends:
                daily_trends[date_key] = 0
            daily_trends[date_key] += 1
        
        # Top issues (based on similar descriptions)
        issue_patterns = self._identify_common_issues(submissions)
        
        return {
            "period": {
                "start_date": start_date,
                "end_date": end_date,
                "days": days
            },
            "overview": {
                "total_submissions": total_submissions,
                "average_rating": round(avg_rating, 2),
                "response_rate": len(response_times) / total_submissions * 100 if total_submissions > 0 else 0,
                "resolution_rate": len(resolution_times) / total_submissions * 100 if total_submissions > 0 else 0,
                "avg_response_time_hours": round(avg_response_time, 2),
                "avg_resolution_time_hours": round(avg_resolution_time, 2)
            },
            "distributions": {
                "sentiment": sentiment_analysis,
                "categories": category_distribution,
                "priorities": priority_distribution,
                "types": type_distribution,
                "ratings": rating_distribution
            },
            "trends": {
                "daily": daily_trends
            },
            "top_issues": issue_patterns
        }
    
    def _identify_common_issues(self, submissions: List[FeedbackSubmission]) -> List[Dict[str, Any]]:
        """Identify common issues from feedback submissions"""
        
        # Group submissions by similar keywords
        issue_groups = {}
        
        for submission in submissions:
            # Extract key phrases from title and description
            text = f"{submission.title} {submission.description}".lower()
            words = re.findall(r'\b\w+\b', text)
            
            # Filter common words and create signature
            filtered_words = [w for w in words if len(w) > 3 and w not in ['this', 'that', 'with', 'from', 'they', 'have', 'been', 'were', 'said', 'each', 'which', 'their']]
            
            # Create issue signature based on most common words
            word_freq = {}
            for word in filtered_words:
                word_freq[word] = word_freq.get(word, 0) + 1
            
            # Use top 3 words as signature
            top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:3]
            signature = '_'.join([word for word, freq in top_words if freq > 0])
            
            if signature and len(signature) > 3:
                if signature not in issue_groups:
                    issue_groups[signature] = []
                issue_groups[signature].append(submission)
        
        # Find groups with multiple submissions (common issues)
        common_issues = []
        for signature, group in issue_groups.items():
            if len(group) >= 2:  # At least 2 similar submissions
                # Calculate average rating for this issue
                ratings = [s.rating for s in group if s.rating is not None]
                avg_rating = sum(ratings) / len(ratings) if ratings else None
                
                # Get example submission
                example = group[0]
                
                common_issues.append({
                    "issue_signature": signature,
                    "occurrence_count": len(group),
                    "average_rating": round(avg_rating, 2) if avg_rating else None,
                    "example_title": example.title,
                    "example_description": example.description[:200] + "..." if len(example.description) > 200 else example.description,
                    "categories": list(set([s.category for s in group if s.category])),
                    "types": list(set([s.feedback_type for s in group])),
                    "priority_distribution": {
                        priority: len([s for s in group if s.priority == priority])
                        for priority in set([s.priority for s in group])
                    }
                })
        
        # Sort by occurrence count
        common_issues.sort(key=lambda x: x["occurrence_count"], reverse=True)
        
        return common_issues[:10]  # Return top 10 common issues
    
    async def is_user_eligible_for_survey(self, user_profile_id: uuid.UUID, survey_template_id: uuid.UUID) -> bool:
        """Check if user is eligible for a specific survey"""
        
        # Get survey template
        template_result = await self.db.execute(
            select(SurveyTemplate).where(SurveyTemplate.id == survey_template_id)
        )
        template = template_result.scalar_one_or_none()
        
        if not template or not template.is_active:
            return False
        
        # Check expiration
        if template.expiration_date and datetime.utcnow() > template.expiration_date:
            return False
        
        # Check if user has already responded recently
        if template.frequency_limit:
            cutoff_date = datetime.utcnow() - timedelta(days=template.frequency_limit)
            recent_response_result = await self.db.execute(
                select(SurveyResponse).where(
                    and_(
                        SurveyResponse.user_profile_id == user_profile_id,
                        SurveyResponse.survey_template_id == survey_template_id,
                        SurveyResponse.created_at >= cutoff_date
                    )
                )
            )
            recent_response = recent_response_result.scalar_one_or_none()
            if recent_response:
                return False
        
        # Check max responses limit
        if template.max_responses:
            response_count_result = await self.db.execute(
                select(func.count(SurveyResponse.id)).where(
                    SurveyResponse.survey_template_id == survey_template_id
                )
            )
            response_count = response_count_result.scalar() or 0
            if response_count >= template.max_responses:
                return False
        
        # Check targeting rules
        if template.targeting_rules:
            user_result = await self.db.execute(
                select(UserProfile).where(UserProfile.id == user_profile_id)
            )
            user_profile = user_result.scalar_one_or_none()
            
            if not user_profile:
                return False
            
            # Apply targeting rules
            if not self._check_targeting_rules(user_profile, template.targeting_rules):
                return False
        
        # Check trigger conditions
        if template.trigger_conditions:
            if not await self._check_trigger_conditions(user_profile_id, template.trigger_conditions):
                return False
        
        return True
    
    def _check_targeting_rules(self, user_profile: UserProfile, targeting_rules: Dict[str, Any]) -> bool:
        """Check if user matches targeting rules"""
        
        # Example targeting rules:
        # {
        #   "departments": ["engineering", "product"],
        #   "user_types": ["end_user"],
        #   "engagement_levels": ["beginner", "intermediate"],
        #   "min_logins": 5,
        #   "created_after": "2024-01-01"
        # }
        
        # Department targeting
        if "departments" in targeting_rules:
            if user_profile.department not in targeting_rules["departments"]:
                return False
        
        # User type targeting
        if "user_types" in targeting_rules:
            if user_profile.user_type not in targeting_rules["user_types"]:
                return False
        
        # Engagement level targeting
        if "engagement_levels" in targeting_rules:
            if user_profile.engagement_level not in targeting_rules["engagement_levels"]:
                return False
        
        # Minimum logins
        if "min_logins" in targeting_rules:
            if user_profile.total_logins < targeting_rules["min_logins"]:
                return False
        
        # Created after date
        if "created_after" in targeting_rules:
            created_after = datetime.fromisoformat(targeting_rules["created_after"])
            if user_profile.created_at < created_after:
                return False
        
        return True
    
    async def _check_trigger_conditions(self, user_profile_id: uuid.UUID, trigger_conditions: Dict[str, Any]) -> bool:
        """Check if trigger conditions are met"""
        
        # Example trigger conditions:
        # {
        #   "after_onboarding_completion": true,
        #   "after_feature_usage": "dashboard_create",
        #   "time_since_last_survey": 30,  # days
        #   "activity_threshold": 10  # minimum activities in last 7 days
        # }
        
        # Get user profile
        user_result = await self.db.execute(
            select(UserProfile).where(UserProfile.id == user_profile_id)
        )
        user_profile = user_result.scalar_one_or_none()
        
        if not user_profile:
            return False
        
        # After onboarding completion
        if trigger_conditions.get("after_onboarding_completion"):
            if user_profile.onboarding_status != "completed":
                return False
        
        # After specific feature usage
        if "after_feature_usage" in trigger_conditions:
            feature_name = trigger_conditions["after_feature_usage"]
            # Check if user has used this feature (simplified check)
            if feature_name == "dashboard_create" and user_profile.total_dashboards == 0:
                return False
            elif feature_name == "alert_create" and user_profile.total_alerts == 0:
                return False
        
        # Time since last survey
        if "time_since_last_survey" in trigger_conditions:
            days_threshold = trigger_conditions["time_since_last_survey"]
            cutoff_date = datetime.utcnow() - timedelta(days=days_threshold)
            
            recent_survey_result = await self.db.execute(
                select(SurveyResponse).where(
                    and_(
                        SurveyResponse.user_profile_id == user_profile_id,
                        SurveyResponse.created_at >= cutoff_date
                    )
                )
            )
            recent_survey = recent_survey_result.scalar_one_or_none()
            if recent_survey:
                return False
        
        return True
    
    async def generate_feedback_insights(self, days: int = 30) -> Dict[str, Any]:
        """Generate actionable insights from feedback data"""
        
        analytics = await self.get_feedback_analytics(days)
        
        insights = {
            "priority_insights": [],
            "category_insights": [],
            "sentiment_insights": [],
            "operational_insights": []
        }
        
        # Priority insights
        total_submissions = analytics["overview"]["total_submissions"]
        high_priority = analytics["distributions"]["priorities"].get("high", 0)
        critical_priority = analytics["distributions"]["priorities"].get("critical", 0)
        
        urgent_percentage = (high_priority + critical_priority) / total_submissions * 100 if total_submissions > 0 else 0
        
        if urgent_percentage > 30:
            insights["priority_insights"].append({
                "type": "high_urgency_volume",
                "severity": "high",
                "message": f"{urgent_percentage:.1f}% of feedback is high/critical priority",
                "recommendation": "Review resource allocation for urgent issues"
            })
        
        # Category insights
        categories = analytics["distributions"]["categories"]
        if categories:
            top_category = max(categories, key=categories.get)
            category_percentage = categories[top_category] / total_submissions * 100
            
            if category_percentage > 40:
                insights["category_insights"].append({
                    "type": "dominant_category",
                    "category": top_category,
                    "percentage": round(category_percentage, 1),
                    "message": f"'{top_category}' issues dominate feedback ({category_percentage:.1f}%)",
                    "recommendation": f"Focus improvement efforts on {top_category} area"
                })
        
        # Sentiment insights
        sentiment = analytics["distributions"]["sentiment"]
        negative_percentage = sentiment["negative"] / total_submissions * 100 if total_submissions > 0 else 0
        positive_percentage = sentiment["positive"] / total_submissions * 100 if total_submissions > 0 else 0
        
        if negative_percentage > 50:
            insights["sentiment_insights"].append({
                "type": "negative_sentiment_trend",
                "severity": "high",
                "percentage": round(negative_percentage, 1),
                "message": f"High negative sentiment in feedback ({negative_percentage:.1f}%)",
                "recommendation": "Investigate root causes of user dissatisfaction"
            })
        elif positive_percentage > 70:
            insights["sentiment_insights"].append({
                "type": "positive_sentiment_trend",
                "severity": "low",
                "percentage": round(positive_percentage, 1),
                "message": f"Strong positive sentiment in feedback ({positive_percentage:.1f}%)",
                "recommendation": "Identify and replicate successful practices"
            })
        
        # Operational insights
        avg_response_time = analytics["overview"]["avg_response_time_hours"]
        avg_resolution_time = analytics["overview"]["avg_resolution_time_hours"]
        
        if avg_response_time > 24:
            insights["operational_insights"].append({
                "type": "slow_response_time",
                "severity": "medium",
                "value": avg_response_time,
                "message": f"Average response time is {avg_response_time:.1f} hours",
                "recommendation": "Improve response time to under 24 hours"
            })
        
        if avg_resolution_time > 168:  # 1 week
            insights["operational_insights"].append({
                "type": "slow_resolution_time",
                "severity": "medium",
                "value": avg_resolution_time,
                "message": f"Average resolution time is {avg_resolution_time:.1f} hours",
                "recommendation": "Streamline resolution process"
            })
        
        return insights
    
    async def create_automated_survey_campaigns(self) -> List[Dict[str, Any]]:
        """Create automated survey campaigns based on user behavior"""
        
        campaigns = []
        
        # Onboarding completion survey
        onboarding_survey = {
            "name": "Post-Onboarding Feedback",
            "description": "Collect feedback after users complete onboarding",
            "survey_type": "onboarding",
            "questions": [
                {
                    "id": "onboarding_rating",
                    "type": "rating",
                    "question": "How would you rate your onboarding experience?",
                    "scale": 5,
                    "required": True
                },
                {
                    "id": "most_helpful",
                    "type": "multiple_choice",
                    "question": "Which part of the onboarding was most helpful?",
                    "options": ["Welcome tour", "First query", "Dashboard creation", "Documentation", "Video tutorials"],
                    "required": True
                },
                {
                    "id": "improvement_suggestions",
                    "type": "text",
                    "question": "How can we improve the onboarding experience?",
                    "required": False
                }
            ],
            "targeting_rules": {
                "user_types": ["end_user"],
                "min_logins": 1
            },
            "trigger_conditions": {
                "after_onboarding_completion": True
            },
            "frequency_limit": 90
        }
        campaigns.append(onboarding_survey)
        
        # Feature usage satisfaction survey
        feature_survey = {
            "name": "Feature Usage Satisfaction",
            "description": "Collect feedback on specific feature usage",
            "survey_type": "feature",
            "questions": [
                {
                    "id": "feature_satisfaction",
                    "type": "rating",
                    "question": "How satisfied are you with this feature?",
                    "scale": 5,
                    "required": True
                },
                {
                    "id": "ease_of_use",
                    "type": "rating",
                    "question": "How easy was this feature to use?",
                    "scale": 5,
                    "required": True
                },
                {
                    "id": "feature_improvement",
                    "type": "text",
                    "question": "What would make this feature better?",
                    "required": False
                }
            ],
            "targeting_rules": {
                "engagement_levels": ["intermediate", "advanced"]
            },
            "trigger_conditions": {
                "after_feature_usage": "dashboard_create",
                "activity_threshold": 5
            },
            "frequency_limit": 60
        }
        campaigns.append(feature_survey)
        
        # Periodic satisfaction survey
        satisfaction_survey = {
            "name": "Monthly Satisfaction Survey",
            "description": "Regular satisfaction check with active users",
            "survey_type": "periodic",
            "questions": [
                {
                    "id": "overall_satisfaction",
                    "type": "rating",
                    "question": "How satisfied are you with the platform overall?",
                    "scale": 5,
                    "required": True
                },
                {
                    "id": "recommendation_likelihood",
                    "type": "rating",
                    "question": "How likely are you to recommend this platform to a colleague?",
                    "scale": 10,
                    "required": True
                },
                {
                    "id": "most_valuable_feature",
                    "type": "multiple_choice",
                    "question": "Which feature do you find most valuable?",
                    "options": ["Natural language queries", "Dashboards", "Alerts", "Reports", "Integrations"],
                    "required": True
                },
                {
                    "id": "missing_features",
                    "type": "text",
                    "question": "What features are you missing?",
                    "required": False
                }
            ],
            "targeting_rules": {
                "min_logins": 10,
                "engagement_levels": ["intermediate", "advanced", "expert"]
            },
            "trigger_conditions": {
                "time_since_last_survey": 30,
                "activity_threshold": 15
            },
            "frequency_limit": 30
        }
        campaigns.append(satisfaction_survey)
        
        return campaigns