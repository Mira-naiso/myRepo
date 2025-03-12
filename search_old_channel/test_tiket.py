import requests
import base64
import json

# Конфигурация
JIRA_URL = "https://indriver.atlassian.net"
JIRA_API_TOKEN = os.getenv('JIRA_API_TOKEN')
JIRA_USER_EMAIL = "andrei.anokhin@indriver.com"

TICKET_KEY = "INCIDENT-11755"

# Авторизация
auth = base64.b64encode(f"{JIRA_USER_EMAIL}:{JIRA_API_TOKEN}".encode()).decode()

headers = {
    "Authorization": f"Basic {auth}",
    "Accept": "application/json"
}

# Запрашиваем все поля у конкретного тикета
API_ENDPOINT = f"{JIRA_URL}/rest/api/3/issue/{TICKET_KEY}"

response = requests.get(API_ENDPOINT, headers=headers)

if response.status_code == 200:
    data = response.json()
    print(json.dumps(data["fields"], indent=2))  # Красиво выводим JSON с полями тикета
else:
    print("Ошибка:", response.status_code, response.text)
