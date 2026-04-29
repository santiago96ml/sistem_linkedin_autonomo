import sys
import os
import time
import json
import asyncio
import re
import requests
from playwright.async_api import async_playwright
import logging
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()
USERNAME = os.getenv("LINKEDIN_USERNAME", "santiagomercadoluna26@gmail.com")
PASSWORD = os.getenv("LINKEDIN_PASSWORD", "aAntiagob168")

async def get_voyager_auth():
    user_data_dir = os.path.join(os.environ['USERPROFILE'], ".gemini", "antigravity", "voyager_v3")
    os.makedirs(user_data_dir, exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )
        page = browser.pages[0]
        
        try:
            logger.info("Sistema obteniendo autorizacion maestra...")
            await page.goto("https://www.linkedin.com/feed/", wait_until="networkidle")
            
            if await page.query_selector("#username"):
                await page.fill("#username", USERNAME)
                await page.fill("#password", PASSWORD)
                await page.click("button[type='submit']")
                await page.wait_for_url("**/feed/**", timeout=45000)
            
            cookies = await browser.cookies()
            cookie_dict = {c['name']: c['value'] for c in cookies}
            csrf_token = cookie_dict.get('JSESSIONID', '').replace('"', '')
            ua = await page.evaluate("navigator.userAgent")
            
            return cookie_dict, csrf_token, ua
        finally:
            await browser.close()

def inject_master(url, text, cookies, csrf, ua):
    # ID Maestro detectado por el sub-agente
    master_activity_id = "7453138784793161728"
    
    # Probaremos el ID maestro primero
    urns = [
        f"urn:li:activity:{master_activity_id}",
        f"urn:li:ugcPost:{master_activity_id}"
    ]
    
    for urn in urns:
        # Protocolo GraphQL (Nuevo Estándar Voyager)
        endpoint = "https://www.linkedin.com/voyager/api/graphql"
        
        headers = {
            "authority": "www.linkedin.com",
            "accept": "application/vnd.linkedin.normalized+json+2.1",
            "content-type": "application/json",
            "csrf-token": csrf,
            "origin": "https://www.linkedin.com",
            "referer": url,
            "user-agent": ua,
            "x-li-track": "eyJjbGllbnRWZXJzaW9uIjoiMTIuMC4wIiwib3NOYW1lIjoiV2luZG93cyJ9", # Base64 genérico
            "x-restli-protocol-version": "2.0.0"
        }
        
        payload = {
            "queryId": "voyagerSocialDashComments.afec6d88d7810d45548797a8dac4fb87",
            "action": "execute",
            "variables": {
                "input": {
                    "commentary": { "text": text },
                    "commentedOn": urn,
                    "socialAction": urn
                }
            }
        }
        
        try:
            logger.info(f"Inyectando via Protocolo GraphQL en {urn}...")
            res = requests.post(endpoint, json=payload, cookies=cookies, headers=headers)
            
            if res.status_code in [200, 201]:
                logger.info(f"✅ INYECCION GRAPHQL EXITOSA EN {urn}.")
                return True
            else:
                logger.warning(f"Fallo {urn} (Status {res.status_code}): {res.text}")
        except Exception as e:
            logger.error(f"Error: {e}")
            
    return False

async def run(url, text):
    cookies, csrf, ua = await get_voyager_auth()
    if cookies and csrf:
        inject_master(url, text, cookies, csrf, ua)

if __name__ == "__main__":
    if len(sys.argv) < 2: sys.exit(1)
    asyncio.run(run(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "Inyeccion Maestra"))
