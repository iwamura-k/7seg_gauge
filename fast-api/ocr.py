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


# セグメントパターンマッチング
def segment_pattern_matching(result):
    pattern = {"0000000": "", "1011111": "0", "0000011": "1", "1110110": "2", "1110011": "3", "0101011": "4",
               "1111001": "5", "1111101": "6",
               "1000011": "7", "1111111": "8", "1101011": "9", "1111011": "9", "0100000": "-"}
    result = "".join(result)
    if result in pattern:
        return pattern[result]
    else:
        return "NaN"



class OCR:

    def read_image(self):
        return cv2.imread(f"{DIR}/20230803154155.jpg")

    def get_perspective_image(self,array, img):
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

    def get_recognition_points(self):
        for info in segment_info:
            sx_ul = int(info[2])
            sy_ul = int(info[3])
            sx_ur = int(info[4])
            sy_ur = int(info[5])
            sx_lr = int(info[6])
            sy_lr = int(info[7])
            is_decimal = int(info[8])
            decimal_x = int(info[9])
            decimal_y = int(info[10])

            dx_ul_ur = sx_ur - sx_ul
            dy_ul_ur = sy_ur - sy_ul

            sx_ll = sx_lr - dx_ul_ur
            sy_ll = sy_lr - dy_ul_ur

            sx_lm = sx_ul + (sx_ll - sx_ul) / 2
            sy_lm = sy_ul + (sy_ll - sy_ul) / 2

            sx_rm = sx_ur + (sx_lr - sx_ur) / 2
            sy_rm = sy_ur + (sy_lr - sy_ur) / 2

            seg_p1 = [sx_ul + (sx_ur - sx_ul) / 2, sy_ul + (sy_ur - sy_ul) / 2]
            seg_p2 = [sx_lm + (sx_rm - sx_lm) / 2, sy_lm + (sy_rm - sy_lm) / 2]
            seg_p3 = [sx_ll + (sx_lr - sx_ll) / 2, sy_ll + (sy_lr - sy_ll) / 2]
            seg_p4 = [sx_ul + (sx_ll - sx_ul) / 4, sy_ul + (sy_ll - sy_ul) / 4]
            seg_p5 = [sx_ul + 3 * (sx_ll - sx_ul) / 4, sy_ul + 3 * (sy_ll - sy_ul) / 4]
            seg_p6 = [sx_ur + (sx_lr - sx_ur) / 4, sy_ur + (sy_lr - sy_ur) / 4]
            seg_p7 = [sx_ur + 3 * (sx_lr - sx_ur) / 4, sy_ur + 3 * (sy_lr - sy_ur) / 4]

            segment_pattern = [seg_p1, seg_p2, seg_p3, seg_p4, seg_p5, seg_p6, seg_p7, is_decimal,
                               [decimal_x, decimal_y]]
            array.append(segment_pattern)

    # 差分画像取得
    def get_diff_image(color, img):
        off_color = list(map(int, setting["off_color"]))
        # on_b=int(setting["on_color_blue"])
        # on_g=int(setting["on_color_green"])
        # on_r=int(setting["on_color_red"])
        on_color = list(map(int, setting["on_color"]))
        if np.sum(off_color) > np.sum(on_color):
            img3 = cv2.bitwise_not(img3)
            off_color = list(map(lambda n: 255 - n, off_color))
        off_color
        height, width = img.shape[:2]
        for i in range(width):
            for j in range(height):
                img[j, i] = list(map(lambda x, y: x - y if x > y else 0, img[j, i], color))
        return img


    def get_normalized_image(self,img):
        return cv2.normalize(img, None, alpha=0,beta=255, norm_type=cv2.NORM_MINMAX)


    def get_gray_image(self,img):
        if img.all()!=0:
            img,_=cv2.decolor(img)
        else:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        return img

    def get_gray_normalized_image(self,img):
        mi, ma = np.min(img), np.max(img)
        #print(mi,ma)
        gray = (255.0* (img - mi) / (ma-mi)).astype(np.uint8)
        #print(gray)
        return gray

    def get_threshold_image(self,img):

        I_MAX=255
        MEAN=cv2.ADAPTIVE_THRESH_GAUSSIAN_C
        #MEAN=cv2.ADAPTIVE_THRESH_MEAN_C
        SIZE=91
        C=0
        img= cv2.adaptiveThreshold(img, I_MAX, MEAN,cv2.THRESH_BINARY, SIZE, C)
        return img

# 結果を格納する配列の定義
result_a = []
result_o = []
result_str = ""
segments_num_a = []
segments_num_o = []
# 桁数分処理
for setting in array:
    # 桁の数字の認識結果を格納する配列の定義
    segment_result_a = []
    segment_result_o = []
    segment_num_a = 0
    segment_num_o = 0

    # セグメント数分処理
    for j in range(7):
        x = int(setting[j][0])
        y = int(setting[j][1])
        if img_a[y, x] == 255:
            segment_result_a.append("1")
            segment_num_a += 1
        else:
            segment_result_a.append("0")

        if img_o[y, x] == 255:
            segment_result_o.append("1")
            segment_num_o += 1
        else:
            segment_result_o.append("0")

    is_decimal = setting[7]
    decimal_x = setting[8][0]
    decimal_y = setting[8][1]

    segments_num_a.append(segment_num_a)
    segments_num_o.append(segment_num_o)
    # print(segments_num_a)
    # print(segments_num_o)
    # セグメントパターンマッチング
    # print(segment_result_a)
    # print(segment_result_o)
    matching_result_a = segment_pattern_matching(segment_result_a)
    matching_result_o = segment_pattern_matching(segment_result_o)
    # print(matching_result)

    if matching_result_a == "NaN":
        result_a.append("NaN")

    else:
        result_a.append(matching_result_a)

    if matching_result_o == "NaN":
        result_o.append("NaN")

    else:
        result_o.append(matching_result_o)

    if is_decimal == 1 and img_a[decimal_y, decimal_x] == 255:
        result_a.append(".")

    if is_decimal == 1 and img_o[decimal_y, decimal_x] == 255:
        result_o.append(".")

    print(result_a)
    print(result_o)

final_result = []
for o, a, o_num, a_num in zip(result_o, result_a, segments_num_o, segments_num_a):
    if o == "NaN" and a == "NaN":
        final_result.append("NaN")
    elif o == "NaN" and a != "NaN":
        final_result.append(a)
    elif o != "NaN" and a == "NaN":
        final_result.append(o)
    else:
        if o_num <= a_num:
            final_result.append(o)
        else:
            final_result.append(a)

print(final_result)
# final_result=["-",".","8","3","8"]

