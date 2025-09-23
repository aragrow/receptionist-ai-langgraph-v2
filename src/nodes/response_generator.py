# ==================== src/nodes/response_generator.py ====================
"""Response generator node."""

import html
from typing import Dict, Any

from src.models.workflow_models import WorkflowState, CallerType, Intent


class ResponseGenerator:
    """Node for generating responses."""
    
    def __init__(self):
        self.templates = {
            CallerType.CLIENT: {
                Intent.STATUS_CHECK: "Let me check the status of your current projects...",
                Intent.SERVICE_REQUEST: "I'd be happy to help you with a service request...",
                Intent.COMPLAINT: "I understand your concern. Let me look into this for you...",
                Intent.GENERAL_INQUIRY: "Hello! How can I assist you with your property today?"
            },
            CallerType.VENDOR: {
                Intent.STATUS_CHECK: "Let me check your current job assignments...",
                Intent.GENERAL_INQUIRY: "Hello! What can I help you with regarding your jobs?"
            },
            CallerType.LEAD: {
                Intent.SALES_INQUIRY: "Thank you for your interest in our services...",
                Intent.GENERAL_INQUIRY: "Welcome! How can we help you today?"
            }
        }
    
    def _escape_output(self, text: str) -> str:
        """Escape text for safe display."""
        return html.escape(text)
    
    async def __call__(self, state: WorkflowState) -> WorkflowState:
        """Generate response based on context and intent."""
        try:
            # Get base template
            caller_templates = self.templates.get(state.caller_type, {})
            base_response = caller_templates.get(
                state.intent, 
                "Hello! How can I help you today?"
            )
            
            # Enhance response with context
            enhanced_response = self._enhance_response(base_response, state)
            
            # Escape for safe output
            state.response_text = self._escape_output(enhanced_response)
            state.next_action = self._determine_next_action(state)
            
        except Exception as e:
            state.error_message = f"Response generation failed: {str(e)}"
            state.response_text = "I apologize, but I'm having trouble processing your request right now."
        
        state.processed = True
        return state
    
    def _enhance_response(self, base_response: str, state: WorkflowState) -> str:
        """Enhance response with contextual information."""
        if state.caller_type == CallerType.CLIENT and state.context_data.get("properties"):
            property_count = len(state.context_data["properties"])
            if property_count > 0:
                base_response += f" I see you have {property_count} property(ies) with us."
        
        elif state.caller_type == CallerType.VENDOR and state.context_data.get("jobs"):
            job_count = len(state.context_data["jobs"])
            if job_count > 0:
                base_response += f" You currently have {job_count} job(s) assigned."
        
        return base_response
    
    def _determine_next_action(self, state: WorkflowState) -> str:
        """Determine the next action to take."""
        if state.intent == Intent.SERVICE_REQUEST:
            return "schedule_service"
        elif state.intent == Intent.STATUS_CHECK:
            return "provide_status"
        elif state.intent == Intent.COMPLAINT:
            return "escalate_to_human"
        else:
            return "continue_conversation"