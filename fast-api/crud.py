from sqlalchemy.orm import Session

from db_model import CameraSetting
from schema import UICameraSetting, CameraSettingCheck, USBPortResponse
import config


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
