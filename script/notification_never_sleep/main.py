import os
import requests
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Получение переменных окружения
api_token = os.getenv('PD_API_TOKEN')
service_id = os.getenv('SERVICE_ID')
title = "DADM Check"
description = "Almaty Never Sleeps"
slack_webhook_url = os.getenv('SLACK_BOT_TOKEN')
slack_channel_id = os.getenv('SLACK_CHANNEL_PUBLIC_ID')

def get_active_incidents(api_token):
    url = "https://api.pagerduty.com/incidents"
    headers = {
        "Authorization": f"Token token={api_token}",
        "Accept": "application/vnd.pagerduty+json;version=2"
    }
    params = {
        "statuses[]": ["triggered", "acknowledged"]
    }
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        return response.json().get("incidents", [])
    except requests.exceptions.RequestException as e:
        logger.error("Ошибка при получении инцидентов: %s", e)
        return []

def create_incident(api_token, service_id, title, description):
    url = "https://api.pagerduty.com/incidents"
    headers = {
        "Authorization": f"Token token={api_token}",
        "Content-Type": "application/json",
        "Accept": "application/vnd.pagerduty+json;version=2"
    }
    payload = {
        "incident": {
            "type": "incident",
            "title": title,
            "service": {
                "id": service_id,
                "type": "service_reference"
            },
            "body": {
                "type": "incident_body",
                "details": description
            }
        }
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        logger.info("Инцидент успешно создан: %s", response.json())
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error("Ошибка при создании инцидента: %s", e)
        return None

def send_slack_message(webhook_url, channel_id, message):
    headers = {"Content-Type": "application/json"}
    payload = {
        "channel": channel_id,
        "text": message
    }
    try:
        response = requests.post(webhook_url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        logger.info("Сообщение отправлено в Slack: %s", message)
    except requests.exceptions.RequestException as e:
        logger.error("Ошибка при отправке сообщения в Slack: %s", e)

def main():
    active_incidents = get_active_incidents(api_token)

    # Проверка на наличие активных инцидентов с приоритетом P1 или P2
    high_priority_exists = any(
        incident.get("priority") and
        incident["priority"].get("summary", "").lower() in {"p1", "p2"}
        for incident in active_incidents
    )

    if high_priority_exists:
        logger.info("Существуют активные инциденты уровня P1 или P2. Новый инцидент не будет создан.")
        slack_message = "⚠️ Новая проверка не была заведена, так как существуют активные инциденты уровня P1 или P2. Удачи в разрешении инцидента"
        send_slack_message(slack_webhook_url, slack_channel_id, slack_message)
    else:
        result = create_incident(api_token, service_id, title, description)
        if result:
            logger.info("Детали инцидента: %s", result)
        else:
            slack_message = "❗ Не удалось создать инцидент в PagerDuty. Пожалуйста, проверьте логи или конфигурацию."
            send_slack_message(slack_webhook_url, slack_channel_id, slack_message)

if __name__ == "__main__":
    main()
