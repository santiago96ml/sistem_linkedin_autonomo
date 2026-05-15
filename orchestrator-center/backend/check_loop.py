import asyncio
import sys

async def check_loop():
    loop = asyncio.get_running_loop()
    print(f"Platform: {sys.platform}")
    print(f"Python Version: {sys.version}")
    print(f"Loop type: {type(loop)}")
    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable, "--version",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        print(f"Subprocess success: {stdout.decode().strip()}")
    except NotImplementedError:
        print("Subprocess FAILED: NotImplementedError")
    except Exception as e:
        print(f"Subprocess FAILED: {e}")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(check_loop())
