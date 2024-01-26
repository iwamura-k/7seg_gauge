from common_libs.db_models import DBCameraSetting,SensorValue2,ScopedSessionClass
from common_libs import utils



def get_camera_list():
    with ScopedSessionClass() as session:
        try:
            settings = session.query(DBCameraSetting.usb_port).all()
            usb_port=[setting[0] for setting in settings]
            return usb_port


        except Exception as e:
            # エラーが発生した場合はロールバック
            session.rollback()
            return None



cameras=["camera1","camera2"]
def main():
    while True:
        current_time=utils.get_time()
        camera_list=get_camera_list()
        print(current_time,camera_list)

        for
        """
        for camera in cameras:
            with ScopedSessionClass() as session:
                try:
                    setting = session.query(SensorValue2).filter(SensorValue2.id == setting_id).first()
                except Exception as e:
                    # エラーが発生した場合はロールバック
                    session.rollback()
                    raise e
        """



if __name__=="__main__":
    main()