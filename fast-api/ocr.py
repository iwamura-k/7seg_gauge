import numpy as np
import cv2



# 射影変換画像を求める
def get_perspective_image(array, img):
    # 変換前4点の座標　p1:左上　p2:右上 p3:右下 p4:左下
    p1 = [array[0], array[1]]
    p2 = [array[2], array[3]]
    p3 = [array[4], array[5]]
    p4 = [array[6], array[7]]

    # 　幅取得
    width_1 = np.linalg.norm(np.array(p2) - np.array(p1))
    width_2 = np.linalg.norm(np.array(p4) - np.array(p3))
    width = int(max(width_1, width_2))

    # 高さ取得
    height_1 = np.linalg.norm(np.array(p3) - np.array(p2))
    height_2 = np.linalg.norm(np.array(p4) - np.array(p1))
    height = int(max(height_1, height_2))
    print(width, height)
    # 変換前の4点
    src = np.float32([p1, p2, p3, p4])

    # 変換後の4点
    dst = np.float32([[0, 0], [width, 0], [width, height], [0, height]])

    # 変換行列
    M = cv2.getPerspectiveTransform(src, dst)

    # 射影変換・透視変換する
    output = cv2.warpPerspective(img, M, (width, height))

    return output