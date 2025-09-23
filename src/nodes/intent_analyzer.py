# ==================== src/nodes/intent_analyzer.py ====================
"""Intent analyzer node."""

import re
from src.models.workflow_models import WorkflowState, Intent


class IntentAnalyzer:
    """Node for analyzing caller intent."""
    
    def __init__(self):
        self.intent_patterns = {
            Intent.STATUS_CHECK: [
                r"status", r"progress", r"update", r"how.*going", r"when.*complete"
            ],
            Intent.SERVICE_REQUEST: [
                r"need.*service", r"repair", r"fix", r"maintenance", r"problem"
            ],
            Intent.COMPLAINT: [
                r"complain", r"issue", r"problem", r"dissatisfied", r"unhappy"
            ],
            Intent.SALES_INQUIRY: [
                r"price", r"cost", r"quote", r"estimate", r"how much"
            ]
        }
    
    async def __call__(self, state: WorkflowState) -> WorkflowState:
        """Analyze caller intent from speech."""
        if not state.speech_text:
            state.intent = Intent.GENERAL_INQUIRY
            return state
        
        text = state.speech_text.lower()
        
        try:
            # Check patterns for each intent
            for intent, patterns in self.intent_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, text):
                        state.intent = intent
                        return state
            
            # Default intent
            state.intent = Intent.GENERAL_INQUIRY
            
        except Exception as e:
            state.error_message = f"Intent analysis failed: {str(e)}"
            state.intent = Intent.GENERAL_INQUIRY
        
        return state    