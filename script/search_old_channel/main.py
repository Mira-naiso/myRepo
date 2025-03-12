import requests
import re
import os
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Конфигурация
JIRA_URL = "https://indriver.atlassian.net"
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
JIRA_USER_EMAIL = "andrei.anokhin@indriver.com"
SLACK_TOKEN = os.getenv("SLACK_TOKEN")

PROJECT_KEY = "INCIDENT"
SLACK_FIELD = "customfield_13454"
MAX_RESULTS = 100  # Ограничение Jira API

# Проверка переменных окружения
if not JIRA_API_TOKEN or not JIRA_USER_EMAIL or not SLACK_TOKEN:
    logging.error("Отсутствуют необходимые переменные окружения!")
    exit(1)

# Авторизация
auth = requests.auth.HTTPBasicAuth(JIRA_USER_EMAIL, JIRA_API_TOKEN)
headers_jira = {"Accept": "application/json"}
headers_slack = {
    "Authorization": f"Bearer {SLACK_TOKEN}",
    "Content-Type": "application/json"
}

# JQL-запрос к Jira
JQL_QUERY = f'project={PROJECT_KEY} AND status="Closed" AND created >= -365d'
API_ENDPOINT = f"{JIRA_URL}/rest/api/3/search"

# Получаем общее количество инцидентов
params = {"jql": JQL_QUERY, "maxResults": 0}
total_response = requests.get(API_ENDPOINT, headers=headers_jira, params=params, auth=auth)
total_issues = total_response.json().get("total", 0)
logging.info(f"Общее количество закрытых инцидентов: {total_issues}")

start_at = 0
all_channels = {}

while start_at < total_issues:
    params = {"jql": JQL_QUERY, "fields": ["key", SLACK_FIELD], "startAt": start_at, "maxResults": MAX_RESULTS}
    response = requests.get(API_ENDPOINT, headers=headers_jira, params=params, auth=auth)
    
    if response.status_code != 200:
        logging.error(f"Ошибка запроса к Jira: {response.status_code} {response.text}")
        break
    
    data = response.json()
    issues = data.get("issues", [])
    logging.info(f"Обработано инцидентов: {start_at + len(issues)} / {total_issues}")
    
    for issue in issues:
        ticket_id = issue["key"]
        slack_link = issue["fields"].get(SLACK_FIELD, "")
        if not slack_link:
            logging.warning(f"Инцидент {ticket_id} не имеет ссылки на Slack.")
            continue
        
        match = re.search(r"(?:archives|huddle/[A-Z0-9]+|slack://(?:channel\?team=[A-Z0-9]+&id=)?|app_redirect\?channel=)([A-Z0-9]+)", slack_link)
        if match:
            channel_id = match.group(1)
            all_channels[ticket_id] = channel_id
        else:
            logging.warning(f"Не удалось извлечь Channel ID для {ticket_id}: {slack_link}")
    
    start_at += MAX_RESULTS

incident_pattern = re.compile(r"^incident_[a-zA-Z0-9_-]+_\d{4}-\d{2}-\d{2}_\d+$")
filtered_channels = {}

for incident, channel in all_channels.items():
    channel_info_response = requests.get("https://slack.com/api/conversations.info", headers=headers_slack, params={"channel": channel})
    if channel_info_response.status_code != 200:
        logging.error(f"Ошибка получения информации о канале {channel}: {channel_info_response.text}")
        continue
    
    channel_info = channel_info_response.json()
    if channel_info.get("ok"):
        channel_name = channel_info["channel"]["name"]
        is_archived = channel_info["channel"].get("is_archived", False)
        
        if is_archived:
            logging.info(f"Канал {channel} (Инцидент {incident}) уже заархивирован.")
            continue
        
        if incident_pattern.match(channel_name):
            filtered_channels[incident] = channel

logging.info(f"Найдено {len(filtered_channels)} каналов для архивирования.")

def join_channel(channel):
    join_response = requests.post("https://slack.com/api/conversations.join", headers=headers_slack, json={"channel": channel})
    join_data = join_response.json()
    if join_data.get("ok"):
        logging.info(f"Бот вступил в канал {channel}.")
    else:
        logging.error(f"Ошибка вступления в канал {channel}: {join_data.get('error')}")

def archive_channel(channel):
    join_channel(channel)
    archive_response = requests.post("https://slack.com/api/conversations.archive", headers=headers_slack, json={"channel": channel})
    archive_data = archive_response.json()
    if archive_data.get("ok"):
        logging.info(f"Канал {channel} заархивирован!")
    else:
        logging.error(f"Ошибка архивирования канала {channel}: {archive_data.get('error')}")

if filtered_channels:
    logging.info("Будут заархивированы следующие каналы:")
    for incident, channel in filtered_channels.items():
        logging.info(f"Инцидент {incident} → Канал {channel}")
    
    for incident, channel in filtered_channels.items():
        logging.info(f"Канал {channel} (Инцидент {incident}) будет заархивирован.")
        archive_channel(channel)
else:
    logging.info("Не найдено каналов для архивирования.")
