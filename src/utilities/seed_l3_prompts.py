# ==================== src/utilities/seed_l3_prompts.py ====================
"""
Seed L3 agent prompts into the database.
Run this script to populate confirmation message generation prompts for L3 agents.
"""

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.services.database_service import DatabaseService


# ============ L3 Confirmation Prompts ============

L3_PROMPTS = [
    {
        "agent": "sales_agent_l3",
        "action": "generate_confirmation",
        "level": 1,
        "active": True,
        "version": "1.0",
        "notes": "Sales confirmation message generation",
        "prompt": """You are generating a friendly confirmation message for a booking action.

Context:
- Customer name: {customer_name}
- Action taken: {action_name}
- Action result: {action_result}

Generate a warm, conversational confirmation message (2-3 sentences) that:
1. Confirms what was done
2. Includes key details (booking number, date, etc.)
3. Sets expectations for next steps

Keep it natural and friendly, as if speaking to the customer directly.

Example for booking:
"Great! I've scheduled your house cleaning for Tuesday, March 15th at 2:00 PM. Your confirmation number is BK-12345678. We'll send you a reminder 24 hours before your appointment."

Now generate a confirmation for the current action."""
    },
    {
        "agent": "support_agent_l3",
        "action": "generate_confirmation",
        "level": 1,
        "active": True,
        "version": "1.0",
        "notes": "Support confirmation message generation",
        "prompt": """You are generating an empathetic confirmation message for a support action.

Context:
- Customer name: {customer_name}
- Action taken: {action_name}
- Action result: {action_result}

Generate a caring, professional confirmation message (2-3 sentences) that:
1. Acknowledges the issue/concern
2. Confirms the action taken (ticket created, etc.)
3. Provides clear next steps and timeline

Show empathy and urgency. Reassure the customer.

Example for support ticket:
"I understand your concern, and I've created support ticket TK-87654321 to address this immediately. Our team will contact you within 2 hours to resolve this. We appreciate your patience."

Now generate a confirmation for the current action."""
    },
    {
        "agent": "scheduling_agent_l3",
        "action": "generate_confirmation",
        "level": 1,
        "active": True,
        "version": "1.0",
        "notes": "Scheduling confirmation message generation",
        "prompt": """You are generating a clear confirmation message for a scheduling action.

Context:
- Customer name: {customer_name}
- Action taken: {action_name}
- Action result: {action_result}

Generate a clear, concise confirmation message (2-3 sentences) that:
1. Confirms the schedule change
2. Includes old and new dates if applicable
3. Provides confirmation number

Be efficient and clear about the scheduling details.

Example for reschedule:
"Done! I've rescheduled your appointment from Friday, March 10th to Monday, March 13th at 10:00 AM. Your new confirmation number is RS-23456789. You'll receive an updated calendar invite shortly."

Now generate a confirmation for the current action."""
    },
    {
        "agent": "billing_agent_l3",
        "action": "generate_confirmation",
        "level": 1,
        "active": True,
        "version": "1.0",
        "notes": "Billing confirmation message generation",
        "prompt": """You are generating a professional confirmation message for a billing action.

Context:
- Customer name: {customer_name}
- Action taken: {action_name}
- Action result: {action_result}

Generate a clear, professional confirmation message (2-3 sentences) that:
1. Confirms the transaction/action
2. Includes amounts, invoice numbers, etc.
3. Provides receipt or next payment steps

Be precise with financial information.

Example for payment:
"Thank you! Your payment of $150.00 has been successfully processed. Your receipt number is RCP-20250315-ABC123. You'll receive an email confirmation within a few minutes."

Now generate a confirmation for the current action."""
    },
    {
        "agent": "partner_agent_l3",
        "action": "generate_confirmation",
        "level": 1,
        "active": True,
        "version": "1.0",
        "notes": "Partner/vendor confirmation message generation",
        "prompt": """You are generating a confirmation message for a vendor/partner action.

Context:
- Vendor name: {customer_name}
- Action taken: {action_name}
- Action result: {action_result}

Generate a brief, professional confirmation message (2-3 sentences) that:
1. Confirms the action (check-in, update, etc.)
2. Includes job details if applicable
3. Provides next steps or reminders

Keep it concise and action-oriented for field workers.

Example for check-in:
"You're checked in at the Johnson residence, job #JB-45678. The estimated completion time is 2 hours. Remember to take before and after photos."

Now generate a confirmation for the current action."""
    },
    {
        "agent": "general_agent_l3",
        "action": "generate_confirmation",
        "level": 1,
        "active": True,
        "version": "1.0",
        "notes": "General information confirmation message generation",
        "prompt": """You are generating a helpful response message for a general inquiry.

Context:
- Customer name: {customer_name}
- Action taken: {action_name}
- Action result: {action_result}

Generate a friendly, informative message (2-3 sentences) that:
1. Answers the question clearly
2. Provides relevant details
3. Offers to help with anything else

Be helpful and conversational.

Example for business hours:
"We're open Monday through Friday from 8 AM to 6 PM, and Saturdays from 9 AM to 4 PM. We're closed on Sundays. Is there anything else I can help you with today?"

Now generate a response for the current inquiry."""
    }
]


async def seed_prompts():
    """Seed L3 prompts into the database."""
    
    db_service = DatabaseService()
    
    try:
        # Connect to database
        print("=" * 80)
        print("L3 PROMPTS SEEDING")
        print("=" * 80)
        print(f"Database: {db_service.database}")
        print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
        print("=" * 80)
        print()
        
        await db_service.connect()
        print("✅ Connected to database")
        print()
        
        # Seed prompts
        inserted_count = 0
        updated_count = 0
        skipped_count = 0
        
        print("Seeding L3 prompts...")
        print()
        
        for prompt_data in L3_PROMPTS:
            # Check if prompt already exists
            existing = await db_service.db.agent_action_prompts.find_one({
                "agent": prompt_data["agent"],
                "action": prompt_data["action"],
                "level": prompt_data["level"]
            })
            
            if existing:
                # Update if different
                if existing.get("prompt") != prompt_data["prompt"]:
                    prompt_data["updated_at"] = datetime.now(timezone.utc)
                    prompt_data["created_at"] = existing.get("created_at", datetime.now(timezone.utc))
                    
                    await db_service.db.agent_action_prompts.update_one(
                        {"_id": existing["_id"]},
                        {"$set": prompt_data}
                    )
                    print(f"✏️  Updated: {prompt_data['agent']}/{prompt_data['action']}")
                    updated_count += 1
                else:
                    print(f"⭐ Skipped (unchanged): {prompt_data['agent']}/{prompt_data['action']}")
                    skipped_count += 1
            else:
                # Insert new
                prompt_data["created_at"] = datetime.now(timezone.utc)
                prompt_data["updated_at"] = datetime.now(timezone.utc)
                result = await db_service.db.agent_action_prompts.insert_one(prompt_data)
                print(f"✅ Inserted: {prompt_data['agent']}/{prompt_data['action']}")
                inserted_count += 1
        
        print()
        print("=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"✅ Inserted: {inserted_count}")
        print(f"✏️  Updated:  {updated_count}")
        print(f"⭐ Skipped:  {skipped_count}")
        print(f"📊 Total:    {len(L3_PROMPTS)}")
        print()
        
        # Verify
        print("🔍 Verifying L3 prompts...")
        l3_prompts_count = await db_service.db.agent_action_prompts.count_documents({
            "agent": {"$regex": "_l3$"}
        })
        print(f"✅ L3 prompts in database: {l3_prompts_count}")
        print()
        
        print("✅ L3 prompts seeded successfully!")
        
    except Exception as e:
        print(f"❌ Error seeding prompts: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Disconnect
        await db_service.disconnect()
        print("📡 Disconnected from database")
    
    return True


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("SEED L3 AGENT PROMPTS")
    print("=" * 80 + "\n")
    
    success = asyncio.run(seed_prompts())
    
    if success:
        print("\n✅ Seeding completed successfully!\n")
        sys.exit(0)
    else:
        print("\n❌ Seeding failed!\n")
        sys.exit(1)