# ==================== src/services/feedback_service.py ====================

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from src.models.database_models import (
    UserFeedback, EscalationFeedback, FeedbackAnalytics,
    FeedbackType, FeedbackCategory
)
from src.services.database_service import DatabaseService
from src.utilities.logger import get_logger

logger = get_logger(__name__)

class FeedbackService:
    """Service for collecting and analyzing user feedback"""
    
    def __init__(self, db_service: DatabaseService):
        self.db = db_service
    
    async def collect_feedback(
        self,
        session_id: str,
        feedback_type: FeedbackType,
        agent_name: str,
        rating: Optional[int] = None,
        feedback_text: Optional[str] = None,
        category: Optional[FeedbackCategory] = None,
        message_id: Optional[str] = None,
        intent: Optional[str] = None,
        routing_path: Optional[List[str]] = None,
        user_id: Optional[str] = None,
        caller_type: Optional[str] = None
    ) -> UserFeedback:
        """Collect feedback from a user"""
        
        feedback = UserFeedback(
            session_id=session_id,
            message_id=message_id,
            feedback_type=feedback_type,
            rating=rating,
            feedback_text=feedback_text,
            category=category,
            agent_name=agent_name,
            intent=intent,
            routing_path=routing_path or [],
            user_id=user_id,
            caller_type=caller_type
        )
        
        await self.db.insert_one("user_feedback", feedback.model_dump())
        
        logger.info(
            f"Collected {feedback_type} feedback for session {session_id} "
            f"(agent: {agent_name}, rating: {rating})"
        )
        
        # Trigger analysis if negative feedback
        if feedback_type == FeedbackType.THUMBS_DOWN or (rating and rating <= 2):
            await self._analyze_negative_feedback(feedback)
        
        return feedback
    
    async def collect_escalation_feedback(
        self,
        ticket_id: str,
        session_id: str,
        escalation_reason: str,
        was_escalation_necessary: bool,
        user_satisfaction: int,
        resolved: bool = False,
        resolution_time_minutes: Optional[int] = None,
        feedback_text: Optional[str] = None,
        could_have_been_automated: bool = False,
        suggested_improvement: Optional[str] = None
    ) -> EscalationFeedback:
        """Collect feedback on escalated cases"""
        
        feedback = EscalationFeedback(
            ticket_id=ticket_id,
            session_id=session_id,
            escalation_reason=escalation_reason,
            resolved=resolved,
            resolution_time_minutes=resolution_time_minutes,
            was_escalation_necessary=was_escalation_necessary,
            user_satisfaction=user_satisfaction,
            feedback_text=feedback_text,
            could_have_been_automated=could_have_been_automated,
            suggested_improvement=suggested_improvement
        )
        
        await self.db.insert_one("escalation_feedback", feedback.model_dump())
        
        logger.info(
            f"Collected escalation feedback for ticket {ticket_id} "
            f"(necessary: {was_escalation_necessary}, satisfaction: {user_satisfaction})"
        )
        
        # If escalation wasn't necessary, flag for review
        if not was_escalation_necessary:
            await self._flag_unnecessary_escalation(feedback)
        
        return feedback
    
    async def _analyze_negative_feedback(self, feedback: UserFeedback):
        """Analyze negative feedback to identify patterns"""
        
        # Check if this is a recurring issue
        similar_feedback = await self.db.find_many(
            "user_feedback",
            {
                "agent_name": feedback.agent_name,
                "intent": feedback.intent,
                "feedback_type": {"$in": [FeedbackType.THUMBS_DOWN, FeedbackType.RATING]},
                "timestamp": {"$gte": datetime.now(datetime.UTC) - timedelta(days=7)}
            }
        )
        
        if len(similar_feedback) >= 5:  # Threshold for pattern detection
            logger.warning(
                f"Pattern detected: Multiple negative feedback for "
                f"{feedback.agent_name}/{feedback.intent} "
                f"({len(similar_feedback)} occurrences in last 7 days)"
            )
            
            # Create improvement opportunity
            await self._create_improvement_opportunity(
                agent_name=feedback.agent_name,
                intent=feedback.intent,
                issue_description=f"High negative feedback rate: {len(similar_feedback)} occurrences",
                sample_feedback=[fb["feedback_text"] for fb in similar_feedback if fb.get("feedback_text")]
            )
    
    async def _flag_unnecessary_escalation(self, feedback: EscalationFeedback):
        """Flag unnecessary escalations for training data improvement"""
        
        logger.warning(
            f"Unnecessary escalation flagged: ticket {feedback.ticket_id} "
            f"(reason: {feedback.escalation_reason})"
        )
        
        # Retrieve the full session to understand what could have been done differently
        session = await self.db.find_one("sessions", {"session_id": feedback.session_id})
        
        if session and feedback.could_have_been_automated:
            await self._create_improvement_opportunity(
                agent_name="escalation_handler",
                intent=feedback.escalation_reason,
                issue_description="Could have been automated",
                sample_feedback=[feedback.feedback_text] if feedback.feedback_text else [],
                session_context=session
            )
    
    async def _create_improvement_opportunity(
        self,
        agent_name: str,
        intent: str,
        issue_description: str,
        sample_feedback: List[str],
        session_context: Optional[Dict[str, Any]] = None
    ):
        """Create an improvement opportunity for review"""
        
        opportunity = {
            "opportunity_id": str(uuid.uuid4()),
            "created_at": datetime.now(datetime.UTC),
            "agent_name": agent_name,
            "intent": intent,
            "issue_description": issue_description,
            "sample_feedback": sample_feedback[:5],  # Limit to 5 samples
            "session_context": session_context,
            "status": "open",
            "priority": "high" if len(sample_feedback) >= 10 else "medium",
            "assigned_to": None,
            "resolved": False
        }
        
        await self.db.insert_one("improvement_opportunities", opportunity)
        
        logger.info(f"Created improvement opportunity: {opportunity['opportunity_id']}")
    
    async def get_feedback_summary(
        self,
        agent_name: Optional[str] = None,
        days: int = 7
    ) -> Dict[str, Any]:
        """Get summary of feedback for a time period"""
        
        start_date = datetime.now(datetime.UTC) - timedelta(days=days)
        
        query = {"timestamp": {"$gte": start_date}}
        if agent_name:
            query["agent_name"] = agent_name
        
        all_feedback = await self.db.find_many("user_feedback", query)
        
        if not all_feedback:
            return {
                "period_days": days,
                "total_feedback": 0,
                "message": "No feedback in this period"
            }
        
        # Calculate metrics
        total = len(all_feedback)
        positive = sum(
            1 for fb in all_feedback
            if fb.get("feedback_type") == FeedbackType.THUMBS_UP or
               (fb.get("rating") and fb["rating"] >= 4)
        )
        negative = sum(
            1 for fb in all_feedback
            if fb.get("feedback_type") == FeedbackType.THUMBS_DOWN or
               (fb.get("rating") and fb["rating"] <= 2)
        )
        
        ratings = [fb["rating"] for fb in all_feedback if fb.get("rating")]
        avg_rating = sum(ratings) / len(ratings) if ratings else None
        
        # Breakdown by category
        category_counts = Counter(
            fb.get("category") for fb in all_feedback if fb.get("category")
        )
        
        # Breakdown by intent
        intent_feedback = defaultdict(lambda: {"positive": 0, "negative": 0, "total": 0})
        for fb in all_feedback:
            intent = fb.get("intent", "unknown")
            intent_feedback[intent]["total"] += 1
            if fb.get("feedback_type") == FeedbackType.THUMBS_UP or (fb.get("rating") and fb["rating"] >= 4):
                intent_feedback[intent]["positive"] += 1
            elif fb.get("feedback_type") == FeedbackType.THUMBS_DOWN or (fb.get("rating") and fb["rating"] <= 2):
                intent_feedback[intent]["negative"] += 1
        
        return {
            "period_days": days,
            "total_feedback": total,
            "positive_feedback": positive,
            "negative_feedback": negative,
            "neutral_feedback": total - positive - negative,
            "positive_rate": positive / total if total > 0 else 0,
            "avg_rating": avg_rating,
            "category_breakdown": dict(category_counts),
            "intent_breakdown": dict(intent_feedback),
            "agent_name": agent_name or "all"
        }
    
    async def generate_analytics(
        self,
        period_days: int = 30
    ) -> FeedbackAnalytics:
        """Generate comprehensive feedback analytics"""
        
        end_date = datetime.now(datetime.UTC)
        start_date = end_date - timedelta(days=period_days)
        
        all_feedback = await self.db.find_many(
            "user_feedback",
            {"timestamp": {"$gte": start_date, "$lte": end_date}}
        )
        
        # Overall metrics
        total_count = len(all_feedback)
        positive_count = sum(
            1 for fb in all_feedback
            if fb.get("feedback_type") == FeedbackType.THUMBS_UP or
               (fb.get("rating") and fb["rating"] >= 4)
        )
        negative_count = sum(
            1 for fb in all_feedback
            if fb.get("feedback_type") == FeedbackType.THUMBS_DOWN or
               (fb.get("rating") and fb["rating"] <= 2)
        )
        
        ratings = [fb["rating"] for fb in all_feedback if fb.get("rating")]
        avg_rating = sum(ratings) / len(ratings) if ratings else None
        
        # By agent
        feedback_by_agent = defaultdict(lambda: {
            "total": 0,
            "positive": 0,
            "negative": 0,
            "avg_rating": None
        })
        
        for fb in all_feedback:
            agent = fb.get("agent_name", "unknown")
            feedback_by_agent[agent]["total"] += 1
            
            if fb.get("feedback_type") == FeedbackType.THUMBS_UP or (fb.get("rating") and fb["rating"] >= 4):
                feedback_by_agent[agent]["positive"] += 1
            elif fb.get("feedback_type") == FeedbackType.THUMBS_DOWN or (fb.get("rating") and fb["rating"] <= 2):
                feedback_by_agent[agent]["negative"] += 1
        
        # By intent
        feedback_by_intent = defaultdict(lambda: {
            "total": 0,
            "positive": 0,
            "negative": 0
        })
        
        for fb in all_feedback:
            intent = fb.get("intent", "unknown")
            feedback_by_intent[intent]["total"] += 1
            
            if fb.get("feedback_type") == FeedbackType.THUMBS_UP or (fb.get("rating") and fb["rating"] >= 4):
                feedback_by_intent[intent]["positive"] += 1
            elif fb.get("feedback_type") == FeedbackType.THUMBS_DOWN or (fb.get("rating") and fb["rating"] <= 2):
                feedback_by_intent[intent]["negative"] += 1
        
        # Identify top issues
        negative_feedback = [
            fb for fb in all_feedback
            if fb.get("feedback_type") == FeedbackType.THUMBS_DOWN or
               (fb.get("rating") and fb["rating"] <= 2)
        ]
        
        issue_counter = Counter()
        for fb in negative_feedback:
            if fb.get("category"):
                issue_counter[fb["category"]] += 1
        
        top_issues = [
            {
                "category": category,
                "count": count,
                "percentage": count / len(negative_feedback) if negative_feedback else 0
            }
            for category, count in issue_counter.most_common(5)
        ]
        
        # Improvement opportunities
        improvement_opps = await self.db.find_many(
            "improvement_opportunities",
            {"status": "open"}
        )
        
        improvement_opportunities = [
            opp["issue_description"] for opp in improvement_opps[:10]
        ]
        
        analytics = FeedbackAnalytics(
            period_start=start_date,
            period_end=end_date,
            total_feedback_count=total_count,
            positive_feedback_count=positive_count,
            negative_feedback_count=negative_count,
            avg_rating=avg_rating,
            feedback_by_agent=dict(feedback_by_agent),
            feedback_by_intent=dict(feedback_by_intent),
            top_issues=top_issues,
            improvement_opportunities=improvement_opportunities
        )
        
        # Save analytics
        await self.db.insert_one("feedback_analytics", analytics.model_dump())
        
        logger.info(
            f"Generated feedback analytics for {period_days} days: "
            f"{total_count} total, {positive_count} positive, {negative_count} negative"
        )
        
        return analytics
    
    async def get_improvement_opportunities(
        self,
        status: str = "open",
        priority: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get improvement opportunities for review"""
        
        query = {"status": status}
        if priority:
            query["priority"] = priority
        
        opportunities = await self.db.find_many(
            "improvement_opportunities",
            query,
            limit=limit,
            sort=[("priority", -1), ("created_at", -1)]
        )
        
        return opportunities
    
    async def update_improvement_opportunity(
        self,
        opportunity_id: str,
        status: Optional[str] = None,
        assigned_to: Optional[str] = None,
        resolved: Optional[bool] = None,
        resolution_notes: Optional[str] = None
    ):
        """Update an improvement opportunity"""
        
        update_fields = {}
        if status:
            update_fields["status"] = status
        if assigned_to:
            update_fields["assigned_to"] = assigned_to
        if resolved is not None:
            update_fields["resolved"] = resolved
        if resolution_notes:
            update_fields["resolution_notes"] = resolution_notes
        
        if update_fields:
            update_fields["updated_at"] = datetime.now(datetime.UTC)
            
            await self.db.update_one(
                "improvement_opportunities",
                {"opportunity_id": opportunity_id},
                {"$set": update_fields}
            )
            
            logger.info(f"Updated improvement opportunity {opportunity_id}: {update_fields}")