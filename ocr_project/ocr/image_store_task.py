import sys
sys.path.append('/home/pi/.local/lib/python3.9/site-packages')
sys.path.append('/home/pi/ocr_project')
import threading
import time
from rixiot_libs.camera import create_camera
import os
import cv2
import config
from common_libs.db_models import DBCameraSetting
from common_libs import utils
from common_libs.db_models import SessionClass
from rixiot_libs.mqtt_factory import MQTTClientFactory, on_connect, on_disconnect
from image_processing_task import EmailMessagePool,EventPolicyFactory

def get_camera_list():
    session = SessionClass()
    port_list = session.query(DBCameraSetting.usb_port).all()
    print(port_list)
    camera_list = [create_camera(config.CameraType.USB, port=port[0], fps=config.FPS, buffer_size=1) for port in
                   port_list]
    print(camera_list)
    return camera_list


class CameraImageStorage(threading.Thread):
    def __init__(self, camera_list, mqtt_broker_ip, mqtt_client, mqtt_broker_port, mqtt_keep_alive, mqtt_topic,event_policies,email_message_pool):
        super().__init__()
        self._stop_event = threading.Event()
        self._camera_list = camera_list
        self.mqtt_broker_ip = mqtt_broker_ip
        self.mqtt_client = mqtt_client
        self.mqtt_broker_port = mqtt_broker_port
        self.mqtt_keep_alive = mqtt_keep_alive
        self.mqtt_topic = mqtt_topic

    def run(self):
        while not self._stop_event.is_set():
            timestamp = utils.get_timestamp()
            for camera in self._camera_list:
                try:
                    print(f"camera.port:{camera.port}")
                    image_directory = f"{config.IMAGE_STORAGE_DIR}/PORT_{camera.port}/{timestamp}"
                    
                    image_list = []
                    for i in range(config.IMAGE_COUNT):
                        print(str(i))
                        image_list.append(camera.get_image())
                        time.sleep(1)
                    os.makedirs(image_directory, exist_ok=True)
                    for i, image in enumerate(image_list):
                        if image is not None:
                            cv2.imwrite(f"{image_directory}/{timestamp}_{i}.jpg", image)

                except Exception as e:

                    print(e)

                    time.sleep(5)

            time.sleep(config.STORE_INTERVAL_SEC)

    def send_message_to_browser(self, message):
        self.connect_mqtt()
        self.mqtt_client.loop_start()
        self.mqtt_client.publish(self.mqtt_topic, message)
        self.mqtt_client.loop_stop()

    def connect_mqtt(self):
        self.mqtt_client.connect(self.mqtt_broker_ip, self.mqtt_broker_port, self.mqtt_keep_alive)


    def stop(self):
        self._stop_event.set()


# スレッドのインスタンスをグローバルに保持
#camera_list = get_camera_list()
#thread_instance = CameraImageStorage(camera_list=camera_list)

if __name__ == "__main__":
    
    # スレッドのインスタンスをグローバルに保持
    camera_list = get_camera_list()
    mqtt_client = MQTTClientFactory(on_connect=on_connect, on_disconnect=on_disconnect, user_name=None, password=None,
                                    on_message=None).create()
    event_policies = EventPolicyFactory().create_event_policies()
    email_message_pool = EmailMessagePool()

    CameraImageStorage(camera_list=camera_list,
                       mqtt_broker_ip=config.MQTT_BROKER_IP,
                       mqtt_client=mqtt_client,
                       mqtt_broker_port=config.MQTT_BROKER_PORT,
                       mqtt_keep_alive=config.MQTT_KEEP_ALIVE_SEC,
                       mqtt_topic=config.MQTT_BROWSER_TOPIC,
                       event_policies=event_policies,
                       email_message_pool=email_message_pool).run()
