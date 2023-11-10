# 標準モジュール
import json
# サードパーティーライブラリ
from sqlalchemy import Column, Integer, String, Boolean, JSON, ForeignKey,Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
# 自作モジュール

Base = declarative_base()


# カメラ設定テーブルの定義
class DBCameraSetting(Base):
    __tablename__ = "camera_setting"
    usb_port = Column(String, primary_key=True, index=True)
    name = Column(String)
    is_valid = Column(Boolean)

    def __repr__(self):
        return json.dumps({"usb_port": self.usb_port, "name": self.name, "is_valid": self.is_valid})


class DBOCRSetting(Base):
    __tablename__ = "ocr_setting"
    id = Column(String, primary_key=True, index=True)
    camera_port = Column(Integer, ForeignKey(DBCameraSetting.usb_port, ondelete="CASCADE"))
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
    # 親テーブルとのリレーションシップを設定（オプショナル）
    parent = relationship("DBCameraSetting", back_populates="children")


class DBThresholdSetting(Base):
    __tablename__ = "threshold_setting"
    setting_id=Column(String,ForeignKey("ocr_setting.id", ondelete="CASCADE"),primary_key=True)
    is_alert=Column(Boolean,default=True)
    abnormal_low_th=Column(Float,default=-100)
    alert_low_th = Column(Float,default=-50)
    alert_high_th = Column(Float,default=50)
    abnormal_high_th = Column(Float,default=100)
    # 親テーブルとのリレーションシップを設定（オプショナル）
    parent = relationship("DBOCRSetting", back_populates="children")


class ReceiverMailAddresses(Base):
    __tablename__ = "reciever_mail_addresses"
    address=Column(String, primary_key=True, index=True)
    is_disable=Column(Boolean)

# 親テーブルに子テーブルとのリレーションシップを追加（オプショナル）
DBOCRSetting.children = relationship("DBThresholdSetting", back_populates="parent", cascade="all, delete")
DBCameraSetting.children = relationship("DBOCRSetting", back_populates="parent", cascade="all, delete")