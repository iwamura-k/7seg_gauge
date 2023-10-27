import base64
import datetime
import json
import io
import subprocess
import time
import uuid

from sqlalchemy.orm import Session
from db_model import CameraSetting, OCRSetting, Base
from data_schema import UICameraSetting, CameraSettingCheck, USBPortResponse, UIOCRSetting,UIOCRSetting2,CameraSettingResponse
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


def get_all_camera_setting(db: Session):
    """
    カメラのすべての設定データを取得し、返却する
    :param db:
    :return:
    """
    # print(db.query(CameraSetting).all())
    temps=db.query(CameraSetting.usb_port,CameraSetting.name,CameraSetting.is_valid).all()
    print(temps)
    send_data=[]
    for temp in temps:

        #send_data.append({"value":temp[0],"name":temp[1],"is_valid":temp[2]})
        send_data.append(CameraSettingResponse(usb_port=temp[0],name=temp[1],is_valid=temp[2]))
    return send_data


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


def convert_to_byte_image(image):
    # バイナリデータに変換
    _, img_encoded = cv2.imencode('.png', image)
    return img_encoded.tobytes()


def insert_ocr_setting(db: Session, setting: UIOCRSetting):
    """
    引数settingのカメラ設定データをデータベースに新規追加する
    :param db:
    :param setting:
    :return:
    """
    perspective_transformation_setting = json.dumps([setting.roi_x1, setting.roi_y1, setting.roi_x2, setting.roi_y2,
                                                     setting.roi_x3, setting.roi_y3, setting.roi_x4, setting.roi_y4])

    segment_on_color = json.dumps({"b": setting.on_color_blue, "g": setting.on_color_green, "r": setting.on_color_red})
    segment_off_color = json.dumps(
        {"b": setting.off_color_blue, "g": setting.off_color_green, "r": setting.off_color_red})

    new_setting = OCRSetting(id=str(uuid.uuid4()),
                             camera_port=setting.camera_port,
                             setting_image=setting.image_name,
                             unit=setting.value_unit,
                             setting_name=setting.setting_name,
                             is_segment_points_detection=setting.is_segment_outline_setting_enabled,
                             perspective_transformation_setting=perspective_transformation_setting,
                             segment_on_color=segment_on_color,
                             segment_off_color=segment_off_color,
                             segment_point_setting=json.dumps(setting.segment_point_table),
                             segment_region_settings=json.dumps(setting.segment_region_table),
                             segment_region_space=int(setting.segment_region_space),
                             decimal_point_setting=json.dumps(setting.decimal_point_table),
                             is_setting_disabled=setting.is_setting_disabled,
                             pivot_color=setting.pivot_color_select,
                             pivot_size=int(setting.pivot_size)

                             )

    db.add(new_setting)
    db.commit()





def setting_ids_and_names(db: Session):
    temps=db.query(OCRSetting.id,OCRSetting.setting_name).all()
    send_data=[]
    for temp in temps:
        send_data.append({"value":temp[0],"name":temp[1]})

    return send_data

def get_ocr_setting(setting_id:str,db: Session):
    setting=db.query(OCRSetting).filter(OCRSetting.id == setting_id).all()[0]
    send_data = UIOCRSetting(
        setting_name=setting.setting_name,
        value_unit=setting.unit,
        camera_port=setting.camera_port,
        image_name=setting.setting_image,
        segment_region_table=json.loads(setting.segment_region_settings),
        segment_region_space=setting.segment_region_space,
        segment_point_table=json.loads(setting.segment_point_setting),
        roi_x1=json.loads(setting.perspective_transformation_setting)[0],
        roi_y1=json.loads(setting.perspective_transformation_setting)[1],
        roi_x2=json.loads(setting.perspective_transformation_setting)[2],
        roi_y2=json.loads(setting.perspective_transformation_setting)[3],
        roi_x3=json.loads(setting.perspective_transformation_setting)[4],
        roi_y3=json.loads(setting.perspective_transformation_setting)[5],
        roi_x4=json.loads(setting.perspective_transformation_setting)[6],
        roi_y4=json.loads(setting.perspective_transformation_setting)[7],
        on_color_blue=json.loads(setting.segment_on_color)["b"],
        on_color_green=json.loads(setting.segment_on_color)["g"],
        on_color_red=json.loads(setting.segment_on_color)["r"],
        off_color_blue=json.loads(setting.segment_off_color)["b"],
        off_color_green=json.loads(setting.segment_off_color)["g"],
        off_color_red=json.loads(setting.segment_off_color)["r"],
        is_setting_disabled=setting.is_setting_disabled,
        is_segment_outline_setting_enabled=setting.is_segment_points_detection,
        decimal_point_table=json.loads(setting.decimal_point_setting),
        pivot_color_select=setting.pivot_color,
        pivot_size=setting.pivot_size
    )

    return send_data


def update_ocr_setting(db: Session,setting:UIOCRSetting2):
    perspective_transformation_setting = json.dumps([setting.roi_x1, setting.roi_y1, setting.roi_x2, setting.roi_y2,
                                                     setting.roi_x3, setting.roi_y3, setting.roi_x4, setting.roi_y4])

    segment_on_color = json.dumps({"b": setting.on_color_blue, "g": setting.on_color_green, "r": setting.on_color_red})
    segment_off_color = json.dumps(
        {"b": setting.off_color_blue, "g": setting.off_color_green, "r": setting.off_color_red})

    db_setting:OCRSetting = db.query(OCRSetting).get(setting.setting_id)

    db_setting.camera_port=setting.camera_port
    db_setting.setting_name=setting.setting_name
    db_setting.perspective_transformation_setting=perspective_transformation_setting
    db_setting.is_setting_disabled=setting.is_setting_disabled
    db_setting.pivot_size=setting.pivot_size
    db_setting.segment_region_space=int(setting.segment_region_space)
    db_setting.unit=setting.value_unit
    db_setting.decimal_point_setting=json.dumps(setting.decimal_point_table)
    db_setting.pivot_color=setting.pivot_color_select
    db_setting.is_segment_points_detection=setting.is_segment_outline_setting_enabled
    db_setting.segment_off_color= segment_off_color
    db_setting.segment_on_color = segment_on_color
    db_setting.segment_point_setting=json.dumps(setting.segment_point_table)
    db_setting.segment_region_settings=json.dumps(setting.segment_region_table)
    db_setting.setting_image = setting.image_name

    db.commit()
    db.refresh(db_setting)


def delete_ocr_setting(db: Session, setting_id: str):
    """
    引数usb_portに該当するカメラ設定を削除する
    :param db:
    :param usb_port:
    :return:
    """
    db.query(OCRSetting).filter(OCRSetting.id == setting_id).delete()
    db.commit()