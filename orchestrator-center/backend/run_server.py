import asyncio
import sys
import uvicorn

if __name__ == "__main__":
    if sys.platform == 'win32':
        # Force ProactorEventLoop on Windows
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        print("WindowsProactorEventLoopPolicy forced in run_server.py")
    
    # Run WITHOUT reload to ensure loop stability on some Windows environments
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False, loop="asyncio")
