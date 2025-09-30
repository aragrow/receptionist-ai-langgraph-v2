# ==================== src/utilities/seed_l1_prompts.py ====================
"""
Seed L1 agent prompts into the database.
Run this script to populate the agent_action_prompts collection with L1 system prompts.
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.services.database_service import DatabaseService
from config.settings import settings


# ============ L1 System Prompts ============

L1_SYSTEM_PROMPT = """You are a fast, efficient call classifier for an AI receptionist system.

Your role is to quickly categorize incoming calls into broad intent categories with minimal processing time.

Key Guidelines:
1. **Speed is Critical**: Make decisions quickly, aim for < 1 second processing
2. **Be Decisive**: Don't overthink - choose the most likely category
3. **Use Context**: Consider caller type if known (client vs prospect vs partner)
4. **Default to General**: If uncertain, classify as "general" with lower confidence
5. **JSON Only**: Always respond with valid JSON, no explanatory text

Intent Categories:
- **scheduling**: Booking appointments, rescheduling, cancellations, calendar changes
- **support**: Problems, complaints, technical issues, help requests, service quality
- **billing**: Payments, invoices, account questions, charges, refunds
- **sales**: New service inquiries, quotes, interested prospects, pricing questions
- **general**: General information, FAQs, company info, hours, other

Caller Types:
- **client**: Existing customer with active account
- **prospect**: Potential new customer, leads
- **partner**: Vendor, contractor, business partner
- **unknown**: Cannot determine from available information

Confidence Guidelines:
- 0.90-1.0: Very clear intent with strong keywords (e.g., "I want to book a cleaning for Tuesday")
- 0.70-0.89: Clear intent with supporting context (e.g., "Can you help me with my appointment?")
- 0.50-0.69: Probable intent but some ambiguity (e.g., "I have a question about my service")
- 0.30-0.49: Uncertain, multiple possible intents (e.g., "I need help")
- 0.0-0.29: Very unclear, default to general

Response Format:
Always respond with this exact JSON structure, no additional text:

{
    "intent_name": "scheduling|support|billing|sales|general",
    "intent_category": "same as intent_name",
    "confidence": 0.0-1.0,
    "caller_type": "client|prospect|partner|unknown",
    "caller_type_confidence": 0.0-1.0,
    "reasoning": "Brief one-sentence explanation"
}

Examples:

Input: "I need to schedule a cleaning for next Tuesday"
Output: {"intent_name": "scheduling", "intent_category": "scheduling", "confidence": 0.95, "caller_type": "prospect", "caller_type_confidence": 0.60, "reasoning": "User explicitly requested scheduling with specific date"}

Input: "My last cleaning was terrible, need to complain"
Output: {"intent_name": "support", "intent_category": "support", "confidence": 0.92, "caller_type": "client", "caller_type_confidence": 0.85, "reasoning": "Complaint about service quality from existing customer"}

Input: "How much does a cleaning cost?"
Output: {"intent_name": "sales", "intent_category": "sales", "confidence": 0.88, "caller_type": "prospect", "caller_type_confidence": 0.75, "reasoning": "Pricing inquiry typical of new prospect"}

Input: "When did I pay my last invoice?"
Output: {"intent_name": "billing", "intent_category": "billing", "confidence": 0.90, "caller_type": "client", "caller_type_confidence": 0.90, "reasoning": "Invoice history question from existing client"}

Input: "Hi, can you help me?"
Output: {"intent_name": "general", "intent_category": "general", "confidence": 0.35, "caller_type": "unknown", "caller_type_confidence": 0.30, "reasoning": "Vague request without clear intent indicators"}

Remember: Be fast, be decisive, output valid JSON only."""


L1_CLASSIFICATION_EXAMPLES = """Additional Classification Examples for L1 Agent:

Scheduling Intent:
- "I want to book a cleaning for my house"
- "Can I reschedule my appointment from Friday to Monday?"
- "Need to cancel tomorrow's service"
- "What times are available next week?"
- "When is my next cleaning scheduled?"

Support Intent:
- "The cleaners didn't show up yesterday"
- "I'm not satisfied with the service quality"
- "There's a problem with my last cleaning"
- "My house wasn't cleaned properly"
- "I need to speak to a manager about an issue"

Billing Intent:
- "I was charged twice this month"
- "Can I get a copy of my invoice?"
- "When is my payment due?"
- "I want to update my credit card"
- "Why is my bill higher than usual?"

Sales Intent:
- "Do you offer commercial cleaning services?"
- "I'm interested in getting a quote"
- "What services do you provide?"
- "How much does a one-time deep clean cost?"
- "I saw your ad and want more information"

General Intent:
- "What are your business hours?"
- "Where are you located?"
- "Do you serve my area?"
- "Hello, is anyone there?"
- "I have a general question"

Multi-Intent Handling:
- If user mentions multiple intents, choose the PRIMARY one
- Example: "I want to schedule a cleaning and also ask about pricing" → scheduling (action intent takes priority)
- Example: "I have a billing question but also want to complain" → support (complaints are higher priority)

Caller Type Detection:
- Look for indicators: "my account", "my last service" → client
- New inquiry language: "I'm interested", "looking for" → prospect
- Business language: "our company", "vendor check-in" → partner
- No indicators: unknown (default)"""


L1_PROMPT_VARIANTS = {
    "concise": """You are a fast call classifier. Categorize user input into: scheduling, support, billing, sales, or general.
Output JSON only: {"intent_name": "...", "intent_category": "...", "confidence": 0.0-1.0, "caller_type": "...", "caller_type_confidence": 0.0-1.0, "reasoning": "..."}
Be fast and decisive. Default to "general" if uncertain.""",
    
    "detailed": L1_SYSTEM_PROMPT,
    
    "with_examples": L1_SYSTEM_PROMPT + "\n\n" + L1_CLASSIFICATION_EXAMPLES
}


# ============ Prompt Documents ============

L1_PROMPTS = [
    {
        "agent": "receptionist",
        "action": "l1_classification",
        "level": 1,
        "prompt": L1_PROMPT_VARIANTS["detailed"],
        "active": True,
        "notes": "Primary L1 classification prompt with detailed guidelines",
        "version": "1.0.0",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    },
    {
        "agent": "receptionist",
        "action": "l1_classification",
        "level": 2,
        "prompt": L1_PROMPT_VARIANTS["with_examples"],
        "active": False,
        "notes": "Extended L1 prompt with comprehensive examples (for testing/training)",
        "version": "1.1.0",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    },
    {
        "agent": "receptionist",
        "action": "l1_classification",
        "level": 3,
        "prompt": L1_PROMPT_VARIANTS["concise"],
        "active": False,
        "notes": "Ultra-concise L1 prompt for maximum speed (experimental)",
        "version": "0.9.0",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    },
    {
        "agent": "receptionist",
        "action": "l1_fallback",
        "level": 1,
        "prompt": """You are a fallback classifier when primary classification fails.
Given user input, quickly determine the most likely intent from: scheduling, support, billing, sales, general.
Be extremely fast and simple. Output only JSON: {"intent_name": "...", "confidence": 0.0-1.0}""",
        "active": True,
        "notes": "Fallback prompt for L1 when primary method fails",
        "version": "1.0.0",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    },
    {
        "agent": "receptionist",
        "action": "l1_clarification",
        "level": 1,
        "prompt": """You need to ask ONE clarifying question because the user's intent is unclear.

User said: "{user_input}"
Detected intent: {intent_name} (confidence: {confidence})

Generate a single, direct clarification question to determine their true intent.

Question Guidelines:
1. Keep it conversational and natural
2. Don't repeat what they said
3. Offer 2-3 clear options if helpful
4. Be brief (one sentence)

Examples:
- "Are you looking to schedule a new service or modify an existing appointment?"
- "Is this about a billing question or a service issue?"
- "Would you like to book a cleaning or get pricing information?"

Output JSON only: {{"question": "...", "question_type": "multiple_choice|open_ended"}}""",
        "active": True,
        "notes": "L1 clarification question generator",
        "version": "1.0.0",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
]


# ============ Seed Function ============

async def seed_l1_prompts():
    """Seed L1 prompts into the database."""
    
    print("=" * 80)
    print("L1 PROMPT SEEDING UTILITY")
    print("=" * 80)
    print()
    
    # Initialize database service
    db_service = DatabaseService()
    
    try:
        # Connect to database
        print("📡 Connecting to database...")
        await db_service.connect()
        print(f"✅ Connected to: {settings.database.database_name}")
        print()
        
        # Check if collection exists
        collections = await db_service.db.list_collection_names()
        if "agent_action_prompts" not in collections:
            print("⚠️  Creating 'agent_action_prompts' collection...")
            await db_service.db.create_collection("agent_action_prompts")
            print("✅ Collection created")
        
        print(f"📝 Seeding {len(L1_PROMPTS)} L1 prompts...")
        print()
        
        inserted_count = 0
        updated_count = 0
        skipped_count = 0
        
        for prompt_doc in L1_PROMPTS:
            # Check if prompt already exists
            existing = await db_service.db.agent_action_prompts.find_one({
                "agent": prompt_doc["agent"],
                "action": prompt_doc["action"],
                "level": prompt_doc["level"]
            })
            
            if existing:
                # Update if different
                if existing.get("prompt") != prompt_doc["prompt"]:
                    prompt_doc["updated_at"] = datetime.utcnow()
                    prompt_doc["created_at"] = existing.get("created_at", datetime.utcnow())
                    
                    await db_service.db.agent_action_prompts.update_one(
                        {"_id": existing["_id"]},
                        {"$set": prompt_doc}
                    )
                    print(f"✏️  Updated: {prompt_doc['agent']}/{prompt_doc['action']}/level-{prompt_doc['level']}")
                    updated_count += 1
                else:
                    print(f"⏭️  Skipped (unchanged): {prompt_doc['agent']}/{prompt_doc['action']}/level-{prompt_doc['level']}")
                    skipped_count += 1
            else:
                # Insert new
                result = await db_service.db.agent_action_prompts.insert_one(prompt_doc)
                print(f"✅ Inserted: {prompt_doc['agent']}/{prompt_doc['action']}/level-{prompt_doc['level']}")
                inserted_count += 1
        
        print()
        print("=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"✅ Inserted: {inserted_count}")
        print(f"✏️  Updated:  {updated_count}")
        print(f"⏭️  Skipped:  {skipped_count}")
        print(f"📊 Total:    {len(L1_PROMPTS)}")
        print()
        
        # Verify active prompts
        print("🔍 Verifying active prompts...")
        active_prompts = await db_service.db.agent_action_prompts.count_documents({"active": True})
        print(f"✅ Active prompts in database: {active_prompts}")
        print()
        
        # Show active L1 prompt
        active_l1 = await db_service.db.agent_action_prompts.find_one({
            "agent": "receptionist",
            "action": "l1_classification",
            "active": True
        })
        
        if active_l1:
            print("📋 Active L1 Classification Prompt:")
            print(f"   Level: {active_l1['level']}")
            print(f"   Version: {active_l1.get('version', 'N/A')}")
            print(f"   Notes: {active_l1.get('notes', 'N/A')}")
            print(f"   Length: {len(active_l1['prompt'])} characters")
        else:
            print("⚠️  No active L1 classification prompt found!")
        
        print()
        print("✅ L1 prompts seeded successfully!")
        
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


# ============ Utility Functions ============

async def list_all_prompts():
    """List all prompts in the database."""
    
    db_service = DatabaseService()
    
    try:
        await db_service.connect()
        
        print("=" * 80)
        print("ALL AGENT PROMPTS IN DATABASE")
        print("=" * 80)
        print()
        
        cursor = db_service.db.agent_action_prompts.find({}).sort([
            ("agent", 1),
            ("action", 1),
            ("level", 1)
        ])
        
        count = 0
        async for prompt in cursor:
            count += 1
            status = "🟢 ACTIVE" if prompt.get("active") else "⚪ INACTIVE"
            print(f"{status} | {prompt['agent']}/{prompt['action']}/level-{prompt['level']}")
            print(f"   Version: {prompt.get('version', 'N/A')}")
            print(f"   Notes: {prompt.get('notes', 'N/A')}")
            print(f"   Length: {len(prompt.get('prompt', ''))} chars")
            print()
        
        print(f"Total prompts: {count}")
        
    finally:
        await db_service.disconnect()


async def activate_prompt(agent: str, action: str, level: int):
    """Activate a specific prompt and deactivate others with same agent/action."""
    
    db_service = DatabaseService()
    
    try:
        await db_service.connect()
        
        # Deactivate all prompts for this agent/action
        await db_service.db.agent_action_prompts.update_many(
            {"agent": agent, "action": action},
            {"$set": {"active": False, "updated_at": datetime.utcnow()}}
        )
        
        # Activate the specified prompt
        result = await db_service.db.agent_action_prompts.update_one(
            {"agent": agent, "action": action, "level": level},
            {"$set": {"active": True, "updated_at": datetime.utcnow()}}
        )
        
        if result.modified_count > 0:
            print(f"✅ Activated: {agent}/{action}/level-{level}")
        else:
            print(f"⚠️  Prompt not found: {agent}/{action}/level-{level}")
        
    finally:
        await db_service.disconnect()


async def delete_all_prompts(confirm: bool = False):
    """Delete all prompts from database (use with caution!)."""
    
    if not confirm:
        print("⚠️  This will delete ALL prompts from the database!")
        print("To confirm, run: delete_all_prompts(confirm=True)")
        return
    
    db_service = DatabaseService()
    
    try:
        await db_service.connect()
        
        result = await db_service.db.agent_action_prompts.delete_many({})
        print(f"🗑️  Deleted {result.deleted_count} prompts")
        
    finally:
        await db_service.disconnect()


# ============ Main Entry Point ============

async def main():
    """Main entry point."""
    
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "seed":
            await seed_l1_prompts()
        
        elif command == "list":
            await list_all_prompts()
        
        elif command == "activate":
            if len(sys.argv) != 5:
                print("Usage: python seed_l1_prompts.py activate <agent> <action> <level>")
                print("Example: python seed_l1_prompts.py activate receptionist l1_classification 2")
                return
            
            agent = sys.argv[2]
            action = sys.argv[3]
            level = int(sys.argv[4])
            await activate_prompt(agent, action, level)
        
        elif command == "delete-all":
            confirm = len(sys.argv) > 2 and sys.argv[2] == "--confirm"
            await delete_all_prompts(confirm=confirm)
        
        else:
            print(f"Unknown command: {command}")
            print_usage()
    
    else:
        # Default: seed prompts
        await seed_l1_prompts()


def print_usage():
    """Print usage instructions."""
    
    print("""
L1 Prompt Seeding Utility

Usage:
    python seed_l1_prompts.py [command]

Commands:
    seed         Seed L1 prompts into database (default)
    list         List all prompts in database
    activate     Activate a specific prompt
    delete-all   Delete all prompts (requires --confirm)

Examples:
    python seed_l1_prompts.py
    python seed_l1_prompts.py seed
    python seed_l1_prompts.py list
    python seed_l1_prompts.py activate receptionist l1_classification 2
    python seed_l1_prompts.py delete-all --confirm
""")


if __name__ == "__main__":
    asyncio.run(main())