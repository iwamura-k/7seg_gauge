import time
from paho.mqtt import client as mqtt_client

RECONNECT_RATE_SEC = 10


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("MQTTブローカーに接続しました！")
    else:
        print("接続に失敗しました、リターンコード %d\n", rc)


def on_disconnect(client, userdata, rc):
    while True:
        time.sleep(RECONNECT_RATE_SEC)
        try:
            client.reconnect()
            print("再接続に成功しました！")
            return
        except Exception as e:
            print("%s。再接続に失敗しました。再試行します...", e)


class MQTTClientFactory:

    def __init__(self, user_name, password, on_connect, on_disconnect, on_message):
        self.user_name = user_name
        self.password = password
        self.on_connect = on_connect
        self.on_disconnect = on_disconnect
        self.on_message = on_message

    def create(self):
        client = mqtt_client.Client()
        if not (self.user_name is None or self.password is None):
            client.username_pw_set(self.user_name, self.password)

        client.on_connect = self.on_connect
        client.on_disconnect = self.on_disconnect
        client.on_message = self.on_message
        return client
