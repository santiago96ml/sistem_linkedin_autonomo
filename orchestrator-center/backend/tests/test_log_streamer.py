import pytest
import asyncio
from orchestrator import LogStreamer

@pytest.mark.asyncio
async def test_push_and_consume():
    streamer = LogStreamer()
    queue = streamer.subscribe(1)
    
    streamer.push(1, {"message": "Test log 1"})
    streamer.push(1, {"message": "Test log 2"})
    
    msg1 = await queue.get()
    msg2 = await queue.get()
    
    assert msg1["message"] == "Test log 1"
    assert msg2["message"] == "Test log 2"

@pytest.mark.asyncio
async def test_multiple_consumers():
    streamer = LogStreamer()
    queue1 = streamer.subscribe(2)
    queue2 = streamer.subscribe(2)
    
    streamer.push(2, {"message": "Broadcast log"})
    
    msg1 = await queue1.get()
    msg2 = await queue2.get()
    
    assert msg1["message"] == "Broadcast log"
    assert msg2["message"] == "Broadcast log"

@pytest.mark.asyncio
async def test_cleanup_on_complete():
    streamer = LogStreamer()
    queue = streamer.subscribe(3)
    streamer.push(3, {"message": "Before cleanup"})
    
    streamer.unsubscribe(3)
    
    assert 3 not in streamer._queues
    
    # Push after unsubscribe should not fail but not queue it
    streamer.push(3, {"message": "After cleanup"})

@pytest.mark.asyncio
async def test_queue_overflow():
    streamer = LogStreamer()
    queue = streamer.subscribe(4)
    
    # LogStreamer should limit queue size to 1000
    for i in range(1005):
        streamer.push(4, {"message": f"Log {i}"})
        
    assert queue.qsize() <= 1000
