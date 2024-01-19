import json
import uuid

from sqlalchemy.orm import Session
from .db_models import DBCameraSetting, DBOCRSetting, DBThresholdSetting, ReceiverMailAddresses
from .data_schema import UICameraSetting, CameraSettingCheck, USBPortResponse, UIOCRSetting, UIOCRSetting2, \
    CameraSettingResponse, BaseThresholdSetting, UIThresholdSetting, UIReceiverSetting, UIReceiverSettingResponse
import config
import cv2
#from schema import Coordinate


class CameraSetting:
    """
    システム画面のカメラ登録機能
    """

    @classmethod
    def check(cls, settings: list[UICameraSetting]):
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

    @classmethod
    def delete(cls, db: Session, usb_port: str):
        """
        引数usb_portに該当するカメラ設定を削除する
        :param db:
        :param usb_port:
        :return:
        """
        db.query(DBCameraSetting).filter(DBCameraSetting.usb_port == usb_port).delete()
        db.commit()

    @classmethod
    def update(cls, db: Session, setting: UICameraSetting):
        """
        データベースにあるカメラの設定データを引数settingの内容で更新する
        :param setting:
        :return:
        """
        db_setting = db.query(DBCameraSetting).get(setting.usb_port)
        db_setting.name = setting.name
        db_setting.is_valid = setting.is_valid
        db.commit()
        db.refresh(db_setting)

    @classmethod
    def insert(cls, db: Session, setting: UICameraSetting):
        """
        引数settingのカメラ設定データをデータベースに新規追加する
        :param db:
        :param setting:
        :return:
        """
        new_setting = DBCameraSetting(usb_port=setting.usb_port, name=setting.name, is_valid=setting.is_valid)
        db.add(new_setting)
        db.commit()

    @classmethod
    def get_all(cls, db: Session):
        """
        カメラのすべての設定データを取得し、返却する
        :param db:
        :return:
        """
        # print(db.query(CameraSetting).all())
        temps = db.query(DBCameraSetting.usb_port, DBCameraSetting.name, DBCameraSetting.is_valid).all()
        print(temps)
        send_data = []
        for temp in temps:
            send_data.append(CameraSettingResponse(usb_port=temp[0], name=temp[1], is_valid=temp[2]))
        return send_data

    @classmethod
    def get_available_usb_port(cls, db: Session):
        """
        データベースに登録されていないカメラのリストを取得し、返却する
        :param db:
        :return:
        """
        usb_ports = db.query(DBCameraSetting.usb_port).all()
        if usb_ports:
            usb_ports = [port[0] for port in db.query(DBCameraSetting.usb_port).all()]
            print(usb_ports)
            available_ports = [port for port in config.CAMERA_USB_PORTS if port not in usb_ports]
            print(available_ports)
            if available_ports:
                return [USBPortResponse(name=f"ポート{port}", value=port) for port in available_ports]
            else:
                return []

        available_ports = config.CAMERA_USB_PORTS
        return [USBPortResponse(name=f"ポート{port}", value=port) for port in available_ports]

    @classmethod
    def is_setting_exist(cls, db: Session, setting):
        """
        引数の設定データのＩＤがテーブルに存在する場合はTrue、存在しない場合はTrueを返す

        :param db:
        :param setting:
        :return:
        """
        old_setting = db.query(DBCameraSetting).filter(DBCameraSetting.usb_port == setting.usb_port).first()
        # 設定データがあれば、設定データをUPDATE操作
        if old_setting is not None:
            return True
        return False


class OCRSetting:
    """
    システム画面のOCR設定機能
    """

    @classmethod
    def convert_to_byte_image(cls, image):
        """
        画像をバイト文字列に変換して、返す
        :param image:
        :return:
        """
        # バイナリデータに変換
        _, img_encoded = cv2.imencode('.png', image)
        return img_encoded.tobytes()

    @classmethod
    def insert(cls, db: Session, setting):
        """
        引数settingのOCR設定データをデータベースに新規追加する
        :param db:
        :param setting:
        :return:
        """
        perspective_transformation_setting = json.dumps([setting.roi_x1, setting.roi_y1, setting.roi_x2, setting.roi_y2,
                                                         setting.roi_x3, setting.roi_y3, setting.roi_x4,
                                                         setting.roi_y4])

        segment_on_color = json.dumps(
            {"b": setting.on_color_blue, "g": setting.on_color_green, "r": setting.on_color_red})
        segment_off_color = json.dumps(
            {"b": setting.off_color_blue, "g": setting.off_color_green, "r": setting.off_color_red})
        setting_id = str(uuid.uuid4())
        recognition_points = cls.get_recognition_points(setting.segment_point_table)
        print(f"recognition_points:{recognition_points}")
        decimal_points = setting.decimal_point_table
        decimal_exponents = cls.get_decimal_exponents(decimal_points, recognition_points)
        print(decimal_exponents)

        new_setting = DBOCRSetting(id=setting_id,
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
                                   pivot_size=int(setting.pivot_size),
                                   segment_recognition_points=json.dumps(recognition_points),
                                   decimal_exponents=json.dumps(decimal_exponents)
                                   )

        db.add(new_setting)
        db.flush()
        return setting_id

    @classmethod
    def get_setting_ids_and_names(cls, db: Session):
        """
        設定IDと設定名のペアのリスト一覧をデータベースから取得し、返す
        :param db:
        :return:
        """
        temps = db.query(DBOCRSetting.id, DBOCRSetting.setting_name).all()
        send_data = []
        for temp in temps:
            send_data.append({"value": temp[0], "name": temp[1]})

        return send_data

    @classmethod
    def get(cls, setting_id: str, db: Session):
        """
        引数setting_idに該当する設定をデータベースから取得し、返す

        :param setting_id:
        :param db:
        :return:
        """
        setting = db.query(DBOCRSetting).filter(DBOCRSetting.id == setting_id).all()[0]
        print(setting)
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

    @classmethod
    def update(cls, db: Session, setting):
        """
        引数settingの内容で、データを上書き
        :param db:
        :param setting:
        :return:
        """
        perspective_transformation_setting = json.dumps([setting.roi_x1, setting.roi_y1, setting.roi_x2, setting.roi_y2,
                                                         setting.roi_x3, setting.roi_y3, setting.roi_x4,
                                                         setting.roi_y4])

        segment_on_color = json.dumps(
            {"b": setting.on_color_blue, "g": setting.on_color_green, "r": setting.on_color_red})
        segment_off_color = json.dumps(
            {"b": setting.off_color_blue, "g": setting.off_color_green, "r": setting.off_color_red})

        recognition_points = cls.get_recognition_points(setting.segment_point_table)
        decimal_points = setting.decimal_point_table
        decimal_exponents = cls.get_decimal_exponents(decimal_points, recognition_points)
        print(decimal_exponents)
        db_setting: DBOCRSetting = db.query(DBOCRSetting).get(setting.setting_id)

        db_setting.camera_port = setting.camera_port
        db_setting.setting_name = setting.setting_name
        db_setting.perspective_transformation_setting = perspective_transformation_setting
        db_setting.is_setting_disabled = setting.is_setting_disabled
        db_setting.pivot_size = setting.pivot_size
        db_setting.segment_region_space = int(setting.segment_region_space)
        db_setting.unit = setting.value_unit
        db_setting.decimal_point_setting = json.dumps(setting.decimal_point_table)
        db_setting.pivot_color = setting.pivot_color_select
        db_setting.is_segment_points_detection = setting.is_segment_outline_setting_enabled
        db_setting.segment_off_color = segment_off_color
        db_setting.segment_on_color = segment_on_color
        db_setting.segment_point_setting = json.dumps(setting.segment_point_table)
        db_setting.segment_region_settings = json.dumps(setting.segment_region_table)
        db_setting.setting_image = setting.image_name
        db_setting.segment_recognition_points = json.dumps(recognition_points)
        db_setting.decimal_exponents = json.dumps(decimal_exponents)
        db.commit()
        db.refresh(db_setting)

    @classmethod
    def delete(cls, db: Session, setting_id: str):
        """
        引数setting_idに該当するOCR設定を削除する
        :param db:
        :param usb_port:
        :return:
        """
        db.query(DBOCRSetting).filter(DBOCRSetting.id == setting_id).delete()
        db.commit()

    @classmethod
    def calculate_recognition_points(cls, points):
        recognition_points = []
        for point in points:
            upper_left_x = int(point["segment_upper_left_x"])
            upper_left_y = int(point["segment_upper_left_y"])
            upper_right_x = int(point["segment_upper_right_x"])
            upper_right_y = int(point["segment_upper_right_y"])
            lower_right_x = int(point["segment_lower_right_x"])
            lower_right_y = int(point["segment_lower_right_y"])
            lower_left_x = int(point["segment_lower_left_x"])
            lower_left_y = int(point["segment_lower_left_y"])

            upper_middle_x = int((upper_left_x + upper_right_x) / 2)
            upper_middle_y = int((upper_left_y + upper_right_y) / 2)

            lower_middle_x = int((lower_left_x + lower_right_x) / 2)
            lower_middle_y = int((lower_left_y + lower_right_y) / 2)

            middle_x = int((upper_middle_x + lower_middle_x) / 2)
            middle_y = int((upper_middle_y + lower_middle_y) / 2)

            r_lower_left_x = lower_left_x + int((upper_left_x - lower_left_x) / 4)
            r_lower_left_y = lower_left_y + int((upper_left_y - lower_left_y) / 4)

            r_upper_left_x = lower_left_x + int(3 * (upper_left_x - lower_left_x) / 4)
            r_upper_left_y = lower_left_y + int(3 * (upper_left_y - lower_left_y) / 4)

            r_lower_right_x = lower_right_x + int((upper_right_x - lower_right_x) / 4)
            r_lower_right_y = lower_right_y + int((upper_right_y - lower_right_y) / 4)

            r_upper_right_x = lower_right_x + int(3 * (upper_right_x - lower_right_x) / 4)
            r_upper_right_y = lower_right_y + int(3 * (upper_right_y - lower_right_y) / 4)

            upper_middle = [upper_middle_x, upper_middle_y]
            middle = [middle_x, middle_y]
            lower_middle = [lower_middle_x, lower_middle_y]
            r_upper_left = [r_upper_left_x, r_upper_left_y]
            r_lower_left = [r_lower_left_x, r_lower_left_y]
            r_upper_right = [r_upper_right_x, r_upper_right_y]
            r_lower_right = [r_lower_right_x, r_lower_right_y]

            recognition_points.append(
                [upper_middle, middle, lower_middle, r_upper_left, r_lower_left, r_upper_right, r_lower_right])
        return recognition_points

    @classmethod
    def sort_recognition_points(cls, points):
        sorted_points = sorted(points, key=lambda coord: coord[0][0])
        return sorted_points

    @classmethod
    def get_recognition_points(cls, points):
        recognition_points = cls.calculate_recognition_points(points)
        sorted_recognition_points = cls.sort_recognition_points(recognition_points)

        return sorted_recognition_points

    @classmethod
    def calculate_segment_exponent(cls, decimal_x, segment_points):
        for i, segment_point in enumerate(segment_points):
            segment_middle_x = segment_point[1][0]
            if decimal_x < segment_middle_x:
                return len(segment_points) - i
        else:
            return 0

    @classmethod
    def get_decimal_exponents(cls, decimal_points, segment_points):
        decimal_exponents = []
        for point in decimal_points:
            x = int(point["decimal_x"])
            exponent = cls.calculate_segment_exponent(x, segment_points)
            decimal_exponents.append(exponent)

        return decimal_exponents


class ThresholdSetting:

    @classmethod
    def update(cls, db: Session, setting: UIThresholdSetting):
        """
        データベースにある閾値の設定データを引数settingの内容で更新する
        :param setting:
        :return:
        """
        db_setting = db.query(DBThresholdSetting).get(setting.setting_id)
        db_setting.is_alert = setting.is_alert
        db_setting.abnormal_low_th = setting.abnormal_low_th
        db_setting.alert_low_th = setting.alert_low_th
        db_setting.alert_high_th = setting.alert_high_th
        db_setting.abnormal_high_th = setting.abnormal_high_th

        db.commit()
        db.refresh(db_setting)

    @classmethod
    def insert(cls, db: Session, setting: BaseThresholdSetting):
        """
        引数settingの閾値設定データをデータベースに新規追加する
        :param db:
        :param setting:
        :return:
        """
        new_setting = DBThresholdSetting(
            setting_id=setting.setting_id,
            is_alert=setting.is_alert,
            abnormal_low_th=setting.abnormal_low_th,
            alert_low_th=setting.alert_low_th,
            alert_high_th=setting.alert_high_th,
            abnormal_high_th=setting.abnormal_high_th
        )

        db.add(new_setting)
        db.commit()

    @classmethod
    def get_all(cls, db: Session):
        """
        すべての閾値設定データを取得し、返却する
        :param db:
        :return:
        """
        # print(db.query(CameraSetting).all())
        return db.query(DBThresholdSetting).all()


class JsonTextStorage:
    """
    テキストファイルにJSONデータを保存、読み込みするクラス
    """

    def __init__(self, file_path):
        self.file_path = file_path

    def save(self, data):
        with open(self.file_path, encoding="utf-8", mode="w") as f:
            f.write(json.dumps(dict(data)))

    def load(self):
        with open(self.file_path, encoding="utf-8") as f:
            data = json.load(f)

        return data


class MailSetting:
    """
    システムのメール送信設定画面
    """

    @classmethod
    def delete(cls, db: Session, address: str):
        """
        引数addressに該当する受信者アドレス設定を削除する
        :param db:
        :param usb_port:
        :return:
        """
        db.query(ReceiverMailAddresses).filter(ReceiverMailAddresses.address == address).delete()
        db.commit()

    @classmethod
    def update(cls, db: Session, setting: UIReceiverSetting):
        """
        データベースにある受信者アドレスの設定データを引数settingの内容で更新する
        :param setting:
        :return:
        """
        db_setting = db.query(ReceiverMailAddresses).get(setting.address)
        db_setting.is_disable = setting.is_disable
        db.commit()
        db.refresh(db_setting)

    @classmethod
    def insert(cls, db: Session, setting: UIReceiverSetting):
        """
        引数settingの受信者アドレス設定データをデータベースに新規追加する
        :param db:
        :param setting:
        :return:
        """
        new_setting = ReceiverMailAddresses(address=setting.address, is_disable=setting.is_disable)
        db.add(new_setting)
        db.commit()

    @classmethod
    def get_all(cls, db: Session):
        """
        すべての受信者アドレス設定データを取得し、返却する
        :param db:
        :return:
        """
        # print(db.query(CameraSetting).all())
        send_data = db.query(ReceiverMailAddresses).all()
        print(send_data)

        return send_data

    @classmethod
    def is_setting_exist(cls, db: Session, setting):
        """
        引数settingの受信者アドレス設定データがデータベースに存在する場合は、True,そうでなければFalseを返す
        :param db:
        :param setting:
        :return:
        """
        old_setting = db.query(ReceiverMailAddresses).filter(ReceiverMailAddresses.address == setting.address).first()
        # 設定データがあれば、設定データをUPDATE操作
        if old_setting is not None:
            return True
        return False
