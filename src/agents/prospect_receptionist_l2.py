# ==================== src/agents/prospect_receptionist_l2.py ====================
"""
Prospect Receptionist L2 - Intent refiner for prospective clients.
Handles new potential customers who don't have accounts yet.
"""

import logging
from typing import Dict, List

from src.agents.receptionist_l2_base import ReceptionistL2Base
from src.services.database_service import DatabaseService

logger = logging.getLogger(__name__)


class ProspectReceptionistL2(ReceptionistL2Base):
    """
    Level 2 Receptionist for Prospects/Leads.
    
    Specializes in:
    - Quote requests
    - First-time bookings
    - Service inquiries
    - Coverage area checks
    - Converting leads to customers
    
    Challenges:
    - No profile data available
    - Need to capture all information
    - Educational approach needed
    """
    
    def __init__(self, db_service: DatabaseService):
        """
        Initialize Prospect Receptionist L2.
        
        Args:
            db_service: Database service for data access
        """
        super().__init__(
            agent_name="prospect_receptionist_l2",
            caller_type="prospect",
            db_service=db_service
        )
        
        logger.info("ProspectReceptionistL2 initialized")
    
    def get_intent_mappings(self) -> Dict[str, List[str]]:
        """
        Get mapping from L1 broad intents to specific prospect L2 intents.
        
        Returns:
            Dictionary mapping L1 intent to list of possible L2 intents
        """
        return {
            # Sales intents (most common for prospects)
            "sales": [
                "request_quote",              # Most common
                "book_home_cleaning",         # Ready to book
                "book_commercial_cleaning",
                "service_inquiry",            # Learning about services
                "pricing_inquiry",
                "package_comparison",
                "coverage_area_check"
            ],
            
            # Scheduling intents
            "scheduling": [
                "book_first_service",         # New customer booking
                "check_availability",
                "schedule_consultation"       # May want to meet first
            ],
            
            # General intents (educational)
            "general": [
                "company_info",               # About us
                "service_details",            # What do you offer?
                "hours_of_operation",
                "service_areas",              # Do you serve my area?
                "testimonials_request",       # Social proof
                "referral_inquiry"
            ],
            
            # Support intents (rare for prospects)
            "support": [
                "general_question",
                "how_it_works",
                "safety_protocols"            # COVID, background checks
            ],
            
            # Billing intents (pre-sale)
            "billing": [
                "payment_methods",            # How do I pay?
                "pricing_details",
                "discount_inquiry"
            ]
        }
    
    def get_specialized_prompts(self) -> str:
        """
        Get prospect-specific prompt additions.
        
        Returns:
            Additional prompt text for prospect handling
        """
        return """
**PROSPECT-SPECIFIC REFINEMENT GUIDELINES:**

You are handling a PROSPECTIVE CLIENT who is interested but doesn't have an account yet.

🎯 **Intent Priority for Prospects:**
1. **Quote Requests** (CONVERT TO SALE) - Pricing inquiries
   - "How much does it cost?", "Can I get a quote?", "What's your pricing?"
   
2. **Service Inquiries** (EDUCATION) - Learning phase
   - "What services do you offer?", "Do you do deep cleaning?", "How does it work?"
   
3. **First Bookings** (HIGH PRIORITY) - Ready to buy
   - "I want to book a cleaning", "Schedule my first service", "Sign me up"
   
4. **Coverage Checks** (QUALIFICATION) - Can you serve me?
   - "Do you service my area?", "How far do you travel?", "Are you available in [city]?"

📋 **Entity Extraction for Prospects:**

**NO PRE-FILLED DATA** - Must capture everything!

**CRITICAL to Capture:**
- 🔴 **Location/Address** (MUST HAVE) - Need to verify coverage and calculate pricing
- 🔴 **Contact Method** (MUST HAVE) - Phone or email for follow-up
- 🔴 **Service Type** (MUST HAVE) - What are they interested in?

**IMPORTANT to Capture:**
- 🟡 **Property Details**: Type (house/apt/office), size (sqft or bedrooms), condition
- 🟡 **Timeline**: When do they need service? (ASAP, this week, next month, just browsing)
- 🟡 **Frequency**: One-time or recurring? How often?

**NICE to Capture:**
- 🟢 **Budget/Price Sensitivity**: "Looking for affordable", "premium service"
- 🟢 **Special Requirements**: Pets, allergies, eco-friendly, specific focus areas
- 🟢 **How They Found Us**: Referral, Google, ad, etc. (marketing data)
- 🟢 **Competition**: "Comparing with other services"

**Validation Requirements:**
- Phone: Full 10-digit number required
- Email: Valid format required
- Address: At minimum need city/zip for coverage check

💬 **Communication Style for Prospects:**
- **Educational**: Explain how things work, don't assume knowledge
- **Thorough**: Gather complete information, don't rush
- **Value-Focused**: Emphasize benefits and quality
- **Patient**: Expect more back-and-forth
- **Professional**: First impression matters

⚠️ **Special Handling:**

**Quote Requests:**
- Need detailed property information for accurate quote
- Required slots: address, service_type, property_type, square_footage (or bedrooms)
- Optional but helpful: special_requirements, preferred_date, frequency
- High confidence only if we have enough info for accurate quote

**Coverage Area Checks:**
- Quick qualification - high priority
- Just need location (city/zip)
- Fast response if out of area: be helpful, maybe refer
- Required slots: city or zip_code

**First Bookings:**
- Conversion opportunity - handle carefully
- Need ALL contact info, full address, service details, payment method discussion
- Required slots: address, service_type, preferred_date, contact_number, email
- May need to educate on process: "First, we'll need to..."

**Service Inquiries:**
- Educational, may convert later
- Focus on value proposition
- Capture contact info for follow-up
- Lower information requirements but still capture lead data

🎯 **Confidence Adjustments:**
- Lower baseline (no history, new relationship)
- More information required before high confidence
- Timeline affects confidence: "just browsing" = lower confidence
- Complete contact info significantly boosts confidence

📊 **Slot Filling Priority:**
1. **CRITICAL**: address/location (for coverage), contact_number or email, service_type
2. **HIGH**: property_details (for quotes), preferred_date (shows commitment)
3. **MEDIUM**: frequency, budget, special_requirements
4. **LOW**: how_found_us (nice for marketing but not blocking)

🎁 **Lead Capture Strategy:**
Even if they're not ready to book:
- ALWAYS try to capture contact info
- Mark timeline as "researching" or "future"
- Offer to send information by email
- Create lead record even if no immediate sale

🚫 **Common Prospect Pitfalls:**
- ❌ Assuming they know our process
- ❌ Rushing to booking without education
- ❌ Not capturing contact info from "just looking" callers
- ❌ Not qualifying coverage area early
- ❌ Asking for payment details before they're ready

✅ **Best Practices:**
- ✅ Qualify coverage area in first exchange
- ✅ Educate before selling
- ✅ Always get contact info
- ✅ Set expectations clearly
- ✅ Offer next steps even if not ready now

Remember: Every prospect is a potential client. Capture information, provide value, build trust!
"""


# ============ Factory Function ============

def create_prospect_receptionist_l2(db_service: DatabaseService) -> ProspectReceptionistL2:
    """
    Factory function to create Prospect Receptionist L2 agent.
    
    Args:
        db_service: Database service instance
    
    Returns:
        Initialized ProspectReceptionistL2 agent
    """
    return ProspectReceptionistL2(db_service=db_service)