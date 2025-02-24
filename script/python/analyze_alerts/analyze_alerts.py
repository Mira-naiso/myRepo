import yaml
import os
import sys

ALERTS_DIR_NAME = 'alerts'
NOT_DEFINE_RUNBOOK = [
    "https://runbook",
    "https://indriver.atlassian.net/wiki/spaces/MON/pages/1463288220/Golden+Signals+imp"
]


def load_yaml(file_path):
    with open(file_path, 'r') as file:
        return yaml.safe_load(file)


def analyze_alerts(data, file_path):
    total_alerts = len(data)
    alerts_without_runbook = []
    alerts_with_runbook = []

    for alert in data:
        try:
            alert_name = alert.get('alert', 'Unknown Alert')
            annotations = alert.get('annotations', {})
            runbook_url = annotations.get('runbook_url',
                                          "https://indriver.atlassian.net/wiki/spaces/MON/pages/1463288220/Golden+Signals+imp")

            if not runbook_url or runbook_url in NOT_DEFINE_RUNBOOK:
                alerts_without_runbook.append((alert_name, file_path))
            else:
                alerts_with_runbook.append(alert)
        except Exception as e:
            pass

    return total_alerts, len(alerts_without_runbook), len(alerts_with_runbook), alerts_without_runbook


def find_alerts_directories(start_path):
    alerts_dirs = []
    for root, dirs, files in os.walk(start_path):
        for dir_name in dirs:
            if dir_name == ALERTS_DIR_NAME:
                alerts_dirs.append(os.path.join(root, dir_name))
    return alerts_dirs


def main(folders: list):
    total_alerts = 0
    no_runbook_count = 0
    with_runbook_count = 0
    all_no_runbook_alerts = []

    for folder_path in folders:
        print("Dir: %s" % folder_path)
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            if os.path.isfile(file_path) and filename.endswith('.yaml'):
                print("Analyzing file: %s" % os.path.join(folder_path, file_path), )
                data = load_yaml(file_path)

                file_total_alerts, file_no_runbook_count, file_with_runbook_count, file_no_runbook_alerts = analyze_alerts(
                    data, file_path)

                total_alerts += file_total_alerts
                no_runbook_count += file_no_runbook_count
                with_runbook_count += file_with_runbook_count
                all_no_runbook_alerts.extend(file_no_runbook_alerts)

        print(f"Total number of alerts: {total_alerts}")
        print(f"Number of alerts without runbooks: {no_runbook_count}")
        print(f"Number of alerts with runbooks: {with_runbook_count}")

        if all_no_runbook_alerts:
            print("List of alerts without runbooks:")
            for alert, path in all_no_runbook_alerts:
                print(f"- {alert} (файл: {path})")
        else:
            print("All alerts have runbooks.")
        print("-" * 40)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python analyze_alerts.py <folder_path>")
    else:
        folder_path = sys.argv[1]
        alerts_directories = find_alerts_directories(folder_path)
        main(alerts_directories)
