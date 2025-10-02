# ==================== src/services/model_benchmark_service.py ====================

import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import asyncio
from src.utilities.logger import get_logger

logger = get_logger(__name__)

@dataclass
class ModelConfig:
    """Configuration for an LLM model"""
    model_name: str
    provider: str  # 'openai', 'anthropic', 'local', etc.
    api_key: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 500
    cost_per_1k_tokens: float = 0.0

@dataclass
class BenchmarkResult:
    """Results from model benchmarking"""
    model_name: str
    avg_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    avg_tokens_used: float
    avg_cost_per_request: float
    accuracy: float
    success_rate: float
    total_requests: int

class ModelBenchmarkService:
    """Benchmark different LLM models for performance and cost"""
    
    def __init__(self):
        self.test_prompts: List[Dict[str, Any]] = []
        self.results: Dict[str, BenchmarkResult] = {}
    
    def add_test_case(
        self,
        user_message: str,
        expected_intent: str,
        expected_confidence_min: float = 0.7,
        context: Dict[str, Any] = None
    ):
        """Add a test case for benchmarking"""
        self.test_prompts.append({
            "user_message": user_message,
            "expected_intent": expected_intent,
            "expected_confidence_min": expected_confidence_min,
            "context": context or {}
        })
    
    async def benchmark_model(
        self,
        model_config: ModelConfig,
        agent_prompt: str,
        num_iterations: int = 100
    ) -> BenchmarkResult:
        """Benchmark a specific model configuration"""
        
        logger.info(f"Benchmarking {model_config.model_name} with {num_iterations} iterations")
        
        latencies = []
        token_counts = []
        costs = []
        correct_predictions = 0
        successful_requests = 0
        
        for i, test_case in enumerate(self.test_prompts):
            if i >= num_iterations:
                break
            
            start_time = time.time()
            
            try:
                # Make request to model
                result = await self._call_model(
                    model_config,
                    agent_prompt,
                    test_case["user_message"],
                    test_case["context"]
                )
                
                latency_ms = (time.time() - start_time) * 1000
                latencies.append(latency_ms)
                
                # Track tokens and cost
                tokens = result.get("tokens_used", 0)
                token_counts.append(tokens)
                costs.append((tokens / 1000) * model_config.cost_per_1k_tokens)
                
                # Check accuracy
                predicted_intent = result.get("intent", {}).get("name", "")
                if predicted_intent.lower() == test_case["expected_intent"].lower():
                    correct_predictions += 1
                
                successful_requests += 1
                
            except Exception as e:
                logger.error(f"Error benchmarking {model_config.model_name}: {e}")
                continue
        
        # Calculate metrics
        latencies.sort()
        result = BenchmarkResult(
            model_name=model_config.model_name,
            avg_latency_ms=sum(latencies) / len(latencies) if latencies else 0,
            p95_latency_ms=latencies[int(len(latencies) * 0.95)] if latencies else 0,
            p99_latency_ms=latencies[int(len(latencies) * 0.99)] if latencies else 0,
            avg_tokens_used=sum(token_counts) / len(token_counts) if token_counts else 0,
            avg_cost_per_request=sum(costs) / len(costs) if costs else 0,
            accuracy=correct_predictions / successful_requests if successful_requests > 0 else 0,
            success_rate=successful_requests / num_iterations,
            total_requests=num_iterations
        )
        
        self.results[model_config.model_name] = result
        
        logger.info(f"Benchmark complete for {model_config.model_name}:")
        logger.info(f"  Avg Latency: {result.avg_latency_ms:.2f}ms")
        logger.info(f"  P95 Latency: {result.p95_latency_ms:.2f}ms")
        logger.info(f"  Accuracy: {result.accuracy:.2%}")
        logger.info(f"  Avg Cost: ${result.avg_cost_per_request:.6f}")
        
        return result
    
    async def _call_model(
        self,
        model_config: ModelConfig,
        system_prompt: str,
        user_message: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Call the model API (implement based on your LLM client)"""
        # This would integrate with your actual LLM client
        # Placeholder implementation
        raise NotImplementedError("Implement based on your LLM client")
    
    async def compare_models(
        self,
        model_configs: List[ModelConfig],
        agent_prompt: str,
        num_iterations: int = 100
    ) -> Dict[str, BenchmarkResult]:
        """Compare multiple models and return results"""
        
        tasks = [
            self.benchmark_model(config, agent_prompt, num_iterations)
            for config in model_configs
        ]
        
        await asyncio.gather(*tasks)
        
        # Print comparison table
        self._print_comparison_table()
        
        return self.results
    
    def _print_comparison_table(self):
        """Print a comparison table of benchmark results"""
        
        if not self.results:
            logger.info("No results to compare")
            return
        
        print("\n" + "="*100)
        print(f"{'Model':<25} {'Latency (avg)':<15} {'P95 Latency':<15} {'Accuracy':<12} {'Cost/req':<15}")
        print("="*100)
        
        for name, result in sorted(self.results.items(), key=lambda x: x[1].avg_cost_per_request):
            print(
                f"{name:<25} "
                f"{result.avg_latency_ms:>10.2f}ms    "
                f"{result.p95_latency_ms:>10.2f}ms    "
                f"{result.accuracy:>8.1%}     "
                f"${result.avg_cost_per_request:>12.6f}"
            )
        
        print("="*100 + "\n")
    
    def get_recommendation(self) -> Optional[str]:
        """Get model recommendation based on benchmarks"""
        
        if not self.results:
            return None
        
        # Score models based on latency, accuracy, and cost
        scores = {}
        for name, result in self.results.items():
            # Normalize metrics (lower is better for latency and cost)
            latency_score = 1 / (result.avg_latency_ms + 1)
            accuracy_score = result.accuracy
            cost_score = 1 / (result.avg_cost_per_request + 0.000001)
            
            # Weighted score (adjust weights as needed)
            scores[name] = (
                0.3 * latency_score +
                0.5 * accuracy_score +
                0.2 * cost_score
            )
        
        best_model = max(scores.items(), key=lambda x: x[1])[0]
        
        logger.info(f"Recommended model: {best_model}")
        return best_model