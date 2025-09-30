# ==================== src/nodes/intent_analyzer.py ====================
"""Intent analyzer node with Google Gemini integration."""
import logging
import json
# Get a logger instance for your module
logger = logging.getLogger(__name__)
# Set the logging level (e.g., INFO, DEBUG, WARNING, ERROR, CRITICAL)
logger.setLevel(logging.INFO)

import re
import os
import json
import google.generativeai as genai
from src.models.workflow_models import WorkflowState, Intent
from dotenv import load_dotenv
from src.services.database_service import DatabaseService

load_dotenv()

class IntentAnalyzer:
    """Node for analyzing caller intent using Google Gemini."""
    
    def __init__(self, db_service: DatabaseService):
        self.db_service = db_service

        # Configure Google AI with API key
        api_key = os.getenv("LLM__GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("API_KEY environment variable is required")
        
        genai.configure(api_key=api_key)

        self.model_name = os.getenv("LLM__MODEL_NAME")
        if not self.model_name:
            raise ValueError("MODEL environment variable is required")
        
    async def _create_intent_prompt(self, state: WorkflowState) -> WorkflowState:
        print("""Create a structured prompt for Gemini to analyze intent.""")
        agent_prompt = await self.db_service.find_agent_action_prompt('receptionist','intent_analysis',1)
        
        # Build prompt dynamically with context
        prompt = f"""
            You are an AI receptionist assistant having a phone conversation. 
            {agent_prompt}.

            Current Context:
            - Caller Type: {state.caller_type}
            - Caller Speech: {state.speech_text}
        """

        state.agent_prompt = prompt
        return state
    
    async def _analyze_with_gemini(self, state: WorkflowState) -> WorkflowState:
        print("""Use Google Gemini to analyze intent.""")
        try:
            workflow_state = await self._create_intent_prompt(state)

            # Configure Gemini model
            model = genai.GenerativeModel(self.model_name)
            
            # Generate response
            response = model.generate_content(workflow_state.agent_prompt)
            
            # Parse response
            intent_value = response.text.strip().lower()
            workflow_state.intent = intent_value
            print(f"Intent: {intent_value}")
            workflow_state.error_message = None
            
        except Exception as e:
            print(f"⚠️ Gemini intent analysis failed: {e}")
            workflow_state.error_message = f"⚠️ Gemini intent analysis failed: {e}""
            workflow_state.intent = "Customer Service"`
            
        return workflow_state

    async def __call__(self, state: WorkflowState) -> WorkflowState:
        workflow_state = state
        """Analyze caller intent from speech using Gemini + regex fallback."""
        if not state.speech_text:
            workflow_state.intent = "Customer Service"
            return state
        
        try:
            # Primary: Use Gemini for intent analysis
            workflow_state = await self._analyze_with_gemini(state)
            
        except Exception as e:
            # Fallback: Use regex patterns
            workflow_state.error_message = f"Intent analysis error: {str(e)}"
            workflow_state.intent = self._fallback_regex_analysis(state.speech_text)
        
        return workflow_state