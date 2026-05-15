"""Check post-login page for error messages."""
import asyncio

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
    
    await asyncio.sleep(6)
    
    # Check for error messages in the page
    error_info = await page.evaluate("""() => {
        const results = {};
        // LinkedIn error alerts
        const alerts = document.querySelectorAll('[data-test-id*=\"error\"], .alert, [role=\"alert\"]');
        results.alerts = Array.from(alerts).map(a => a.textContent.trim().slice(0, 100));
        // Any element with "error" in class or id
        const errorEls = document.querySelectorAll('[class*=\"error\" i], [id*=\"error\" i]');
        results.errorElements = Array.from(errorEls).map(e => ({
            id: e.id,
            class: (e.className || '').slice(0, 40),
            text: (e.textContent || '').trim().slice(0, 80)
        })).slice(0, 5);
        // URL params
        results.url = window.location.href;
        // Check if there's a "Please try again" or similar message
        const body = document.body.innerText;
        results.hasErrorMessage = body.includes('incorrect') || body.includes('wrong') || 
                                   body.includes('try again') || body.includes('error') ||
                                   body.includes('invalid') || body.includes('not recognized');
        // Snapshot key text around the form
        const loginSection = document.querySelector('.login-form, [class*=\"login\"], main, section');
        results.formAreaText = loginSection ? loginSection.innerText.slice(0, 500) : 'no form section found';
        return results;
    }""")
    
    import json
    print(json.dumps(error_info, indent=2, ensure_ascii=False))
    
    await browser.close()
    await p.stop()

asyncio.run(test())
