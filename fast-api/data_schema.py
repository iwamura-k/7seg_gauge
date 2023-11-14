from typing import Union, Literal, Optional
from pydantic import BaseModel, Field


class BaseCameraSetting(BaseModel):
    """
    カメラ設定のＤＢフォーマット
    """
    usb_port: str
    name: Optional[str]
    is_valid: bool


class UICameraSetting(BaseCameraSetting):
    """
    サーバーに入力されるカメラ設定のフォーマット
    """
    is_delete: bool


class CameraSettingResponse(BaseCameraSetting):
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


class SettingImageResponse(BaseModel):
    """
    設定画像のレスポンス
    """
    name: str
    value: str

    class Config:
        orm_mode = True


class UIOCRSetting(BaseModel):
    setting_name: str
    value_unit: str
    camera_port: int
    image_name: str
    segment_region_table: list
    segment_region_space: int
    segment_point_table: list
    roi_x1: int
    roi_y1: int
    roi_x2: int
    roi_y2: int
    roi_x3: int
    roi_y3: int
    roi_x4: int
    roi_y4: int
    on_color_blue: int
    on_color_green: int
    on_color_red: int
    off_color_blue: int
    off_color_green: int
    off_color_red: int
    is_setting_disabled: bool
    is_segment_outline_setting_enabled: bool
    decimal_point_table: list
    pivot_color_select: str
    pivot_size: int


class UIOCRSetting2(BaseModel):
    setting_id: str
    setting_name: str
    value_unit: str
    camera_port: int
    image_name: str
    segment_region_table: list
    segment_region_space: int
    segment_point_table: list
    roi_x1: int
    roi_y1: int
    roi_x2: int
    roi_y2: int
    roi_x3: int
    roi_y3: int
    roi_x4: int
    roi_y4: int
    on_color_blue: int
    on_color_green: int
    on_color_red: int
    off_color_blue: int
    off_color_green: int
    off_color_red: int
    is_setting_disabled: bool
    is_segment_outline_setting_enabled: bool
    decimal_point_table: list
    pivot_color_select: str
    pivot_size: int


class BaseThresholdSetting(BaseModel):
    setting_id: str
    is_alert: bool
    abnormal_low_th: float
    alert_low_th: float
    alert_high_th: float
    abnormal_high_th: float


class UIThresholdSetting(BaseThresholdSetting):
    setting_name:Optional[str]


class UISenderSetting(BaseModel):
    smtp_server: str
    smtp_port: str
    sender_address: str
    sender_password: str
    class Config:
        orm_mode = True

class UIReceiverSetting(BaseModel):
    address:str
    is_disable:bool
    is_delete:bool


class UIMailSetting(BaseModel):
    sender_setting:UISenderSetting
    receiver_setting:list[UIReceiverSetting]

class UIReceiverSettingResponse(BaseModel):
    address:str
    is_disable:bool

    class Config:
        orm_mode = True

class UIMailSettingResponse(BaseModel):
    sender_setting:UISenderSetting
    receiver_setting:list[dict]

    class Config:
        orm_mode = True