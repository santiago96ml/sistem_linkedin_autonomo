import sys
import os
import re
import logging
import json
from dotenv import load_dotenv

# Configurar rutas
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
api_path = os.path.join(project_root, "linkedin_voice_bot", "linkedin-api")
sys.path.append(api_path)

from linkedin_api.linkedin import Linkedin

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv(os.path.join(api_path, ".env"))
USERNAME = os.getenv("LINKEDIN_USERNAME", "santiagomercadoluna26@gmail.com")
PASSWORD = os.getenv("LINKEDIN_PASSWORD", "aAntiagob168")

def run_triple_injection(url, text):
    match = re.search(r'([0-9]{19})', url)
    if not match:
        logger.error("URL invalida.")
        return False
        
    post_id = match.group(1)
    # Lista de formatos de URN posibles
    urn_formats = [
        f"urn:li:ugcPost:{post_id}",
        f"urn:li:activity:{post_id}",
        f"urn:li:share:{post_id}"
    ]
    
    try:
        logger.info("Iniciando Protocolo de Triple Inyeccion API...")
        api = Linkedin(USERNAME, PASSWORD, debug=True)
        
        for urn in urn_formats:
            logger.info(f"Probando inyeccion con formato: {urn}")
            # Acceso directo al cliente para ver la respuesta real
            success = api.post_comment(urn, text)
            
            if success:
                logger.info(f"✅ EXITO con formato {urn}. Inyeccion confirmada.")
                return True
            else:
                logger.warning(f"Fallo formato {urn}. Reintentando con el siguiente...")
        
        logger.error("❌ El sistema agoto todas las vias de inyeccion API. LinkedIn requiere intervencion manual (Captcha/2FA).")
        return False
        
    except Exception as e:
        logger.error(f"Falla total: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2: sys.exit(1)
    run_triple_injection(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "Test")
