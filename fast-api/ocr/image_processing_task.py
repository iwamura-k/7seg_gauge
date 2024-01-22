import glob
import json
import os
import time
import numpy as np

from watchdog.events import FileSystemEventHandler
from watchdog.observers.polling import PollingObserver

import config
from common_libs.db_models import DBOCRSetting, DBThresholdSetting, SensorValue2, ScopedSessionClass, DBCameraSetting, \
    ReceiverMailAddresses
from common_libs.models import JsonTextStorage
from common_libs.schema import Coordinate
from common_libs import utils
from rixiot_libs.event import ValueEventCalculator, EventPolicy
from rixiot_libs.mail import EmailMessagePool, EmailMessageCreator, EmailSender
from rixiot_libs.ocr import OCRHandler, TesseractOCREngine, SegmentOCREngine, DecimalPointOCREngine
from rixiot_libs.mqtt_factory import MQTTClientFactory, on_connect, on_disconnect


def load_setting_ids(camera_port):
    session = ScopedSessionClass()
    settings = session.query(DBOCRSetting.id).filter(DBOCRSetting.camera_port == camera_port).all()
    id_list = [setting[0] for setting in settings]
    return id_list


def get_setting_ids():
    session = ScopedSessionClass()
    setting_ids = [arr[0] for arr in session.query(DBOCRSetting.id).all()]
    return setting_ids


class OCRHandlerFactory:

    def load_ocr_setting(self, setting_id):
        session = ScopedSessionClass()
        setting = session.query(DBOCRSetting).filter(DBOCRSetting.id == setting_id).all()[0]
        return setting

    def create_ocr_handlers(self):
        setting_ids = get_setting_ids()
        handlers = {setting_id: self.create_ocr_handler(setting_id) for setting_id in setting_ids}
        return handlers

    def create_ocr_handler(self, setting_id):
        ocr_points = self._calculate_ocr_points(setting_id)
        display_region = self._load_display_region(setting_id)
        segment_regions = self._load_segment_regions(setting_id)
        on_color = self._load_on_color(setting_id)
        off_color = self._load_off_color(setting_id)
        tesseract_ocr_engine = self._create_tesseract_ocr_engine()
        decimal_point_ocr_engine = self._create_decimal_point_ocr_engine(setting_id)
        is_segment_points_detection = self._load_is_segment_points_detection(setting_id)
        if is_segment_points_detection:
            segment_ocr_engine = self._create_segment_ocr_engine(setting_id)
        else:
            segment_ocr_engine = None

        return OCRHandler(
            tesseract_ocr_engine=tesseract_ocr_engine, segment_ocr_engine=segment_ocr_engine,
            decimal_point_ocr_engine=decimal_point_ocr_engine, ocr_points=ocr_points, display_region=display_region,
            segment_regions=segment_regions, on_color=on_color, off_color=off_color)

    def _load_display_region(self, setting_id):
        display_region = json.loads(self.load_ocr_setting(setting_id).perspective_transformation_setting)
        return display_region

    def _load_on_color(self, setting_id):
        on_color = json.loads(self.load_ocr_setting(setting_id).segment_on_color)
        on_color = [on_color["b"], on_color["g"], on_color["r"]]

        return on_color

    def _load_off_color(self, setting_id):
        off_color = json.loads(self.load_ocr_setting(setting_id).segment_off_color)
        off_color = [off_color["b"], off_color["g"], off_color["r"]]
        return off_color

    def _calculate_segment_color(self, setting_id):
        on_color = self._load_on_color(setting_id)
        off_color = self._load_off_color(setting_id)
        if np.sum(off_color) > np.sum(on_color):
            return "black"
        return "white"

    def _create_tesseract_ocr_engine(self):
        tesseract_path = config.TESSERACT_PATH

        return TesseractOCREngine(ocr_config=config.OCR_CONFIG, tesseract_path=tesseract_path)

    def _create_segment_ocr_engine(self, setting_id):
        segment_color = self._calculate_segment_color(setting_id)
        return SegmentOCREngine(segment_color=segment_color)

    def _create_decimal_point_ocr_engine(self, setting_id):
        ocr_points = json.loads(self.load_ocr_setting(setting_id).decimal_point_setting)
        ocr_points = [Coordinate(x=int(point["decimal_x"]), y=int(point["decimal_y"])) for point in ocr_points]
        decimal_point_positions = json.loads(self.load_ocr_setting(setting_id).decimal_exponents)
        return DecimalPointOCREngine(ocr_points=ocr_points, decimal_point_positions=decimal_point_positions)

    def _load_segment_regions(self, setting_id):
        segment_region_settings = json.loads(self.load_ocr_setting(setting_id).segment_region_settings)
        return segment_region_settings

    def _load_is_segment_points_detection(self, setting_id):
        return self.load_ocr_setting(setting_id).is_segment_points_detection

    def _load_ocr_points(self, setting_id):
        return json.loads(self.load_ocr_setting(setting_id).segment_recognition_points)

    def _calculate_ocr_points(self, setting_id):
        segment_regions = self._load_segment_regions(setting_id)
        ocr_points = self._load_ocr_points(setting_id)
        int_ocr_points = []
        for segment_region, ocr_point in zip(segment_regions, ocr_points):
            offset_x = int(segment_region["region_left_x"])
            offset_y = int(segment_region["region_left_y"])
            int_ocr_points.append(
                [Coordinate(x=int(point[0]) - offset_x, y=int(point[1]) - offset_y) for point in ocr_point])

        return int_ocr_points


class EventCalculatorFactory:

    def create_event_calculators(self):
        setting_ids = get_setting_ids()
        handlers = {setting_id: self.create_event_calculator(setting_id) for setting_id in setting_ids}
        return handlers

    def load_th_setting(self, setting_id):
        session = ScopedSessionClass()
        setting = session.query(DBThresholdSetting).filter(DBOCRSetting.id == setting_id).first()
        return setting

    def create_event_calculator(self, setting_id):
        setting = self.load_th_setting(setting_id)
        alert_low_th = setting.alert_low_th
        alert_high_th = setting.alert_high_th
        abnormal_low_th = setting.abnormal_low_th
        abnormal_high_th = setting.abnormal_high_th
        return ValueEventCalculator(alert_low_th=alert_low_th, alert_high_th=alert_high_th,
                                    abnormal_low_th=abnormal_low_th, abnormal_high_th=abnormal_high_th)


class FileEventHandler:

    def __init__(self, directory=".", handler=FileSystemEventHandler()):
        self.observer = PollingObserver()
        self.handler = handler
        self.directory = directory

    def run(self):
        self.observer.schedule(self.handler, self.directory, recursive=True)
        self.observer.start()
        print(f"MyWatcher Running in {self.directory}")
        try:
            while True:
                time.sleep(1)
        except:
            self.observer.stop()
        self.observer.join()
        print("\nMyWatcher Terminated\n")



class EmailMessageFactory:
    def create(self, setting_id):
        camera_name = self.load_camera_name(setting_id)
        setting_name = self.load_setting_name(setting_id)
        return EmailMessageCreator(camera_name=camera_name, setting_name=setting_name)

    def create_all(self):
        setting_ids = get_setting_ids()
        handlers = {setting_id: self.create(setting_id) for setting_id in setting_ids}
        return handlers

    def load_camera_name(self, setting_id):
        session = ScopedSessionClass()
        setting = session.query(DBOCRSetting).filter(DBOCRSetting.id == setting_id).first()
        camera_port = setting.camera_port
        camera_setting = session.query(DBCameraSetting).filter(DBCameraSetting.usb_port == camera_port).first()
        return camera_setting.name

    def load_setting_name(self, setting_id):
        session = ScopedSessionClass()
        setting = session.query(DBOCRSetting).filter(DBOCRSetting.id == setting_id).first()
        return setting.setting_name


class EmailSenderFactory:

    def load_sender_mail_setting(self):
        file = JsonTextStorage(file_path=config.MAIL_SETTING_PATH)
        return file.load()

    def load_receiver_email_address(self):
        session = ScopedSessionClass()
        receiver_emails = [arr[0] for arr in session.query(ReceiverMailAddresses.address).all()]
        return ', '.join(receiver_emails) if receiver_emails else None

    def create_email_sender(self):
        sender_mail_setting = self.load_sender_mail_setting()
        smtp_server = sender_mail_setting["smtp_server"]
        sender_address = sender_mail_setting["sender_address"]
        smtp_port = sender_mail_setting["smtp_port"]
        sender_password = sender_mail_setting["sender_password"]
        receiver_emails = self.load_receiver_email_address()

        return EmailSender(smtp_server=smtp_server,
                           smtp_port=smtp_port,
                           sender_email=sender_address,
                           sender_password=sender_password,
                           receiver_emails=receiver_emails,
                           subject=config.SUBJECT
                           )

class EventPolicyFactory:

    def create_event_policy(self, setting_id):
        dead_band_sec = config.ALERT_MAIL_DEAD_BAND_SEC
        return EventPolicy(dead_band_sec=dead_band_sec)

    def create_event_policies(self):
        setting_ids = get_setting_ids()
        handlers = {setting_id: self.create_event_policy(setting_id) for setting_id in setting_ids}
        return handlers



class OCRProcessHandler(FileSystemEventHandler):

    def __init__(self, event_policies, message_pool, mqtt_client, mqtt_broker_ip, mqtt_broker_port, mqtt_keep_alive,
                 mqtt_topic):
        self.event_policies = event_policies
        self.message_pool = message_pool
        self.mqtt_client = mqtt_client
        self.mqtt_broker_ip = mqtt_broker_ip
        self.mqtt_broker_port = mqtt_broker_port
        self.mqtt_keep_alive = mqtt_keep_alive
        self.mqtt_topic = mqtt_topic

    def connect_mqtt(self):
        self.mqtt_client.connect(self.mqtt_broker_ip, self.mqtt_broker_port, self.mqtt_keep_alive)

    def on_created(self, event):
        directory = event.src_path.replace(os.sep, '/')
        print(directory)
        if os.path.isdir(directory):
            self.do_tasks(directory)

    def send_message_to_browser(self, message):
        self.connect_mqtt()
        self.mqtt_client.loop_start()
        self.mqtt_client.publish(self.mqtt_topic, message)
        self.mqtt_client.loop_stop()

    def do_tasks(self, directory):
        timestamp = self.extract_timestamp(directory)
        port = self.extract_port(directory)
        setting_ids = load_setting_ids(port)
        images = self.extract_image_pathes(directory)

        for setting_id in setting_ids:
            ocr_value = self.calculate_ocr_value(setting_id, images)
            event_type, is_send_alert = self.calculate_event_type_and_is_send_alert(setting_id, ocr_value,
                                                                                    timestamp)
            save_data = SensorValue2(
                timestamp=timestamp,
                setting_id=setting_id,
                value=str(ocr_value),
                event=event_type,
                is_sent=is_send_alert
            )

            temp=utils.to_time_object(timestamp)
            ui_timestamp=utils.to_time_string(temp)
            send_message = {"setting_id":setting_id,"ocr_value": ocr_value, "timestamp": ui_timestamp, "event_type": event_type}
            self.send_message_to_browser(json.dumps(send_message))

            self.save(save_data)

            if is_send_alert:
                alert_message = self.create_alert_message(setting_id, ocr_value, event_type)
                self.message_pool.add(alert_message)

        self.send_alert()

    def create_alert_message(self, setting_id, ocr_value, event_type):
        email_message_creator = EmailMessageFactory().create(setting_id)
        alert_message = email_message_creator.create_message(value=ocr_value, event=event_type)
        return alert_message

    def calculate_ocr_value(self, setting_id, images):
        ocr_handler = OCRHandlerFactory().create_ocr_handler(setting_id)
        ocr_value = ocr_handler.calculate_ocr_value(images)
        return ocr_value

    def calculate_event_type_and_is_send_alert(self, setting_id, ocr_value, timestamp):
        value_event_calculator = EventCalculatorFactory().create_event_calculator(setting_id)
        event_policy = self.event_policies[setting_id]
        raw_event_type = value_event_calculator.calculate_status(ocr_value)
        event_type, is_send_alert = event_policy.get_event_type(event_type=raw_event_type,
                                                                event_time=utils.to_time_object(timestamp))
        return event_type, is_send_alert

    def send_alert(self):
        email_sender = EmailSenderFactory().create_email_sender()

        alert_messages = self.message_pool.merge_to_string()
        print(alert_messages)
        if alert_messages != "":
            email_sender.send_email(alert_messages)

    def save(self, data):
        with ScopedSessionClass() as session:
            try:
                session.add(data)
                session.commit()
            except Exception as e:
                # エラーが発生した場合はロールバック
                session.rollback()
                raise e

    def extract_image_pathes(self, directory):
        print(glob.glob(f"{directory}/*"))
        return glob.glob(f"{directory}/*")

    def extract_timestamp(self, directory):
        return os.path.basename(directory)

    def extract_port(self, directroy):
        port_name = directroy.split("/")[3]
        return port_name.split("_")[-1]


def main():
    event_policies = EventPolicyFactory().create_event_policies()
    email_message_pool = EmailMessagePool()
    mqtt_client = MQTTClientFactory(on_connect=on_connect, on_disconnect=on_disconnect, user_name=None, password=None,
                                    on_message=None).create()
    ocr_process_handler = OCRProcessHandler(event_policies=event_policies,
                                            message_pool=email_message_pool,
                                            mqtt_broker_ip=config.MQTT_BROKER_IP,
                                            mqtt_client=mqtt_client,
                                            mqtt_broker_port=config.MQTT_BROKER_PORT,
                                            mqtt_keep_alive=config.MQTT_KEEP_ALIVE_SEC,
                                            mqtt_topic=config.MQTT_BROWSER_TOPIC)
    w = FileEventHandler("../files/images", ocr_process_handler)
    w.run()


if __name__ == "__main__":
    main()


