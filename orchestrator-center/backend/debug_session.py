"""Debug: verify if the stored session is still valid and can access LinkedIn."""
import asyncio
from playwright.async_api import async_playwright
import sqlite3
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

async def main():
    # Load storage_state from DB
    conn = sqlite3.connect("orchestrator.db")
    c = conn.cursor()
    c.execute("SELECT storage_state FROM accounts WHERE id = 2")
    row = c.fetchone()
    conn.close()
    
    if not row or not row[0]:
        print("ERROR: No storage_state found for account ID 2")
        return
    
    storage_state = json.loads(row[0]) if isinstance(row[0], str) else row[0]
    print(f"Storage state loaded: {len(json.dumps(storage_state))} bytes")
    print(f"Cookies: {len(storage_state.get('cookies', []))}")
    
    # Check for key cookies
    cookies = storage_state.get('cookies', [])
    key_cookies = ['li_at', 'JSESSIONID', 'li_mc']
    for name in key_cookies:
        found = [c for c in cookies if c.get('name') == name]
        if found:
            val = found[0].get('value', '')[:20]
            print(f"  {name}: {val}... (found)")
        else:
            print(f"  {name}: NOT FOUND")
    
    # Launch browser with the stored session and navigate to post
    POST_URL = "https://www.linkedin.com/posts/romerofabio_comenta-aprendo-y-te-lo-paso-por-privado-ugcPost-7454701416536842240--h4v"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            storage_state=storage_state,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        print(f"\nNavigating to: {POST_URL[:60]}...")
        await page.goto(POST_URL, wait_until="domcontentloaded")
        await asyncio.sleep(8)
        
        current_url = page.url
        print(f"Current URL: {current_url}")
        
        # Check if we got redirected to login
        if "login" in current_url or "authwall" in current_url:
            print("\n[!!!] SESSION EXPIRED - Redirected to login page")
            print("Need to re-authenticate")
        elif "/feed" in current_url or "linkedin.com/posts/" in current_url:
            print("\n[OK] Session appears valid - page loaded")
        
        # Take screenshot
        await page.screenshot(path="debug_session_check.png", full_page=True)
        print("Screenshot saved: debug_session_check.png")
        
        # Check page content for key elements
        content = await page.content()
        checks = [
            ("Like button", ['react-button', 'Recomendar', 'Like', 'recomendar']),
            ("Comment box", ['ql-editor', 'contenteditable', 'comment-box', 'Comentar']),
            ("Post content", ['comenta-aprendo', 'ugcPost']),
            ("Login form", ['login-form', 'session_key', '#username']),
        ]
        
        print("\nPage content analysis:")
        for name, keywords in checks:
            found = any(kw.lower() in content.lower() for kw in keywords)
            symbol = "[+]" if found else "[-]"
            print(f"  {symbol} {name}: {'FOUND' if found else 'NOT FOUND'}")
        
        # Try to find buttons
        buttons = await page.query_selector_all("button")
        print(f"\nTotal buttons on page: {len(buttons)}")
        for btn in buttons[:15]:
            aria = await btn.get_attribute("aria-label") or ""
            text = (await btn.inner_text() or "").strip()[:40]
            if aria or text:
                print(f"  button: aria='{aria}' text='{text}'")
        
        await browser.close()

asyncio.run(main())
