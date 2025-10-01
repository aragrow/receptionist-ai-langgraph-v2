# ==================== verify_workflow_migration.py ====================
"""
Verification script for workflow migration to 3-tier routing.
Run this after updating workflow files to verify everything is working.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


async def verify_imports():
    """Verify all necessary imports are available."""
    print("=" * 80)
    print("STEP 1: Verifying Imports")
    print("=" * 80)
    
    checks = []
    
    # Check core models
    try:
        from src.models.workflow_models import WorkflowState, CallerType, IntentL1, IntentL2
        checks.append(("✅", "WorkflowState model"))
    except Exception as e:
        checks.append(("❌", f"WorkflowState model: {e}"))
    
    # Check agent models
    try:
        from src.models.agent_models import L1Output, L2Output, L3Output, RoutingDecision
        checks.append(("✅", "Agent models"))
    except Exception as e:
        checks.append(("❌", f"Agent models: {e}"))
    
    # Check L1 agent
    try:
        from src.agents.receptionist_l1 import ReceptionistL1
        checks.append(("✅", "ReceptionistL1"))
    except Exception as e:
        checks.append(("❌", f"ReceptionistL1: {e}"))
    
    # Check L2 agents
    try:
        from src.agents.l2_agent_factory import L2AgentFactory
        checks.append(("✅", "L2AgentFactory"))
    except Exception as e:
        checks.append(("❌", f"L2AgentFactory: {e}"))
    
    try:
        from src.agents.client_receptionist_l2 import ClientReceptionistL2
        from src.agents.prospect_receptionist_l2 import ProspectReceptionistL2
        from src.agents.partner_receptionist_l2 import PartnerReceptionistL2
        from src.agents.general_receptionist_l2 import GeneralReceptionistL2
        checks.append(("✅", "All L2 agents"))
    except Exception as e:
        checks.append(("❌", f"L2 agents: {e}"))
    
    # Check base agents
    try:
        from src.agents.base_agent import BaseAgent
        from src.agents.receptionist_l2_base import ReceptionistL2Base
        checks.append(("✅", "Base agent classes"))
    except Exception as e:
        checks.append(("❌", f"Base agents: {e}"))
    
    # Check services
    try:
        from src.services.database_service import DatabaseService
        from src.services.context_service import ContextService
        checks.append(("✅", "Services"))
    except Exception as e:
        checks.append(("❌", f"Services: {e}"))
    
    # Check workflow
    try:
        from src.workflow.ai_receptionist_workflow import AIReceptionistWorkflow
        from src.workflow.workflow_runner import WorkflowRunner
        checks.append(("✅", "Workflow classes"))
    except Exception as e:
        checks.append(("❌", f"Workflow classes: {e}"))
    
    # Print results
    print()
    for status, message in checks:
        print(f"{status} {message}")
    
    # Summary
    passed = sum(1 for status, _ in checks if status == "✅")
    total = len(checks)
    print()
    print(f"Import Checks: {passed}/{total} passed")
    
    return passed == total


async def verify_database_connection():
    """Verify database connection and collections."""
    print("\n" + "=" * 80)
    print("STEP 2: Verifying Database Connection")
    print("=" * 80)
    
    try:
        from src.services.database_service import DatabaseService
        from config.settings import settings
        
        db_service = DatabaseService()
        await db_service.connect()
        
        print(f"✅ Connected to MongoDB: {settings.database.database_name}")
        
        # Check collections
        collections = await db_service.db.list_collection_names()
        
        required_collections = [
            "clients",
            "vendors",
            "agent_action_prompts",
            "sessions",
            "routing_logs"
        ]
        
        print("\nChecking collections:")
        for coll in required_collections:
            if coll in collections:
                count = await db_service.db[coll].estimated_document_count()
                print(f"  ✅ {coll} ({count} documents)")
            else:
                print(f"  ❌ {coll} (not found)")
        
        await db_service.disconnect()
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False


async def verify_prompts():
    """Verify L1 and L2 prompts are seeded."""
    print("\n" + "=" * 80)
    print("STEP 3: Verifying Prompts")
    print("=" * 80)
    
    try:
        from src.services.database_service import DatabaseService
        
        db_service = DatabaseService()
        await db_service.connect()
        
        # Check L1 prompts
        l1_prompt = await db_service.find_agent_action_prompt(
            agent="receptionist_l1",
            action="classify_intent",
            level=1
        )
        
        if l1_prompt:
            print(f"✅ L1 classification prompt found ({len(l1_prompt)} chars)")
        else:
            print("❌ L1 classification prompt not found")
            print("   Run: python src/utilities/seed_l1_prompts.py")
        
        # Check L2 prompts
        l2_caller_types = ["client", "prospect", "partner", "general"]
        print("\nL2 prompts:")
        for caller_type in l2_caller_types:
            prompt = await db_service.find_agent_action_prompt(
                agent="receptionist_l1",
                action=f"l2_refinement_{caller_type}",
                level=1
            )
            if prompt:
                print(f"  ✅ {caller_type} ({len(prompt)} chars)")
            else:
                print(f"  ❌ {caller_type} (not found)")
        
        # Check clarification prompt
        clarification_prompt = await db_service.find_agent_action_prompt(
            agent="receptionist_l1",
            action="l2_clarification",
            level=1
        )
        
        if clarification_prompt:
            print(f"✅ L2 clarification prompt found")
        else:
            print("❌ L2 clarification prompt not found")
            print("   Run: python src/utilities/seed_l2_prompts.py")
        
        await db_service.disconnect()
        return True
        
    except Exception as e:
        print(f"❌ Prompt verification failed: {e}")
        return False


async def test_l1_agent():
    """Test L1 agent with sample input."""
    print("\n" + "=" * 80)
    print("STEP 4: Testing L1 Agent")
    print("=" * 80)
    
    try:
        from src.agents.receptionist_l1 import ReceptionistL1
        from src.services.database_service import DatabaseService
        from src.models.workflow_models import WorkflowState
        
        db_service = DatabaseService()
        await db_service.connect()
        
        l1_agent = ReceptionistL1(db_service)
        
        test_inputs = [
            "I need to schedule a cleaning",
            "I have a complaint about my last service",
            "How much does it cost?"
        ]
        
        print("\nTesting L1 classification:")
        for text in test_inputs:
            state = WorkflowState(
                caller_phone="555-123-4567",
                speech_text=text
            )
            
            result = await l1_agent.process(state)
            
            if result.intent_l1:
                print(f"  ✅ '{text[:40]}...'")
                print(f"     → Intent: {result.intent_l1.name} (confidence: {result.intent_l1.confidence:.2f})")
            else:
                print(f"  ❌ '{text[:40]}...' - No intent detected")
        
        await db_service.disconnect()
        return True
        
    except Exception as e:
        print(f"❌ L1 test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_l2_factory():
    """Test L2 agent factory."""
    print("\n" + "=" * 80)
    print("STEP 5: Testing L2 Agent Factory")
    print("=" * 80)
    
    try:
        from src.agents.l2_agent_factory import L2AgentFactory
        from src.services.database_service import DatabaseService
        from src.models.workflow_models import CallerType
        
        db_service = DatabaseService()
        await db_service.connect()
        
        factory = L2AgentFactory(db_service)
        
        print("\nSupported caller types:")
        for caller_type in factory.get_supported_caller_types():
            print(f"  - {caller_type.value}")
        
        print("\nCreating L2 agents:")
        test_types = [CallerType.CLIENT, CallerType.PROSPECT, CallerType.PARTNER, CallerType.UNKNOWN]
        
        for caller_type in test_types:
            agent = factory.create_agent(caller_type)
            print(f"  ✅ {caller_type.value} → {agent.agent_name}")
        
        await db_service.disconnect()
        return True
        
    except Exception as e:
        print(f"❌ L2 factory test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_workflow():
    """Test complete workflow."""
    print("\n" + "=" * 80)
    print("STEP 6: Testing Complete Workflow")
    print("=" * 80)
    
    try:
        from src.workflow.workflow_runner import WorkflowRunner
        
        runner = WorkflowRunner()
        
        test_call = {
            "caller_phone": "555-123-4567",
            "speech_text": "I need to schedule a cleaning for next Tuesday",
            "call_sid": "test_verification_call"
        }
        
        print(f"\nTest input: '{test_call['speech_text']}'")
        print("Processing...")
        
        result = await runner.run_workflow(test_call)
        
        print(f"\n✅ Workflow completed")
        print(f"   Success: {result.get('success')}")
        print(f"   Caller Type: {result.get('caller_type')}")
        
        if result.get('intent_l1'):
            print(f"   L1 Intent: {result['intent_l1']['name']} ({result['intent_l1']['confidence']:.2f})")
        
        if result.get('intent_l2'):
            print(f"   L2 Intent: {result['intent_l2']['name']} ({result['intent_l2']['confidence']:.2f})")
        
        if result.get('routing'):
            print(f"   Current Tier: {result['routing']['current_tier']}")
            print(f"   Routing Steps: {len(result['routing']['routing_history'])}")
        
        print(f"\n   Response: {result.get('response', 'No response')[:80]}...")
        
        return result.get('success', False)
        
    except Exception as e:
        print(f"❌ Workflow test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all verification steps."""
    print("\n" + "=" * 80)
    print("WORKFLOW MIGRATION VERIFICATION")
    print("=" * 80)
    print()
    
    results = []
    
    # Run all checks
    results.append(("Imports", await verify_imports()))
    results.append(("Database", await verify_database_connection()))
    results.append(("Prompts", await verify_prompts()))
    results.append(("L1 Agent", await test_l1_agent()))
    results.append(("L2 Factory", await test_l2_factory()))
    results.append(("Workflow", await test_workflow()))
    
    # Summary
    print("\n" + "=" * 80)
    print("VERIFICATION SUMMARY")
    print("=" * 80)
    
    for step, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status} - {step}")
    
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    print()
    print(f"Overall: {passed_count}/{total_count} checks passed")
    
    if passed_count == total_count:
        print("\n🎉 All verification checks passed! Workflow migration successful.")
        return 0
    else:
        print("\n⚠️  Some checks failed. Please review the errors above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)