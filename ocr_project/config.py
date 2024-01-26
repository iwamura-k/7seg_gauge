from enum import Enum
import os
import sys

# データベース接続設定
DATABASE = 'mydb'
USER = 'postgres'
PASSWORD = 'admin'
HOST = 'localhost'
PORT = '5432'
DB_NAME = 'setting'

# カメラ設定
MAX_LENGTH_OF_CAMERA_NAME = 20
CAMERA_USB_PORTS = ["1", "2", "3", "4", "5", "6", "7"]

# カメラ名とUSBポート値のマッピング
USB_PORT_MAPPING = {"1": "1.4", "2": "1.3", "3": "1.2", "4": "1.1", "5": "1.1.3", "6": "1.1.2",
                    "7": "1.1.1"}
FPS = 30
BUFFER_SIZE = 1
STORE_INTERVAL_SEC = 60

# 撮影画像保存フォルダパス
IMAGE_STORAGE_DIR = "/home/pi/node-red-static/files/images"
SETTING_IMAGE_PATH = "/home/pi/node-red-static/files/setting_images"
JSON_SETTING_FILE_DIR = "/home/pi/ocr_project/files/json_settings"
REGION_IMAGE_DIR = "/home/pi/node-red-static/files/region_images"
if os.name == 'nt':
    SETTING_IMAGE_PATH = "../files/setting_images"
    IMAGE_STORAGE_DIR = "../files/images"
    JSON_SETTING_FILE_DIR = "../files/json_settings"
    REGION_IMAGE_DIR = "../files/region_images"

# メールアドレス設定の保存ファイルパス
MAIL_SETTING_PATH = f"{JSON_SETTING_FILE_DIR}/mail_settings.json"


class CameraType(Enum):
    USB = 0


IMAGE_COUNT = 10

# OCR_CONFIG="-l 7seg --psm 10 --oem 1 -c tessedit_char_whitelist=-0123456789 --dpi 300"
OCR_CONFIG = "-l eng --psm 10 --oem 1 -c tessedit_char_whitelist=-0123456789 --dpi 300"
TESSERACT_PATH = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

ALERT_MAIL_DEAD_BAND_SEC = 5
ALERT_MAIL_MAX_SEND_LIMIT = 500

SUBJECT = "test"

databese_file = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'sample_db.sqlite3')
DB_PATH = f"sqlite:///{databese_file}"

TARGET_DIRECTORY = '/'
MAX_PERCENTAGE_OF_DATA = 90
MQTT_BROKER_IP = "192.168.3.35"
MQTT_BROKER_PORT = 1883
MQTT_BROWSER_TOPIC = "mqtt_test"
MQTT_KEEP_ALIVE_SEC = 60
