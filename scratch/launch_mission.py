import requests
import json

API_URL = "http://localhost:8000/missions/"

mission_data = {
    "account_id": 1,
    "tasks": [
        {
            "type": "comment",
            "payload": {
                "url": "https://www.linkedin.com/posts/romerofabio_%C3%BA%F0%9D%97%9F%F0%9D%97%A7%F0%9D%97%9C%F0%9D%97%A0%F0%9D%97%94-%F0%9D%97%9B%F0%9D%97%A2%F0%9D%97%A5%F0%9D%97%94-%F0%9D%97%9F%F0%9D%97%AE-%F0%9D%97%BF%F0%9D%97%B2%F0%9D%97%AE%F0%9D%97%B9%F0%9D%97%B6%F0%9D%97%B1%F0%9D%97%AE%F0%9D%97%B1-ugcPost-7452166043847843840-I8Tf",
                "text": "Excelente perspectiva sobre el contenido digital y la autenticidad. ¡Muy necesario hoy en día!"
            }
        }
    ]
}

try:
    response = requests.post(API_URL, json=mission_data)
    if response.status_code == 200:
        print(f"SUCCESS: Mission {response.json()['id']} created and running in background.")
    else:
        print(f"FAILED: {response.status_code} - {response.text}")
except Exception as e:
    print(f"ERROR: {e}")
