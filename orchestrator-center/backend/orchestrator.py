import asyncio
from playwright.async_api import async_playwright
import logging
import json
import re
import os
import time

logger = logging.getLogger(__name__)

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

class MissionRunner:
    def __init__(self, storage_state: dict, proxy: str = None):
        self.storage_state = storage_state
        self.proxy = {"server": proxy} if proxy else None

    async def execute_mission(self, tasks: list):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                storage_state=self.storage_state,
                proxy=self.proxy,
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
            )
            page = await context.new_page()

            results = []
            for task in tasks:
                task_type = task.get("type")
                payload = task.get("payload", {})
                
                if task_type == "comment":
                    res = await self.inject_comment(page, payload.get("url"), payload.get("text"))
                    results.append({"task": task, "result": res})
                elif task_type == "reaction":
                    res = await self.inject_reaction(page, payload.get("url"), payload.get("reaction_type", "LIKE"))
                    results.append({"task": task, "result": res})
                else:
                    results.append({"task": task, "result": f"UNSUPPORTED_TASK_TYPE:{task_type}"})
                    
                # Take screenshot to prove execution
                try:
                    os.makedirs("screenshots", exist_ok=True)
                    timestamp = int(time.time())
                    screenshot_filename = f"proof_{task_type}_{timestamp}.png"
                    screenshot_path = os.path.join("screenshots", screenshot_filename)
                    await asyncio.sleep(2)  # Allow UI to settle
                    await page.screenshot(path=screenshot_path, full_page=True)
                    logger.info(f"Screenshot taken: {screenshot_path}")
                    results[-1]["screenshot"] = screenshot_filename
                except Exception as e:
                    logger.error(f"Failed to take screenshot: {e}")
                    
            await browser.close()
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
                            # Type out the comment
                            await page.keyboard.type(text, delay=30)
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
                "button.comments-comment-box__submit-button",
                "button[data-control-name='comment_submit']",
                "button.comments-comment-box__submit-button--cr",
                "form.comments-comment-texteditor button[type='submit']",
                ".comments-comment-box button.artdeco-button--primary",
                ".comments-comment-box button:not([aria-label])",
            ]
            submit_success = False

            # First try Ctrl+Enter to submit
            await page.keyboard.press("Control+Enter")
            await asyncio.sleep(2)

            # Check if editor is cleared
            try:
                text_after = await page.locator(comment_editor_selectors[0]).text_content(timeout=1000)
                if not text_after or len(text_after.strip()) == 0:
                    submit_success = True
            except Exception:
                submit_success = True  # Editor disappeared, likely success

            if not submit_success:
                # If still visible, try clicking submit button
                for selector in submit_selectors:
                    try:
                        submit_btn = page.locator(selector).first
                        if await submit_btn.is_visible(timeout=1500):
                            await submit_btn.click(force=True, timeout=5000)
                            await asyncio.sleep(2)
                            
                            # Verify again
                            try:
                                text_after2 = await page.locator(comment_editor_selectors[0]).text_content(timeout=1000)
                                if not text_after2 or len(text_after2.strip()) == 0:
                                    submit_success = True
                            except Exception:
                                submit_success = True
                                
                            if submit_success:
                                break
                    except Exception:
                        continue

            await asyncio.sleep(2)
            if not submit_success:
                return "COMMENT_SUBMIT_FAILED"
            return 200

        except Exception as e:
            logger.error(f"Comment injection error: {e}")
            return str(e)


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
            await self.page.fill("#username", self.email)
            await self.page.fill("#password", self.password)
            await self.page.click("button[type='submit']")

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
