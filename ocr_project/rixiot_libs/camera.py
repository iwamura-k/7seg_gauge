import subprocess
import config
import cv2
import abc


def create_camera(camera_type, **kwargs):
    if camera_type == config.CameraType.USB:
        return UsbCamera(**kwargs)



class Camera(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def get_image(self):
        pass


class UsbCamera(Camera):

    def __init__(self, port, fps, buffer_size):
        self.port = port
        self.fps = fps
        self.buffer_size = buffer_size

    def _get_cap(self):
        video_id = self._get_video_id()
        #print(video_id)
        if video_id is not None:
            cap = cv2.VideoCapture(video_id)
            # 画像をキャプチャする
            cap.set(cv2.CAP_PROP_FPS, self.fps)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, self.buffer_size)
            return cap
        return None

    def _get_video_id(self):
        usb_hub = UsbHub(mapping=config.USB_PORT_MAPPING)
        #print(usb_hub.mapping)
        port_id = usb_hub.get_port_id(self.port)
        #print(f"port_id:{port_id}")
        usb_video_device = UsbVideoDevice()
        #print("ok")
        return usb_video_device.get_video_id(port_id)

    @staticmethod
    def _get_image(cap):
        ret, frame = cap.read()
        if ret:
            return frame
        return None

    def get_image(self):
        cap = self._get_cap()
        #print(cap)
        if cap is None:
            #print("none")
            return None
        image = None
        for i in range(self.fps):
            image = self._get_image(cap)
        cap.release()
        return image


class UsbHub:
    def __init__(self, mapping):
        self.mapping = mapping

    def get_port_id(self, port):
        return self.mapping[port]


class UsbVideoDevice:
    def __init__(self):
        self.__device_list = []
        #print("usb?")
        try:
            cmd = 'ls -la /dev/v4l/by-id'
            res = subprocess.check_output(cmd.split())
            by_id = res.decode()
        except Exception as e:
            print(e)
        #print("done")
        try:
            cmd = 'ls -la /dev/v4l/by-path'
            res = subprocess.check_output(cmd.split())
            by_path = res.decode()
        except Exception as e:
            print(e)
        #print("done")
      
          
                
        # ポート番号取得
        for line in by_path.split('\n'):
            
            if 'usb-0' in line:
                #print(line)
                tmp = self.__split(line, '0-usb-0:1.')
                tmp = self.__split(tmp[1], ':')
                port = tmp[0]
                #print(port)
                tmp = self.__split(tmp[1], '../../video')
                device_id = int(tmp[1])
                #print(f"device_id:{device_id}")
                self.__device_list.append((device_id, port))
        
        
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
        for (device_id, p) in self.__device_list:
            if p == port:
                print(device_id,port)
                return device_id
        return None
