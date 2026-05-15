import asyncio
from playwright.async_api import async_playwright
import logging
import json
import re
import os
import time
import random

logger = logging.getLogger(__name__)

class LogStreamer:
    """Manages WebSocket log streams for missions."""
    def __init__(self):
        self._queues = {} # dict[int, list[asyncio.Queue]]

    def subscribe(self, mission_id: int) -> asyncio.Queue:
        if mission_id not in self._queues:
            self._queues[mission_id] = []
        queue = asyncio.Queue()
        self._queues[mission_id].append(queue)
        return queue

    def push(self, mission_id: int, log_entry: dict):
        if mission_id in self._queues:
            for queue in self._queues[mission_id]:
                if queue.qsize() < 1000:
                    try:
                        queue.put_nowait(log_entry)
                    except asyncio.QueueFull:
                        pass

    def unsubscribe(self, mission_id: int, queue: asyncio.Queue = None):
        if mission_id in self._queues:
            if queue and queue in self._queues[mission_id]:
                self._queues[mission_id].remove(queue)
            else:
                del self._queues[mission_id]
            
            if mission_id in self._queues and not self._queues[mission_id]:
                del self._queues[mission_id]

class ModalSentry:
    """Detects and dismisses intrusive LinkedIn overlays (modals, popups, message bubbles)."""
    
    SELECTORS = [
        "button[aria-label^='Cerrar']",
        "button[aria-label^='Dismiss']",
        "button[aria-label*='no gracias']",
        "button[aria-label*='not now']",
        "button.artdeco-modal__dismiss",
        # Message bubble minimize buttons
        ".msg-overlay-bubble-header__controls button[data-control-name='overlay_tab_control_minimize_bubble']",
        # Specific 'interest-consumption-large' overlay often comes with a modal
        ".artdeco-modal",
    ]

    @staticmethod
    async def dismiss_all(page):
        """Attempts to clear the screen of any blocking elements."""
        # Special case: Message overlay (LinkedIn chat) often blocks the bottom right
        try:
            msg_bubble = page.locator(".msg-overlay-list-bubble--is-expanded").first
            if await msg_bubble.is_visible(timeout=500):
                header = page.locator(".msg-overlay-bubble-header").first
                await header.click(force=True, timeout=1000)
                await asyncio.sleep(0.5)
        except Exception:
            pass

        for selector in ModalSentry.SELECTORS:
            try:
                # If it's a modal, we try to click its specific dismiss button if found inside
                if selector == ".artdeco-modal":
                    modal = page.locator(selector).first
                    if await modal.is_visible(timeout=500):
                        dismiss = modal.locator(".artdeco-modal__dismiss").first
                        if await dismiss.is_visible(timeout=500):
                            await dismiss.click(force=True, timeout=1000)
                            await asyncio.sleep(0.5)
                        continue

                btn = page.locator(selector).first
                if await btn.is_visible(timeout=500):
                    await btn.click(force=True, timeout=1000)
                    await asyncio.sleep(0.5)
            except Exception:
                continue

class BrowserManager:
    """Manages persistent browser contexts for active accounts to allow live interaction."""
    _instances = {} # {account_id: {browser, context, page}}

    @classmethod
    async def get_page(cls, account_id, storage_state, proxy_url=None):
        if account_id in cls._instances:
            # Check if still healthy
            try:
                page = cls._instances[account_id]['page']
                if not page.is_closed():
                    return page
            except Exception:
                pass
        
        # Launch new persistent instance
        from playwright.async_api import async_playwright
        pw = await async_playwright().start()
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(storage_state=storage_state)
        page = await context.new_page()
        
        cls._instances[account_id] = {
            "pw": pw,
            "browser": browser,
            "context": context,
            "page": page
        }
        return page

    @classmethod
    async def close_all(cls):
        for data in cls._instances.values():
            await data['browser'].close()
            await data['pw'].stop()
        cls._instances = {}

class BrowserInstance:
    """Represents a managed browser instance in the pool."""
    def __init__(self, account_id: int, browser, context, page, pw):
        self.account_id = account_id
        self.browser = browser
        self.context = context
        self.page = page
        self.pw = pw
        self.acquired_at = time.time()
        self.last_used = time.time()

    async def close(self):
        try:
            if self.browser:
                await self.browser.close()
        except Exception:
            pass
        try:
            if self.pw:
                await self.pw.stop()
        except Exception:
            pass

    @property
    def is_open(self):
        try:
            return self.page is not None and not self.page.is_closed()
        except Exception:
            return False

class BrowserPool:
    """Pool of browser instances with max concurrency limit and TTL-based cleanup."""
    def __init__(self, max_instances: int = 5, instance_ttl: int = 600):
        self.max_instances = max_instances
        self.instance_ttl = instance_ttl
        self._instances: dict[int, BrowserInstance] = {}
        self._semaphore = asyncio.Semaphore(max_instances)
        self._lock = asyncio.Lock()

    async def acquire(self, account_id: int, storage_state: dict, proxy_url: str = None, timeout: float = 30.0) -> BrowserInstance:
        async with self._lock:
            instance = self._instances.get(account_id)
            if instance and instance.is_open:
                instance.last_used = time.time()
                return instance
        try:
            await asyncio.wait_for(self._semaphore.acquire(), timeout=timeout)
        except asyncio.TimeoutError:
            raise TimeoutError(f"Browser pool full after {timeout}s wait (max={self.max_instances})")
        try:
            pw = await async_playwright().start()
            proxy_cfg = {"server": proxy_url} if proxy_url else None
            browser = await pw.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
            context = await browser.new_context(storage_state=storage_state, proxy=proxy_cfg, user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
            page = await context.new_page()
            instance = BrowserInstance(account_id, browser, context, page, pw)
            async with self._lock:
                old = self._instances.get(account_id)
                if old:
                    await old.close()
                self._instances[account_id] = instance
            return instance
        except Exception:
            self._semaphore.release()
            raise

    async def release(self, account_id: int):
        async with self._lock:
            instance = self._instances.pop(account_id, None)
        if instance:
            await instance.close()
            self._semaphore.release()

    async def get_page(self, account_id: int, storage_state: dict, proxy_url: str = None):
        inst = await self.acquire(account_id, storage_state, proxy_url)
        return inst.page

    async def _cleanup_stale(self):
        now = time.time()
        async with self._lock:
            stale_ids = [aid for aid, inst in self._instances.items() if (now - inst.last_used) > self.instance_ttl or not inst.is_open]
            for aid in stale_ids:
                inst = self._instances.pop(aid)
                await inst.close()
                self._semaphore.release()

    def get_metrics(self) -> dict:
        return {
            "active_instances": len(self._instances),
            "max_instances": self.max_instances,
            "available_slots": self.max_instances - len(self._instances),
            "ttl_seconds": self.instance_ttl
        }

browser_pool = BrowserPool(max_instances=5, instance_ttl=600)
log_streamer = LogStreamer()

class MissionRunner:
    def __init__(self, storage_state: dict, proxy: str = None, account_id: int = None):
        self.storage_state = storage_state
        self.proxy = {"server": proxy} if proxy else None
        self.account_id = account_id

    async def _human_type(self, page, text):
        """Simula tipeo humano con delays erráticos y pausas."""
        for char in text:
            # Velocidad de tipeo humana (entre 50ms y 150ms por tecla)
            await page.keyboard.type(char, delay=random.randint(50, 150))
            # 5% de probabilidad de una pausa más larga (simulando pensar o cansancio)
            if random.random() < 0.05:
                await asyncio.sleep(random.uniform(0.5, 1.2))
        logger.info(f"Human-like typing finished for: {text[:20]}...")

    async def execute_mission(self, tasks: list):
        if self.account_id:
            # Use persistent browser
            page = await browser_pool.get_page(self.account_id, self.storage_state, self.proxy["server"] if self.proxy else None)
            return await self._run_on_page(page, tasks)
        else:
            # Use temporary browser
            from playwright.async_api import async_playwright
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(storage_state=self.storage_state, proxy=self.proxy)
                page = await context.new_page()
                return await self._run_on_page(page, tasks)

    async def _run_on_page(self, page, tasks):
        results = []
        for index, task in enumerate(tasks):
            task_type = task.get("type")
            payload = task.get("payload", {})
            if task_type == "comment":
                res = await self.inject_comment(page, payload.get("url"), payload.get("text"))
            elif task_type == "reaction":
                res = await self.inject_reaction(page, payload.get("url"), payload.get("reaction_type", "LIKE"))
            elif task_type == "check_notifications":
                res = await self.check_notifications(page)
            elif task_type == "smart_comment":
                res = await self.handle_smart_comment(page, payload.get("url"), payload.get("target_profile_id"))
            else:
                res = f"UNSUPPORTED_TASK_TYPE:{task_type}"
            


            results.append({"task": task, "result": res})
        return results

    async def inject_reaction(self, page, url, reaction_type="LIKE"):
        """Inject a reaction (like) on a LinkedIn post via DOM interaction."""
        try:
            # Only navigate if we aren't already on the correct post (ignoring query params if any)
            current_url = page.url
            if url.split('?')[0] not in current_url:
                await page.goto(url, wait_until="domcontentloaded")
                await asyncio.sleep(5)
                await ModalSentry.dismiss_all(page)

            # Strategy 1: Find and click the Like button directly
            like_button_selectors = [
                "button[aria-label^='Estado del botón de reacción']",
                "button.react-button__trigger",
                "button[aria-label*='Recomendar']",
                "button[aria-label*='Like']",
                "button[aria-label*='recomendar']",
                "button[aria-label*='like']",
                "button.reactions-react-button",
                "span.react-button__text",
                # Fallback: social action bar first button
                ".social-actions-bar button:first-child",
                ".feed-shared-social-action-bar button:first-child",
            ]

            for selector in like_button_selectors:
                try:
                    btn = page.locator(selector).first
                    if await btn.is_visible(timeout=2000):
                        # Check if already liked (aria-pressed="true")
                        aria_pressed = await btn.get_attribute("aria-pressed")
                        if aria_pressed == "true":
                            logger.info(f"Post already liked: {url}")
                            return "ALREADY_LIKED"
                        
                        await btn.click(force=True, timeout=5000)
                        await asyncio.sleep(2)
                        logger.info(f"Reaction '{reaction_type}' sent via selector: {selector}")
                        return 200
                except Exception:
                    continue

            # Strategy 2: Use JavaScript to find and click like button
            try:
                result = await page.evaluate("""() => {
                    // Find like/react buttons
                    const buttons = document.querySelectorAll('button');
                    for (const btn of buttons) {
                        const label = (btn.getAttribute('aria-label') || '').toLowerCase();
                        const text = (btn.textContent || '').toLowerCase().trim();
                        if (label.includes('recomendar') || label.includes('like') || 
                            text === 'recomendar' || text === 'like') {
                            if (btn.getAttribute('aria-pressed') === 'true') {
                                return 'ALREADY_LIKED';
                            }
                            btn.click();
                            return 'CLICKED';
                        }
                    }
                    return 'NOT_FOUND';
                }""")
                
                if result == "CLICKED":
                    await asyncio.sleep(2)
                    return 200
                elif result == "ALREADY_LIKED":
                    return "ALREADY_LIKED"
                else:
                    return "LIKE_BUTTON_NOT_FOUND"
            except Exception as e:
                logger.error(f"JS Like injection failed: {e}")
                return f"JS_ERROR:{str(e)[:100]}"

        except Exception as e:
            logger.error(f"Reaction injection error: {e}")
            return str(e)

    async def inject_comment(self, page, url, text):
        """Inject a comment on a LinkedIn post using Triple Vía strategy."""
        try:
            current_url = page.url
            if url.split('?')[0] not in current_url:
                await page.goto(url, wait_until="domcontentloaded")
                await asyncio.sleep(5)
                await ModalSentry.dismiss_all(page)

            # First, click the "Comment" button to open the comment box
            comment_button_selectors = [
                "button[aria-label*='Comentar']",
                "button[aria-label*='Comment']",
                "button[aria-label*='comentar']",
                "button[aria-label*='comment']",
                ".comment-button",
                ".social-actions-bar button:nth-child(2)",
            ]
            
            for selector in comment_button_selectors:
                try:
                    btn = page.locator(selector).first
                    if await btn.is_visible(timeout=2000):
                        await btn.click(force=True, timeout=5000)
                        await asyncio.sleep(2)
                        await ModalSentry.dismiss_all(page)
                        break
                except Exception:
                    continue

            # Now find the comment editor — LinkedIn uses multiple editors
            comment_editor_selectors = [
                "div[role='textbox'][aria-label='Editor de texto para crear comentarios']",
                # Tiptap editor (modern LinkedIn)
                "div.ql-editor[contenteditable='true']",
                "div[role='textbox'][contenteditable='true']",
                "div.editor-content[contenteditable='true']",
                # Legacy Quill editor
                ".ql-editor",
                # Generic contenteditable in comment area
                ".comments-comment-texteditor div[contenteditable='true']",
                ".comments-comment-box__form div[contenteditable='true']",
                # Broadest fallback
                "div[contenteditable='true'][aria-label*='comentario']",
                "div[contenteditable='true'][aria-label*='comment']",
                "div[contenteditable='true'][aria-placeholder*='comentario']",
                "div[contenteditable='true'][aria-placeholder*='Añade']",
                "div[contenteditable='true'][data-placeholder*='Añade']",
            ]

            editor_found = False
            for selector in comment_editor_selectors:
                try:
                    editor = page.locator(selector).first
                    if await editor.is_visible(timeout=3000):
                        # Force real keyboard typing so React definitely registers the state
                        try:
                            await editor.click(force=True, timeout=5000)
                            await asyncio.sleep(1)
                            # Select all and delete to clear any existing text
                            await page.keyboard.press("Control+A")
                            await page.keyboard.press("Backspace")
                            await asyncio.sleep(0.5)
                            # Type out the comment with human-like behavior
                            await self._human_type(page, text)
                        except Exception as e:
                            logger.warning(f"Typing error: {e}")
                            
                        # Hack to ensure state updates
                        await page.keyboard.press("Space")
                        await page.keyboard.press("Backspace")
                        await asyncio.sleep(1.5) # Give React time to enable the button
                        editor_found = True
                        break
                except Exception:
                    continue

            if not editor_found:
                return "COMMENT_EDITOR_NOT_FOUND"

            submit_selectors = [
                "form.comments-comment-box__form button[type='submit']",
                "button.comments-comment-box__submit-button",
                "button[data-control-name='comment_submit']",
                ".comments-comment-box__form button:has-text('Comentar')",
                ".comments-comment-box__form button:has-text('Post')",
                "button:has-text('Comentar')", # Fallback
                "button:has-text('Post')", # Fallback
            ]
            submit_success = False

            # Small pause and focus out to ensure state update
            await page.mouse.click(10, 10) 
            await asyncio.sleep(1)

            # First try Ctrl+Enter to submit
            await page.keyboard.press("Control+Enter")
            await asyncio.sleep(3)

            # Check if editor is cleared or disappeared
            submit_success = False
            try:
                # Try to find the editor again
                editors = page.locator("div[contenteditable='true']")
                count = await editors.count()
                if count == 0:
                    submit_success = True # Editor gone, likely submitted
                else:
                    # Check if the visible editor still has text
                    for i in range(count):
                        ed = editors.nth(i)
                        if await ed.is_visible():
                            val = await ed.inner_text()
                            if not val.strip():
                                submit_success = True
                                break
            except Exception:
                pass

            if not submit_success:
                logger.info("Ctrl+Enter failed, trying manual button click...")
                # If still visible, try clicking submit button
                for selector in submit_selectors:
                    try:
                        locators = page.locator(selector)
                        count = await locators.count()
                        for i in range(count):
                            submit_btn = locators.nth(i)
                            if await submit_btn.is_visible(timeout=500):
                                logger.info(f"Attempting hover and click: {selector} (index {i})")
                                await submit_btn.hover()
                                await asyncio.sleep(random.uniform(0.3, 0.8))
                                await submit_btn.click(force=True, timeout=5000)
                                await asyncio.sleep(4)
                                
                                # Double check if still there, try mouse click fallback if needed
                                editors = page.locator("div[contenteditable='true']")
                                still_has_text = False
                                ed_count = await editors.count()
                                for j in range(ed_count):
                                    ed = editors.nth(j)
                                    if await ed.is_visible():
                                        val = await ed.inner_text()
                                        if val.strip():
                                            still_has_text = True
                                
                                if still_has_text:
                                    logger.info("Button click didn't clear editor, trying JS click and Tab sequence...")
                                    try:
                                        await page.evaluate(f"document.querySelector('{selector}').click()")
                                        await asyncio.sleep(2)
                                    except Exception:
                                        pass
                                    
                                    # Focus again and try Tab-Tab-Enter
                                    await ed.focus()
                                    await page.keyboard.press("Tab")
                                    await asyncio.sleep(0.1)
                                    await page.keyboard.press("Tab")
                                    await asyncio.sleep(0.1)
                                    await page.keyboard.press("Enter")
                                    await asyncio.sleep(4)
                                
                                break # Found and clicked a visible button
                    except Exception as e:
                        logger.warning(f"Submission attempt failed for {selector}: {e}")
                        continue
                
                # Final verification
                editors = page.locator("div[contenteditable='true']")
                count = await editors.count()
                if count == 0:
                    submit_success = True
                else:
                    all_empty = True
                    for i in range(count):
                        ed = editors.nth(i)
                        if await ed.is_visible():
                            val = await ed.inner_text()
                            if val.strip():
                                all_empty = False
                    if all_empty:
                        submit_success = True

            await asyncio.sleep(2)
            if not submit_success:
                return "COMMENT_SUBMIT_FAILED"
            return 200

        except Exception as e:
            logger.error(f"Comment injection error: {e}")
            return str(e)

    async def check_notifications(self, page):
        """Scrapes the notifications page to identify recent interactions."""
        try:
            await page.goto("https://www.linkedin.com/notifications/", wait_until="domcontentloaded")
            await asyncio.sleep(5)
            await ModalSentry.dismiss_all(page)

            # Wait for the notifications list to load
            try:
                await page.wait_for_selector(".nt-card", timeout=5000)
            except Exception:
                logger.warning("No notifications found or page structure changed.")
                return []

            notifications = await page.evaluate("""() => {
                const cards = document.querySelectorAll('.nt-card');
                const results = [];
                cards.forEach((card, index) => {
                    if (index > 10) return; // Only top 10
                    const text = card.innerText || "";
                    const link = card.querySelector('a')?.href || "";
                    const time = card.querySelector('.nt-card__time-ago')?.innerText || "";
                    const isUnread = card.classList.contains('nt-card--unread');
                    
                    results.push({
                        text: text.replace(/\\n/g, ' ').trim(),
                        link,
                        time,
                        unread: isUnread
                    });
                });
                return results;
            }""")
            
            return notifications
        except Exception as e:
            logger.error(f"Error checking notifications: {e}")
            return f"ERROR: {str(e)}"

    async def handle_smart_comment(self, page, post_url, target_id):
        """Analyzes a post and injects either a CTA keyword or an AI comment."""
        try:
            # 1. Visit post and get text
            await page.goto(post_url, wait_until="domcontentloaded")
            await asyncio.sleep(5)
            await ModalSentry.dismiss_all(page)

            # Get post text
            post_text = await page.evaluate("""() => {
                const textEl = document.querySelector('.feed-shared-update-v2__description-wrapper, .update-components-text');
                return textEl ? textEl.innerText : "";
            }""")
            
            if not post_text:
                logger.warning(f"SmartComment: Could not find text for {post_url}")
                return "NO_TEXT_FOUND"

            # 2. Check for CTA Keywords
            from database import SessionLocal
            import models
            import re
            
            db = SessionLocal()
            target = db.query(models.TargetProfile).filter(models.TargetProfile.id == target_id).first()
            db.close()
            
            final_comment = None
            if target and target.cta_keywords:
                # Use shared multi-language CTA detection from autopilot
                from autopilot import _detect_call_to_action
                detected = _detect_call_to_action(post_text, target.cta_keywords)
                if detected:
                    logger.info(f"SmartComment: CTA Keyword '{detected}' detected!")
                    final_comment = detected

            # 3. If no CTA, generate AI comment
            if not final_comment:
                logger.info("SmartComment: No specific CTA detected. Generating AI response...")
                # Here we would call Muapi.ai or Wan2GP
                # For now, we use the comment_base or a placeholder
                final_comment = target.comment_base if target else "Excelente contenido."
                
            # 4. Inject the comment
            return await self.inject_comment(page, post_url, final_comment)

        except Exception as e:
            logger.error(f"SmartComment error: {e}")
            return f"ERROR: {str(e)}"


class GuidedLogin:
    def __init__(self, email, password, proxy=None):
        self.email = email
        self.password = password
        self.proxy = {"server": proxy} if proxy else None
        self.browser = None
        self.context = None
        self.page = None
        self.p = None
        self.storage_state = None  # Guardamos state para success sin 2FA

    async def _cleanup(self):
        """Cierra el browser y el playwright context de forma segura."""
        try:
            if self.browser:
                await self.browser.close()
        except Exception:
            pass
        try:
            if self.p:
                await self.p.stop()
        except Exception:
            pass
        self.browser = None
        self.context = None
        self.page = None
        self.p = None

    async def start(self):
        try:
            self.p = await async_playwright().start()
            self.browser = await self.p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"]
            )
            self.context = await self.browser.new_context(
                proxy=self.proxy,
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
            )
            self.page = await self.context.new_page()

            await self.page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded")

            # LinkedIn A/B tests between two login page versions:
            #   Classic: #username and #password exist directly in HTML
            #   React:   auto-generated IDs like :r0:, autocomplete="username"
            # We detect and handle both.
            try:
                form_found = False
                for i in range(30):  # Poll up to 15 seconds
                    has_classic_user = await self.page.evaluate("document.querySelector('#username') !== null")
                    has_classic_pw = await self.page.evaluate("document.querySelector('#password') !== null")

                    if has_classic_user and has_classic_pw:
                        form_found = "classic"
                        break

                    # React version: check for autocomplete fields
                    has_react_user = await self.page.evaluate(
                        "document.querySelector('input[autocomplete=\"username\"]') !== null"
                    )
                    has_react_pw = await self.page.evaluate(
                        "document.querySelector('input[autocomplete=\"current-password\"]') !== null"
                    )
                    if has_react_user and has_react_pw:
                        form_found = "react"
                        break

                    await asyncio.sleep(0.5)

                if not form_found:
                    raise TimeoutError("LinkedIn login form not found after 15s polling")

                await asyncio.sleep(0.5)

                if form_found == "classic":
                    await self.page.fill("#username", self.email)
                    await self.page.fill("#password", self.password)
                else:
                    # React version: fields exist but may not pass visibility checks
                    # (LinkedIn anti-bot hides them with CSS). Use force=True.
                    email_input = self.page.locator("input[autocomplete='username']").first
                    await email_input.wait_for(state="attached", timeout=5000)
                    await email_input.fill(self.email, force=True)

                    pw_input = self.page.locator("input[autocomplete='current-password']").first
                    await pw_input.wait_for(state="attached", timeout=5000)
                    await pw_input.fill(self.password, force=True)

                logger.info(f"[GuidedLogin] Credentials filled ({form_found} mode) for {self.email[:8]}...")

            except Exception as e:
                logger.warning(f"[GuidedLogin] LinkedIn login form not found. Error: {e}")
                os.makedirs("screenshots", exist_ok=True)
                await self.page.screenshot(path=f"screenshots/login_failed_{self.email}.png")
                raise e

            # Click "Sign in" — LinkedIn uses type="button" and all form
            # elements are hidden by CSS anti-bot. Use JS click to bypass.
            await self.page.wait_for_selector("button:has-text('Sign in')", state="attached", timeout=5000)
            await self.page.evaluate("""() => {
                const buttons = document.querySelectorAll('button');
                for (const btn of buttons) {
                    if (btn.textContent.trim() === 'Sign in') {
                        btn.click();
                        return true;
                    }
                }
                return false;
            }""")
            logger.info("[GuidedLogin] Sign in button clicked via JS")

            await asyncio.sleep(5)

            current_url = self.page.url
            logger.info(f"[GuidedLogin] Redirect tras login: {current_url}")

            # Éxito directo sin 2FA
            if "/feed" in current_url or "/in/" in current_url:
                self.storage_state = await self.context.storage_state()
                await self._cleanup()
                return "success"

            # Requiere verificación 2FA / challenge
            if "checkpoint" in current_url or "challenge" in current_url:
                # Detectar tipo de 2FA y posibles captchas
                content = await self.page.content()
                content_lower = content.lower()
                
                if "security verification" in content_lower or "verificación de seguridad" in content_lower or "captcha" in content_lower:
                    await self._cleanup()
                    return "needs_captcha"
                
                if "authenticator app" in content_lower or "aplicación de autenticación" in content_lower:
                    return "needs_2fa_app"
                    
                if "email" in content_lower or "correo" in content_lower:
                    dest = "unknown_email"
                    match = re.search(r'([a-zA-Z0-9*._-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', content)
                    if match:
                        dest = match.group(1)
                    return f"needs_2fa_email:{dest}"
                    
                if "sms" in content_lower or "mensaje de texto" in content_lower:
                    return "needs_2fa_sms"
                
                # NO cerramos — el usuario debe enviar el código
                return "2fa_required"

            # Login fallido (contraseña incorrecta, etc.)
            await self._cleanup()
            return "failed"

        except Exception as e:
            logger.error(f"[GuidedLogin.start] Error: {e}")
            await self._cleanup()
            raise

    async def submit_code(self, code):
        try:
            # LinkedIn puede usar diferentes selectores para el PIN
            pin_selectors = [
                "input[name='pin']",
                "input[id='input__email_verification_pin']",
                "input[autocomplete='one-time-code']"
            ]
            pin_filled = False
            for sel in pin_selectors:
                try:
                    await self.page.wait_for_selector(sel, timeout=3000)
                    await self.page.fill(sel, code)
                    pin_filled = True
                    break
                except Exception:
                    continue

            if not pin_filled:
                logger.error("[GuidedLogin] No se encontró el campo PIN")
                await self._cleanup()
                return None

            # Intentar diferentes botones de submit
            submit_selectors = [
                "#email-pin-submit-button",
                "button[type='submit']",
                "button[data-litms-control-urn]"
            ]
            for sel in submit_selectors:
                try:
                    if await self.page.is_visible(sel):
                        await self.page.click(sel)
                        break
                except Exception:
                    continue

            await asyncio.sleep(5)

            current_url = self.page.url
            if "/feed" in current_url or "/in/" in current_url:
                state = await self.context.storage_state()
                await self._cleanup()
                return state

            logger.warning(f"[GuidedLogin] 2FA no completó el login. URL actual: {current_url}")
        except Exception as e:
            logger.error(f"[GuidedLogin.submit_code] Error: {e}")

        await self._cleanup()
        return None
