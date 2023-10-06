import subprocess




def get_video_id(usb_string):
    cmd = "v4l2-ctl --list-devices"
    p = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE)
    ret = p.communicate()[0].decode()
    ret = ret.split("\n")
    # usb_port=camera_info.split("usb-0000:01:00.0-1.1.4")[1][:-2]
    index_list = [i for i, s in enumerate(ret) if usb_string in s]
    if index_list:
        index=index_list[0]
        video_id=ret[index + 1].split("/")[-1][5:]
        print(video_id)
        return video_id
    return None
