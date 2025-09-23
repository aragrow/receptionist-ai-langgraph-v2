# ==================== src/services/context_service.py ====================
"""Context service for building caller context."""

from typing import Dict, Any, List
from bson import ObjectId

from src.models.workflow_models import WorkflowState, CallerType
from src.models.database_models import Client, Vendor
from .database_service import DatabaseService


class ContextService:
    """Service for building caller context."""
    
    def __init__(self, db_service: DatabaseService):
        self.db_service = db_service
    
    async def build_client_context(self, client: Client) -> Dict[str, Any]:
        """Build comprehensive context for a client."""
        context = {
            "client": client.dict(),
            "properties": [],
            "jobs": [],
            "visits": [],
            "vendors": []
        }
        
        # Get client properties
        properties = await self.db_service.get_client_properties(client.id)
        context["properties"] = [prop.dict() for prop in properties]
        
        # Get jobs for all properties
        all_jobs = []
        vendor_ids = set()
        
        for prop in properties:
            jobs = await self.db_service.get_property_jobs(prop.id)
            all_jobs.extend(jobs)
            vendor_ids.update(job.vendor_id for job in jobs)
        
        context["jobs"] = [job.dict() for job in all_jobs]
        
        # Get visits for all jobs
        all_visits = []
        for job in all_jobs:
            visits = await self.db_service.get_job_visits(job.id)
            all_visits.extend(visits)
        
        context["visits"] = [visit.dict() for visit in all_visits]
        
        # Get vendor information
        vendors = []
        for vendor_id in vendor_ids:
            vendor_doc = await self.db_service.db.vendors.find_one({"_id": vendor_id})
            if vendor_doc:
                vendors.append(Vendor(**vendor_doc).dict())
        
        context["vendors"] = vendors
        
        return context
    
    async def build_vendor_context(self, vendor: Vendor) -> Dict[str, Any]:
        """Build comprehensive context for a vendor."""
        context = {
            "vendor": vendor.dict(),
            "jobs": [],
            "visits": [],
            "clients": []
        }
        
        # Get vendor jobs
        jobs = await self.db_service.get_vendor_jobs(vendor.id)
        context["jobs"] = [job.dict() for job in jobs]
        
        # Get visits and clients for vendor jobs
        all_visits = []
        client_ids = set()
        
        for job in jobs:
            visits = await self.db_service.get_job_visits(job.id)
            all_visits.extend(visits)
            
            # Get property to find client
            prop_doc = await self.db_service.db.properties.find_one({"_id": job.property_id})
            if prop_doc:
                client_ids.add(prop_doc["client_id"])
        
        context["visits"] = [visit.dict() for visit in all_visits]
        
        # Get client information
        clients = []
        for client_id in client_ids:
            client_doc = await self.db_service.db.clients.find_one({"_id": client_id})
            if client_doc:
                clients.append(Client(**client_doc).dict())
        
        context["clients"] = clients
        
        return context
    
    async def build_lead_context(self) -> Dict[str, Any]:
        """Build limited context for leads."""
        return {
            "general_info": "Welcome to our service. How can we help you today?",
            "services": ["Property Management", "Maintenance", "Repairs"]
        }