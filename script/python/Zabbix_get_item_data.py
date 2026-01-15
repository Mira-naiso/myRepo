from pyzabbix import ZabbixAPI
from time import mktime
from datetime import datetime, timedelta
from csv import DictWriter

#Выводит данные и item всего хоста. Нужен для переноса информации в CSV

class Settings:
    # Zabbix settings:
    zabbix_username: str = 'YOU-USERNAME'
    zabbix_password: str = 'YOU-PASSWORD'
    zabbix_url: str = 'https://zabbix.console3.com/'

    host_id: str = "ID"


class GetDataFromZabbixItem(Settings):
    def __init__(self):
        # Login to the Zabbix API:
        self._zabbix_api: ZabbixAPI = ZabbixAPI(self.zabbix_url)
        self._zabbix_api.login(
            user=self.zabbix_username,
            password=self.zabbix_password
        )

        self._item_id_collections: dict = {}
        self._item_raw_data_collection: dict = {}

    def _get_host_items(self):
        all_host_items: dict = self._zabbix_api.item.get(
            filter={
                "hostid": self.host_id
            }
        )
        for item in all_host_items:
            self._item_id_collections.update(
                {
                    item["itemid"]: {
                        "item_name": item['name'],
                        "item_key": item["key_"]
                    }
                }
            )

    @staticmethod
    def _create_data_time() -> (int, int):
        return (
            int(
                mktime(
                    datetime.now()
                    .timetuple()
                )
            ),
            int(
                mktime(
                    (
                        datetime.now()
                        - timedelta(days=730)
                    ).timetuple()
                )
            )
        )

    def _land_data(self):
        """
        Parse items values to hash table.
        """
        for item_id in self._item_raw_data_collection:
            data_for_landing: list = []
            for item_data in self._item_raw_data_collection[item_id]["item_history"]:
                data_for_landing.append(
                    {
                        "item_id": item_id,
                        "item_name": self._item_raw_data_collection[item_id]["item_name"],
                        "Unix_timestamp": item_data["clock"],
                        "Nano_seconds": item_data["ns"],
                        "Value": item_data["value"]
                    }
                )
            with open(
                f"{self._item_raw_data_collection[item_id]['item_name']}.csv",
                "w",
                newline='',
                encoding="UTF-8"
            ) as file:
                writer = DictWriter(
                    file,
                    fieldnames=[
                        "item_id",
                        "item_name",
                        "Unix_timestamp",
                        "Nano_seconds",
                        "Value"
                    ]
                )
                writer.writeheader()
                writer.writerows(data_for_landing)

    def execute(self):
        self._get_host_items()
        time_till, time_from = self._create_data_time()

        for item_id in self._item_id_collections:
            item_history: list = self._get_zabbix_history(
                item_id=item_id,
                time_from=time_from,
                time_till=time_till
            )
            self._item_raw_data_collection.update(
                {
                    item_id: {
                        "item_name": self._item_id_collections[item_id]["item_name"],
                        "item_history": item_history
                    }
                }
            )
        self._land_data()
        print(
            "Successfully"
        )

    def _get_zabbix_history(self, *, item_id: str, time_from: int, time_till: int) -> list:
        """
        Get history with orders count from Zabbix server.

        :param item_id: Zabbix item id.
        :type item_id: str
        :param time_from: datatime from time.
        :type time_from: int
        :param time_till: datatime till time.
        :type time_till: int
        :return: list
        """
        history: list = self._zabbix_api.history.get(
            itemids=[item_id],
            time_from=time_from,
            time_till=time_till,
            output='extend',
        )
        if not len(history):
            history = self._zabbix_api.history.get(
                itemids=[item_id],
                time_from=time_from,
                time_till=time_till,
                output='extend',
                history=0
            )
        return history


if __name__ == "__main__":
    GetDataFromZabbixItem().execute()
