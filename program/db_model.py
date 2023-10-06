# 標準モジュール
import json
# サードパーティーライブラリ
from sqlalchemy import  Column, Integer, String, Boolean
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



