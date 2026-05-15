import asyncio
import logging
import datetime
from datetime import timezone, timedelta
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
        # Use UTC-3 explicitly (Argentina/Buenos Aires timezone)
        tz = timezone(timedelta(hours=-3))
        now = datetime.datetime.now(tz).time()
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


def _detect_call_to_action(post_text: str, cta_keywords_str: str):
    """Multi-language CTA detection: checks if post asks readers to comment a specific keyword.
    Supports patterns in Spanish, English, and Portuguese."""
    if not cta_keywords_str or not cta_keywords_str.strip():
        return None  # No keywords configured
        
    keywords = [k.strip().lower() for k in cta_keywords_str.split(",") if k.strip()]
    if not keywords:
        return None
        
    text_lower = post_text.lower()
    for kw in keywords:
        # Patterns in Spanish, English, Portuguese
        patterns = [
            f"comenta\\s+{re.escape(kw)}",      # spanish
            f"escribe\\s+{re.escape(kw)}",       # spanish
            f"dime\\s+{re.escape(kw)}",           # spanish
            f"pon\\s+{re.escape(kw)}",            # spanish
            f"comment\\s+{re.escape(kw)}",        # english
            f"type\\s+{re.escape(kw)}",           # english
            f"say\\s+{re.escape(kw)}",            # english
            f"write\\s+{re.escape(kw)}",          # english
            f"comente\\s+{re.escape(kw)}",        # portuguese
            f"digite\\s+{re.escape(kw)}",          # portuguese
            f"keyword\\s*[:\\-]?\\s*{re.escape(kw)}",  # universal
            f"palabra\\s*[:\\-]?\\s*{re.escape(kw)}",   # universal
        ]
        if any(re.search(p, text_lower) for p in patterns):
            return kw
    return None

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

        # 2. Get scraper accounts (any active account with session) with fallback
        scraper_accounts = db.query(models.Account).filter(
            models.Account.status == "active",
            models.Account.storage_state.isnot(None)
        ).all()

        if not scraper_accounts:
            logger.warning("AutoPilot: No active accounts available for scraping.")
            return

        # Try scraper accounts in order until one succeeds (via BrowserPool)
        from orchestrator import browser_pool
        page = None
        used_account_id = None
        for scraper_account in scraper_accounts:
            try:
                inst = await browser_pool.acquire(
                    scraper_account.id,
                    scraper_account.storage_state,
                    scraper_account.proxy_url,
                    timeout=15.0
                )
                # Test session validity with a quick navigation
                await inst.page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=15000)
                if "/feed" in inst.page.url or "/in/" in inst.page.url:
                    logger.info(f"AutoPilot: Using scraper account {scraper_account.email} (via BrowserPool)")
                    page = inst.page
                    used_account_id = scraper_account.id
                    break
                # Not logged in, release and try next
                logger.warning(f"AutoPilot: Account {scraper_account.email} session invalid, trying next...")
                await browser_pool.release(scraper_account.id)
            except Exception as e:
                logger.warning(f"AutoPilot: Account {scraper_account.email} failed: {e}, trying next...")
                try:
                    await browser_pool.release(scraper_account.id)
                except Exception:
                    pass

        if page is None:
            logger.error("AutoPilot: All scraper accounts failed. Aborting cycle.")
            return

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
                    
                # 4. New post! Check CTA (keyword presence + multi-language call-to-action)
                logger.info(f"AutoPilot: NEW POST detected: {post_url}")
                cta_matched = _check_cta(post_text, target.cta_keywords)
                detected_cmd = _detect_call_to_action(post_text, target.cta_keywords) if target.cta_keywords else None
                
                if cta_matched:
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
                        # Use detected CTA keyword as comment text if found, otherwise fall back to comment_base
                        comment_text = detected_cmd if detected_cmd else (target.comment_base or "Excelente.")
                        tasks = [
                            {"type": "reaction", "payload": {"url": post_url, "reaction_type": "LIKE"}},
                            {"type": "comment", "payload": {"url": post_url, "text": comment_text}}
                        ]
                        
                        # We create missions in DB
                        mission_ids = []
                        for aid in account_ids:
                            db_mission = models.Mission(account_id=aid, tasks=tasks, source="autopilot")
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

        if used_account_id:
            await browser_pool.release(used_account_id)
            
    except Exception as e:
        logger.error(f"AutoPilot: Critical error in cycle: {e}")
        traceback.print_exc()
    finally:
        db.close()
        logger.info("AutoPilot: Cycle complete.")

async def _trigger_smart_mission(db, target, post_url, trigger_account_id):
    """Analyzes a post and triggers a smart mission for all accounts."""
    # 1. We need to get the post text to detect CTAs
    # (Since we have a scraper account active in run_notifications_cycle, we can use it)
    # But for now, let's just trigger a mission that includes a 'smart_comment' task
    
    # Get all active accounts
    all_accounts = db.query(models.Account).filter(
        models.Account.status == "active",
        models.Account.storage_state.isnot(None)
    ).all()
    account_ids = [a.id for a in all_accounts]
    
    if not account_ids:
        return

    # We'll use a new task type 'smart_comment' which the MissionRunner will handle
    tasks = [
        {"type": "reaction", "payload": {"url": post_url, "reaction_type": "LIKE"}},
        {"type": "smart_comment", "payload": {"url": post_url, "target_profile_id": target.id}}
    ]
    
    mission_ids = []
    for aid in account_ids:
        db_mission = models.Mission(account_id=aid, tasks=tasks, source="autopilot_notification", target_profile_id=target.id)
        db.add(db_mission)
        db.commit()
        db.refresh(db_mission)
        mission_ids.append(db_mission.id)
        
    from main import _run_bulk_with_delays
    asyncio.create_task(
        _run_bulk_with_delays(
            account_ids=account_ids,
            tasks=tasks,
            comment_mode="ai",
            delay_min=30,
            delay_max=300,
            mission_ids=mission_ids
        )
    )


async def run_notifications_cycle():
    """Cycle to check notifications for all active accounts."""
    logger.info("Notifications: Starting cycle...")
    db = SessionLocal()
    try:
        active_accounts = db.query(models.Account).filter(
            models.Account.status == "active",
            models.Account.storage_state.isnot(None)
        ).all()

        if not active_accounts:
            logger.info("Notifications: No active accounts found.")
            return

        from orchestrator import MissionRunner, browser_pool

        for account in active_accounts:
            try:
                logger.info(f"Notifications: Checking account {account.email}")
                runner = MissionRunner(account.storage_state, account.proxy_url)
                
                # Use BrowserPool — acquirerelease per account
                page = await browser_pool.get_page(account.id, account.storage_state, account.proxy_url)
                notifs = await runner.check_notifications(page)
                # Release immediately so the pool doesn't accumulate idle browsers
                await browser_pool.release(account.id)

                if isinstance(notifs, list):
                    for n in notifs:
                        # 1. Detect if it's a new post notification from a target profile
                        # Example text: "Fabio Robles shared a post: 'Check out this new...'"
                        target_matched = None
                        all_targets = db.query(models.TargetProfile).filter(models.TargetProfile.status == "active").all()
                        for target in all_targets:
                            # We check if the name or URL part is in the notification text
                            # (LinkedIn notification text varies, but usually contains the name)
                            if target.linkedin_url.split('/')[-1] in n['link'] or any(word in n['text'] for word in target.linkedin_url.split('/')[-1].split('-')):
                                target_matched = target
                                break
                        
                        if target_matched and "shared a post" in n['text'].lower() and n['unread']:
                            # Check if already processed (dedup against autopilot cycle)
                            already_processed = db.query(models.ProcessedPost).filter(
                                models.ProcessedPost.post_url == n['link']
                            ).first()
                            if already_processed:
                                logger.info(f"Notifications: Post {n['link']} already processed, skipping.")
                            else:
                                logger.info(f"Notifications: NEW POST detected via notification from {target_matched.linkedin_url}")
                                # Mark as processed immediately (dup prevention)
                                db.add(models.ProcessedPost(
                                    target_profile_id=target_matched.id,
                                    post_url=n['link']
                                ))
                                db.commit()
                                # Trigger immediate action
                                await _trigger_smart_mission(db, target_matched, n['link'], account.id)

                        # 2. Save notification to DB
                        existing = db.query(models.Notification).filter(
                            models.Notification.account_id == account.id,
                            models.Notification.text == n['text']
                        ).first()
                        
                        if not existing:
                            new_n = models.Notification(
                                account_id=account.id,
                                text=n['text'],
                                link=n['link'],
                                time_ago=n['time'],
                                is_unread=1 if n['unread'] else 0
                            )
                            db.add(new_n)
                    db.commit()

            except Exception as e:
                logger.error(f"Notifications: Error for {account.email}: {e}")

    except Exception as e:
        logger.error(f"Notifications: Critical error: {e}")
    finally:
        db.close()
        logger.info("Notifications: Cycle complete.")

# ── Scheduler state (readable from API) ──
_MAX_CONSECUTIVE_FAILURES = 3
_COOLDOWN_CYCLES = 4  # 4 cycles * 30min = 120min cooldown

_scheduler_state = {
    "status": "starting",       # "starting" | "running" | "cooldown" | "error"
    "failures": 0,
    "cooldown_remaining": 0,
    "last_autopilot_cycle": None,   # iso timestamp
    "last_notifications_cycle": None, # iso timestamp
    "last_error": None,
    "started_at": None,              # iso timestamp
    "targets_active": 0,
    "total_cycles_run": 0,
}

def get_scheduler_status(db_session=None):
    """Returns a snapshot of the scheduler state for the API."""
    s = dict(_scheduler_state)
    s["started_at"] = _scheduler_state["started_at"]
    # Compute active targets count if we have a db session
    if db_session is not None:
        try:
            s["targets_active"] = db_session.query(models.TargetProfile).filter(
                models.TargetProfile.status == "active"
            ).count()
        except Exception:
            pass
    return s


async def start_autopilot_scheduler():
    """Background loop to run the autopilot cycle and notifications periodically"""
    logger.info("AutoPilot Scheduler: Started! First cycle in 10 seconds...")
    _scheduler_state["started_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    _scheduler_state["status"] = "running"
    await asyncio.sleep(10) # Wait a bit before starting
    
    count = 0
    cooldown_counter = 0
    while True:
        try:
            # Circuit breaker: skip cycle if too many consecutive failures
            if _scheduler_state["failures"] >= _MAX_CONSECUTIVE_FAILURES and cooldown_counter < _COOLDOWN_CYCLES:
                remaining = (_COOLDOWN_CYCLES - cooldown_counter) * 30
                _scheduler_state["status"] = "cooldown"
                _scheduler_state["cooldown_remaining"] = remaining
                logger.warning(
                    f"AutoPilot Circuit Breaker: Skipping cycle "
                    f"({_scheduler_state['failures']} consecutive failures, "
                    f"cooldown {cooldown_counter}/{_COOLDOWN_CYCLES} = ~{remaining}min remaining)"
                )
                cooldown_counter += 1
                await asyncio.sleep(1800)
                continue
            
            if cooldown_counter >= _COOLDOWN_CYCLES:
                logger.info("AutoPilot Circuit Breaker: Cooldown ended, resetting failure counter.")
                _scheduler_state["failures"] = 0
                cooldown_counter = 0
                _scheduler_state["status"] = "running"
                _scheduler_state["cooldown_remaining"] = 0

            if count % 2 == 0:  # Every 2 cycles = every ~60 min
                logger.info("AutoPilot: Running autopilot cycle (scanning posts)...")
                _scheduler_state["status"] = "running"
                await run_autopilot_cycle()
                _scheduler_state["last_autopilot_cycle"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
            
            logger.info("AutoPilot: Running notifications cycle...")
            await run_notifications_cycle()
            _scheduler_state["last_notifications_cycle"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
            
            # Success — reset circuit breaker
            _scheduler_state["failures"] = 0
            _scheduler_state["last_error"] = None
            count += 1
            _scheduler_state["total_cycles_run"] = count
        except Exception as e:
            _scheduler_state["failures"] += 1
            _scheduler_state["status"] = "error"
            _scheduler_state["last_error"] = str(e)[:200]
            logger.error(f"AutoPilot Scheduler error ({_scheduler_state['failures']}/{_MAX_CONSECUTIVE_FAILURES}): {e}")
            traceback.print_exc()
        
        await asyncio.sleep(1800)  # 30 minutes between cycles
