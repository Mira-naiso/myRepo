import requests
import json
import yaml
import os
from datetime import datetime, timezone, timedelta
import time
import impconfig
from pprint import pprint
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Загрузка конфигурации с использованием impconfig
def load_config() -> dict:
    config_path = os.getenv("CONFIG_FILE_PATH", "/app/config/settings.yaml")
    config = impconfig.parse_config(
        directory=str(os.path.dirname(config_path)),
        prodfile=os.path.basename(config_path)
    )
    logger.info("Загруженная конфигурация из Vault/Consul и локального файла:")
    pprint(config)
    return config

config = load_config()

# Извлечение параметров из конфигурации
PAGERDUTY_API_TOKEN = config.get('pagerduty', {}).get('api_token', '')
PAGERDUTY_BASE_URL = config.get('pagerduty', {}).get('base_url', '')
SLACK_WEBHOOK_URL = config.get('slack', {}).get('webhook_url_sit', '')
SLACK_BOT_TOKEN = config.get('slack', {}).get('slack_bot_token', '')

TRIGGERED_INCIDENT_THRESHOLD_MINUTES = config.get('incident_thresholds', {}).get('triggered_minutes', 30)
ACKNOWLEDGED_INCIDENT_THRESHOLD_HOURS = config.get('incident_thresholds', {}).get('acknowledged_hours', 2)

EXCLUDED_SERVICES = config.get('excluded_services', [])

# Проверка наличия токенов
required_tokens = {
    "PAGERDUTY_API_TOKEN": PAGERDUTY_API_TOKEN,
    "SLACK_WEBHOOK_URL": SLACK_WEBHOOK_URL,
    "SLACK_BOT_TOKEN": SLACK_BOT_TOKEN
}
for token_name, token_value in required_tokens.items():
    if not token_value:
        raise ValueError(f"{token_name} отсутствует. Проверьте настройки или переменные окружения.")

# Логика работы с PagerDuty и Slack
processed_incidents = {}
last_clear_date = None

headers = {
    'Authorization': f'Token token={PAGERDUTY_API_TOKEN}',
    'Accept': 'application/vnd.pagerduty+json;version=2'
}

def is_within_working_hours() -> bool:
    """
    Проверяет, находится ли текущее время в интервале с 7:00 до 14:00 по UTC и является ли день рабочим (понедельник - пятница).
    """
    now = datetime.now(timezone.utc)
    
    # 0 - Понедельник, 6 - Воскресенье
    if now.weekday() >= 5:  # 5 — суббота, 6 — воскресенье
        return False
    # Проверяем, что время с 7:00 до 14:00 UTC
    return 7 <= now.hour < 14

def send_to_slack(message):
    """
    Отправляет сообщение в Slack и возвращает thread_ts, если успешно.
    """
    url = "https://slack.com/api/chat.postMessage"
    headers = {
        'Authorization': f'Bearer {SLACK_BOT_TOKEN}',
        'Content-Type': 'application/json',
    }
    payload = {
        'channel': SLACK_CHANNEL,
        'text': message
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response_data = response.json()
        if response_data.get("ok"):
            return response_data.get("ts")  # thread_ts
        else:
            logger.error(f"Ошибка Slack API: {response_data}")
            return None
    except Exception as e:
        logger.error(f'Ошибка отправки в Slack: {e}')
        return None


def send_to_slack_thread(message, thread_ts):
    """
    Отправляет сообщение в тред Slack, используя thread_ts.
    """
    if not is_within_working_hours():
        logger.info(f"Вне рабочего времени (7:00-14:00 UTC). Сообщение не отправлено: {message}")
        return

    payload = {
        'text': message,
        'thread_ts': thread_ts  # Указываем thread_ts для отправки в тред
    }
    try:
        response = requests.post(SLACK_WEBHOOK_URL, data=json.dumps(payload), headers={'Content-Type': 'application/json'}, timeout=10)
        response.raise_for_status()
    except Exception as e:
        logger.error(f'Ошибка отправки в Slack: {e}')

def get_high_urgency_incidents():
    params = {
        'urgency': 'high',
        'statuses[]': ['triggered', 'acknowledged'],
        'limit': 100
    }
    try:
        response = requests.get(f"{PAGERDUTY_BASE_URL}/incidents", headers=headers, params=params, timeout=10)
        response.raise_for_status()
        return response.json().get('incidents', [])
    except Exception as e:
        logger.error(f"Ошибка при запросе инцидентов: {e}")
        return []

def check_incident_times(incident):
    now = datetime.now(timezone.utc)
    created_at = datetime.strptime(incident['created_at'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
    status = incident['status']

    if status == 'triggered' and now - created_at > timedelta(minutes=TRIGGERED_INCIDENT_THRESHOLD_MINUTES):
        return (True, 'triggered', now - created_at)
    elif status == 'acknowledged' and now - created_at > timedelta(hours=ACKNOWLEDGED_INCIDENT_THRESHOLD_HOURS):
        return (True, 'acknowledged', now - created_at)
    return (False, '', timedelta(0))

def get_user_email(user_id: str) -> str:
    """
    Получает email пользователя по его ID.
    """
    url = f'{PAGERDUTY_BASE_URL}/users/{user_id}'
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        user_data = response.json().get('user', {})
        return user_data.get('email', 'Неизвестный email')
    except Exception as e:
        logger.error(f"Ошибка получения данных пользователя из PagerDuty: {e}")
        return 'Неизвестный email'

def get_slack_user_id_by_email(email: str) -> str:
    """
    Получает Slack ID пользователя по его email.
    """
    url = "https://slack.com/api/users.lookupByEmail"
    headers = {
        'Authorization': f'Bearer {SLACK_BOT_TOKEN}',
        'Content-Type': 'application/x-www-form-urlencoded',
    }
    data = {'email': email}
    try:
        response = requests.post(url, headers=headers, data=data, timeout=10)
        response.raise_for_status()
        if not response.json().get("ok"):
            logger.warning(f"Не удалось найти Slack ID для email {email}: {response.text}")
            return email
        user = response.json().get("user", {})
        return f"<@{user['id']}>"
    except Exception as e:
        logger.error(f"Ошибка получения Slack ID для {email}: {e}")
        return email

def get_on_call_users_for_service(service_id):
    """
    Получает список дежурных пользователей для указанного сервиса, включая их email и Slack-упоминания.
    """
    url = f"{PAGERDUTY_BASE_URL}/services/{service_id}"
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        escalation_policy_id = response.json().get("service", {}).get("escalation_policy", {}).get("id")
        if not escalation_policy_id:
            return []

        url_oncalls = f"{PAGERDUTY_BASE_URL}/oncalls"
        params = {"escalation_policy_ids[]": escalation_policy_id}
        response = requests.get(url_oncalls, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        on_calls = response.json().get("oncalls", [])

        result = []
        for on_call in on_calls:
            if on_call.get("escalation_level") == 1:
                user = on_call.get("user", {})
                email = get_user_email(user.get("id"))
                slack_mention = get_slack_user_id_by_email(email)
                result.append({"name": user.get("summary", "Неизвестно"), "email": email, "slack_mention": slack_mention})
        return result
    except Exception as e:
        logger.error(f"Ошибка получения дежурных пользователей для сервиса {service_id}: {e}")
        return []

def clear_processed_incidents():
    global last_clear_date
    now = datetime.now(timezone.utc)
    
    # Сбрасываем инциденты только в 7:00 UTC
    if now.hour == 7 and (now.date() != last_clear_date):
        if last_clear_date != now.date():
            processed_incidents.clear()
            last_clear_date = now.date()
            logger.info("Сброс обработанных инцидентов в 7:00 UTC.")

def has_pending_actions(incident):
    """
    Проверяет наличие незавершенных действий (pending actions) в инциденте.
    """
    try:
        pending_actions = incident['pending_actions']
        # Проверяем, что список pending_actions не пустой
        return pending_actions != []
    except KeyError:
        return False

def check_incidents():
    incidents = get_high_urgency_incidents()
    for incident in incidents:
        service_name = incident['service']['summary']
        urgency = incident['urgency']
        incident_id = incident['id']

        # Пропускаем инциденты
        if service_name in EXCLUDED_SERVICES or urgency != 'high':
            continue

        if incident_id in processed_incidents:
            continue

        # Проверка на pending actions перед отправкой сообщения
        if has_pending_actions(incident):
            processed_incidents[incident_id] = datetime.now(timezone.utc)
            logger.info(f"Инцидент {incident_id} имеет pending actions и был добавлен в processed_incidents.")
            continue  # Пропускаем отправку сообщения, если есть pending actions

        # Получаем дежурных пользователей
        on_call_users = get_on_call_users_for_service(incident['service']['id'])
        on_call_users_mentions = ", ".join([user['slack_mention'] for user in on_call_users]) or "никого нет"

        check, status, time_passed = check_incident_times(incident)
        if check:
            time_str = str(time_passed).split('.')[0]
            incident_url = incident['html_url']
            message = (f"Привет {on_call_users_mentions}, я вижу, что <{incident_url}|{incident['summary']}> (Impacted Service: {service_name}) "
                       f"уже висит более {time_str} в статусе {status}. "
                       "Подскажите, ведутся ли по нему работы?")

            # Отправляем основное сообщение и получаем thread_ts
            thread_ts = send_to_slack(message)
            if thread_ts:
                # Отправляем второе сообщение в тред
                reminder_message = (f"Если ведутся работы, чтобы мы не писали тебе во время выполнения работ, установи snooze time "
                                   f"в <{incident_url}|{incident['summary']}> на планируемое время работ.")
                send_to_slack_thread(reminder_message, thread_ts)

            processed_incidents[incident_id] = datetime.now(timezone.utc)

if __name__ == '__main__':
    try:
        logger.info("Скрипт запущен.")
        while True:
            clear_processed_incidents()  # Сбрасываем обработанные инциденты, если пришло время
            check_incidents()           # Проверяем инциденты
            time.sleep(300)             # Ждём 5 минут перед следующей проверкой
    except KeyboardInterrupt:
        logger.info("Скрипт завершён вручную.")
    except Exception as e:
        logger.exception(f'Необработанное исключение: {e}')