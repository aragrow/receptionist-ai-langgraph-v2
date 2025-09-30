# ==================== src/agents/base_agent.py ====================
"""
Base agent class for all L1, L2, and L3 agents.
Provides common functionality for LLM interaction, JSON parsing, and confidence calculation.
"""

import json
import time
import logging
import os
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Union, Type
from datetime import datetime

import google.generativeai as genai
from pydantic import BaseModel, ValidationError
from dotenv import load_dotenv

from config.routing_config import (
    ConfidenceThresholds,
    CONFIDENCE_THRESHOLDS,
    should_clarify,
    should_escalate_to_human
)

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Abstract base class for all agents (L1, L2, L3).
    Provides common LLM interaction and utility methods.
    """
    
    def __init__(
        self,
        agent_name: str,
        agent_tier: str,
        model_name: Optional[str],
        temperature: float = 0.3,
        max_tokens: int = 500
    ):
        """
        Initialize base agent.
        
        Args:
            agent_name: Name of the agent (e.g., "receptionist_l1")
            agent_tier: Tier level (L1, L2, L3)
            model_name: Google Gemini model name
            temperature: LLM temperature (0.0-1.0, lower = more deterministic)
            max_tokens: Maximum output tokens
        """
        self.agent_name = agent_name
        self.agent_tier = agent_tier
        if model_name is None:
            model_name = os.getenv("LLM__MODEL_NAME", "gemini-1.5-flash-123")
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        # Initialize Gemini model
        self.model = genai.GenerativeModel(
            model_name=model_name,
            generation_config={
                "temperature": temperature,
                "max_output_tokens": max_tokens,
            }
        )
        
        logger.info(f"Initialized {agent_name} (tier: {agent_tier})")
    
    # ============ Abstract Methods (must be implemented by subclasses) ============
    
    @abstractmethod
    async def process(self, state: Any) -> Any:
        """
        Main processing method that each agent must implement.
        
        Args:
            state: WorkflowState object
        
        Returns:
            Updated state or agent-specific output model
        """
        pass
    
    @abstractmethod
    def build_prompt(self, state: Any) -> str:
        """
        Build the LLM prompt for this agent.
        
        Args:
            state: WorkflowState object
        
        Returns:
            Formatted prompt string
        """
        pass
    
    # ============ LLM Interaction Methods ============
    
    async def call_llm(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        retry_count: int = 3
    ) -> str:
        """
        Call the LLM with retry logic.
        
        Args:
            prompt: User prompt
            system_instruction: System instruction (optional)
            retry_count: Number of retries on failure
        
        Returns:
            LLM response text
        
        Raises:
            Exception: If all retries fail
        """
        start_time = time.time()
        
        for attempt in range(retry_count):
            try:
                # Build full prompt with system instruction if provided
                if system_instruction:
                    full_prompt = f"{system_instruction}\n\n{prompt}"
                else:
                    full_prompt = prompt
                
                logger.debug(f"{self.agent_name} - Calling LLM (attempt {attempt + 1}/{retry_count})")
                
                response = self.model.generate_content(full_prompt)
                
                if not response or not response.text:
                    raise ValueError("Empty response from LLM")
                
                elapsed_ms = (time.time() - start_time) * 1000
                logger.info(f"{self.agent_name} - LLM call successful ({elapsed_ms:.0f}ms)")
                
                return response.text.strip()
            
            except Exception as e:
                logger.warning(f"{self.agent_name} - LLM call failed (attempt {attempt + 1}): {e}")
                
                if attempt == retry_count - 1:
                    logger.error(f"{self.agent_name} - All LLM retry attempts failed")
                    raise Exception(f"LLM call failed after {retry_count} attempts: {str(e)}")
                
                # Exponential backoff
                wait_time = 2 ** attempt
                logger.debug(f"Waiting {wait_time}s before retry...")
                await self._async_sleep(wait_time)
        
        raise Exception("LLM call failed - should not reach here")
    
    async def _async_sleep(self, seconds: float):
        """Async sleep helper."""
        import asyncio
        await asyncio.sleep(seconds)
    
    # ============ JSON Parsing Methods ============
    
    def parse_llm_json(
        self,
        llm_response: str,
        output_model: Type[BaseModel],
        strict: bool = True
    ) -> Union[BaseModel, Dict[str, Any]]:
        """
        Parse LLM JSON response into a Pydantic model.
        
        Args:
            llm_response: Raw LLM response text
            output_model: Pydantic model class to parse into
            strict: If True, raise on validation errors; if False, return best-effort dict
        
        Returns:
            Parsed Pydantic model or dictionary
        
        Raises:
            ValidationError: If strict=True and parsing fails
        """
        try:
            # Extract JSON from response (handle markdown code blocks)
            json_str = self._extract_json_from_response(llm_response)
            
            # Parse JSON
            json_data = json.loads(json_str)
            
            # Validate with Pydantic model
            parsed_model = output_model(**json_data)
            
            logger.debug(f"{self.agent_name} - Successfully parsed JSON into {output_model.__name__}")
            return parsed_model
        
        except json.JSONDecodeError as e:
            logger.error(f"{self.agent_name} - JSON parsing failed: {e}")
            logger.debug(f"Raw response: {llm_response[:500]}")
            
            if strict:
                raise ValidationError(f"Invalid JSON from LLM: {str(e)}")
            
            # Return raw text wrapped in dict
            return {"raw_response": llm_response, "parse_error": str(e)}
        
        except ValidationError as e:
            logger.error(f"{self.agent_name} - Pydantic validation failed: {e}")
            
            if strict:
                raise
            
            # Return raw JSON data even if validation failed
            try:
                return json.loads(self._extract_json_from_response(llm_response))
            except:
                return {"raw_response": llm_response, "validation_error": str(e)}
    
    def _extract_json_from_response(self, response: str) -> str:
        """
        Extract JSON from LLM response, handling markdown code blocks.
        
        Args:
            response: Raw LLM response
        
        Returns:
            Extracted JSON string
        """
        response = response.strip()
        
        # Remove markdown code blocks
        if response.startswith("```json"):
            response = response[7:]  # Remove ```json
        elif response.startswith("```"):
            response = response[3:]  # Remove ```
        
        if response.endswith("```"):
            response = response[:-3]
        
        response = response.strip()
        
        # If still not JSON, try to find JSON object in text
        if not response.startswith("{") and not response.startswith("["):
            # Look for JSON object
            start_idx = response.find("{")
            end_idx = response.rfind("}")
            
            if start_idx != -1 and end_idx != -1:
                response = response[start_idx:end_idx + 1]
        
        return response
    
    # ============ Confidence Calculation Methods ============
    
    def calculate_confidence(
        self,
        llm_response: str,
        parsed_data: Optional[Dict[str, Any]] = None,
        keyword_matches: Optional[int] = None,
        total_keywords: Optional[int] = None
    ) -> float:
        """
        Calculate confidence score for agent output.
        
        Args:
            llm_response: Raw LLM response
            parsed_data: Parsed JSON data (optional)
            keyword_matches: Number of matched keywords (optional)
            total_keywords: Total expected keywords (optional)
        
        Returns:
            Confidence score (0.0 to 1.0)
        """
        confidence = 0.5  # Default medium confidence
        
        # Factor 1: LLM explicitly provided confidence
        if parsed_data and "confidence" in parsed_data:
            confidence = float(parsed_data["confidence"])
            logger.debug(f"{self.agent_name} - Using LLM-provided confidence: {confidence}")
            return min(max(confidence, 0.0), 1.0)  # Clamp to [0, 1]
        
        # Factor 2: Response completeness
        response_length = len(llm_response)
        if response_length > 200:
            confidence += 0.1  # Detailed response = higher confidence
        elif response_length < 50:
            confidence -= 0.1  # Very short response = lower confidence
        
        # Factor 3: JSON structure quality
        if parsed_data:
            # More fields filled = higher confidence
            filled_fields = sum(1 for v in parsed_data.values() if v not in [None, "", [], {}])
            total_fields = len(parsed_data)
            
            if total_fields > 0:
                field_ratio = filled_fields / total_fields
                confidence += (field_ratio - 0.5) * 0.2  # Adjust by up to ±0.2
        
        # Factor 4: Keyword matching (if provided)
        if keyword_matches is not None and total_keywords is not None and total_keywords > 0:
            keyword_ratio = keyword_matches / total_keywords
            confidence += (keyword_ratio - 0.5) * 0.3  # Adjust by up to ±0.3
        
        # Clamp to [0, 1]
        confidence = min(max(confidence, 0.0), 1.0)
        
        logger.debug(f"{self.agent_name} - Calculated confidence: {confidence:.2f}")
        return confidence
    
    def adjust_confidence_with_context(
        self,
        base_confidence: float,
        has_caller_profile: bool = False,
        conversation_turn: int = 1,
        has_previous_context: bool = False
    ) -> float:
        """
        Adjust confidence based on contextual factors.
        
        Args:
            base_confidence: Initial confidence score
            has_caller_profile: Whether we have caller profile info
            conversation_turn: Which turn in conversation (1-indexed)
            has_previous_context: Whether we have previous conversation context
        
        Returns:
            Adjusted confidence score
        """
        adjusted = base_confidence
        
        # Boost confidence if we have caller profile
        if has_caller_profile:
            adjusted += 0.05
        
        # Boost confidence for multi-turn conversations (more context)
        if conversation_turn > 1:
            adjusted += min(0.1, 0.02 * (conversation_turn - 1))
        
        # Boost if we have previous context
        if has_previous_context:
            adjusted += 0.05
        
        # Clamp to [0, 1]
        return min(max(adjusted, 0.0), 1.0)
    
    # ============ Routing Decision Helpers ============
    
    def should_clarify(self, confidence: float) -> bool:
        """
        Check if clarification should be requested.
        
        Args:
            confidence: Confidence score
        
        Returns:
            True if clarification needed
        """
        return should_clarify(confidence, tier=self.agent_tier)
    
    def should_escalate(
        self,
        confidence: float,
        clarification_count: int = 0,
        user_text: Optional[str] = None
    ) -> tuple[bool, Optional[str]]:
        """
        Check if human escalation is needed.
        
        Args:
            confidence: Confidence score
            clarification_count: Number of clarifications attempted
            user_text: User's message text
        
        Returns:
            Tuple of (should_escalate, reason)
        """
        should_esc, reason = should_escalate_to_human(
            confidence,
            clarification_count,
            user_text
        )
        return should_esc, reason.value if reason else None
    
    # ============ Logging and Debugging ============
    
    def log_agent_execution(
        self,
        state: Any,
        output: Any,
        processing_time_ms: float,
        success: bool = True,
        error: Optional[str] = None
    ):
        """
        Log agent execution details.
        
        Args:
            state: Input state
            output: Agent output
            processing_time_ms: Processing time in milliseconds
            success: Whether execution succeeded
            error: Error message if failed
        """
        log_data = {
            "agent": self.agent_name,
            "tier": self.agent_tier,
            "processing_time_ms": processing_time_ms,
            "success": success,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if error:
            log_data["error"] = error
            logger.error(f"{self.agent_name} - Execution failed: {error}")
        else:
            logger.info(f"{self.agent_name} - Execution completed ({processing_time_ms:.0f}ms)")
        
        # Log to structured logging system (if available)
        # This could be sent to ELK, Datadog, etc.
        logger.debug(f"Agent execution: {json.dumps(log_data)}")
    
    # ============ Utility Methods ============
    
    def sanitize_input(self, text: str, max_length: int = 2000) -> str:
        """
        Sanitize user input for safety.
        
        Args:
            text: Input text
            max_length: Maximum allowed length
        
        Returns:
            Sanitized text
        """
        if not text:
            return ""
        
        # Limit length
        text = text[:max_length]
        
        # Remove potentially harmful characters (basic sanitization)
        # Note: More robust sanitization may be needed for production
        text = text.strip()
        
        return text
    
    def format_timestamp(self, dt: Optional[datetime] = None) -> str:
        """
        Format timestamp for logging.
        
        Args:
            dt: Datetime object (defaults to now)
        
        Returns:
            Formatted timestamp string
        """
        if dt is None:
            dt = datetime.utcnow()
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    
    def extract_keywords(self, text: str, keywords: list[str]) -> tuple[int, list[str]]:
        """
        Extract and count matching keywords from text.
        
        Args:
            text: Input text
            keywords: List of keywords to match
        
        Returns:
            Tuple of (match_count, matched_keywords)
        """
        text_lower = text.lower()
        matched = [kw for kw in keywords if kw.lower() in text_lower]
        return len(matched), matched
    
    # ============ Error Handling ============
    
    def handle_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Handle and log errors consistently.
        
        Args:
            error: Exception that occurred
            context: Additional context for debugging
        
        Returns:
            Error information dictionary
        """
        error_info = {
            "agent": self.agent_name,
            "tier": self.agent_tier,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "timestamp": self.format_timestamp()
        }
        
        if context:
            error_info["context"] = context
        
        logger.error(
            f"{self.agent_name} - Error occurred: {error_info['error_type']} - {error_info['error_message']}"
        )
        
        return error_info
    
    # ============ Template Methods (can be overridden) ============
    
    def preprocess_state(self, state: Any) -> Any:
        """
        Preprocess state before main processing (can be overridden).
        
        Args:
            state: Input state
        
        Returns:
            Preprocessed state
        """
        return state
    
    def postprocess_output(self, output: Any, state: Any) -> Any:
        """
        Postprocess output after main processing (can be overridden).
        
        Args:
            output: Agent output
            state: Input state
        
        Returns:
            Postprocessed output
        """
        return output