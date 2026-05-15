import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from orchestrator import BrowserPool, BrowserInstance, LogStreamer

@pytest.mark.asyncio
async def test_browser_pool_init():
    pool = BrowserPool(max_instances=3, instance_ttl=300)
    assert pool.max_instances == 3
    assert pool.instance_ttl == 300
    metrics = pool.get_metrics()
    assert metrics["active_instances"] == 0
    assert metrics["max_instances"] == 3
    assert metrics["available_slots"] == 3

@pytest.mark.asyncio
async def test_cleanup_stale():
    pool = BrowserPool(max_instances=5, instance_ttl=0)
    mock1 = AsyncMock(spec=BrowserInstance)
    mock1.is_open = True
    mock1.last_used = 0
    mock1.close = AsyncMock()
    pool._instances[1] = mock1
    pool._semaphore = asyncio.Semaphore(5)
    await pool._cleanup_stale()
    assert 1 not in pool._instances
    mock1.close.assert_called_once()

@pytest.mark.asyncio
async def test_log_streamer_global():
    streamer = LogStreamer()
    queue = streamer.subscribe(99)
    streamer.push(99, {"message": "test"})
    msg = await queue.get()
    assert msg["message"] == "test"
