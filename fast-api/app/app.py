# 標準ライブラリ
import glob
import io
import os
import sys

from common_libs import utils

sys.path.append('/home/pi/.local/lib/python3.9/site-packages')

# サードパーティーライブラリ
import cv2
from fastapi import FastAPI, Request, Depends, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, StreamingResponse
#from sqlalchemy.orm import sessionmaker, Session
from starlette.middleware.cors import CORSMiddleware
import uvicorn

# 自作モジュール
import config
from common_libs.data_schema import UICameraSetting, CameraSettingCheckResponse, \
    SettingImageResponse, UIOCRSetting, UIOCRSetting2, BaseThresholdSetting, UIThresholdSetting, UIMailSetting
from rixiot_libs.ocr import get_perspective_image,load_image
from common_libs.db_models import start_sqlorm,get_db
from ocr.image_processing_task import OCRHandlerFactory
from common_libs.models import CameraSetting, OCRSetting, ThresholdSetting, JsonTextStorage, MailSetting
from rixiot_libs.camera import create_camera
from common_libs.db_models import DBOCRSetting,DBThresholdSetting,DBCameraSetting

"""
ユーザーインターフェース(画面)からの要求を処理するAPIを定義
"""


app = FastAPI()
#  CORESを回避するために追加
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


@app.exception_handler(RequestValidationError)
async def handler(request: Request, exc: RequestValidationError):
    """
    :param request:
    :param exc:
    :return:
    """
    print(exc)
    return JSONResponse(content={}, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)




@app.post("/register_camera_setting/")
def register_camera_setting(settings: list[UICameraSetting], db = Depends(get_db)):
    """
    UIに入力されたカメラ設定をチェックし、チェックＯＫで設定をデータベースCRUD操作する
    チェックNGでチェックデータをＵＩに返却
    :param settings:
    :param db:
    :return:
    """
    print(settings)
    # 設定データをチェックし、判定データとチェックデータを取得
    is_success, check_data_list = CameraSetting.check(settings)
    # チェックNGで、チェックデータをＵＩに返却
    if not is_success:
        return CameraSettingCheckResponse(is_success=is_success, check_data=check_data_list)
    # チェックＯＫでCRUD操作
    for setting in settings:
        # 設定データの削除
        if setting.is_delete:
            CameraSetting.delete(db, setting.usb_port)
        else:
            if CameraSetting.is_setting_exist(db, setting):
                CameraSetting.update(db, setting)
            # 設定データが無ければ、設定データをINSERT
            else:
                CameraSetting.insert(db, setting)

    if is_success:
        return CameraSetting.get_all(db)


@app.get("/load_camera_setting/")
def load_camera_setting(db = Depends(get_db)):
    """
    カメラの設定をすべて取得し、UIに返却する
    :param db:
    :return:
    """

    return CameraSetting.get_all(db)


@app.get("/load_camera_setting_page_parameter/", response_model=list)
def load_camera_setting_page_parameter(db = Depends(get_db)):
    """
    カメラ設定UIのパラメータをUIに返却する
    :param db:
    :return:
    """

    return CameraSetting.get_available_usb_port(db)


@app.get("/get_camera/", response_model=list)
def get_camera(db = Depends(get_db)):
    """
    登録されているカメラ名とUSBポート値をリストで取得する
    :param db:
    :return:
    """

    return CameraSetting.get_all(db)


@app.get("/take_an_image/")
def take_an_image(usb_port):
    """
    選択したカメラで設定用の画像を撮影する
    :param usb_port:
    :param db:
    :return:
    """
    print(usb_port)
    camera=create_camera(config.CameraType.USB,port=usb_port,fps=config.FPS,buffer_size=1)
    frame=camera.get_image()
    if frame is not None:
        timestamp = utils.get_timestamp()
        print(timestamp)
        # 画像を保存する
        image_directory = f"{config.SETTING_IMAGE_PATH}/PORT_{usb_port}"
        os.makedirs(image_directory, exist_ok=True)
        cv2.imwrite(f"{image_directory}/{timestamp}.jpg", frame)
        return "画像の撮影に成功しました"
    else:
        return "画像の撮影に失敗しました"



@app.get("/delete_an_image/")
def delete_an_image(usb_port, image_name):
    """
    選択したカメラで設定用の画像を撮影する
    :param usb_port:
    :param db:
    :return:
    """

    s = config.USB_PORT_MAPPING[usb_port]

    image_path = f"{config.SETTING_IMAGE_PATH}/PORT_{usb_port}/{image_name}"
    try:
        os.remove(image_path)
    except FileNotFoundError:
        return "ファイルが存在しません"
    return "ファイルを削除しました"


@app.get("/get_setting_image/")
def get_setting_image(usb_port):
    """
    選択したカメラで設定用の画像を撮影する
    :param usb_port:
    :param db:
    :return:
    """
    print(usb_port)
    image_directory = f"{config.SETTING_IMAGE_PATH}/PORT_{usb_port}"
    images = glob.glob(f"{image_directory}/*")
    print(images)
    #images = [image.split("/")[-1] for image in images]
    images = [image.split("\\")[-1] for image in images]
    print(images)
    return [SettingImageResponse(name=image, value=image) for image in images]


@app.get("/do_keystone_correction/")
def add_setting(x1, y1, x2, y2, x3, y3, x4, y4, path):
    """
    選択したカメラで設定用の画像を撮影する
    :param image:
    :param usb_port:
    :param db:
    :return:
    """
    print(x1, y1, x2, y2, x3, y3, x4, y4, path)
    perspective_points = list(map(int, [x1, y1, x2, y2, x3, y3, x4, y4]))
    path=path.replace("%2F","/")
    print(f"{config.SETTING_IMAGE_PATH}/{path}")
    img = cv2.imread(filename=f"{config.SETTING_IMAGE_PATH}/{path}")
    perspective_image = get_perspective_image(perspective_points, img)
    byte_image = OCRSetting.convert_to_byte_image(perspective_image)
    # FastAPIのStreamingResponseを使用して画像をストリーミングレスポンスとして送信
    return StreamingResponse(io.BytesIO(byte_image), media_type="image/png")


# uvicorn app:app --reload --host=0.0.0.0 --port=8000

@app.post("/add_new_setting/")
def add_new_setting(data: UIOCRSetting, db = Depends(get_db)):
    ret = ""
    try:
        setting_id = OCRSetting.insert(db, data)
        setting_name = data.setting_name
        threshold_setting = BaseThresholdSetting(
            setting_id=setting_id,
            is_alert=True,
            abnormal_low_th=-100,
            alert_low_th=-50,
            alert_high_th=50,
            abnormal_high_th=100

        )
        ThresholdSetting.insert(db, threshold_setting)
        ret = "実行に成功しました。"
    except Exception as e:
        print(e)
        ret = "実行に失敗しました。"
    finally:
        return ret


@app.get("/setting_ids_and_names/")
def get_setting_ids_and_names(db = Depends(get_db)):
    return OCRSetting.get_setting_ids_and_names(db)


@app.get("/get_ocr_setting/")
def get_ocr_setting(setting_id: str, db = Depends(get_db)):
    return OCRSetting.get(setting_id, db)


@app.post("/update_ocr_setting/")
def update_ocr_setting(data: UIOCRSetting2, db = Depends(get_db)):
    ret = ""
    try:
        OCRSetting.update(db, data)
        ret = "実行に成功しました。"
    except Exception:
        ret = "実行に失敗しました。"
    finally:
        return ret


@app.get("/delete_ocr_setting/")
def delete_ocr_setting(id: str, db = Depends(get_db)):
    ret = ""
    try:
        OCRSetting.delete(db, id)
        ret = "実行に成功しました。"
    except Exception:
        ret = "実行に失敗しました。"
    finally:
        return ret


@app.get("/get_threshold_setting/")
def get_threshold_setting(db = Depends(get_db)):
    print(ThresholdSetting.get_all(db))
    threshold_settings = ThresholdSetting.get_all(db)
    ret = []
    for threshold_setting in threshold_settings:
        print(threshold_setting.setting_id)
        setting_name = OCRSetting.get(threshold_setting.setting_id, db).setting_name
        print(OCRSetting.get(threshold_setting.setting_id, db))
        ui_threshold_setting = UIThresholdSetting(
            setting_id=threshold_setting.setting_id,
            setting_name=setting_name,
            is_alert=threshold_setting.is_alert,
            abnormal_low_th=threshold_setting.abnormal_low_th,
            alert_low_th=threshold_setting.alert_low_th,
            alert_high_th=threshold_setting.alert_high_th,
            abnormal_high_th=threshold_setting.abnormal_high_th
        )
        ret.append(ui_threshold_setting)
    return ret


@app.post("/register_threshold_setting/")
def register_camera_setting(settings: list[UIThresholdSetting], db = Depends(get_db)):
    print(settings)
    ret = ""
    try:
        # チェックＯＫでCRUD操作
        for setting in settings:
            ThresholdSetting.update(db, setting)
        ret = "実行に成功しました。"
    except Exception:
        ret = "実行に失敗しました"
    finally:
        return ret


@app.post("/register_mail_settings/")
def register_reciever_mail_setting(settings: UIMailSetting, db = Depends(get_db)):
    print(settings)
    ret = ""

    os.makedirs(config.JSON_SETTING_FILE_DIR, exist_ok=True)
    json_storage = JsonTextStorage(file_path=config.MAIL_SETTING_PATH)
    json_storage.save(settings.sender_setting)

    for setting in settings.receiver_setting:
        # 設定データの削除
        print(setting.address)
        if setting.is_delete:
            MailSetting.delete(db, setting.address)
        else:
            if MailSetting.is_setting_exist(db, setting):
                MailSetting.update(db, setting)
            # 設定データが無ければ、設定データをINSERT
            else:
                print("insert")
                MailSetting.insert(db, setting)

    return ret


@app.get("/get_mail_setting/")
def get_mail_setting(db = Depends(get_db)):
    json_storage = JsonTextStorage(file_path=config.MAIL_SETTING_PATH)
    print("ok")
    receiver_setting = MailSetting.get_all(db)
    print(receiver_setting[0].address,receiver_setting[0].is_disable)
    sender_setting = json_storage.load()
    return {"receiver_setting":receiver_setting, "sender_setting":sender_setting}


@app.get("/test_ocr_setting/")
def test_ocr_setting(usb_port:str,image:str,setting_id:str,db = Depends(get_db)):
    print(usb_port,image,setting_id)
    ocr_handler = OCRHandlerFactory().create_ocr_handler(setting_id=setting_id)
    image_path = f"{config.SETTING_IMAGE_PATH}/PORT_{usb_port}/{image}"
    image=load_image(image_path)
    ocr_string = ocr_handler.image_to_string(image)
    return ocr_string

@app.get("/get_dashboard_setting/")
def test_ocr_setting(db = Depends(get_db)):
    ret=[]
    setting_ids= [setting.id for setting in db.query(DBOCRSetting).all() if not setting.is_setting_disabled]
    for setting_id in setting_ids:
        setting=db.query(DBOCRSetting).filter(DBOCRSetting.id == setting_id).all()[0]
        setting_name=setting.setting_name
        setting_unit=setting.unit
        camera_port=setting.camera_port
        camera_name=db.query(DBCameraSetting).filter(DBCameraSetting.usb_port== camera_port).all()[0].name

        setting_dict={"setting_id":setting_id,"setting_name":setting_name,"setting_unit":setting_unit,"camera_name":camera_name}
        ret.append(setting_dict)


    return ret




if __name__ == "__main__":
    start_sqlorm()
    uvicorn.run(app, host="0.0.0.0", port=8000)