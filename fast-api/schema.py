from typing import Union, Literal, Optional
from pydantic import BaseModel, Field


class DBCameraSetting(BaseModel):
    """
    カメラ設定のＤＢフォーマット
    """
    usb_port: str
    name: Optional[str]
    is_valid: bool


class UICameraSetting(DBCameraSetting):
    """
    サーバーに入力されるカメラ設定のフォーマット
    """
    is_delete: bool


class CameraSettingResponse(DBCameraSetting):
    """
    サーバーから出力されるカメラ設定のフォーマット
    """

    class Config:
        orm_mode = True


class CameraSettingCheck(BaseModel):
    """
    カメラ設定のチェックデータのフォーマット
    """
    usb_port: str
    name: str
    is_valid: str


class CameraSettingCheckResponse(BaseModel):
    """
    カメラ設定のチェックデータのレスポンスのフォーマット
    """
    is_success: bool
    check_data: list[CameraSettingCheck]

    class Config:
        orm_mode = True


class USBPortResponse(BaseModel):
    """
    使用可能なUSBポートのリストのフォーマット
    """
    name: str
    value: str

    class Config:
        orm_mode = True
