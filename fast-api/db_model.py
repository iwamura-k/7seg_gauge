# 標準モジュール
import json
# サードパーティーライブラリ
from sqlalchemy import  Column, Integer, String, Boolean,JSON
from sqlalchemy.ext.declarative import declarative_base
# 自作モジュール

Base = declarative_base()

# カメラ設定テーブルの定義
class CameraSetting(Base):
    __tablename__ = 'camera_setting'
    usb_port = Column(String, primary_key=True, index=True)
    name = Column(String)
    is_valid = Column(Boolean)

    def __repr__(self):
        return json.dumps({"usb_port": self.usb_port, "name": self.name, "is_valid": self.is_valid})


class OCRSetting(Base):
    __tablename__ = 'ocr_setting'

    id=Column(String,primary_key=True, index=True)
    camera_usb_port= Column(String)
    setting_image=Column(String)
    setting_name=Column(String)
    unit=Column(String)
    is_valid=Column(Boolean)
    is_keystone_correction=Column(Boolean)
    keystone_correction=Column(JSON)
    line_color=Column(String)
    digit_space=Column(Integer)
    digit_settings=Column(JSON)
    decimal_point_settings=Column(JSON)
    digit_color=Column(JSON)
    background_color=Column(JSON)





