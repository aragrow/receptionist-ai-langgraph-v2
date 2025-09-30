# ==================== src/agents/client_receptionist_l2.py ====================
"""
Client Receptionist L2 - Intent refiner for existing clients.
Handles existing customers with accounts and service history.
"""

import logging
from typing import Dict, List

from src.agents.receptionist_l2_base import ReceptionistL2Base
from src.services.database_service import DatabaseService

logger = logging.getLogger(__name__)


class ClientReceptionistL2(ReceptionistL2Base):
    """
    Level 2 Receptionist for Existing Clients.
    
    Specializes in:
    - Rescheduling existing appointments
    - Service status checks
    - Complaints and quality issues
    - Billing inquiries for existing accounts
    - Profile updates
    
    Advantages:
    - Has access to client profile data
    - Can pre-fill known information
    - Understands service history context
    """
    
    def __init__(self, db_service: DatabaseService):
        """
        Initialize Client Receptionist L2.
        
        Args:
            db_service: Database service for data access
        """
        super().__init__(
            agent_name="client_receptionist_l2",
            caller_type="client",
            db_service=db_service
        )
        
        logger.info("ClientReceptionistL2 initialized")
    
    def get_intent_mappings(self) -> Dict[str, List[str]]:
        """
        Get mapping from L1 broad intents to specific client L2 intents.
        
        Returns:
            Dictionary mapping L1 intent to list of possible L2 intents
        """
        return {
            # Scheduling intents
            "scheduling": [
                "reschedule_service",      # Most common for existing clients
                "cancel_service",
                "check_service_schedule",
                "modify_recurring_service",
                "book_additional_service"  # Less common but possible
            ],
            
            # Support intents
            "support": [
                "service_complaint",       # Quality issues
                "check_service_status",    # Where is my cleaner?
                "quality_issue",           # Not satisfied with last service
                "report_problem",          # Something went wrong
                "technical_issue",         # App/portal issues
                "request_callback"
            ],
            
            # Billing intents
            "billing": [
                "check_invoice",           # View invoice
                "payment_inquiry",         # Payment questions
                "billing_dispute",         # Charge dispute
                "update_payment_method",   # Change credit card
                "request_receipt",
                "explain_charges"
            ],
            
            # Sales intents (less common for existing clients)
            "sales": [
                "request_quote",           # Additional services
                "upgrade_service",         # Move to different tier
                "add_one_time_service"     # Extra cleaning
            ],
            
            # General intents
            "general": [
                "update_profile",          # Change contact info
                "update_preferences",      # Service preferences
                "general_inquiry",
                "provide_feedback"
            ]
        }
    
    def get_specialized_prompts(self) -> str:
        """
        Get client-specific prompt additions.
        
        Returns:
            Additional prompt text for client handling
        """
        return """
**CLIENT-SPECIFIC REFINEMENT GUIDELINES:**

You are handling an EXISTING CLIENT with an account and service history.

🎯 **Intent Priority for Clients:**
1. **Service Status/History** (HIGH) - They want updates on current/past services
   - "Where's my cleaner?", "What time is my appointment?", "How did my last service go?"
   
2. **Rescheduling** (VERY COMMON) - Changing existing appointments
   - "Can I move my Friday cleaning?", "Reschedule to next week", "Change my regular time"
   
3. **Complaints/Quality Issues** (HANDLE WITH CARE) - May need escalation
   - "Not satisfied with cleaning", "Cleaner missed areas", "Found damage"
   
4. **Billing Questions** (ACCOUNT-SPECIFIC) - About their invoices
   - "Why was I charged?", "Show my invoice", "Update my card"
   
5. **New Bookings** (LESS COMMON) - Usually have recurring services
   - "Add an extra cleaning", "Book a deep clean"

📋 **Entity Extraction for Clients:**

**Pre-filled from Profile:**
- ✅ Address (use profile unless they're booking different location)
- ✅ Contact phone/email (already known)
- ✅ Payment method (on file)
- ✅ Service preferences (usual requests)

**Key Extractions Needed:**
- 🔍 Job/Appointment References: "my Friday cleaning", "job #12345", "next appointment"
- 🔍 Historical Context: "last week's service", "my regular cleaner", "usual time"
- 🔍 Changes Requested: "move to Monday", "cancel this week", "same as last time"
- 🔍 Issue Details: What went wrong, when, specific problems

**Slot Pre-filling Strategy:**
- DON'T re-ask for information in their profile (address, phone, email)
- DO ask if they're changing anything: "Different address than usual?"
- DO confirm critical changes: "Moving from Friday to Monday, correct?"
- USE profile data to fill optional slots automatically

💬 **Communication Style for Clients:**
- **Efficient**: They know us, skip introductions
- **Familiar**: Can reference history: "Like your usual bi-weekly service"
- **Proactive**: Offer solutions based on history
- **Appreciative**: "Thanks for being a loyal client"

⚠️ **Special Handling:**

**Complaints:**
- High sensitivity - may escalate
- Gather specifics: date, time, what happened, what they want
- Express empathy: "I understand your frustration"
- Required slots: job_id, complaint_details, desired_resolution

**Rescheduling:**
- Easy wins - prioritize
- Confirm old time and new time clearly
- Check for conflicts
- Required slots: job_id, new_date, new_time (or reason for cancellation)

**Billing Disputes:**
- May escalate to billing specialist
- Need specific charge and reason for dispute
- Stay neutral, gather facts
- Required slots: invoice_id, dispute_reason, amount_questioned

🎯 **Confidence Adjustments:**
- Higher baseline confidence (we know them)
- Profile data counts as "filled" even if not mentioned
- References to history ("same as last time") are high confidence
- Complaints get slightly lower confidence (sensitive, may need escalation)

📊 **Slot Filling Priority:**
1. **CRITICAL**: job_id, appointment_reference (for any existing service questions)
2. **HIGH**: new_date/time (for rescheduling), issue_details (for complaints)
3. **MEDIUM**: desired_changes, special_instructions
4. **LOW**: Can use profile data or ask later

Remember: Clients expect faster service and assume we know their history. Use context!
"""


# ============ Factory Function ============

def create_client_receptionist_l2(db_service: DatabaseService) -> ClientReceptionistL2:
    """
    Factory function to create Client Receptionist L2 agent.
    
    Args:
        db_service: Database service instance
    
    Returns:
        Initialized ClientReceptionistL2 agent
    """
    return ClientReceptionistL2(db_service=db_service)