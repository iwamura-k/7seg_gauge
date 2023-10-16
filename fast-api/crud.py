import base64
import datetime
import io
import subprocess
import time
import uuid


from sqlalchemy.orm import Session
from db_model import CameraSetting, OCRSetting,Base
from schema import UICameraSetting, CameraSettingCheck, USBPortResponse
import config
from PIL import Image
import cv2


def check_camera_setting(settings: list[UICameraSetting]):
    """
    引数settingsのカメラ設定データのフォーマットをチェックし
    チェック判定(OK,NG)とチェック結果(OK,NGのリスト)を返却する
    :param settings:
    :return:
    """
    check_data_list = []
    is_success = True
    for setting in settings:
        if setting.name is None:
            check_data = CameraSettingCheck(usb_port="ok", name="ng", is_valid="ok")
            is_success = False
        elif len(setting.name) > config.MAX_LENGTH_OF_CAMERA_NAME:
            check_data = CameraSettingCheck(usb_port="ok", name="ng", is_valid="ok")
            is_success = False
        else:
            check_data = CameraSettingCheck(usb_port="ok", name="ok", is_valid="ok")
        check_data_list.append(check_data)
    return is_success, check_data_list


def delete_camera_setting(db: Session, usb_port: str):
    """
    引数usb_portに該当するカメラ設定を削除する
    :param db:
    :param usb_port:
    :return:
    """
    db.query(CameraSetting).filter(CameraSetting.usb_port == usb_port).delete()
    db.commit()


def update_camera_setting(db: Session, setting: UICameraSetting):
    """
    データベースにあるカメラの設定データを引数settingの内容で更新する
    :param setting:
    :return:
    """
    db_setting = db.query(CameraSetting).get(setting.usb_port)
    db_setting.name = setting.name
    db_setting.is_valid = setting.is_valid
    db.commit()
    db.refresh(db_setting)


def insert_camera_setting(db: Session, setting: UICameraSetting):
    """
    引数settingのカメラ設定データをデータベースに新規追加する
    :param db:
    :param setting:
    :return:
    """
    new_setting = CameraSetting(usb_port=setting.usb_port, name=setting.name, is_valid=setting.is_valid)
    db.add(new_setting)
    db.commit()
    db.refresh(new_setting)


def get_all_camera_setting(db: Session):
    """
    カメラのすべての設定データを取得し、返却する
    :param db:
    :return:
    """
    # print(db.query(CameraSetting).all())
    return db.query(CameraSetting).all()


def get_available_usb_port(db: Session):
    """
    データベースに登録されていないカメラのリストを取得し、返却する
    :param db:
    :return:
    """
    usb_ports = db.query(CameraSetting.usb_port).all()
    if usb_ports:
        usb_ports = [port[0] for port in db.query(CameraSetting.usb_port).all()]
        print(usb_ports)
        available_ports = [port for port in config.CAMERA_USB_PORTS if port not in usb_ports]
        print(available_ports)
        if available_ports:
            return [USBPortResponse(name=f"ポート{port}", value=port) for port in available_ports]
        else:
            return []

    available_ports = config.CAMERA_USB_PORTS
    return [USBPortResponse(name=f"ポート{port}", value=port) for port in available_ports]


class UsbVideoDevice():
    def __init__(self):
        self.__device_list = []

        try:
            cmd = 'ls -la /dev/v4l/by-id'
            res = subprocess.check_output(cmd.split())
            by_id = res.decode()
        except Exception as e:
            print(e)

        try:
            cmd = 'ls -la /dev/v4l/by-path'
            res = subprocess.check_output(cmd.split())
            by_path = res.decode()
        except Exception as e:
            print(e)

        # デバイス名取得
        device_names = {}
        for line in by_id.split('\n'):
            if '../../video' in line:
                tmp = self.__split(line, ' ')
                if "" in tmp:
                    tmp.remove("")
                name = tmp[8]
                device_id = tmp[10].replace('../../video', '')
                device_names[device_id] = name

        # ポート番号取得
        for line in by_path.split('\n'):
            if 'usb-0' in line:
                tmp = self.__split(line, '0-usb-0:1.')
                tmp = self.__split(tmp[1], ':')
                port = tmp[0]
                tmp = self.__split(tmp[1], '../../video')
                device_id = int(tmp[1])
                if device_id % 2 == 0:
                    name = device_names[str(device_id)]
                    self.__device_list.append((device_id, port, name))

    @staticmethod
    def __split(string, val):
        tmp = string.split(val)
        if '' in tmp:
            tmp.remove('')
        return tmp

    # 認識しているVideoデバイスの一覧を表示する
    def display_video_devices(self):
        for (device_id, port, name) in self.__device_list:
            print("/dev/video{} port:{} {}".format(device_id, port, name))

    # ポート番号（1..）を指定してVideoIDを取得する
    def get_video_id(self, port):
        print(self.__device_list)
        for (device_id, p, _) in self.__device_list:
            if p == port:
                return device_id
        return None


def get_timestamp() -> str:
    jst = datetime.timezone(datetime.timedelta(hours=+9), "JST")
    now = datetime.datetime.now(jst)
    timestamp = now.strftime('%Y%m%d%H%M%S')
    return timestamp


def insert_ocr_setting(usb_port,image,db: Session):
    """
    引数settingのカメラ設定データをデータベースに新規追加する
    :param db:

    :return:
    """

    new_setting = OCRSetting(id=str(uuid.uuid4()),
                             camera_usb_port=usb_port,
                             setting_image=image,
                             setting_name="",
                             unit="",
                             is_valid=True,
                             is_keystone_correction=True,
                             keystone_correction=
                             {},
                             line_color="red",
                             digit_space="10",
                             digit_settings={},
                             decimal_point_settings={},
                             digit_color={},
                             background_color={}

                             )
    db.add(new_setting)
    db.commit()
    db.refresh(new_setting)
    return db.query(OCRSetting).all()


def convert_to_byte_image(image):
    # バイナリデータに変換
    _, img_encoded = cv2.imencode('.png', image)
    return img_encoded.tobytes()
