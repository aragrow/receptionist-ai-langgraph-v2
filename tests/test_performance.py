# ============================== tests/test_performance.py ==============================
"""
Performance and load tests for the 3-tier routing system
Tests throughput, latency, and resource usage under load
"""
import pytest
import asyncio
import time
from datetime import datetime, UTC
from unittest.mock import patch, Mock
from statistics import mean, median, stdev
from src.workflow.ai_receptionist_workflow import AIReceptionistWorkflow
from src.services.session_service import SessionService


@pytest.fixture
def performance_workflow():
    """Create workflow optimized for performance testing"""
    with patch('src.services.llm_service.LLMService') as mock_llm, \
         patch('src.actions.booking_actions.BookingService') as mock_booking:
        
        # Configure fast mock responses
        mock_llm.return_value.generate_json.return_value = {
            "intent": "scheduling",
            "confidence": 0.90,
            "caller_type": "client"
        }
        
        mock_booking.return_value.create_booking.return_value = {
            "success": True,
            "booking_id": "BOOK-PERF-TEST"
        }
        
        workflow = AIReceptionistWorkflow()
        yield workflow


class TestL1Performance:
    """Test L1 agent performance characteristics"""
    
    @pytest.mark.asyncio
    async def test_l1_classification_latency(self, performance_workflow):
        """Test L1 classification completes within acceptable time"""
        latencies = []
        num_requests = 50
        
        for i in range(num_requests):
            start_time = time.perf_counter()
            
            result = await performance_workflow.run(
                f"I need a cleaning service - request {i}",
                user_id=f"perf-user-{i}"
            )
            
            end_time = time.perf_counter()
            latency_ms = (end_time - start_time) * 1000
            latencies.append(latency_ms)
        
        # Assert performance metrics
        avg_latency = mean(latencies)
        p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]
        p99_latency = sorted(latencies)[int(len(latencies) * 0.99)]
        
        print(f"\nL1 Performance Metrics:")
        print(f"  Average latency: {avg_latency:.2f}ms")
        print(f"  Median latency: {median(latencies):.2f}ms")
        print(f"  P95 latency: {p95_latency:.2f}ms")
        print(f"  P99 latency: {p99_latency:.2f}ms")
        print(f"  Std dev: {stdev(latencies):.2f}ms")
        
        # L1 should be very fast - under 1 second average
        assert avg_latency < 1000, f"L1 average latency {avg_latency}ms exceeds 1000ms"
        assert p95_latency < 2000, f"L1 P95 latency {p95_latency}ms exceeds 2000ms"
    
    @pytest.mark.asyncio
    async def test_l1_throughput(self, performance_workflow):
        """Test L1 can handle multiple concurrent requests"""
        num_concurrent = 20
        
        async def single_request(request_id):
            start = time.perf_counter()
            result = await performance_workflow.run(
                f"Booking request {request_id}",
                user_id=f"concurrent-{request_id}"
            )
            elapsed = time.perf_counter() - start
            return elapsed, result.success
        
        # Execute concurrent requests
        start_time = time.perf_counter()
        tasks = [single_request(i) for i in range(num_concurrent)]
        results = await asyncio.gather(*tasks)
        total_time = time.perf_counter() - start_time
        
        # Calculate throughput
        successful = sum(1 for _, success in results if success)
        throughput = num_concurrent / total_time
        
        print(f"\nL1 Throughput Test:")
        print(f"  Concurrent requests: {num_concurrent}")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Successful: {successful}/{num_concurrent}")
        print(f"  Throughput: {throughput:.2f} req/s")
        
        assert successful >= num_concurrent * 0.95, "Less than 95% success rate"
        assert throughput > 5, f"Throughput {throughput:.2f} req/s too low"


class TestEndToEndPerformance:
    """Test full L1->L2->L3 flow performance"""
    
    @pytest.mark.asyncio
    async def test_complete_flow_latency(self, performance_workflow):
        """Test complete booking flow latency"""
        latencies = []
        num_requests = 30
        
        with patch('src.services.llm_service.LLMService') as mock_llm:
            # Configure complete flow mocks
            mock_llm.return_value.generate_json.side_effect = lambda *args: {
                "intent": "scheduling",
                "confidence": 0.92,
                "caller_type": "client",
                "refined_intent": "book_home_cleaning",
                "entities": {
                    "address": "123 Test St",
                    "preferred_date": "2025-10-20T10:00:00-05:00"
                },
                "required_slots": [],
                "suggested_l3_agent": "SalesAgentL3"
            }
            
            for i in range(num_requests):
                start_time = time.perf_counter()
                
                result = await performance_workflow.run(
                    "Book cleaning at 123 Test St on Oct 20",
                    user_id=f"e2e-user-{i}"
                )
                
                end_time = time.perf_counter()
                latency_ms = (end_time - start_time) * 1000
                latencies.append(latency_ms)
        
        avg_latency = mean(latencies)
        p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]
        
        print(f"\nEnd-to-End Performance:")
        print(f"  Average latency: {avg_latency:.2f}ms")
        print(f"  P95 latency: {p95_latency:.2f}ms")
        
        # Full flow should complete in reasonable time
        assert avg_latency < 3000, f"E2E average latency {avg_latency}ms exceeds 3000ms"
        assert p95_latency < 5000, f"E2E P95 latency {p95_latency}ms exceeds 5000ms"
    
    @pytest.mark.asyncio
    async def test_tier_breakdown_latency(self, performance_workflow):
        """Test latency breakdown by tier"""
        with patch('src.agents.receptionist_l1.ReceptionistL1.classify') as mock_l1, \
             patch('src.agents.receptionist_l2_client.ClientReceptionistL2.process') as mock_l2, \
             patch('src.agents.l3_sales_agent.SalesAgentL3.execute') as mock_l3:
            
            # Track timing for each tier
            l1_times = []
            l2_times = []
            l3_times = []
            
            async def timed_l1(*args):
                start = time.perf_counter()
                await asyncio.sleep(0.05)  # Simulate L1 work
                l1_times.append((time.perf_counter() - start) * 1000)
                return Mock(intent_name="scheduling", confidence=0.90, routing_decision="route_to_l2")
            
            async def timed_l2(*args):
                start = time.perf_counter()
                await asyncio.sleep(0.1)  # Simulate L2 work
                l2_times.append((time.perf_counter() - start) * 1000)
                return Mock(refined_intent="book", confidence=0.92, required_slots=[], suggested_l3_agent="SalesAgentL3")
            
            async def timed_l3(*args):
                start = time.perf_counter()
                await asyncio.sleep(0.15)  # Simulate L3 work
                l3_times.append((time.perf_counter() - start) * 1000)
                return Mock(success=True, booking_id="BOOK-123")
            
            mock_l1.side_effect = timed_l1
            mock_l2.side_effect = timed_l2
            mock_l3.side_effect = timed_l3
            
            # Run multiple requests
            for i in range(20):
                await performance_workflow.run(f"Test request {i}")
            
            print(f"\nTier Latency Breakdown:")
            print(f"  L1 avg: {mean(l1_times):.2f}ms")
            print(f"  L2 avg: {mean(l2_times):.2f}ms")
            print(f"  L3 avg: {mean(l3_times):.2f}ms")
            print(f"  Total avg: {mean(l1_times) + mean(l2_times) + mean(l3_times):.2f}ms")
            
            # L1 should be fastest, L3 can be slowest (does real work)
            assert mean(l1_times) < mean(l2_times), "L1 should be faster than L2"
            assert mean(l2_times) < mean(l3_times), "L2 should be faster than L3"


class TestSessionStoragePerformance:
    """Test session storage and retrieval performance"""
    
    @pytest.mark.asyncio
    async def test_session_save_performance(self):
        """Test session save operations are fast"""
        session_service = SessionService()
        latencies = []
        
        for i in range(100):
            from src.models.workflow_models import WorkflowState
            
            state = WorkflowState(
                session_id=f"perf-session-{i}",
                user_id=f"user-{i}",
                caller_type="client",
                current_tier="L1",
                messages=[
                    {"role": "user", "text": f"Message {j}", "timestamp": datetime.now(UTC).isoformat()}
                    for j in range(10)  # 10 messages
                ],
                entities={"key1": "value1", "key2": "value2"},
                required_slots=["slot1", "slot2"]
            )
            
            start_time = time.perf_counter()
            await session_service.save_state(state)
            end_time = time.perf_counter()
            
            latency_ms = (end_time - start_time) * 1000
            latencies.append(latency_ms)
        
        avg_latency = mean(latencies)
        p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]
        
        print(f"\nSession Save Performance:")
        print(f"  Average: {avg_latency:.2f}ms")
        print(f"  P95: {p95_latency:.2f}ms")
        
        # Session saves should be very fast
        assert avg_latency < 50, f"Session save avg {avg_latency}ms exceeds 50ms"
        assert p95_latency < 100, f"Session save P95 {p95_latency}ms exceeds 100ms"
    
    @pytest.mark.asyncio
    async def test_session_load_performance(self):
        """Test session load operations are fast"""
        session_service = SessionService()
        
        # First, create sessions
        session_ids = []
        for i in range(50):
            from src.models.workflow_models import WorkflowState
            
            state = WorkflowState(
                session_id=f"load-test-{i}",
                user_id=f"user-{i}",
                caller_type="client",
                current_tier="L2",
                messages=[],
                entities={},
                required_slots=[]
            )
            await session_service.save_state(state)
            session_ids.append(state.session_id)
        
        # Now test loading performance
        latencies = []
        for session_id in session_ids:
            start_time = time.perf_counter()
            state = await session_service.load_state(session_id)
            end_time = time.perf_counter()
            
            latency_ms = (end_time - start_time) * 1000
            latencies.append(latency_ms)
        
        avg_latency = mean(latencies)
        
        print(f"\nSession Load Performance:")
        print(f"  Average: {avg_latency:.2f}ms")
        
        assert avg_latency < 50, f"Session load avg {avg_latency}ms exceeds 50ms"


class TestConcurrentSessionsLoad:
    """Test system under concurrent session load"""
    
    @pytest.mark.asyncio
    async def test_100_concurrent_sessions(self, performance_workflow):
        """Test handling 100 concurrent active sessions"""
        num_sessions = 100
        
        async def simulate_session(session_id):
            """Simulate a complete user session"""
            try:
                # Initial request
                result1 = await performance_workflow.run(
                    f"I need a cleaning - session {session_id}",
                    user_id=f"concurrent-user-{session_id}"
                )
                
                # Follow-up (if needed)
                if result1.requires_clarification:
                    result2 = await performance_workflow.continue_conversation(
                        result1.session_id,
                        "123 Test St on Oct 20"
                    )
                    return result2.success
                
                return result1.success
            except Exception as e:
                print(f"Session {session_id} failed: {e}")
                return False
        
        # Run concurrent sessions
        start_time = time.perf_counter()
        tasks = [simulate_session(i) for i in range(num_sessions)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.perf_counter() - start_time
        
        # Analyze results
        successful = sum(1 for r in results if r is True)
        failed = sum(1 for r in results if isinstance(r, Exception))
        
        print(f"\nConcurrent Sessions Load Test:")
        print(f"  Total sessions: {num_sessions}")
        print(f"  Successful: {successful}")
        print(f"  Failed: {failed}")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Throughput: {num_sessions / total_time:.2f} sessions/s")
        
        # Should handle most sessions successfully
        success_rate = successful / num_sessions
        assert success_rate >= 0.90, f"Success rate {success_rate:.2%} below 90%"
        assert total_time < 30, f"Took {total_time:.2f}s, should be under 30s"
    
    @pytest.mark.asyncio
    async def test_sustained_load(self, performance_workflow):
        """Test system under sustained load over time"""
        duration_seconds = 10
        requests_per_second = 5
        
        results = []
        start_time = time.perf_counter()
        
        async def sustained_requests():
            request_count = 0
            while time.perf_counter() - start_time < duration_seconds:
                # Send batch of requests
                batch_tasks = [
                    performance_workflow.run(
                        f"Request {request_count + i}",
                        user_id=f"sustained-{request_count + i}"
                    )
                    for i in range(requests_per_second)
                ]
                
                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                results.extend(batch_results)
                request_count += requests_per_second
                
                # Wait for next second
                await asyncio.sleep(1)
        
        await sustained_requests()
        total_time = time.perf_counter() - start_time
        
        # Analyze sustained load
        successful = sum(1 for r in results if hasattr(r, 'success') and r.success)
        total_requests = len(results)
        
        print(f"\nSustained Load Test:")
        print(f"  Duration: {total_time:.2f}s")
        print(f"  Total requests: {total_requests}")
        print(f"  Successful: {successful}")
        print(f"  Success rate: {successful/total_requests:.2%}")
        print(f"  Avg throughput: {total_requests/total_time:.2f} req/s")
        
        assert successful / total_requests >= 0.90, "Success rate below 90%"


class TestMemoryUsage:
    """Test memory usage under load"""
    
    @pytest.mark.asyncio
    async def test_session_memory_leak(self):
        """Test that sessions don't leak memory"""
        import gc
        import sys
        
        session_service = SessionService()
        
        # Measure initial memory
        gc.collect()
        initial_objects = len(gc.get_objects())
        
        # Create and destroy many sessions
        for i in range(100):
            from src.models.workflow_models import WorkflowState
            
            state = WorkflowState(
                session_id=f"memory-test-{i}",
                user_id=f"user-{i}",
                caller_type="client",
                current_tier="L1",
                messages=[{"role": "user", "text": "test"}],
                entities={},
                required_slots=[]
            )
            
            await session_service.save_state(state)
            
            # Clean up every 10 sessions
            if i % 10 == 0:
                gc.collect()
        
        # Measure final memory
        gc.collect()
        final_objects = len(gc.get_objects())
        
        object_growth = final_objects - initial_objects
        growth_rate = object_growth / 100  # Per session
        
        print(f"\nMemory Usage Test:")
        print(f"  Initial objects: {initial_objects}")
        print(f"  Final objects: {final_objects}")
        print(f"  Object growth: {object_growth}")
        print(f"  Growth per session: {growth_rate:.2f}")
        
        # Growth should be reasonable (< 100 objects per session)
        assert growth_rate < 100, f"Memory growth {growth_rate:.2f} objects/session too high"


class TestDatabaseQueryPerformance:
    """Test database query performance"""
    
    @pytest.mark.asyncio
    async def test_prompt_retrieval_speed(self):
        """Test agent prompt retrieval is fast"""
        from src.services.database_service import DatabaseService
        
        db_service = DatabaseService()
        latencies = []
        
        agent_actions = [
            ("receptionist_l1", "classify"),
            ("receptionist_l2_client", "extract_slots"),
            ("sales_agent_l3", "create_booking")
        ]
        
        for _ in range(50):
            for agent_name, action_name in agent_actions:
                start_time = time.perf_counter()
                prompt = await db_service.find_agent_action_prompt(agent_name, action_name)
                end_time = time.perf_counter()
                
                latency_ms = (end_time - start_time) * 1000
                latencies.append(latency_ms)
        
        avg_latency = mean(latencies)
        
        print(f"\nPrompt Retrieval Performance:")
        print(f"  Average: {avg_latency:.2f}ms")
        print(f"  Total queries: {len(latencies)}")
        
        # Prompt retrieval should be very fast (cached)
        assert avg_latency < 20, f"Prompt retrieval avg {avg_latency}ms exceeds 20ms"


class TestRoutingPerformance:
    """Test routing decision performance"""
    
    @pytest.mark.asyncio
    async def test_routing_decision_speed(self):
        """Test routing decisions are made quickly"""
        from src.services.routing_service import RoutingService
        from src.models.workflow_models import WorkflowState
        
        routing_service = RoutingService()
        latencies = []
        
        # Test L1->L2 routing
        for i in range(100):
            state = WorkflowState(
                session_id=f"route-test-{i}",
                caller_type="client",
                intent_l1={"name": "scheduling", "confidence": 0.90},
                current_tier="L1",
                messages=[]
            )
            
            start_time = time.perf_counter()
            next_agent = routing_service.route_from_l1(state)
            end_time = time.perf_counter()
            
            latency_ms = (end_time - start_time) * 1000
            latencies.append(latency_ms)
        
        avg_latency = mean(latencies)
        
        print(f"\nRouting Decision Performance:")
        print(f"  Average: {avg_latency:.2f}ms")
        
        # Routing should be nearly instant
        assert avg_latency < 5, f"Routing avg {avg_latency}ms exceeds 5ms"


class TestScalabilityLimits:
    """Test system scalability limits"""
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_find_throughput_limit(self, performance_workflow):
        """Find maximum sustainable throughput"""
        # Start with low concurrency, increase until failure
        concurrency_levels = [10, 20, 50, 100, 200]
        results = {}
        
        for concurrency in concurrency_levels:
            async def single_request(req_id):
                try:
                    start = time.perf_counter()
                    result = await performance_workflow.run(
                        f"Request {req_id}",
                        user_id=f"scale-{req_id}"
                    )
                    elapsed = time.perf_counter() - start
                    return elapsed, result.success
                except Exception as e:
                    return None, False
            
            start_time = time.perf_counter()
            tasks = [single_request(i) for i in range(concurrency)]
            batch_results = await asyncio.gather(*tasks)
            total_time = time.perf_counter() - start_time
            
            successful = sum(1 for _, success in batch_results if success)
            success_rate = successful / concurrency
            throughput = concurrency / total_time
            avg_latency = mean([elapsed for elapsed, _ in batch_results if elapsed is not None])
            
            results[concurrency] = {
                'success_rate': success_rate,
                'throughput': throughput,
                'avg_latency': avg_latency * 1000
            }
            
            print(f"\nConcurrency {concurrency}:")
            print(f"  Success rate: {success_rate:.2%}")
            print(f"  Throughput: {throughput:.2f} req/s")
            print(f"  Avg latency: {avg_latency * 1000:.2f}ms")
            
            # Stop if success rate drops below 80%
            if success_rate < 0.80:
                print(f"\n⚠️ System degraded at concurrency {concurrency}")
                break
        
        # Find optimal operating point
        optimal = max(
            (c for c, r in results.items() if r['success_rate'] >= 0.95),
            key=lambda c: results[c]['throughput'],
            default=None
        )
        
        if optimal:
            print(f"\n✓ Optimal concurrency: {optimal}")
            print(f"  Max throughput: {results[optimal]['throughput']:.2f} req/s")


class TestPerformanceRegression:
    """Test for performance regressions"""
    
    @pytest.mark.asyncio
    async def test_baseline_performance_metrics(self, performance_workflow):
        """Establish and test against baseline metrics"""
        # Run standard test suite
        num_requests = 100
        latencies = []
        
        for i in range(num_requests):
            start_time = time.perf_counter()
            result = await performance_workflow.run(
                f"Standard request {i}",
                user_id=f"baseline-{i}"
            )
            end_time = time.perf_counter()
            latencies.append((end_time - start_time) * 1000)
        
        # Calculate metrics
        metrics = {
            'avg_latency': mean(latencies),
            'p50_latency': median(latencies),
            'p95_latency': sorted(latencies)[int(len(latencies) * 0.95)],
            'p99_latency': sorted(latencies)[int(len(latencies) * 0.99)],
            'std_dev': stdev(latencies)
        }
        
        print(f"\n📊 Performance Baseline Metrics:")
        for key, value in metrics.items():
            print(f"  {key}: {value:.2f}ms")
        
        # Define acceptable thresholds (adjust based on your baseline)
        thresholds = {
            'avg_latency': 1000,  # 1 second
            'p95_latency': 2000,  # 2 seconds
            'p99_latency': 3000   # 3 seconds
        }
        
        # Check for regressions
        for metric, threshold in thresholds.items():
            assert metrics[metric] < threshold, \
                f"Regression detected: {metric} = {metrics[metric]:.2f}ms exceeds {threshold}ms"


if __name__ == "__main__":
    # Run with: pytest test_performance.py -v -s
    # For slow tests: pytest test_performance.py -v -s -m slow
    pytest.main([__file__, "-v", "-s", "--asyncio-mode=auto"])