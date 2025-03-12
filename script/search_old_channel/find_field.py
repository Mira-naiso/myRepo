import requests
import base64
import os

JIRA_URL = "https://indriver.atlassian.net"
JIRA_API_TOKEN = os.getenv('JIRA_API_TOKEN')
JIRA_USER_EMAIL = "andrei.anokhin@indriver.com"

auth = base64.b64encode(f"{JIRA_USER_EMAIL}:{JIRA_API_TOKEN}".encode()).decode()

headers = {
    "Authorization": f"Basic {auth}",
    "Accept": "application/json"
}

API_ENDPOINT = f"{JIRA_URL}/rest/api/3/field"

response = requests.get(API_ENDPOINT, headers=headers)

if response.status_code == 200:
    fields = response.json()
    for field in fields:
        print(f"{field['id']} - {field['name']}")
else:
    print("Ошибка:", response.status_code, response.text)
