# ==================== src/workflow/workflow_runner.py ====================
"""Workflow Runner for AI Receptionist. Command-line interface and programmatic runner for the workflow."""

import asyncio
import json
import sys
from typing import Dict, Any

from src.workflow.ai_receptionist_workflow import AIReceptionistWorkflow
from src.models.workflow_models import WorkflowState


class WorkflowRunner:
    """Runner for the AI Receptionist workflow."""
    
    def __init__(self):
        self.workflow = AIReceptionistWorkflow()
    
    async def run_workflow(self, call_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run the workflow with call data."""
        try:
            await self.workflow.initialize()
            
            result = await self.workflow.process_call(call_data)
            
            return {
                "success": True,
                "caller_type": result.caller_type,
                "intent": result.intent,
                "response": result.response_text,
                "next_action": result.next_action,
                "error": result.error_message
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Workflow execution failed: {str(e)}"
            }
        
        finally:
            await self.workflow.cleanup()
    
    async def run_from_cli(self, args: list):
        """Run workflow from command line arguments."""
        if len(args) < 2:
            print("Usage: python workflow_runner.py <caller_phone> [speech_text]")
            return
        
        call_data = {
            "caller_phone": args[1],
            "speech_text": args[2] if len(args) > 2 else "Hello, I need help",
            "call_sid": "test_call_123"
        }
        
        print(f"Processing call from: {call_data['caller_phone']}")
        print(f"Speech text: {call_data['speech_text']}")
        
        result = await self.run_workflow(call_data)
        
        print("\n--- Workflow Result ---")
        print(json.dumps(result, indent=2, default=str))


async def main():
    """Main entry point for CLI."""
    runner = WorkflowRunner()
    await runner.run_from_cli(sys.argv)


if __name__ == "__main__":
    asyncio.run(main())