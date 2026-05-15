import urllib.request
import json

accounts = [
    ("santimene1@gmail.com", "Elsoda12.arg,"),
    ("tiago@leadlinked.ai", "Td44942845"),
    ("bc.market.br@gmail.com", "S2jd~=:p_;U%UH*")
]

url = "http://localhost:8000/accounts/login/start"
headers = {'Content-Type': 'application/json'}

for email, password in accounts:
    data = json.dumps({"email": email, "password": password}).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        response = urllib.request.urlopen(req)
        print(f"Success for {email}: {response.read().decode('utf-8')}")
    except Exception as e:
        print(f"Failed for {email}: {e}")
