import sys
import os
import time
import asyncio
import re
from playwright.async_api import async_playwright
import logging
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()
USERNAME = os.getenv("LINKEDIN_USERNAME", "santiagomercadoluna26@gmail.com")
PASSWORD = os.getenv("LINKEDIN_PASSWORD", "aAntiagob168")

async def run_final_injection(url, text):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        page = await context.new_page()
        
        try:
            logger.info("Sistema v11: Iniciando sesion limpia...")
            await page.goto("https://www.linkedin.com/login", timeout=60000)
            await page.fill("#username", USERNAME)
            await page.fill("#password", PASSWORD)
            await page.click("button[type='submit']")
            await page.wait_for_url("**/feed/**", timeout=60000)
            
            logger.info(f"Sistema: Accediendo al post objetivo: {url}")
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(10)
            
            content = await page.content()
            match = re.search(r'urn:li:activity:([0-9]{19})', content)
            if not match:
                logger.error("Error: ID Maestro no encontrado.")
                return
            
            urn = f"urn:li:activity:{match.group(1)}"
            logger.info(f"✅ ID Maestro detectado: {urn}")
            
            # INYECCION DUAL DE ALTA FIDELIDAD (GraphQL)
            logger.info("Sistema: Ejecutando protocolo de inyeccion dual (GraphQL)...")
            result = await page.evaluate("""
                async ({urn, comment}) => {
                    const cookieMatch = document.cookie.match(/JSESSIONID=\"?([^;\\\"]+)\"?/);
                    if (!cookieMatch) return { status: "NO_COOKIE" };
                    const csrfToken = cookieMatch[1];
                    
                    // 1. Reaccion (LIKE) - Protocolo GraphQL
                    try {
                        await fetch('/voyager/api/graphql?variables=(input:(reactionType:LIKE,threadUrn:' + encodeURIComponent(urn) + '))&queryId=voyagerSocialDashReactions.b731222600772fd42464c0fe19bd722b&action=execute', {
                            method: 'POST',
                            headers: {
                                'accept': 'application/vnd.linkedin.normalized+json+2.1',
                                'content-type': 'application/json',
                                'csrf-token': csrfToken,
                                'x-restli-protocol-version': '2.0.0'
                            }
                        });
                    } catch (e) { console.error("Fallo reaccion:", e); }

                    // 2. Comentario - Protocolo GraphQL
                    const commentRes = await fetch('/voyager/api/graphql', {
                        method: 'POST',
                        headers: {
                            'accept': 'application/vnd.linkedin.normalized+json+2.1',
                            'content-type': 'application/json',
                            'csrf-token': csrfToken,
                            'x-restli-protocol-version': '2.0.0'
                        },
                        body: JSON.stringify({
                            "queryId": "voyagerSocialDashComments.afec6d88d7810d45548797a8dac4fb87",
                            "action": "execute",
                            "variables": {
                                "input": {
                                    "commentary": { "text": comment },
                                    "commentedOn": urn,
                                    "socialAction": urn
                                }
                            }
                        })
                    });
                    return commentRes.status;
                }
            """, {"urn": urn, "comment": text})
            
            if result in [200, 201]:
                logger.info(f"✅ VICTORIA TOTAL: El sistema ha inyectado el comentario via GraphQL (Status {result}).")
            else:
                logger.error(f"❌ FALLO DEFINITIVO: {result}. LinkedIn requiere revision manual de la cuenta.")
                
        except Exception as e:
            logger.error(f"Error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    if len(sys.argv) < 2: sys.exit(1)
    asyncio.run(run_final_injection(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "Sistema funcional v11."))
