from enum import Enum
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
FPS=30
BUFFER_SIZE=1
STORE_INTERVAL_SEC=60

# 撮影画像保存フォルダパス
SETTING_IMAGE_PATH = "/home/pi/node-red-static/setting_images"

# JSON設定ファイルのパス
JSON_SETTING_FILE_DIR = "./json_settings"
# メールアドレス設定の保存ファイルパス
MAIL_SETTING_PATH = f"{JSON_SETTING_FILE_DIR}/mail_settings.json"

class CameraType(Enum):
    USB=0

IMAGE_STORAGE_DIR="./images"