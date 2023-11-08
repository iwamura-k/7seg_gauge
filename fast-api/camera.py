import subprocess
import config
import cv2


class UsbCamera:

    def __init__(self, port):
        self.port = port

    def take_photo(self):
        usb_device = UsbVideoDevice()
        usb_port = f"PORT_{self.port}"
        s = config.USB_DEV_ID[usb_port]
        print(s)
        video_id = usb_device.get_video_id(s)
        if video_id is not None:
            cap = cv2.VideoCapture(video_id)
            # 画像をキャプチャする
            ret, frame = cap.read()
            if ret:
                return frame


class UsbVideoDevice():
    def __init__(self):
        self.__device_list = []

        try:
            cmd = 'ls -la /dev/v4l/by-id'
            res = subprocess.check_output(cmd.split())
            by_id = res.decode()
        except Exception as e:
            print(e)

        try:
            cmd = 'ls -la /dev/v4l/by-path'
            res = subprocess.check_output(cmd.split())
            by_path = res.decode()
        except Exception as e:
            print(e)

        # デバイス名取得
        device_names = {}
        for line in by_id.split('\n'):
            if '../../video' in line:
                tmp = self.__split(line, ' ')
                if "" in tmp:
                    tmp.remove("")
                name = tmp[8]
                device_id = tmp[10].replace('../../video', '')
                device_names[device_id] = name

        # ポート番号取得
        for line in by_path.split('\n'):
            if 'usb-0' in line:
                tmp = self.__split(line, '0-usb-0:1.')
                tmp = self.__split(tmp[1], ':')
                port = tmp[0]
                tmp = self.__split(tmp[1], '../../video')
                device_id = int(tmp[1])
                if device_id % 2 == 0:
                    name = device_names[str(device_id)]
                    self.__device_list.append((device_id, port, name))

    @staticmethod
    def __split(string, val):
        tmp = string.split(val)
        if '' in tmp:
            tmp.remove('')
        return tmp

    # 認識しているVideoデバイスの一覧を表示する
    def display_video_devices(self):
        for (device_id, port, name) in self.__device_list:
            print("/dev/video{} port:{} {}".format(device_id, port, name))

    # ポート番号（1..）を指定してVideoIDを取得する
    def get_video_id(self, port):
        print(self.__device_list)
        for (device_id, p, _) in self.__device_list:
            if p == port:
                return device_id
        return None
