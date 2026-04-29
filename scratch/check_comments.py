import asyncio
from playwright.async_api import async_playwright
import sqlite3
import json

async def main():
    # Get storage state from DB
    conn = sqlite3.connect('orchestrator-center/backend/orchestrator.db')
    c = conn.cursor()
    c.execute("SELECT storage_state FROM accounts WHERE email = 'francorobles.lk@gmail.com' AND storage_state IS NOT NULL")
    row = c.fetchone()
    if not row:
        print("No storage state found for francorobles.lk@gmail.com")
        return
    
    storage_state = json.loads(row[0])
    conn.close()

    url = "https://www.linkedin.com/posts/santiagocosme_he-metido-los-3-libros-de-hormozi-dentro-share-7454787574675570689-qzkd"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(storage_state=storage_state, user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")
        page = await context.new_page()

        print("Navigating to post...")
        await page.goto(url, wait_until="domcontentloaded")
        await asyncio.sleep(5)

        # Extract comments
        print("Extracting comments...")
        comments = await page.locator(".comments-comment-item__main-content").all_inner_texts()
        
        authors = await page.locator(".comments-post-meta__name-text").all_inner_texts()

        print(f"\nFound {len(comments)} comments.")
        for i, comment in enumerate(comments):
            safe_comment = comment.encode('ascii', 'ignore').decode('ascii')
            print(f"Comment {i}: {repr(safe_comment[:200])}")

        await browser.close()

asyncio.run(main())
