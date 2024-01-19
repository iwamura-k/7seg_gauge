import threading
import time
from rixiot_libs.camera import create_camera
import os
import cv2
import config
from common_libs.db_models import DBCameraSetting
from common_libs import utils
from common_libs.db_models import start_sqlorm,SessionClass


def get_camera_list():
    session = SessionClass()
    port_list = session.query(DBCameraSetting.usb_port).all()
    print(port_list)
    camera_list = [create_camera(config.CameraType.USB, port=port[0], fps=config.FPS, buffer_size=1) for port in
                   port_list]
    return camera_list


class CameraImageStorage(threading.Thread):
    def __init__(self, camera_list):
        super().__init__()
        self._stop_event = threading.Event()
        self._camera_list = camera_list

    def run(self):
        while not self._stop_event.is_set():
            try:
                timestamp = utils.get_timestamp()
                for camera in self._camera_list:
                    print(camera.port)
                    image_directory = f"{config.IMAGE_STORAGE_DIR}/PORT_{camera.port}/{timestamp}"
                    os.makedirs(image_directory, exist_ok=True)
                    image_list = []
                    for i in range(config.IMAGE_COUNT):
                        image_list.append(camera.get_image())
                        time.sleep(1)
                    for i, image in enumerate(image_list):
                        if image is not None:
                            cv2.imwrite(f"{image_directory}/{i}.jpg", image)

                time.sleep(config.STORE_INTERVAL_SEC)
            except Exception as e:
                print(e)
                time.sleep(5)

    def stop(self):
        self._stop_event.set()


# スレッドのインスタンスをグローバルに保持
camera_list = get_camera_list()
thread_instance = CameraImageStorage(camera_list=camera_list)

if __name__ == "__main__":
    start_sqlorm()
    # スレッドのインスタンスをグローバルに保持
    camera_list = get_camera_list()
    CameraImageStorage(camera_list=camera_list).run()
