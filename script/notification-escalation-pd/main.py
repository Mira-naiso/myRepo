import requests
import os
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Извлечение параметров из переменных окружения
PAGERDUTY_API_TOKEN = os.getenv('PD_API_TOKEN')
SLACK_WEBHOOK_URL = os.getenv('SLACK_WEBHOOK_URL')

# Проверка наличия необходимых параметров
if not PAGERDUTY_API_TOKEN:
    raise ValueError("Переменная окружения PD_API_TOKEN отсутствует.")
if not SLACK_WEBHOOK_URL:
    raise ValueError("Переменная окружения SLACK_WEBHOOK_URL отсутствует.")

# Заголовки для запросов к API PagerDuty
headers = {
    'Authorization': f'Token token={PAGERDUTY_API_TOKEN}',
    'Accept': 'application/vnd.pagerduty+json;version=2'
}

# Функция для отправки сообщения в Slack через Webhook
def send_to_slack(message):
    payload = {'text': message}
    try:
        response = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=10)
        response.raise_for_status()
        logger.info(f"Сообщение отправлено в Slack: {message}")
    except Exception as e:
        logger.error(f'Ошибка отправки сообщения в Slack: {e}')

# Функция для получения списка всех пользователей
def get_all_users():
    url = "https://api.pagerduty.com/users"
    users = []
    offset = 0
    limit = 100  # Максимальное количество пользователей за один запрос
    while True:
        params = {'offset': offset, 'limit': limit}
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            users.extend(data.get('users', []))
            if not data.get('more', False):
                break
            offset += limit
        except Exception as e:
            logger.error(f"Ошибка при получении списка пользователей: {e}")
            break
    return users

# Функция для проверки наличия альтернативных методов уведомлений у пользователя
def has_alternative_notification_methods(user_id):
    url = f"https://api.pagerduty.com/users/{user_id}/notification_rules"
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        notification_rules = response.json().get('notification_rules', [])
        for rule in notification_rules:
            if rule.get('contact_method', {}).get('type') != 'email_contact_method':
                return True
    except Exception as e:
        logger.error(f"Ошибка при получении методов уведомлений для пользователя {user_id}: {e}")
    return False

# Функция для проверки, включен ли пользователь в расписание дежурств
def is_user_on_call(user_id):
    url = "https://api.pagerduty.com/oncalls"
    params = {'user_ids[]': user_id}
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        oncalls = response.json().get('oncalls', [])
        return len(oncalls) > 0
    except Exception as e:
        logger.error(f"Ошибка при проверке расписания дежурств для пользователя {user_id}: {e}")
    return False

# Основная функция для проверки пользователей и отправки уведомлений
def check_users():
    users = get_all_users()
    if not users:
        logger.info("Список пользователей пуст или не удалось получить данные.")
        return

    users_without_notifications = []
    for user in users:
        user_id = user.get('id')
        user_email = user.get('email')
        if not user_id or not user_email:
            continue

        if is_user_on_call(user_id) and not has_alternative_notification_methods(user_id):
            users_without_notifications.append(user_email)

    if users_without_notifications:
        message = ("Следующие пользователи включены в расписание дежурств, "
                   "но не имеют настроенных методов уведомлений, кроме электронной почты:\n" +
                   "\n".join(users_without_notifications))
        send_to_slack(message)
    else:
        logger.info("Все пользователи имеют настроенные методы уведомлений или не включены в расписание дежурств.")

if __name__ == '__main__':
    try:
        logger.info("Запуск проверки пользователей в PagerDuty")
        check_users()
    except KeyboardInterrupt:
        logger.info("Скрипт завершён вручную.")
    except Exception as e:
        logger.exception(f'Необработанное исключение: {e}')
