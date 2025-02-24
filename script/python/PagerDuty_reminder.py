import requests
import json
from datetime import datetime, timedelta
import os

PAGERDUTY_API_TOKEN = 'api_token' # Paste api token PD
PAGERDUTY_BASE_URL = 'https://api.pagerduty.com/incidents'
SLACK_WEBHOOK_URL = 'slack_webhook' # Paste slack webhook bot
LOG_FILE_PATH = '/var/log/pdscript.log'

headers = {
    'Authorization': f'Token token={PAGERDUTY_API_TOKEN}',
    'Accept': 'application/vnd.pagerduty+json;version=2'
}

# List of services that will be excluded from verification
EXCLUDED_SERVICES = [
    "NORMAL Severity Airflow DI",
    "CRITICAL Severity Airflow DA",
    "NORMAL Severity Airflow DO",
    "HIGH Severity Airflow DO",
    "HIGH Severity Airflow DI",
    "HIGH Severity Airflow DU"
]

def send_to_slack(message):
    payload = {
        'text': message 
    }
    response = requests.post(SLACK_WEBHOOK_URL, data=json.dumps(payload), headers={'Content-Type': 'application/json'})

def get_high_urgency_incidents():
    params = {
        'urgency': 'high',
        'statuses[]': ['triggered', 'acknowledged'],
        'limit': 100
    }
    response = requests.get(PAGERDUTY_BASE_URL, headers=headers, params=params)
    if response.status_code == 200:
        return response.json().get('incidents', [])
    else:
        print(f'Error fetching incidents: {response.status_code} {response.text}')
        return []

def was_recently_notified(incident_id):
    if not os.path.exists(LOG_FILE_PATH):
        return False
    with open(LOG_FILE_PATH, 'r') as log_file:
        for line in log_file:
            logged_id, logged_time = line.strip().split(',')
            if logged_id == incident_id:
                logged_time = datetime.strptime(logged_time, '%Y-%m-%dT%H:%M:%SZ')
                if datetime.utcnow() - logged_time < timedelta(hours=6):
                    return True
    return False

def log_incident(incident_id):
    with open(LOG_FILE_PATH, 'a') as log_file:
        log_file.write(f'{incident_id},{datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")}\n')

def check_incident_times(incident):
    now = datetime.utcnow()
    created_at = datetime.strptime(incident['created_at'], '%Y-%m-%dT%H:%M:%SZ')
    status = incident['status']

    if status == 'triggered' and now - created_at > timedelta(minutes=30):
        return (True, 'triggered', now - created_at)
    elif status == 'acknowledged' and now - created_at > timedelta(hours=2):
        return (True, 'acknowledged', now - created_at)
    return (False, '', timedelta(0))

def get_assigned_user(incident):
    assignments = incident.get('assignments', [])
    if assignments:
        return assignments[0]['assignee']['summary']
    return 'Не назначен'

def check_incidents():
    now = datetime.utcnow()
    if now.hour < 7 or now.hour >= 19:
        return

    incidents = get_high_urgency_incidents()
    for incident in incidents:
        service_name = incident['service']['summary']
        urgency = incident['urgency']
        incident_id = incident['id']
        
        if service_name in EXCLUDED_SERVICES or urgency != 'high':
            continue
        
        if was_recently_notified(incident_id):
            continue

        assigned_to = get_assigned_user(incident)
        check, status, time_passed = check_incident_times(incident)
        
        if check:
            time_str = str(time_passed).split('.')[0]
            message = f"Привет {assigned_to}, я вижу что {incident['summary']} уже висит более {time_str} в статусе {status}, подскажи, ведутся ли по нему работы?"
            send_to_slack(message)
            log_incident(incident_id)
def clear_log_file():
    now = datetime.utcnow()
    if now.hour == 19:
        if os.path.exists(LOG_FILE_PATH):
            os.remove(LOG_FILE_PATH)
if __name__ == '__main__':
    clear_log_file()
    check_incidents()
