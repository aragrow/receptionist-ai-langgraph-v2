# ==================== analytics/analytics_endpoint.py ====================
"""
Analytics API Endpoints for AI Receptionist
Provides REST endpoints for viewing metrics and analytics
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

from src.services.metrics_service import get_metrics_service
from src.services.logging_service import get_logging_service

# Create router
router = APIRouter(prefix="/analytics", tags=["analytics"])

# Initialize services
metrics_service = get_metrics_service()
logging_service = get_logging_service()


# ========== RESPONSE MODELS ==========

class MetricsResponse(BaseModel):
    """Generic metrics response"""
    success: bool
    data: Dict[str, Any]
    generated_at: str


class ErrorResponse(BaseModel):
    """Error response"""
    success: bool = False
    error: str
    details: Optional[str] = None


# ========== ENDPOINTS ==========

@router.get("/dashboard", response_model=MetricsResponse)
async def get_dashboard(
    time_window_hours: int = Query(
        default=24,
        ge=1,
        le=168,
        description="Time window in hours (1-168, default 24)"
    )
) -> MetricsResponse:
    """
    Get comprehensive dashboard with all metrics
    
    Returns L1/L2/L3 performance, routing stats, clarifications, escalations, and session summary
    """
    try:
        dashboard_data = metrics_service.get_full_dashboard(time_window_hours)
        
        logging_service.log_system_event(
            "Dashboard accessed",
            context={"time_window_hours": time_window_hours}
        )
        
        return MetricsResponse(
            success=True,
            data=dashboard_data,
            generated_at=datetime.now(datetime.UTC).isoformat()
        )
    except Exception as e:
        logging_service.log_system_error(
            "Dashboard generation failed",
            error=e
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/l1/accuracy", response_model=MetricsResponse)
async def get_l1_accuracy(
    time_window_hours: int = Query(
        default=24,
        ge=1,
        le=168,
        description="Time window in hours"
    )
) -> MetricsResponse:
    """
    Get L1 intent classification accuracy metrics
    
    Includes overall accuracy, per-intent breakdown, and confidence scores
    """
    try:
        accuracy_data = metrics_service.get_l1_accuracy(time_window_hours)
        
        return MetricsResponse(
            success=True,
            data=accuracy_data,
            generated_at=datetime.now(datetime.UTC).isoformat()
        )
    except Exception as e:
        logging_service.log_system_error(
            "L1 accuracy retrieval failed",
            error=e
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/confidence/{tier}", response_model=MetricsResponse)
async def get_confidence_distribution(
    tier: str = Query(
        ...,
        regex="^(L1|L2)$",
        description="Tier to analyze (L1 or L2)"
    ),
    time_window_hours: int = Query(
        default=24,
        ge=1,
        le=168,
        description="Time window in hours"
    )
) -> MetricsResponse:
    """
    Get confidence score distribution for specified tier
    
    Returns average, median, min, max, and distribution across high/medium/low buckets
    """
    try:
        confidence_data = metrics_service.get_confidence_distribution(
            tier=tier,
            time_window_hours=time_window_hours
        )
        
        return MetricsResponse(
            success=True,
            data=confidence_data,
            generated_at=datetime.now(datetime.UTC).isoformat()
        )
    except Exception as e:
        logging_service.log_system_error(
            f"Confidence distribution retrieval failed for {tier}",
            error=e
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/routing/performance", response_model=MetricsResponse)
async def get_routing_performance(
    time_window_hours: int = Query(
        default=24,
        ge=1,
        le=168,
        description="Time window in hours"
    )
) -> MetricsResponse:
    """
    Get routing performance metrics
    
    Returns average routing times for L1→L2, L2→L3 transitions
    """
    try:
        routing_data = metrics_service.get_avg_routing_time(time_window_hours)
        
        return MetricsResponse(
            success=True,
            data=routing_data,
            generated_at=datetime.now(datetime.UTC).isoformat()
        )
    except Exception as e:
        logging_service.log_system_error(
            "Routing performance retrieval failed",
            error=e
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/clarifications", response_model=MetricsResponse)
async def get_clarification_stats(
    time_window_hours: int = Query(
        default=24,
        ge=1,
        le=168,
        description="Time window in hours"
    )
) -> MetricsResponse:
    """
    Get clarification request statistics
    
    Returns total clarifications, resolution rate, and average attempts per session
    """
    try:
        clarification_data = metrics_service.get_clarification_stats(time_window_hours)
        
        return MetricsResponse(
            success=True,
            data=clarification_data,
            generated_at=datetime.now(datetime.UTC).isoformat()
        )
    except Exception as e:
        logging_service.log_system_error(
            "Clarification stats retrieval failed",
            error=e
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/escalations", response_model=MetricsResponse)
async def get_escalation_stats(
    time_window_hours: int = Query(
        default=24,
        ge=1,
        le=168,
        description="Time window in hours"
    )
) -> MetricsResponse:
    """
    Get human escalation statistics
    
    Returns escalation rate, reasons, and tier breakdown
    """
    try:
        escalation_data = metrics_service.get_escalation_stats(time_window_hours)
        
        return MetricsResponse(
            success=True,
            data=escalation_data,
            generated_at=datetime.now(datetime.UTC).isoformat()
        )
    except Exception as e:
        logging_service.log_system_error(
            "Escalation stats retrieval failed",
            error=e
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/l3/success-rates", response_model=MetricsResponse)
async def get_l3_success_rates(
    time_window_hours: int = Query(
        default=24,
        ge=1,
        le=168,
        description="Time window in hours"
    )
) -> MetricsResponse:
    """
    Get L3 agent success rates
    
    Returns per-agent success rates and common error codes
    """
    try:
        l3_data = metrics_service.get_l3_success_rates(time_window_hours)
        
        return MetricsResponse(
            success=True,
            data=l3_data,
            generated_at=datetime.now(datetime.UTC).isoformat()
        )
    except Exception as e:
        logging_service.log_system_error(
            "L3 success rates retrieval failed",
            error=e
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/summary", response_model=MetricsResponse)
async def get_session_summary(
    time_window_hours: int = Query(
        default=24,
        ge=1,
        le=168,
        description="Time window in hours"
    )
) -> MetricsResponse:
    """
    Get session summary statistics
    
    Returns total sessions, average duration, outcomes, and caller type distribution
    """
    try:
        session_data = metrics_service.get_session_summary(time_window_hours)
        
        return MetricsResponse(
            success=True,
            data=session_data,
            generated_at=datetime.now(datetime.UTC).isoformat()
        )
    except Exception as e:
        logging_service.log_system_error(
            "Session summary retrieval failed",
            error=e
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint for monitoring
    """
    try:
        # Check if services are responsive
        _ = metrics_service.get_session_summary(1)
        
        return {
            "status": "healthy",
            "timestamp": datetime.now(datetime.UTC).isoformat(),
            "services": {
                "metrics": "operational",
                "logging": "operational"
            }
        }
    except Exception as e:
        logging_service.log_system_error(
            "Health check failed",
            error=e
        )
        return {
            "status": "degraded",
            "timestamp": datetime.now(datetime.UTC).isoformat(),
            "error": str(e)
        }


# ========== ADVANCED ENDPOINTS ==========

@router.get("/sessions/{session_id}", response_model=MetricsResponse)
async def get_session_details(
    session_id: str
) -> MetricsResponse:
    """
    Get detailed information about a specific session
    
    Returns full session timeline, routing decisions, and outcomes
    """
    try:
        # Find session in metrics
        session = next(
            (s for s in metrics_service.session_metrics if s.session_id == session_id),
            None
        )
        
        if not session:
            raise HTTPException(
                status_code=404,
                detail=f"Session {session_id} not found"
            )
        
        # Gather all related metrics
        l1_metrics = [m for m in metrics_service.l1_metrics if m.session_id == session_id]
        l2_metrics = [m for m in metrics_service.l2_metrics if m.session_id == session_id]
        l3_metrics = [m for m in metrics_service.l3_metrics if m.session_id == session_id]
        routing_metrics = [m for m in metrics_service.routing_metrics if m.session_id == session_id]
        clarification_metrics = [m for m in metrics_service.clarification_metrics if m.session_id == session_id]
        escalation_metrics = [m for m in metrics_service.escalation_metrics if m.session_id == session_id]
        
        # Convert dataclasses to dicts
        from dataclasses import asdict
        
        session_data = {
            "session": asdict(session),
            "l1_classifications": [asdict(m) for m in l1_metrics],
            "l2_refinements": [asdict(m) for m in l2_metrics],
            "l3_executions": [asdict(m) for m in l3_metrics],
            "routing_decisions": [asdict(m) for m in routing_metrics],
            "clarifications": [asdict(m) for m in clarification_metrics],
            "escalations": [asdict(m) for m in escalation_metrics]
        }
        
        return MetricsResponse(
            success=True,
            data=session_data,
            generated_at=datetime.now(datetime.UTC).isoformat()
        )
    except HTTPException:
        raise
    except Exception as e:
        logging_service.log_system_error(
            f"Session detail retrieval failed for {session_id}",
            error=e
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export/csv")
async def export_metrics_csv(
    metric_type: str = Query(
        ...,
        regex="^(l1|l2|l3|routing|clarifications|escalations|sessions)$",
        description="Type of metrics to export"
    ),
    time_window_hours: int = Query(
        default=24,
        ge=1,
        le=720,
        description="Time window in hours (up to 30 days)"
    )
) -> Dict[str, Any]:
    """
    Export metrics as CSV data
    
    Returns CSV-formatted data for specified metric type
    """
    try:
        from datetime import timedelta
        import csv
        import io
        
        cutoff = datetime.now(datetime.UTC) - timedelta(hours=time_window_hours)
        
        # Select appropriate metrics
        if metric_type == "l1":
            metrics = [m for m in metrics_service.l1_metrics if m.timestamp >= cutoff]
        elif metric_type == "l2":
            metrics = [m for m in metrics_service.l2_metrics if m.timestamp >= cutoff]
        elif metric_type == "l3":
            metrics = [m for m in metrics_service.l3_metrics if m.timestamp >= cutoff]
        elif metric_type == "routing":
            metrics = [m for m in metrics_service.routing_metrics if m.timestamp >= cutoff]
        elif metric_type == "clarifications":
            metrics = [m for m in metrics_service.clarification_metrics if m.timestamp >= cutoff]
        elif metric_type == "escalations":
            metrics = [m for m in metrics_service.escalation_metrics if m.timestamp >= cutoff]
        elif metric_type == "sessions":
            metrics = [m for m in metrics_service.session_metrics if m.start_time >= cutoff]
        else:
            raise HTTPException(status_code=400, detail="Invalid metric type")
        
        if not metrics:
            return {
                "success": True,
                "data": "",
                "row_count": 0,
                "message": "No data available for specified time window"
            }
        
        # Convert to CSV
        from dataclasses import asdict, fields
        
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=[f.name for f in fields(metrics[0])])
        writer.writeheader()
        
        for metric in metrics:
            writer.writerow(asdict(metric))
        
        csv_data = output.getvalue()
        
        return {
            "success": True,
            "data": csv_data,
            "row_count": len(metrics),
            "metric_type": metric_type,
            "time_window_hours": time_window_hours
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logging_service.log_system_error(
            f"CSV export failed for {metric_type}",
            error=e
        )
        raise HTTPException(status_code=500, detail=str(e))