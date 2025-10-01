# ==================== src/test/test_telemetry.py ====================

import asyncio
from src.services.metrics_service import get_metrics_service
from src.services.logging_service import get_logging_service

async def test():
    # Get services
    metrics = get_metrics_service()
    logger = get_logging_service()
    
    # Record some test metrics
    metrics.record_l1_classification(
        session_id="test-001",
        intent_name="scheduling",
        confidence=0.92,
        caller_type="client",
        processing_time_ms=150.0
    )
    
    # Log something
    logger.log_l1_classification(
        session_id="test-001",
        intent="scheduling",
        confidence=0.92,
        caller_type="client",
        processing_time_ms=150.0
    )
    
    # Get dashboard
    dashboard = metrics.get_full_dashboard(time_window_hours=24)
    print("✅ Dashboard generated!")
    print(f"   L1 Classifications: {dashboard['l1_classification'].get('total_classifications', 0)}")
    
    print("\n✅ Telemetry system working!")

if __name__ == "__main__":
    asyncio.run(test())