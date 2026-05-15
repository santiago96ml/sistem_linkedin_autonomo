"""Debug: test login and capture post-login state."""
import asyncio
import os

async def test():
    from playwright.async_api import async_playwright
    
    p = await async_playwright().start()
    browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    )
    page = await context.new_page()

    await page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded", timeout=20000)
    
    # Find form
    for _ in range(20):
        has_user = await page.evaluate("document.querySelector('#username') !== null")
        has_react = await page.evaluate("document.querySelector('input[autocomplete=\"username\"]') !== null")
        if has_user or has_react:
            break
        await asyncio.sleep(0.5)
    
    # Fill
    if await page.evaluate("document.querySelector('#username') !== null"):
        print("Filling classic form...")
        await page.fill("#username", "santimene1@gmail.com")
        await page.fill("#password", "Elsoda12.arg")
    else:
        print("Filling React form...")
        await page.locator("input[autocomplete='username']").first.fill("santimene1@gmail.com", force=True)
        await page.locator("input[autocomplete='current-password']").first.fill("Elsoda12.arg", force=True)
    
    print("Clicking Sign in...")
    btn = page.locator("button:has-text('Sign in')").first
    await btn.click()
    
    await asyncio.sleep(8)
    
    # Check post-login state
    url = page.url
    title = await page.title()
    print(f"\nPost-login URL: {url}")
    print(f"Title: {title}")
    
    # Check for common failure indicators
    content = await page.content()
    if "checkpoint" in url or "challenge" in url:
        print("CHECKPOINT/CHALLENGE page detected!")
    elif "/feed" in url:
        print("SUCCESS! Logged in to feed!")
    elif "password" in content.lower() and "incorrect" in content.lower():
        print("INCORRECT PASSWORD page")
    elif "authwall" in url:
        print("AUTHWALL - login wall")
    else:
        print("UNKNOWN STATE")
        # Take screenshot
        os.makedirs("screenshots", exist_ok=True)
        await page.screenshot(path="screenshots/login_result.png", full_page=True)
        print("Screenshot saved to screenshots/login_result.png")
    
    await browser.close()
    await p.stop()

asyncio.run(test())
