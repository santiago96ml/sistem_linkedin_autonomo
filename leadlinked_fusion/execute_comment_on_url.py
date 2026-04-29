import sys
import os
import time
import asyncio
from playwright.async_api import async_playwright
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

USERNAME = "santiagomercadoluna26@gmail.com"
PASSWORD = "aAntiagob168"

async def system_login_final(page):
    """Intenta loguear al sistema de forma definitiva."""
    try:
        logger.info("El sistema esta forzando el acceso...")
        # Ir a la pagina principal de login
        await page.goto("https://www.linkedin.com/login", wait_until="networkidle")
        
        # Esperar y rellenar
        await page.wait_for_selector("#username", timeout=15000)
        await page.fill("#username", USERNAME)
        await page.fill("#password", PASSWORD)
        await page.click("button[type='submit']")
        
        # Esperar a que la sesion sea confirmada por la presencia de la barra de nav
        await page.wait_for_selector(".global-nav", timeout=45000)
        logger.info("Autenticacion confirmada por el sistema.")
        return True
    except Exception as e:
        logger.error(f"Fallo de autenticacion: {e}")
    return False

async def run_autonomous_protocol(url):
    async with async_playwright() as p:
        # Asegurar que la ruta sea absoluta y accesible en Windows
        user_data_dir = "C:\\Users\\merca\\.gemini\\antigravity\\linkedin_session_v19"
        if not os.path.exists(user_data_dir):
            os.makedirs(user_data_dir, exist_ok=True)

        browser = await p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )
        page = browser.pages[0]
        
        try:
            logger.info(f"Sistema iniciando en: {url}")
            
            # 1. Comprobar sesion
            await page.goto("https://www.linkedin.com/", wait_until="domcontentloaded")
            await asyncio.sleep(4)
            
            if not await page.query_selector(".global-nav"):
                logger.info("Sesion no detectada. El sistema procedera al login...")
                await system_login_final(page)
            
            # 2. Navegar al objetivo
            logger.info(f"Navegando al post objetivo: {url}")
            await page.goto(url, wait_until="domcontentloaded")
            await asyncio.sleep(8)
            
            # 3. Comentar (Accion del Sistema)
            comment = "Este analisis de Claude es sumamente util. Gracias por compartir estos avances en IA, Sebastian."
            
            # Buscar boton comentar agresivamente
            comment_selectors = [
                "button:has-text('Comentar')",
                "button[aria-label*='comentario']",
                ".comment-button",
                "button:has-text('Comment')"
            ]
            
            box_sel = ".tiptap.ProseMirror, [role='textbox']"
            if not await page.query_selector(box_sel):
                for sel in comment_selectors:
                    btn = await page.query_selector(sel)
                    if btn:
                        await btn.click()
                        await asyncio.sleep(4)
                        break
            
            box = await page.wait_for_selector(box_sel, timeout=15000)
            await box.click()
            for char in comment:
                await page.keyboard.type(char, delay=75)
            
            await asyncio.sleep(3)
            # Publicar
            submit_selectors = ["button:has-text('Publicar')", "button:has-text('Post')", ".comments-comment-box__submit-button--intent-positive"]
            for sub_sel in submit_selectors:
                submit_btn = await page.query_selector(sub_sel)
                if submit_btn:
                    await submit_btn.click()
                    logger.info("Comentario enviado.")
                    break
            
            # 4. PERSISTENCIA (35s)
            logger.info("Esperando registro en servidor (35s)...")
            await asyncio.sleep(35)
            
            # Verificacion
            await page.reload(wait_until="domcontentloaded")
            await asyncio.sleep(10)
            
            final_img = f"sistema_final_v19_{int(time.time())}.png"
            await page.screenshot(path=final_img)
            print(f"\n✅ TAREA DEL SISTEMA EXITOSA. Verificado en: {final_img}")
            
        except Exception as e:
            logger.error(f"Falla del sistema v19: {e}")
            await page.screenshot(path="falla_v19.png")
        finally:
            await browser.close()

if __name__ == "__main__":
    if len(sys.argv) < 2: print("URL?")
    else: asyncio.run(run_autonomous_protocol(sys.argv[1]))
