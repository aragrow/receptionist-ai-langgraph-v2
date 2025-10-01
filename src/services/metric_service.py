# ==================== src/services/metric_service.py ====================

"""
Metrics Service for AI Receptionist
Tracks performance metrics across all tiers (L1, L2, L3)
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict
from dataclasses import dataclass, asdict
import statistics
from enum import Enum


class MetricType(Enum):
    """Types of metrics tracked"""
    L1_CLASSIFICATION = "l1_classification"
    L2_REFINEMENT = "l2_refinement"
    L3_EXECUTION = "l3_execution"
    ROUTING_TIME = "routing_time"
    CLARIFICATION = "clarification"
    ESCALATION = "escalation"
    SESSION = "session"


@dataclass
class L1Metric:
    """Metrics for L1 (Receptionist) tier"""
    session_id: str
    timestamp: datetime
    intent_name: str
    confidence: float
    caller_type: str
    processing_time_ms: float
    correct_classification: Optional[bool] = None  # Set via feedback


@dataclass
class L2Metric:
    """Metrics for L2 (Intent Refiner) tier"""
    session_id: str
    timestamp: datetime
    intent_name: str
    confidence: float
    slots_extracted: int
    slots_required: int
    processing_time_ms: float
    clarification_needed: bool


@dataclass
class L3Metric:
    """Metrics for L3 (Domain Specialist) tier"""
    session_id: str
    timestamp: datetime
    agent_name: str
    action: str
    success: bool
    processing_time_ms: float
    error_code: Optional[str] = None


@dataclass
class RoutingMetric:
    """Metrics for routing decisions"""
    session_id: str
    timestamp: datetime
    from_tier: str
    to_tier: str
    routing_time_ms: float
    confidence: float
    routing_reason: str


@dataclass
class ClarificationMetric:
    """Metrics for clarification requests"""
    session_id: str
    timestamp: datetime
    tier: str
    attempt_number: int
    missing_slots: List[str]
    resolved: bool


@dataclass
class EscalationMetric:
    """Metrics for human escalations"""
    session_id: str
    timestamp: datetime
    reason: str
    tier: str
    confidence: float
    clarification_attempts: int
    ticket_id: str


@dataclass
class SessionMetric:
    """Metrics for full session"""
    session_id: str
    start_time: datetime
    end_time: datetime
    total_duration_ms: float
    message_count: int
    tiers_traversed: List[str]
    final_outcome: str  # success, escalated, error, abandoned
    caller_type: str


class MetricsService:
    """
    Service for tracking and aggregating metrics across the AI Receptionist workflow
    """
    
    def __init__(self):
        # In-memory storage (replace with Redis/TimescaleDB in production)
        self.l1_metrics: List[L1Metric] = []
        self.l2_metrics: List[L2Metric] = []
        self.l3_metrics: List[L3Metric] = []
        self.routing_metrics: List[RoutingMetric] = []
        self.clarification_metrics: List[ClarificationMetric] = []
        self.escalation_metrics: List[EscalationMetric] = []
        self.session_metrics: List[SessionMetric] = []
        
    # ========== RECORDING METHODS ==========
    
    def record_l1_classification(
        self,
        session_id: str,
        intent_name: str,
        confidence: float,
        caller_type: str,
        processing_time_ms: float
    ) -> None:
        """Record L1 classification metrics"""
        metric = L1Metric(
            session_id=session_id,
            timestamp=datetime.now(datetime.UTC),
            intent_name=intent_name,
            confidence=confidence,
            caller_type=caller_type,
            processing_time_ms=processing_time_ms
        )
        self.l1_metrics.append(metric)
    
    def record_l2_refinement(
        self,
        session_id: str,
        intent_name: str,
        confidence: float,
        slots_extracted: int,
        slots_required: int,
        processing_time_ms: float,
        clarification_needed: bool
    ) -> None:
        """Record L2 refinement metrics"""
        metric = L2Metric(
            session_id=session_id,
            timestamp=datetime.now(datetime.UTC),
            intent_name=intent_name,
            confidence=confidence,
            slots_extracted=slots_extracted,
            slots_required=slots_required,
            processing_time_ms=processing_time_ms,
            clarification_needed=clarification_needed
        )
        self.l2_metrics.append(metric)
    
    def record_l3_execution(
        self,
        session_id: str,
        agent_name: str,
        action: str,
        success: bool,
        processing_time_ms: float,
        error_code: Optional[str] = None
    ) -> None:
        """Record L3 execution metrics"""
        metric = L3Metric(
            session_id=session_id,
            timestamp=datetime.now(datetime.UTC),
            agent_name=agent_name,
            action=action,
            success=success,
            processing_time_ms=processing_time_ms,
            error_code=error_code
        )
        self.l3_metrics.append(metric)
    
    def record_routing(
        self,
        session_id: str,
        from_tier: str,
        to_tier: str,
        routing_time_ms: float,
        confidence: float,
        routing_reason: str
    ) -> None:
        """Record routing decision metrics"""
        metric = RoutingMetric(
            session_id=session_id,
            timestamp=datetime.now(datetime.UTC),
            from_tier=from_tier,
            to_tier=to_tier,
            routing_time_ms=routing_time_ms,
            confidence=confidence,
            routing_reason=routing_reason
        )
        self.routing_metrics.append(metric)
    
    def record_clarification(
        self,
        session_id: str,
        tier: str,
        attempt_number: int,
        missing_slots: List[str],
        resolved: bool
    ) -> None:
        """Record clarification request metrics"""
        metric = ClarificationMetric(
            session_id=session_id,
            timestamp=datetime.now(datetime.UTC),
            tier=tier,
            attempt_number=attempt_number,
            missing_slots=missing_slots,
            resolved=resolved
        )
        self.clarification_metrics.append(metric)
    
    def record_escalation(
        self,
        session_id: str,
        reason: str,
        tier: str,
        confidence: float,
        clarification_attempts: int,
        ticket_id: str
    ) -> None:
        """Record human escalation metrics"""
        metric = EscalationMetric(
            session_id=session_id,
            timestamp=datetime.now(datetime.UTC),
            reason=reason,
            tier=tier,
            confidence=confidence,
            clarification_attempts=clarification_attempts,
            ticket_id=ticket_id
        )
        self.escalation_metrics.append(metric)
    
    def record_session(
        self,
        session_id: str,
        start_time: datetime,
        end_time: datetime,
        message_count: int,
        tiers_traversed: List[str],
        final_outcome: str,
        caller_type: str
    ) -> None:
        """Record complete session metrics"""
        duration_ms = (end_time - start_time).total_seconds() * 1000
        metric = SessionMetric(
            session_id=session_id,
            start_time=start_time,
            end_time=end_time,
            total_duration_ms=duration_ms,
            message_count=message_count,
            tiers_traversed=tiers_traversed,
            final_outcome=final_outcome,
            caller_type=caller_type
        )
        self.session_metrics.append(metric)
    
    # ========== ANALYTICS METHODS ==========
    
    def get_l1_accuracy(self, time_window_hours: int = 24) -> Dict[str, Any]:
        """Calculate L1 intent classification accuracy"""
        cutoff = datetime.now(datetime.UTC) - timedelta(hours=time_window_hours)
        recent_metrics = [m for m in self.l1_metrics if m.timestamp >= cutoff]
        
        if not recent_metrics:
            return {"error": "No data available"}
        
        # Filter metrics with feedback
        with_feedback = [m for m in recent_metrics if m.correct_classification is not None]
        
        if not with_feedback:
            total_count = len(recent_metrics)
            avg_confidence = statistics.mean([m.confidence for m in recent_metrics])
            return {
                "total_classifications": total_count,
                "avg_confidence": round(avg_confidence, 3),
                "accuracy": "No feedback data available",
                "note": "Accuracy requires human feedback on classifications"
            }
        
        correct = sum(1 for m in with_feedback if m.correct_classification)
        total = len(with_feedback)
        accuracy = correct / total if total > 0 else 0
        
        # Breakdown by intent
        intent_stats = defaultdict(lambda: {"correct": 0, "total": 0})
        for m in with_feedback:
            intent_stats[m.intent_name]["total"] += 1
            if m.correct_classification:
                intent_stats[m.intent_name]["correct"] += 1
        
        return {
            "total_classifications": len(recent_metrics),
            "with_feedback": total,
            "accuracy": round(accuracy, 3),
            "correct_count": correct,
            "avg_confidence": round(statistics.mean([m.confidence for m in recent_metrics]), 3),
            "by_intent": {
                intent: {
                    "accuracy": round(stats["correct"] / stats["total"], 3),
                    "count": stats["total"]
                }
                for intent, stats in intent_stats.items()
            }
        }
    
    def get_confidence_distribution(self, tier: str = "L1", time_window_hours: int = 24) -> Dict[str, Any]:
        """Get confidence score distribution by tier"""
        cutoff = datetime.now(datetime.UTC) - timedelta(hours=time_window_hours)
        
        if tier == "L1":
            metrics = [m for m in self.l1_metrics if m.timestamp >= cutoff]
            confidences = [m.confidence for m in metrics]
        elif tier == "L2":
            metrics = [m for m in self.l2_metrics if m.timestamp >= cutoff]
            confidences = [m.confidence for m in metrics]
        else:
            return {"error": f"Unknown tier: {tier}"}
        
        if not confidences:
            return {"error": "No data available"}
        
        # Calculate distribution buckets
        high = sum(1 for c in confidences if c >= 0.75)
        medium = sum(1 for c in confidences if 0.4 <= c < 0.75)
        low = sum(1 for c in confidences if c < 0.4)
        
        return {
            "tier": tier,
            "total_samples": len(confidences),
            "avg_confidence": round(statistics.mean(confidences), 3),
            "median_confidence": round(statistics.median(confidences), 3),
            "min_confidence": round(min(confidences), 3),
            "max_confidence": round(max(confidences), 3),
            "distribution": {
                "high (≥0.75)": {"count": high, "percentage": round(high / len(confidences) * 100, 1)},
                "medium (0.4-0.74)": {"count": medium, "percentage": round(medium / len(confidences) * 100, 1)},
                "low (<0.4)": {"count": low, "percentage": round(low / len(confidences) * 100, 1)}
            }
        }
    
    def get_avg_routing_time(self, time_window_hours: int = 24) -> Dict[str, Any]:
        """Calculate average routing time from L1→L2→L3"""
        cutoff = datetime.now(datetime.UTC) - timedelta(hours=time_window_hours)
        recent_metrics = [m for m in self.routing_metrics if m.timestamp >= cutoff]
        
        if not recent_metrics:
            return {"error": "No data available"}
        
        # Group by transition type
        transitions = defaultdict(list)
        for m in recent_metrics:
            key = f"{m.from_tier}→{m.to_tier}"
            transitions[key].append(m.routing_time_ms)
        
        return {
            "total_routings": len(recent_metrics),
            "avg_routing_time_ms": round(statistics.mean([m.routing_time_ms for m in recent_metrics]), 2),
            "by_transition": {
                transition: {
                    "avg_ms": round(statistics.mean(times), 2),
                    "min_ms": round(min(times), 2),
                    "max_ms": round(max(times), 2),
                    "count": len(times)
                }
                for transition, times in transitions.items()
            }
        }
    
    def get_clarification_stats(self, time_window_hours: int = 24) -> Dict[str, Any]:
        """Get clarification request statistics"""
        cutoff = datetime.now(datetime.UTC) - timedelta(hours=time_window_hours)
        recent_metrics = [m for m in self.clarification_metrics if m.timestamp >= cutoff]
        
        if not recent_metrics:
            return {"error": "No data available"}
        
        # Group by session to count attempts per session
        session_attempts = defaultdict(int)
        for m in recent_metrics:
            session_attempts[m.session_id] = max(session_attempts[m.session_id], m.attempt_number)
        
        resolved = sum(1 for m in recent_metrics if m.resolved)
        
        return {
            "total_clarifications": len(recent_metrics),
            "unique_sessions": len(session_attempts),
            "resolved_count": resolved,
            "resolution_rate": round(resolved / len(recent_metrics), 3),
            "avg_attempts_per_session": round(statistics.mean(session_attempts.values()), 2),
            "by_tier": {
                tier: len([m for m in recent_metrics if m.tier == tier])
                for tier in set(m.tier for m in recent_metrics)
            }
        }
    
    def get_escalation_stats(self, time_window_hours: int = 24) -> Dict[str, Any]:
        """Get human escalation statistics"""
        cutoff = datetime.now(datetime.UTC) - timedelta(hours=time_window_hours)
        recent_metrics = [m for m in self.escalation_metrics if m.timestamp >= cutoff]
        
        # Also get session count for rate calculation
        recent_sessions = [s for s in self.session_metrics if s.start_time >= cutoff]
        
        if not recent_metrics:
            return {
                "total_escalations": 0,
                "escalation_rate": 0.0,
                "total_sessions": len(recent_sessions)
            }
        
        # Group by reason
        by_reason = defaultdict(int)
        for m in recent_metrics:
            by_reason[m.reason] += 1
        
        # Group by tier
        by_tier = defaultdict(int)
        for m in recent_metrics:
            by_tier[m.tier] += 1
        
        total_sessions = len(recent_sessions) if recent_sessions else len(set(m.session_id for m in recent_metrics))
        escalation_rate = len(recent_metrics) / total_sessions if total_sessions > 0 else 0
        
        return {
            "total_escalations": len(recent_metrics),
            "total_sessions": total_sessions,
            "escalation_rate": round(escalation_rate, 3),
            "avg_clarification_attempts_before_escalation": round(
                statistics.mean([m.clarification_attempts for m in recent_metrics]), 2
            ),
            "by_reason": dict(by_reason),
            "by_tier": dict(by_tier)
        }
    
    def get_l3_success_rates(self, time_window_hours: int = 24) -> Dict[str, Any]:
        """Get L3 agent success rates"""
        cutoff = datetime.now(datetime.UTC) - timedelta(hours=time_window_hours)
        recent_metrics = [m for m in self.l3_metrics if m.timestamp >= cutoff]
        
        if not recent_metrics:
            return {"error": "No data available"}
        
        # Group by agent
        agent_stats = defaultdict(lambda: {"success": 0, "total": 0, "errors": defaultdict(int)})
        for m in recent_metrics:
            agent_stats[m.agent_name]["total"] += 1
            if m.success:
                agent_stats[m.agent_name]["success"] += 1
            elif m.error_code:
                agent_stats[m.agent_name]["errors"][m.error_code] += 1
        
        overall_success = sum(1 for m in recent_metrics if m.success)
        
        return {
            "total_executions": len(recent_metrics),
            "overall_success_rate": round(overall_success / len(recent_metrics), 3),
            "by_agent": {
                agent: {
                    "success_rate": round(stats["success"] / stats["total"], 3),
                    "success_count": stats["success"],
                    "total_count": stats["total"],
                    "top_errors": dict(sorted(stats["errors"].items(), key=lambda x: x[1], reverse=True)[:3])
                }
                for agent, stats in agent_stats.items()
            }
        }
    
    def get_session_summary(self, time_window_hours: int = 24) -> Dict[str, Any]:
        """Get overall session summary statistics"""
        cutoff = datetime.now(datetime.UTC) - timedelta(hours=time_window_hours)
        recent_sessions = [s for s in self.session_metrics if s.start_time >= cutoff]
        
        if not recent_sessions:
            return {"error": "No data available"}
        
        # Outcome distribution
        outcomes = defaultdict(int)
        for s in recent_sessions:
            outcomes[s.final_outcome] += 1
        
        # Caller type distribution
        caller_types = defaultdict(int)
        for s in recent_sessions:
            caller_types[s.caller_type] += 1
        
        avg_duration = statistics.mean([s.total_duration_ms for s in recent_sessions])
        avg_messages = statistics.mean([s.message_count for s in recent_sessions])
        
        return {
            "total_sessions": len(recent_sessions),
            "avg_duration_ms": round(avg_duration, 2),
            "avg_duration_seconds": round(avg_duration / 1000, 2),
            "avg_messages_per_session": round(avg_messages, 2),
            "outcomes": dict(outcomes),
            "caller_types": dict(caller_types),
            "success_rate": round(outcomes.get("success", 0) / len(recent_sessions), 3)
        }
    
    def get_full_dashboard(self, time_window_hours: int = 24) -> Dict[str, Any]:
        """Get comprehensive dashboard with all metrics"""
        return {
            "time_window_hours": time_window_hours,
            "generated_at": datetime.now(datetime.UTC).isoformat(),
            "l1_classification": self.get_l1_accuracy(time_window_hours),
            "l1_confidence": self.get_confidence_distribution("L1", time_window_hours),
            "l2_confidence": self.get_confidence_distribution("L2", time_window_hours),
            "routing_performance": self.get_avg_routing_time(time_window_hours),
            "clarifications": self.get_clarification_stats(time_window_hours),
            "escalations": self.get_escalation_stats(time_window_hours),
            "l3_success_rates": self.get_l3_success_rates(time_window_hours),
            "session_summary": self.get_session_summary(time_window_hours)
        }


# Global instance
_metrics_service_instance = None


def get_metrics_service() -> MetricsService:
    """Get or create the global MetricsService instance"""
    global _metrics_service_instance
    if _metrics_service_instance is None:
        _metrics_service_instance = MetricsService()
    return _metrics_service_instance