# データベース接続設定
DATABASE = 'postgresql'
USER = 'postgres'
PASSWORD = 'admin'
HOST = 'localhost'
PORT = '5432'
DB_NAME = 'setting'

# カメラ設定
MAX_LENGTH_OF_CAMERA_NAME = 20
CAMERA_USB_PORTS = ["1", "2", "3", "4","5","6","7"]

# カメラ名とUSBポート値のマッピング
USB_DEV_ID = {"PORT_1": "1.4", "PORT_2": "1.3", "PORT_3": "1.2", "PORT_4": "1.1", "PORT_5": "1.1.3", "PORT_6": "1.1.2",
              "PORT_7": "1.1.1"}

#撮影画像保存フォルダパス
SETTING_IMAGE_PATH="./setting_images"

