import requests
import os

SLACK_TOKEN = os.getenv('SLACK_TOKEN')
CHANNEL_ID = "C07MV56781M"

join_response = requests.post(
    "https://slack.com/api/conversations.join",
    headers={"Authorization": f"Bearer {SLACK_TOKEN}"},
    json={"channel": CHANNEL_ID}
)
join_data = join_response.json()

if not join_data.get("ok"):
    print(f"Ошибка добавления в канал: {join_data.get('error')}")
else:
    print("Бот успешно добавлен в канал!")

archive_response = requests.post(
    "https://slack.com/api/conversations.archive",
    headers={
        "Authorization": f"Bearer {SLACK_TOKEN}",
        "Content-Type": "application/json"
    },
    json={"channel": CHANNEL_ID}
)
archive_data = archive_response.json()

if archive_data.get("ok"):
    print("Канал успешно заархивирован!")
else:
    print(f"Ошибка архивирования: {archive_data.get('error')}")
