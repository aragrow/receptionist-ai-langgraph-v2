# ==================== src/services/prompt_management_service.py ====================

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import random
from src.models.database_models import PromptVersion, PromptPerformance, MisclassifiedIntent
from src.services.database_service import DatabaseService
from src.utilities.logger import get_logger

logger = get_logger(__name__)

class PromptManagementService:
    """Manage prompt versions, A/B testing, and performance tracking"""
    
    def __init__(self, db_service: DatabaseService):
        self.db = db_service
        self.ab_test_config: Dict[str, Any] = {}
    
    async def create_prompt_version(
        self,
        agent_name: str,
        action_name: str,
        prompt_text: str,
        created_by: str,
        notes: str = ""
    ) -> PromptVersion:
        """Create a new prompt version"""
        
        # Get current max version number
        existing_versions = await self.db.find_many(
            "prompt_versions",
            {"agent_name": agent_name, "action_name": action_name}
        )
        
        version_number = max(
            [v.get("version_number", 0) for v in existing_versions],
            default=0
        ) + 1
        
        version = PromptVersion(
            agent_name=agent_name,
            action_name=action_name,
            prompt_text=prompt_text,
            version_number=version_number,
            created_by=created_by,
            notes=notes,
            is_active=False  # Don't activate immediately
        )
        
        await self.db.insert_one("prompt_versions", version.model_dump())
        logger.info(f"Created prompt version {version_number} for {agent_name}/{action_name}")
        
        return version
    
    async def activate_prompt_version(
        self,
        version_id: str,
        deactivate_others: bool = True
    ) -> bool:
        """Activate a specific prompt version"""
        
        version = await self.db.find_one("prompt_versions", {"version_id": version_id})
        if not version:
            logger.error(f"Prompt version {version_id} not found")
            return False
        
        # Deactivate other versions if requested
        if deactivate_others:
            await self.db.update_many(
                "prompt_versions",
                {
                    "agent_name": version["agent_name"],
                    "action_name": version["action_name"],
                    "is_active": True
                },
                {"$set": {"is_active": False}}
            )
        
        # Activate this version
        await self.db.update_one(
            "prompt_versions",
            {"version_id": version_id},
            {"$set": {"is_active": True}}
        )
        
        logger.info(f"Activated prompt version {version['version_number']} for {version['agent_name']}")
        return True
    
    async def get_active_prompt(
        self,
        agent_name: str,
        action_name: str,
        ab_test_enabled: bool = True
    ) -> Optional[str]:
        """Get active prompt, with A/B testing support"""
        
        # Check if A/B test is running
        test_key = f"{agent_name}:{action_name}"
        if ab_test_enabled and test_key in self.ab_test_config:
            return await self._get_ab_test_prompt(test_key)
        
        # Get single active version
        version = await self.db.find_one(
            "prompt_versions",
            {
                "agent_name": agent_name,
                "action_name": action_name,
                "is_active": True
            }
        )
        
        return version["prompt_text"] if version else None
    
    async def setup_ab_test(
        self,
        agent_name: str,
        action_name: str,
        version_a_id: str,
        version_b_id: str,
        traffic_split: float = 0.5,
        duration_days: int = 7,
        min_sample_size: int = 100
    ):
        """Setup A/B test between two prompt versions"""
        
        test_key = f"{agent_name}:{action_name}"
        
        self.ab_test_config[test_key] = {
            "version_a_id": version_a_id,
            "version_b_id": version_b_id,
            "traffic_split": traffic_split,
            "start_time": datetime.now(datetime.UTC),
            "end_time": datetime.now(datetime.UTC) + timedelta(days=duration_days),
            "min_sample_size": min_sample_size,
            "active": True
        }
        
        logger.info(f"Started A/B test for {test_key}: {version_a_id} vs {version_b_id}")
    
    async def _get_ab_test_prompt(self, test_key: str) -> str:
        """Select prompt version based on A/B test configuration"""
        
        config = self.ab_test_config[test_key]
        
        # Check if test has ended
        if datetime.now(datetime.UTC) > config["end_time"]:
            await self._finalize_ab_test(test_key)
            return await self.get_active_prompt(
                *test_key.split(":"),
                ab_test_enabled=False
            )
        
        # Random selection based on traffic split
        if random.random() < config["traffic_split"]:
            version_id = config["version_a_id"]
        else:
            version_id = config["version_b_id"]
        
        version = await self.db.find_one("prompt_versions", {"version_id": version_id})
        return version["prompt_text"] if version else None
    
    async def _finalize_ab_test(self, test_key: str):
        """Finalize A/B test and activate winning version"""
        
        config = self.ab_test_config[test_key]
        
        # Get performance metrics for both versions
        perf_a = await self._get_version_performance(config["version_a_id"])
        perf_b = await self._get_version_performance(config["version_b_id"])
        
        # Determine winner based on success rate (you can customize this)
        winner_id = (
            config["version_a_id"]
            if perf_a.get("success_rate", 0) >= perf_b.get("success_rate", 0)
            else config["version_b_id"]
        )
        
        # Activate winner
        await self.activate_prompt_version(winner_id)
        
        # Mark test as inactive
        config["active"] = False
        
        logger.info(f"A/B test completed for {test_key}. Winner: {winner_id}")
        logger.info(f"Version A: {perf_a}, Version B: {perf_b}")
    
    async def _get_version_performance(self, version_id: str) -> Dict[str, float]:
        """Get aggregated performance metrics for a version"""
        
        metrics = await self.db.find_many(
            "prompt_performance",
            {"version_id": version_id}
        )
        
        if not metrics:
            return {}
        
        # Calculate averages
        total_samples = sum(m.get("sample_size", 0) for m in metrics)
        
        avg_metrics = {
            "success_rate": sum(
                m.get("success_rate", 0) * m.get("sample_size", 0)
                for m in metrics
            ) / total_samples if total_samples > 0 else 0,
            "avg_confidence": sum(
                m.get("avg_confidence", 0) * m.get("sample_size", 0)
                for m in metrics
            ) / total_samples if total_samples > 0 else 0,
            "escalation_rate": sum(
                m.get("escalation_rate", 0) * m.get("sample_size", 0)
                for m in metrics
            ) / total_samples if total_samples > 0 else 0,
            "sample_size": total_samples
        }
        
        return avg_metrics
    
    async def record_misclassification(
        self,
        session_id: str,
        user_message: str,
        predicted_intent: str,
        predicted_confidence: float,
        actual_intent: str,
        agent_name: str,
        prompt_version_id: str,
        routing_path: List[str],
        context: Dict[str, Any] = None
    ):
        """Record a misclassified intent for later review"""
        
        misclass = MisclassifiedIntent(
            session_id=session_id,
            user_message=user_message,
            predicted_intent=predicted_intent,
            predicted_confidence=predicted_confidence,
            actual_intent=actual_intent,
            agent_name=agent_name,
            prompt_version_id=prompt_version_id,
            routing_path=routing_path,
            context=context or {}
        )
        
        await self.db.insert_one("misclassified_intents", misclass.model_dump())
        logger.warning(
            f"Recorded misclassification: {predicted_intent} -> {actual_intent} "
            f"(confidence: {predicted_confidence})"
        )
    
    async def get_misclassifications(
        self,
        agent_name: Optional[str] = None,
        reviewed: bool = False,
        limit: int = 100
    ) -> List[MisclassifiedIntent]:
        """Get misclassified intents for review"""
        
        query = {"reviewed": reviewed}
        if agent_name:
            query["agent_name"] = agent_name
        
        results = await self.db.find_many(
            "misclassified_intents",
            query,
            limit=limit,
            sort=[("timestamp", -1)]
        )
        
        return [MisclassifiedIntent(**r) for r in results]
    
    async def record_performance_metrics(
        self,
        version_id: str,
        agent_name: str,
        metrics: Dict[str, float],
        sample_size: int
    ):
        """Record performance metrics for a prompt version"""
        
        perf = PromptPerformance(
            version_id=version_id,
            agent_name=agent_name,
            sample_size=sample_size,
            **metrics
        )
        
        await self.db.insert_one("prompt_performance", perf.model_dump())