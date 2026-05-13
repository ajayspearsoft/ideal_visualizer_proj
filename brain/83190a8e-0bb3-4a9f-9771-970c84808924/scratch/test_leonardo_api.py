import requests
import json

url = "https://cloud.leonardo.ai/api/rest/v1/canvas-init-image"
api_key = "45fa1475-362d-48a2-b8ab-6ed163aed8fd"

payload = {
    "initExtension": "png",
    "maskExtension": "png"
}
headers = {
    "accept": "application/json",
    "content-type": "application/json",
    "authorization": f"Bearer {api_key}"
}

response = requests.post(url, json=payload, headers=headers)
print(json.dumps(response.json(), indent=2))
