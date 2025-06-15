import json
import logging
import os
from time import sleep

import schedule
from dotenv import load_dotenv
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from switchbot import Switchbot

# Logging
formatter = "[%(levelname)-8s] %(asctime)s %(funcName)s %(message)s"
logging.basicConfig(level=logging.INFO, format=formatter)
logger = logging.getLogger(__name__)

load_dotenv(".env")

# InfluxDB
INFLUXDB_TOKEN = os.environ["INFLUXDB_TOKEN"]
bucket = "switchbot"
client = InfluxDBClient(url="http://influxdb:8086", token=INFLUXDB_TOKEN, org="org")
write_api = client.write_api(write_options=SYNCHRONOUS)
query_api = client.query_api()

# SwitchBot
ACCESS_TOKEN: str = os.environ["SWITCHBOT_ACCESS_TOKEN"]
SECRET: str = os.environ["SWITCHBOT_SECRET"]
SUPPORTED_DEVICES = ["Meter", "MeterPlus", "WoIOSensor", "MeterPro", "MeterPro(CO2)", "Humidifier", "Hub 2", "Hub 3"]
CO2_DEVICES = ["MeterPro(CO2)"]

def save_device_status(status: dict, devicename: str):
    """SwitchbotデバイスのステータスをInfluxDBに保存する"""

    device_type = status.get("deviceType")

    p = (
        Point("weather")
        .tag("device_id", status["deviceId"])
        .tag("device_name", devicename)
        .field("temperature", float(status["temperature"]))
        .field("humidity", float(status["humidity"]))
    )
    if device_type in CO2_DEVICES:
        p = p.field("CO2", float(status["CO2"]))
    
    write_api.write(bucket=bucket, record=p)
    logging.info(f"Saved: {status}")


def task():
    """定期実行するタスク"""
    bot = Switchbot(ACCESS_TOKEN, SECRET)

    with open("device_list.json", "r") as f:
        device_list = json.load(f)

    for d in device_list:
        device_type = d.get("deviceType")
        if device_type in SUPPORTED_DEVICES:
            try:
                status = bot.get_device_status(d.get("deviceId"))
                devicename = d.get("deviceName")
            except Exception as e:
                logging.error(f"Request error: {e}")
                continue

            try:
                save_device_status(status, devicename)
            except Exception as e:
                logging.error(f"Save error: {e}")


if __name__ == "__main__":
    schedule.every(5).minutes.do(task)

    while True:
        schedule.run_pending()
        sleep(1)
