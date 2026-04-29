import asyncio
import logging
import datetime
import traceback
import json
from playwright.async_api import async_playwright
import re

from database import SessionLocal
import models

logger = logging.getLogger(__name__)

async def _scrape_latest_post(page, profile_url: str):
    """
    Visits the recent-activity/all/ page of a profile and extracts the latest post URL and text.
    Returns {"url": str, "text": str} or None if not found.
    """
    # Make sure we go to the recent activity page
    base_url = profile_url.strip().rstrip("/")
    if "recent-activity" not in base_url:
        activity_url = f"{base_url}/recent-activity/all/"
    else:
        activity_url = base_url

    logger.info(f"AutoPilot: Visiting {activity_url}")
    await page.goto(activity_url, wait_until="domcontentloaded")
    await asyncio.sleep(5)  # Wait for posts to load

    # LinkedIn feed posts usually have a standard structure
    # We look for the first post container
    post_selector = "div.feed-shared-update-v2"
    
    try:
        # Wait up to 10 seconds for at least one post
        await page.wait_for_selector(post_selector, timeout=10000)
    except Exception:
        logger.warning(f"AutoPilot: No posts found on {activity_url}")
        return None

    posts = await page.locator(post_selector).all()
    if not posts:
        return None

    # Get the very first (latest) post
    first_post = posts[0]

    # Try to extract the post URL (usually from the "copy link to post" or the timestamp link)
    # The safest way is to find a link that contains "/posts/"
    # Alternative: check the dropdown menu for copy link
    post_url = None
    links = await first_post.locator("a[href*='/posts/']").all()
    for link in links:
        href = await link.get_attribute("href")
        if href and "/posts/" in href:
            post_url = href.split("?")[0] # clean up tracking params
            # Ensure absolute URL
            if post_url.startswith("/"):
                post_url = "https://www.linkedin.com" + post_url
            break

    # Extract text content
    post_text = ""
    try:
        # The main text is usually inside a container with class containing "update-components-text" or similar
        text_element = first_post.locator(".feed-shared-update-v2__description-wrapper, .update-components-text")
        if await text_element.count() > 0:
            post_text = await text_element.first.inner_text()
    except Exception as e:
        logger.warning(f"AutoPilot: Failed to extract text: {e}")

    if not post_url:
        logger.warning(f"AutoPilot: Found a post but could not extract URL on {activity_url}")
        return None

    return {"url": post_url, "text": post_text}

def _check_schedule(start_time_str, end_time_str):
    """Checks if current time in UTC-3 is within schedule (format HH:MM)"""
    try:
        # Assuming server is UTC, convert to local conceptually or just use UTC
        # For simplicity, let's just use server's current time
        now = datetime.datetime.now().time()
        start = datetime.datetime.strptime(start_time_str, "%H:%M").time()
        end = datetime.datetime.strptime(end_time_str, "%H:%M").time()
        
        if start <= end:
            return start <= now <= end
        else: # crosses midnight
            return start <= now or now <= end
    except Exception:
        return True # Default to active if invalid format

def _check_cta(post_text: str, cta_keywords_str: str):
    """Checks if any of the comma-separated keywords are in the text"""
    if not cta_keywords_str or not cta_keywords_str.strip():
        return True # No keywords = always trigger
        
    keywords = [k.strip().lower() for k in cta_keywords_str.split(",") if k.strip()]
    if not keywords:
        return True
        
    text_lower = post_text.lower()
    for kw in keywords:
        # Use regex for word boundary to avoid partial matches
        pattern = r"\b" + re.escape(kw) + r"\b"
        if re.search(pattern, text_lower):
            return True
            
    return False

async def run_autopilot_cycle():
    """Main cycle for AutoPilot, meant to be run periodically."""
    logger.info("AutoPilot: Starting cycle...")
    db = SessionLocal()
    try:
        # 1. Get targets that are active and within schedule
        all_targets = db.query(models.TargetProfile).filter(models.TargetProfile.status == "active").all()
        active_targets = [t for t in all_targets if _check_schedule(t.schedule_start, t.schedule_end)]
        
        if not active_targets:
            logger.info("AutoPilot: No active targets within schedule window.")
            return

        # 2. Get a scraper account (any active account with session)
        scraper_account = db.query(models.Account).filter(
            models.Account.status == "active",
            models.Account.storage_state.isnot(None)
        ).first()

        if not scraper_account:
            logger.warning("AutoPilot: No active accounts available for scraping.")
            return

        # Prepare to scrape
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                storage_state=scraper_account.storage_state,
                proxy={"server": scraper_account.proxy_url} if scraper_account.proxy_url else None,
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
            )
            page = await context.new_page()

            for target in active_targets:
                try:
                    logger.info(f"AutoPilot: Checking target {target.linkedin_url}")
                    post_data = await _scrape_latest_post(page, target.linkedin_url)
                    
                    if not post_data:
                        continue
                        
                    post_url = post_data["url"]
                    post_text = post_data["text"]
                    
                    # 3. Check if processed
                    already_processed = db.query(models.ProcessedPost).filter(
                        models.ProcessedPost.post_url == post_url,
                        models.ProcessedPost.target_profile_id == target.id
                    ).first()
                    
                    if already_processed:
                        logger.info(f"AutoPilot: Post {post_url} already processed.")
                        continue
                        
                    # 4. New post! Check CTA
                    logger.info(f"AutoPilot: NEW POST detected: {post_url}")
                    if _check_cta(post_text, target.cta_keywords):
                        logger.info("AutoPilot: CTA matches! Triggering bulk mission.")
                        
                        # Create ProcessedPost record immediately to prevent duplicates on next run
                        new_processed = models.ProcessedPost(
                            target_profile_id=target.id,
                            post_url=post_url
                        )
                        db.add(new_processed)
                        db.commit()
                        
                        # Trigger Bulk Mission
                        # Get all active accounts
                        all_accounts = db.query(models.Account).filter(
                            models.Account.status == "active",
                            models.Account.storage_state.isnot(None)
                        ).all()
                        account_ids = [a.id for a in all_accounts]
                        
                        if account_ids:
                            tasks = [
                                {"type": "reaction", "payload": {"url": post_url, "reaction_type": "LIKE"}},
                                {"type": "comment", "payload": {"url": post_url, "text": target.comment_base or "Excelente."}}
                            ]
                            
                            # We create missions in DB
                            mission_ids = []
                            for aid in account_ids:
                                db_mission = models.Mission(account_id=aid, tasks=tasks)
                                db.add(db_mission)
                                db.commit()
                                db.refresh(db_mission)
                                mission_ids.append(db_mission.id)
                                
                            # Fire background task for bulk execution
                            from main import _run_bulk_with_delays
                            asyncio.create_task(
                                _run_bulk_with_delays(
                                    account_ids=account_ids,
                                    tasks=tasks,
                                    comment_mode="ai", # Default to AI for autopilot
                                    delay_min=30,
                                    delay_max=120,
                                    mission_ids=mission_ids
                                )
                            )
                    else:
                        logger.info("AutoPilot: No CTA match in text. Ignoring.")
                        # Should we mark it as processed anyway so we don't check it again? Yes.
                        new_processed = models.ProcessedPost(
                            target_profile_id=target.id,
                            post_url=post_url
                        )
                        db.add(new_processed)
                        db.commit()

                except Exception as e:
                    logger.error(f"AutoPilot: Error processing target {target.linkedin_url}: {e}")
                    traceback.print_exc()

            await browser.close()
            
    except Exception as e:
        logger.error(f"AutoPilot: Critical error in cycle: {e}")
        traceback.print_exc()
    finally:
        db.close()
        logger.info("AutoPilot: Cycle complete.")

async def start_autopilot_scheduler():
    """Background loop to run the autopilot cycle periodically"""
    await asyncio.sleep(10) # Wait a bit before starting
    while True:
        try:
            await run_autopilot_cycle()
        except Exception as e:
            logger.error(f"AutoPilot Scheduler error: {e}")
        
        # Wait 1 hour (3600 seconds) between cycles
        await asyncio.sleep(3600)
