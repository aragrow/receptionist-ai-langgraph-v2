# ==================== src/services/logging_service.py ====================
"""
Structured Logging Service for AI Receptionist
Provides JSON-formatted logs with full context for debugging and monitoring
"""

import json
import logging
import sys
from datetime import datetime
from typing import Any, Dict, Optional
from pathlib import Path
from enum import Enum


class LogLevel(Enum):
    """Log severity levels"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogCategory(Enum):
    """Categories for log organization"""
    ROUTING = "routing"
    CLASSIFICATION = "classification"
    SLOT_EXTRACTION = "slot_extraction"
    CLARIFICATION = "clarification"
    ESCALATION = "escalation"
    ACTION_EXECUTION = "action_execution"
    SESSION = "session"
    SYSTEM = "system"
    ERROR = "error"


class StructuredLogger:
    """
    Structured logger that outputs JSON-formatted logs with full context
    """
    
    def __init__(
        self,
        name: str = "ai_receptionist",
        log_file: Optional[str] = None,
        console_output: bool = True,
        min_level: LogLevel = LogLevel.INFO
    ):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, min_level.value))
        self.logger.handlers.clear()  # Remove existing handlers
        
        # JSON formatter
        formatter = logging.Formatter(
            '%(message)s'  # We'll format as JSON ourselves
        )
        
        # Console handler
        if console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
        
        # File handler
        if log_file:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
    
    def _format_log(
        self,
        level: LogLevel,
        category: LogCategory,
        message: str,
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        error: Optional[Exception] = None
    ) -> str:
        """Format log entry as JSON"""
        log_entry = {
            "timestamp": datetime.now(datetime.UTC).isoformat(),
            "level": level.value,
            "category": category.value,
            "message": message,
        }
        
        if session_id:
            log_entry["session_id"] = session_id
        
        if context:
            log_entry["context"] = context
        
        if error:
            log_entry["error"] = {
                "type": type(error).__name__,
                "message": str(error),
                "traceback": self._get_traceback(error)
            }
        
        return json.dumps(log_entry, default=str)
    
    def _get_traceback(self, error: Exception) -> str:
        """Extract traceback from exception"""
        import traceback
        return ''.join(traceback.format_exception(type(error), error, error.__traceback__))
    
    def debug(
        self,
        category: LogCategory,
        message: str,
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log debug message"""
        log_msg = self._format_log(LogLevel.DEBUG, category, message, session_id, context)
        self.logger.debug(log_msg)
    
    def info(
        self,
        category: LogCategory,
        message: str,
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log info message"""
        log_msg = self._format_log(LogLevel.INFO, category, message, session_id, context)
        self.logger.info(log_msg)
    
    def warning(
        self,
        category: LogCategory,
        message: str,
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log warning message"""
        log_msg = self._format_log(LogLevel.WARNING, category, message, session_id, context)
        self.logger.warning(log_msg)
    
    def error(
        self,
        category: LogCategory,
        message: str,
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        error: Optional[Exception] = None
    ) -> None:
        """Log error message"""
        log_msg = self._format_log(LogLevel.ERROR, category, message, session_id, context, error)
        self.logger.error(log_msg)
    
    def critical(
        self,
        category: LogCategory,
        message: str,
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        error: Optional[Exception] = None
    ) -> None:
        """Log critical message"""
        log_msg = self._format_log(LogLevel.CRITICAL, category, message, session_id, context, error)
        self.logger.critical(log_msg)


class LoggingService:
    """
    Service for logging AI Receptionist workflow events
    Provides convenience methods for common logging scenarios
    """
    
    def __init__(self, logger: Optional[StructuredLogger] = None):
        self.logger = logger or StructuredLogger()
    
    # ========== ROUTING LOGS ==========
    
    def log_routing_decision(
        self,
        session_id: str,
        from_tier: str,
        to_tier: str,
        confidence: float,
        reasoning: str,
        routing_time_ms: float
    ) -> None:
        """Log a routing decision"""
        self.logger.info(
            category=LogCategory.ROUTING,
            message=f"Routing {from_tier} → {to_tier}",
            session_id=session_id,
            context={
                "from_tier": from_tier,
                "to_tier": to_tier,
                "confidence": confidence,
                "reasoning": reasoning,
                "routing_time_ms": routing_time_ms
            }
        )
    
    def log_routing_error(
        self,
        session_id: str,
        from_tier: str,
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log a routing error"""
        self.logger.error(
            category=LogCategory.ROUTING,
            message=f"Routing failed from {from_tier}",
            session_id=session_id,
            context=context,
            error=error
        )
    
    # ========== CLASSIFICATION LOGS ==========
    
    def log_l1_classification(
        self,
        session_id: str,
        intent: str,
        confidence: float,
        caller_type: str,
        processing_time_ms: float,
        raw_output: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log L1 classification result"""
        self.logger.info(
            category=LogCategory.CLASSIFICATION,
            message=f"L1 classified intent: {intent}",
            session_id=session_id,
            context={
                "tier": "L1",
                "intent": intent,
                "confidence": confidence,
                "caller_type": caller_type,
                "processing_time_ms": processing_time_ms,
                "raw_output": raw_output
            }
        )
    
    def log_l2_refinement(
        self,
        session_id: str,
        refined_intent: str,
        confidence: float,
        slots_extracted: Dict[str, Any],
        required_slots: list,
        processing_time_ms: float
    ) -> None:
        """Log L2 intent refinement result"""
        self.logger.info(
            category=LogCategory.CLASSIFICATION,
            message=f"L2 refined intent: {refined_intent}",
            session_id=session_id,
            context={
                "tier": "L2",
                "refined_intent": refined_intent,
                "confidence": confidence,
                "slots_extracted": slots_extracted,
                "required_slots": required_slots,
                "slots_filled": len(slots_extracted),
                "slots_required": len(required_slots),
                "processing_time_ms": processing_time_ms
            }
        )
    
    # ========== SLOT EXTRACTION LOGS ==========
    
    def log_slot_extraction(
        self,
        session_id: str,
        tier: str,
        extracted_entities: Dict[str, Any],
        confidence_scores: Optional[Dict[str, float]] = None
    ) -> None:
        """Log slot/entity extraction"""
        self.logger.info(
            category=LogCategory.SLOT_EXTRACTION,
            message=f"Extracted {len(extracted_entities)} entities",
            session_id=session_id,
            context={
                "tier": tier,
                "entities": extracted_entities,
                "confidence_scores": confidence_scores
            }
        )
    
    def log_slot_validation_failure(
        self,
        session_id: str,
        tier: str,
        slot_name: str,
        value: Any,
        reason: str
    ) -> None:
        """Log slot validation failure"""
        self.logger.warning(
            category=LogCategory.SLOT_EXTRACTION,
            message=f"Slot validation failed: {slot_name}",
            session_id=session_id,
            context={
                "tier": tier,
                "slot_name": slot_name,
                "value": str(value),
                "failure_reason": reason
            }
        )
    
    # ========== CLARIFICATION LOGS ==========
    
    def log_clarification_request(
        self,
        session_id: str,
        tier: str,
        attempt_number: int,
        missing_slots: list,
        question: str
    ) -> None:
        """Log clarification request"""
        self.logger.info(
            category=LogCategory.CLARIFICATION,
            message=f"Clarification requested (attempt {attempt_number})",
            session_id=session_id,
            context={
                "tier": tier,
                "attempt_number": attempt_number,
                "missing_slots": missing_slots,
                "question": question
            }
        )
    
    def log_clarification_response(
        self,
        session_id: str,
        tier: str,
        attempt_number: int,
        resolved: bool,
        slots_filled: Dict[str, Any]
    ) -> None:
        """Log clarification response"""
        self.logger.info(
            category=LogCategory.CLARIFICATION,
            message=f"Clarification {'resolved' if resolved else 'incomplete'}",
            session_id=session_id,
            context={
                "tier": tier,
                "attempt_number": attempt_number,
                "resolved": resolved,
                "slots_filled": slots_filled
            }
        )
    
    def log_max_clarifications_reached(
        self,
        session_id: str,
        tier: str,
        max_attempts: int,
        still_missing_slots: list
    ) -> None:
        """Log when max clarification attempts reached"""
        self.logger.warning(
            category=LogCategory.CLARIFICATION,
            message=f"Max clarification attempts ({max_attempts}) reached",
            session_id=session_id,
            context={
                "tier": tier,
                "max_attempts": max_attempts,
                "still_missing_slots": still_missing_slots
            }
        )
    
    # ========== ESCALATION LOGS ==========
    
    def log_human_escalation(
        self,
        session_id: str,
        tier: str,
        reason: str,
        confidence: float,
        clarification_attempts: int,
        ticket_id: str,
        context_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log human escalation"""
        self.logger.warning(
            category=LogCategory.ESCALATION,
            message=f"Escalating to human: {reason}",
            session_id=session_id,
            context={
                "tier": tier,
                "reason": reason,
                "confidence": confidence,
                "clarification_attempts": clarification_attempts,
                "ticket_id": ticket_id,
                "additional_context": context_data
            }
        )
    
    # ========== ACTION EXECUTION LOGS ==========
    
    def log_l3_action_start(
        self,
        session_id: str,
        agent_name: str,
        action: str,
        parameters: Dict[str, Any]
    ) -> None:
        """Log L3 action start"""
        self.logger.info(
            category=LogCategory.ACTION_EXECUTION,
            message=f"L3 {agent_name} executing: {action}",
            session_id=session_id,
            context={
                "agent": agent_name,
                "action": action,
                "parameters": parameters
            }
        )
    
    def log_l3_action_success(
        self,
        session_id: str,
        agent_name: str,
        action: str,
        result: Dict[str, Any],
        processing_time_ms: float
    ) -> None:
        """Log L3 action success"""
        self.logger.info(
            category=LogCategory.ACTION_EXECUTION,
            message=f"L3 {agent_name} action succeeded: {action}",
            session_id=session_id,
            context={
                "agent": agent_name,
                "action": action,
                "result": result,
                "processing_time_ms": processing_time_ms
            }
        )
    
    def log_l3_action_failure(
        self,
        session_id: str,
        agent_name: str,
        action: str,
        error_code: str,
        error: Exception,
        processing_time_ms: float
    ) -> None:
        """Log L3 action failure"""
        self.logger.error(
            category=LogCategory.ACTION_EXECUTION,
            message=f"L3 {agent_name} action failed: {action}",
            session_id=session_id,
            context={
                "agent": agent_name,
                "action": action,
                "error_code": error_code,
                "processing_time_ms": processing_time_ms
            },
            error=error
        )
    
    # ========== SESSION LOGS ==========
    
    def log_session_start(
        self,
        session_id: str,
        caller_type: str,
        initial_message: str
    ) -> None:
        """Log session start"""
        self.logger.info(
            category=LogCategory.SESSION,
            message="Session started",
            session_id=session_id,
            context={
                "caller_type": caller_type,
                "initial_message": initial_message
            }
        )
    
    def log_session_end(
        self,
        session_id: str,
        final_outcome: str,
        total_duration_ms: float,
        message_count: int,
        tiers_traversed: list
    ) -> None:
        """Log session end"""
        self.logger.info(
            category=LogCategory.SESSION,
            message=f"Session ended: {final_outcome}",
            session_id=session_id,
            context={
                "final_outcome": final_outcome,
                "total_duration_ms": total_duration_ms,
                "message_count": message_count,
                "tiers_traversed": tiers_traversed
            }
        )
    
    def log_session_error(
        self,
        session_id: str,
        error: Exception,
        context_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log session error"""
        self.logger.error(
            category=LogCategory.SESSION,
            message="Session encountered error",
            session_id=session_id,
            context=context_data,
            error=error
        )
    
    # ========== SYSTEM LOGS ==========
    
    def log_system_event(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log system-level event"""
        self.logger.info(
            category=LogCategory.SYSTEM,
            message=message,
            context=context
        )
    
    def log_system_error(
        self,
        message: str,
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log system-level error"""
        self.logger.error(
            category=LogCategory.SYSTEM,
            message=message,
            context=context,
            error=error
        )
    
    # ========== CONFIDENCE THRESHOLD LOGS ==========
    
    def log_low_confidence_detection(
        self,
        session_id: str,
        tier: str,
        confidence: float,
        threshold: float,
        action_taken: str
    ) -> None:
        """Log when low confidence is detected"""
        self.logger.warning(
            category=LogCategory.CLASSIFICATION,
            message=f"Low confidence detected at {tier}",
            session_id=session_id,
            context={
                "tier": tier,
                "confidence": confidence,
                "threshold": threshold,
                "action_taken": action_taken
            }
        )


# Global instance
_logging_service_instance = None


def get_logging_service(
    log_file: Optional[str] = "logs/ai_receptionist.log",
    console_output: bool = True,
    min_level: LogLevel = LogLevel.INFO
) -> LoggingService:
    """Get or create the global LoggingService instance"""
    global _logging_service_instance
    if _logging_service_instance is None:
        logger = StructuredLogger(
            name="ai_receptionist",
            log_file=log_file,
            console_output=console_output,
            min_level=min_level
        )
        _logging_service_instance = LoggingService(logger)
    return _logging_service_instance