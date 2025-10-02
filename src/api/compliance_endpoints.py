# ==================== src/api/compliance_endpoints.py ====================
"""
FastAPI Endpoints for Compliance and Data Privacy

Provides REST API endpoints for:
- Consent management
- Data access requests
- Data deletion (Right to be Forgotten)
- Data export (Right to Data Portability)
- Audit log access
"""

from fastapi import APIRouter, HTTPException, Depends, Request, BackgroundTasks
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, UTC
import logging

from src.services.compliance_service import (
    ComplianceService,
    ConsentType,
    ConsentStatus,
    DataAccessRequestStatus
)
from src.services.retention_service import RetentionService, DataType


logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/compliance", tags=["compliance"])


# ==================== REQUEST/RESPONSE MODELS ====================

class ConsentRequest(BaseModel):
    """Request to record consent."""
    user_id: str
    consent_type: ConsentType
    granted: bool
    metadata: Optional[Dict[str, Any]] = None


class ConsentWithdrawRequest(BaseModel):
    """Request to withdraw consent."""
    user_id: str
    consent_type: ConsentType


class DataAccessRequestCreate(BaseModel):
    """Request to create data access request."""
    user_id: str
    email: EmailStr
    request_type: str = Field(
        default="access",
        description="'access' for data export or 'deletion' for right to be forgotten"
    )


class DataAccessRequestVerify(BaseModel):
    """Request to verify data access request."""
    request_id: str
    verification_token: str


class UserDataDeleteRequest(BaseModel):
    """Request to delete user data."""
    user_id: str
    confirmation: str = Field(
        description="Must be 'DELETE' to confirm"
    )
    reason: Optional[str] = "User request"


class ComplianceReportRequest(BaseModel):
    """Request for compliance report."""
    start_date: datetime
    end_date: datetime


class RetentionPolicyUpdate(BaseModel):
    """Request to update retention policy."""
    data_type: DataType
    retention_days: int
    archive_before_delete: bool = False
    archive_location: Optional[str] = None
    enabled: bool = True


# ==================== DEPENDENCY INJECTION ====================

def get_compliance_service() -> ComplianceService:
    """Get ComplianceService instance."""
    from src.services.database_service import get_mongo_client
    mongo_client = get_mongo_client()
    return ComplianceService(mongo_client)


def get_retention_service() -> RetentionService:
    """Get RetentionService instance."""
    from src.services.database_service import get_mongo_client
    mongo_client = get_mongo_client()
    return RetentionService(mongo_client)


def get_client_info(request: Request) -> Dict[str, Optional[str]]:
    """Extract client information from request."""
    return {
        "ip_address": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent")
    }


# ==================== CONSENT ENDPOINTS ====================

@router.post("/consent")
async def record_consent(
    consent_req: ConsentRequest,
    request: Request,
    compliance_service: ComplianceService = Depends(get_compliance_service)
):
    """
    Record user consent.
    
    **GDPR Article 7**: Conditions for consent
    """
    try:
        client_info = get_client_info(request)
        
        consent = compliance_service.record_consent(
            user_id=consent_req.user_id,
            consent_type=consent_req.consent_type,
            granted=consent_req.granted,
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"],
            metadata=consent_req.metadata
        )
        
        return {
            "success": True,
            "message": "Consent recorded successfully",
            "consent": consent.model_dump()
        }
    except Exception as e:
        logger.error(f"Error recording consent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/consent/withdraw")
async def withdraw_consent(
    withdraw_req: ConsentWithdrawRequest,
    request: Request,
    compliance_service: ComplianceService = Depends(get_compliance_service)
):
    """
    Withdraw previously granted consent.
    
    **GDPR Article 7(3)**: Right to withdraw consent
    """
    try:
        client_info = get_client_info(request)
        
        success = compliance_service.withdraw_consent(
            user_id=withdraw_req.user_id,
            consent_type=withdraw_req.consent_type,
            ip_address=client_info["ip_address"]
        )
        
        if success:
            return {
                "success": True,
                "message": "Consent withdrawn successfully"
            }
        else:
            raise HTTPException(
                status_code=404,
                detail="No granted consent found to withdraw"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error withdrawing consent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/consent/{user_id}")
async def get_user_consents(
    user_id: str,
    compliance_service: ComplianceService = Depends(get_compliance_service)
):
    """
    Get all consents for a user.
    """
    try:
        consents = compliance_service.get_user_consents(user_id)
        
        return {
            "success": True,
            "user_id": user_id,
            "consents": [c.model_dump() for c in consents]
        }
    except Exception as e:
        logger.error(f"Error retrieving consents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== DATA ACCESS REQUEST ENDPOINTS ====================

@router.post("/data-request")
async def create_data_request(
    request_data: DataAccessRequestCreate,
    compliance_service: ComplianceService = Depends(get_compliance_service)
):
    """
    Create a data access or deletion request.
    
    **GDPR Articles**:
    - Article 15: Right of access
    - Article 17: Right to erasure ('right to be forgotten')
    - Article 20: Right to data portability
    """
    try:
        if request_data.request_type not in ["access", "deletion"]:
            raise HTTPException(
                status_code=400,
                detail="request_type must be 'access' or 'deletion'"
            )
        
        data_request = compliance_service.create_data_access_request(
            user_id=request_data.user_id,
            email=request_data.email,
            request_type=request_data.request_type
        )
        
        return {
            "success": True,
            "message": "Data request created. Please check your email to verify.",
            "request_id": data_request.request_id,
            "status": data_request.status.value
        }
    except Exception as e:
        logger.error(f"Error creating data request: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/data-request/verify")
async def verify_data_request(
    verify_req: DataAccessRequestVerify,
    compliance_service: ComplianceService = Depends(get_compliance_service)
):
    """
    Verify a data access request using the emailed token.
    """
    try:
        success = compliance_service.verify_data_request(
            request_id=verify_req.request_id,
            verification_token=verify_req.verification_token
        )
        
        if success:
            return {
                "success": True,
                "message": "Request verified. Processing will begin shortly."
            }
        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid request ID or verification token"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying data request: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data-request/{request_id}")
async def get_data_request_status(
    request_id: str,
    compliance_service: ComplianceService = Depends(get_compliance_service)
):
    """
    Get the status of a data access request.
    """
    try:
        from src.services.compliance_service import DataAccessRequest
        
        request_doc = compliance_service.data_requests_collection.find_one({
            "request_id": request_id
        })
        
        if not request_doc:
            raise HTTPException(status_code=404, detail="Request not found")
        
        data_request = DataAccessRequest(**request_doc)
        
        return {
            "success": True,
            "request": {
                "request_id": data_request.request_id,
                "status": data_request.status.value,
                "request_type": data_request.request_type,
                "requested_at": data_request.requested_at.isoformat(),
                "completed_at": data_request.completed_at.isoformat() if data_request.completed_at else None,
                "data_export_url": data_request.data_export_url,
                "verified": data_request.verified
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving request status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== DATA EXPORT/DELETION ENDPOINTS ====================

@router.get("/export/{user_id}")
async def export_user_data(
    user_id: str,
    compliance_service: ComplianceService = Depends(get_compliance_service)
):
    """
    Export all data for a user.
    
    **GDPR Article 20**: Right to data portability
    
    Note: This endpoint should be protected with proper authentication.
    In production, require user authentication or verification token.
    """
    try:
        user_data = compliance_service.export_user_data(user_id)
        
        return {
            "success": True,
            "message": "User data exported successfully",
            "data": user_data
        }
    except Exception as e:
        logger.error(f"Error exporting user data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/delete-user-data")
async def delete_user_data(
    delete_req: UserDataDeleteRequest,
    background_tasks: BackgroundTasks,
    compliance_service: ComplianceService = Depends(get_compliance_service)
):
    """
    Delete all data for a user (Right to be Forgotten).
    
    **GDPR Article 17**: Right to erasure
    
    CRITICAL: This permanently deletes all user data. Requires confirmation.
    In production, require strong authentication and additional verification.
    """
    try:
        # Require explicit confirmation
        if delete_req.confirmation != "DELETE":
            raise HTTPException(
                status_code=400,
                detail="Confirmation must be 'DELETE' to proceed"
            )
        
        # Delete in background to avoid timeout
        background_tasks.add_task(
            compliance_service.delete_user_data,
            delete_req.user_id,
            delete_req.reason
        )
        
        return {
            "success": True,
            "message": f"User data deletion initiated for user {delete_req.user_id}",
            "warning": "This action cannot be undone"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting user data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== AUDIT LOG ENDPOINTS ====================

@router.get("/audit-logs")
async def get_audit_logs(
    user_id: Optional[str] = None,
    event_type: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 100,
    compliance_service: ComplianceService = Depends(get_compliance_service)
):
    """
    Retrieve audit logs with optional filters.
    
    **GDPR Article 30**: Records of processing activities
    """
    try:
        logs = compliance_service.get_audit_logs(
            user_id=user_id,
            event_type=event_type,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )
        
        return {
            "success": True,
            "count": len(logs),
            "logs": [log.model_dump() for log in logs]
        }
    except Exception as e:
        logger.error(f"Error retrieving audit logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== COMPLIANCE REPORTING ====================

@router.post("/report")
async def generate_compliance_report(
    report_req: ComplianceReportRequest,
    compliance_service: ComplianceService = Depends(get_compliance_service)
):
    """
    Generate compliance report for a date range.
    
    Useful for demonstrating GDPR/CCPA compliance to regulators.
    """
    try:
        report = compliance_service.generate_compliance_report(
            start_date=report_req.start_date,
            end_date=report_req.end_date
        )
        
        return {
            "success": True,
            "report": report
        }
    except Exception as e:
        logger.error(f"Error generating compliance report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== RETENTION POLICY ENDPOINTS ====================

@router.get("/retention/stats")
async def get_retention_stats(
    retention_service: RetentionService = Depends(get_retention_service)
):
    """
    Get statistics about data retention.
    
    Shows how much data is eligible for deletion based on retention policies.
    """
    try:
        stats = retention_service.get_retention_stats()
        
        return {
            "success": True,
            "stats": stats
        }
    except Exception as e:
        logger.error(f"Error retrieving retention stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/retention/policies")
async def get_retention_policies(
    retention_service: RetentionService = Depends(get_retention_service)
):
    """
    Get all retention policies.
    """
    try:
        policies = {}
        for data_type in DataType:
            policy = retention_service.get_retention_policy(data_type)
            policies[data_type.value] = policy.model_dump()
        
        return {
            "success": True,
            "policies": policies
        }
    except Exception as e:
        logger.error(f"Error retrieving retention policies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/retention/policy")
async def update_retention_policy(
    policy_update: RetentionPolicyUpdate,
    retention_service: RetentionService = Depends(get_retention_service)
):
    """
    Update a retention policy.
    
    Changes how long data is retained before automatic deletion.
    """
    try:
        from src.services.retention_service import RetentionPolicy
        
        policy = RetentionPolicy(
            data_type=policy_update.data_type,
            retention_days=policy_update.retention_days,
            archive_before_delete=policy_update.archive_before_delete,
            archive_location=policy_update.archive_location,
            enabled=policy_update.enabled
        )
        
        success = retention_service.update_retention_policy(policy)
        
        if success:
            return {
                "success": True,
                "message": f"Retention policy updated for {policy_update.data_type.value}",
                "policy": policy.model_dump()
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to update policy")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating retention policy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/retention/cleanup")
async def run_retention_cleanup(
    dry_run: bool = True,
    background_tasks: BackgroundTasks = None,
    retention_service: RetentionService = Depends(get_retention_service)
):
    """
    Manually trigger retention cleanup.
    
    **Parameters**:
    - dry_run: If True, only count records without deleting (default: True)
    
    This should typically be run as a scheduled job, but can be triggered manually.
    """
    try:
        if dry_run:
            # Run synchronously for dry run
            results = retention_service.purge_all_expired_data(dry_run=True)
            
            return {
                "success": True,
                "dry_run": True,
                "message": "Dry run completed. No data was deleted.",
                "results": {
                    data_type.value: {
                        "would_delete": result.deleted_count,
                        "would_archive": result.archived_count
                    }
                    for data_type, result in results.items()
                }
            }
        else:
            # Run in background for actual deletion
            if background_tasks:
                background_tasks.add_task(
                    retention_service.purge_all_expired_data,
                    dry_run=False
                )
            
            return {
                "success": True,
                "dry_run": False,
                "message": "Retention cleanup initiated in background"
            }
    except Exception as e:
        logger.error(f"Error running retention cleanup: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== HEALTH CHECK ====================

@router.get("/health")
async def compliance_health_check():
    """
    Health check endpoint for compliance services.
    """
    return {
        "status": "healthy",
        "service": "compliance",
        "timestamp": datetime.now(UTC).isoformat()
    }