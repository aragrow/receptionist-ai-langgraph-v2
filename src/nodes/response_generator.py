# ==================== src/nodes/response_generator.py ====================
"""Response generator node using Google Gemini."""

import html
import os
from src.models.workflow_models import WorkflowState, CallerType, Intent
from config.settings import settings
from dotenv import load_dotenv
from src.services.database_service import DatabaseService

load_dotenv()

class ResponseGenerator:
    """Node for generating responses with Google Gemini."""
        
    def __init__(self):
        self.db_service = DatabaseService

        # Configure Gemini
        api_key = os.getenv("LLM__GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("API_KEY environment variable is required")
        
        genai.configure(api_key=api_key)

        self.model_name = os.getenv("LLM__MODEL_NAME")
        if not self.model_name:
            raise ValueError("MODEL environment variable is required")

    def _escape_output(self, text: str) -> str:
        """Escape text for safe display."""
        return html.escape(text)

    async def __call__(self, state: WorkflowState) -> WorkflowState:
        """Generate response using Gemini based on context and intent."""
        try:
            agent_prompt = await self.db_service.find_agent_action_prompt('receptionist','intent_analysis',1)
            state.agent_prompt = agent_prompt.prompt
            
            # Initialize turn count if not present
            if not hasattr(state, 'turn_count'):
                state.turn_count = 0
            state.turn_count += 1
            
            response = await self._generate_with_gemini(state)

            # If Gemini fails or empty string, fall back to templates
            if not response:
                response = self._get_fallback_response(state)

            # Assign response back into workflow state
            state.response_text = self._escape_output(response)
            state.next_action = 'WIP'

        except Exception as e:
            state.error_message = f"Response generation failed: {str(e)}"
            state.response_text = "I apologize, but I'm having trouble processing your request right now."
            state.next_action = "continue_conversation"

        state.processed = True
        return state

    async def _generate_with_gemini(self, state: WorkflowState) -> str:
        """Ask Gemini to generate a contextual, intent-aware response."""
        try:
            # Build conversation history
            conversation_history = ""
            if hasattr(state, 'conversation_history') and state.conversation_history:
                history_items = []
                for i, turn in enumerate(state.conversation_history[-3:]):  # Last 3 turns
                    history_items.append(f"Turn {i+1}: Caller said '{turn.get('user_input', '')}' -> AI responded '{turn.get('response', '')}'")
                conversation_history = "\n".join(history_items)
            
            # Build prompt dynamically with context
            prompt = f"""
                You are an AI receptionist assistant having a phone conversation. 
                {WorkflowState.agent_prompt}.

                Current Context:
                - Caller Type: {state.caller_type.value}
                - Turn Number: {state.turn_count}
                - Caller Speech: "{state.speech_text}"

                Previous Conversation:
                {conversation_history}

                Response:
            """
            
            # Configure model with specific parameters for consistency
            model = genai.GenerativeModel(
                self.model_name,
                generation_config={
                    "temperature": 0.7,
                    "max_output_tokens": 150,
                    "stop_sequences": ["\n\n", "."]
                }
            )
            
            response = model.generate_content(prompt)
            
            result = response.text.strip() if response and response.text else None
            
            # Update conversation history
            if not hasattr(state, 'conversation_history'):
                state.conversation_history = []
            
            state.conversation_history.append({
                'user_input': state.speech_text,
                'response': result,
                'intent': result,
                'turn': state.turn_count
            })
            
            # Keep only last 5 turns to prevent context overflow
            if len(state.conversation_history) > 5:
                state.conversation_history = state.conversation_history[-5:]

            return result

        except Exception as e:
            print(f"⚠️ Gemini failed: {e}")
            return None

    def _get_fallback_response(self, state: WorkflowState) -> str:
        """Fallback template when Gemini fails."""
        caller_templates = self.templates.get(state.caller_type, {})
        return caller_templates.get(state.intent, "Hello! How can I help you today?")

    def _determine_next_action(self, state: WorkflowState) -> str:
        """Decide what the workflow should do next."""
        if state.intent == Intent.SERVICE_REQUEST:
            return "schedule_service"
        elif state.intent == Intent.STATUS_CHECK:
            return "provide_status"
        elif state.intent == Intent.COMPLAINT:
            return "escalate_to_human"
        elif state.intent == Intent.PROFILE_UPDATE:
            return "authenticate_profile_update"
        elif state.intent == Intent.SCHEDULE_UPDATE:
            # Check if we have time details to confirm appointment
            if hasattr(state, 'time_details') and state.time_details:
                return "confirm_appointment"
            return "reschedule_job"
        else:
            return "continue_conversation"