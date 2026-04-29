import sys
import os
import time
import json
import asyncio
import re
from playwright.async_api import async_playwright
import logging
from dotenv import load_dotenv

# Configurar rutas
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
api_path = os.path.join(project_root, "linkedin_voice_bot", "linkedin-api")
sys.path.append(api_path)

from linkedin_api.linkedin import Linkedin
from linkedin_api.client import Client

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv(os.path.join(api_path, ".env"))
USERNAME = os.getenv("LINKEDIN_USERNAME", "santiagomercadoluna26@gmail.com")
PASSWORD = os.getenv("LINKEDIN_PASSWORD", "aAntiagob168")

async def get_fresh_cookies():
    user_data_dir = os.path.join(os.environ['USERPROFILE'], ".gemini", "antigravity", "session_hybrid_v2")
    os.makedirs(user_data_dir, exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )
        page = browser.pages[0]
        
        try:
            logger.info("Sistema (Navegador) obteniendo llaves de acceso...")
            await page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded")
            
            # Login visual si es necesario
            if await page.query_selector("#username"):
                await page.fill("#username", USERNAME)
                await page.fill("#password", PASSWORD)
                await page.click("button[type='submit']")
                await page.wait_for_url("**/feed/**", timeout=45000)
            
            await asyncio.sleep(5)
            cookies = await browser.cookies()
            cookie_file = os.path.join(current_dir, "fresh_cookies.json")
            with open(cookie_file, "w") as f:
                json.dump(cookies, f)
            
            logger.info("✅ Llaves obtenidas.")
            return cookie_file
        finally:
            await browser.close()

def inject_via_api_ghost(url, text, cookie_file):
    try:
        match = re.search(r'([0-9]{19})', url)
        if not match: return False
        post_id = match.group(1)
        
        logger.info(f"Inyectando via API Fantasma (Post ID: {post_id})")
        
        # 1. Crear cliente MANUALMENTE sin autenticar
        client = Client(debug=True)
        # Inyectar cookies ANTES de cualquier peticion
        with open(cookie_file, "r") as f:
            cookies = json.load(f)
            for c in cookies:
                client.session.cookies.set(c['name'], c['value'], domain=c['domain'])
        
        # 2. Configurar la clase Linkedin con el cliente ya 'cocinado'
        api = Linkedin(USERNAME, PASSWORD)
        api.client = client # Sobreescribir con el cliente que tiene las cookies
        
        # 3. Triple intento de URN
        urn_formats = [f"urn:li:ugcPost:{post_id}", f"urn:li:activity:{post_id}", f"urn:li:share:{post_id}"]
        
        for urn in urn_formats:
            logger.info(f"Intentando inyeccion en tunel: {urn}")
            try:
                if api.post_comment(urn, text):
                    logger.info(f"✅ INYECCION EXITOSA EN {urn}")
                    return True
            except:
                continue
        
        logger.error("❌ El sistema no pudo inyectar el comentario tras agotar todos los tuneles.")
        return False
            
    except Exception as e:
        logger.error(f"Falla en el protocolo Fantasma: {e}")
        return False

async def run_protocol(url, text):
    cookie_path = await get_fresh_cookies()
    if cookie_path:
        inject_via_api_ghost(url, text, cookie_path)

if __name__ == "__main__":
    if len(sys.argv) < 2: sys.exit(1)
    asyncio.run(run_protocol(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "Test"))
