# 標準ライブラリ
import datetime
import sys

sys.path.append('/home/pi/.local/lib/python3.9/site-packages')

# サードパーティーライブラリ
from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from starlette.middleware.cors import CORSMiddleware
import uvicorn

# 自作モジュール
import config
import crud
from db_model import Base, CameraSetting
from schema import UICameraSetting, CameraSettingResponse, DBCameraSetting, CameraSettingCheckResponse, \
    AvailableUSBPortResponse
from typing import Union, Literal

# SQLAlchemyEngine の作成
CONNECT_STR = '{}://{}:{}@{}:{}/{}'.format(config.DATABASE, config.USER, config.PASSWORD, config.HOST, config.PORT,
                                           config.DB_NAME)
engine = create_engine(
    CONNECT_STR,
    encoding="utf-8",
    echo=False
)
# DBセッションを作るクラスを作成
SessionClass = sessionmaker(engine)
# DBテーブルを作成
Base.metadata.create_all(bind=engine)

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


# Dependency
def get_db():
    db = SessionClass()
    try:
        yield db
    finally:
        db.close()


@app.post("/register_camera_setting/", response_model=Union[list[CameraSettingResponse], CameraSettingCheckResponse])
def register_camera_setting(settings: list[UICameraSetting], db: Session = Depends(get_db)):
    """
    UIに入力されたカメラ設定をチェックし、チェックＯＫで設定をデータベースCRUD操作する
    チェックNGでチェックデータをＵＩに返却
    :param settings:
    :param db:
    :return:
    """
    print(settings)
    # 設定データをチェックし、判定データとチェックデータを取得
    is_success, check_data_list = crud.check_camera_setting(settings)
    # チェックNGで、チェックデータをＵＩに返却
    if not is_success:
        return CameraSettingCheckResponse(is_success=is_success, check_data=check_data_list)
    # チェックＯＫでCRUD操作
    for setting in settings:
        # 設定データの削除
        if setting.is_delete:
            crud.delete_camera_setting(db, setting.usb_port)
        else:
            old_setting = db.query(CameraSetting).filter(CameraSetting.usb_port == setting.usb_port).first()
            # 設定データがあれば、設定データをUPDATE操作
            if old_setting is not None:

                crud.update_camera_setting(db, setting)
            # 設定データが無ければ、設定データをINSERT
            else:
                crud.insert_camera_setting(db, setting)

    if is_success:
        return crud.get_all_camera_setting(db)


@app.get("/load_camera_setting/", response_model=list[CameraSettingResponse])
def load_camera_setting(db: Session = Depends(get_db)):
    """
    カメラの設定をすべて取得し、UIに返却する
    :param db:
    :return:
    """
    return crud.get_all_camera_setting(db)


@app.get("/load_camera_setting_page_parameter/", response_model=list)
def load_camera_setting_page_parameter(db: Session = Depends(get_db)):
    """
    カメラ設定UIのパラメータをUIに返却する
    :param db:
    :return:
    """
    return crud.get_available_usb_port(db)

# uvicorn app:app --reload --host=0.0.0.0

