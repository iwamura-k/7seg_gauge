# 標準モジュール
import json
# サードパーティーライブラリ
from sqlalchemy import  Column, Integer, String, Boolean,JSON
from sqlalchemy.ext.declarative import declarative_base
# 自作モジュール

Base = declarative_base()

# カメラ設定テーブルの定義
class CameraSetting(Base):
    __tablename__ = "camera_setting"
    usb_port = Column(String, primary_key=True, index=True)
    name = Column(String)
    is_valid = Column(Boolean)

    def __repr__(self):
        return json.dumps({"usb_port": self.usb_port, "name": self.name, "is_valid": self.is_valid})


class OCRSetting(Base):
    __tablename__ = "ocr_setting"

    id = Column(String, primary_key=True, index=True)
    camera_port = Column(Integer)
    setting_image = Column(String)
    setting_name = Column(String)
    unit = Column(String)
    is_segment_points_detection = Column(Boolean)
    perspective_transformation_setting = Column(JSON)
    segment_on_color = Column(JSON)
    segment_off_color = Column(JSON)
    segment_point_setting = Column(JSON)
    segment_region_settings = Column(JSON)
    segment_region_space = Column(Integer)
    decimal_point_setting = Column(JSON)
    is_setting_disabled = Column(Boolean)
    pivot_color = Column(String)
    pivot_size = Column(Integer)

