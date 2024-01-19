import shutil
import time

import config
from common_libs.db_models import  SensorValue2,ScopedSessionClass

def get_used_percentage(target_directory):
    total, used, free = shutil.disk_usage(target_directory)
    return round(used / total, 3)

def main():
    while True:
        try:
            if get_used_percentage(config.TARGET_DIRECTORY) > config.MAX_PERCENTAGE_OF_DATA / 100:
                with ScopedSessionClass() as session:
                    try:
                        oldest_data = session.query(SensorValue2).order_by(SensorValue2.id).first()
                        print(oldest_data.timestamp)
                        if oldest_data:
                            session.delete(oldest_data)
                            session.commit()

                    except Exception as e:
                        # エラーが発生した場合はロールバック
                        session.rollback()
            time.sleep(5)
        except Exception as e:
            time.sleep(10)



if __name__=="__main__":
    main()




