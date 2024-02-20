# 標準ライブラリ
import os
import numpy as np
import collections
# サードパーティーライブラリ
import cv2
from PIL import Image
import pytesseract
# 自作モジュール
import uuid
from common_libs.schema import Coordinate


def load_image(image_path):
    return cv2.imread(image_path)


def get_perspective_image(corner_points, image):
    """
    入力画像を４隅の入力点を基に、射影変換し、射影変換された画像を出力する
    :param corner_points: 射影変換に必要な画像上の４隅の座標["左上X","左上Y","右上X","右上Y","右下X","右下Y","左下X","左下Y"]
    :param image: 入力画像
    :return: 射影変換された画像
    """
    # Extract corner points
    p1, p2, p3, p4 = [corner_points[i:i + 2] for i in range(0, len(corner_points), 2)]

    # Compute widths and heights of the new image
    width = int(max(np.linalg.norm(np.array(p2) - np.array(p1)),
                    np.linalg.norm(np.array(p4) - np.array(p3))))
    height = int(max(np.linalg.norm(np.array(p3) - np.array(p2)),
                     np.linalg.norm(np.array(p4) - np.array(p1))))

    # Source and destination points for perspective transformation
    src = np.float32([p1, p2, p3, p4])
    dst = np.float32([[0, 0], [width, 0], [width, height], [0, height]])

    # Compute the perspective transformation matrix and apply it
    transformation_matrix = cv2.getPerspectiveTransform(src, dst)
    transformed_image = cv2.warpPerspective(image, transformation_matrix, (width, height))

    return transformed_image


def calculate_difference_color(on_bgr_colors, off_bgr_colors):
    """
    消灯セグメントが２値化画像で点灯セグメントと誤認識しないように、画像全体から差分するＲ，Ｇ，Ｂの画素値を決める
    :param on_bgr_colors:点灯セグメントのＢＧＲ配列[255,21,15]
    :param off_bgr_colors:消灯セグメントのBGR配列[6,2,1]
    :return:配列[249,19,14]
    """

    on_bgr_colors = np.array(on_bgr_colors)
    off_bgr_colors = np.array(off_bgr_colors)

    return 255 - off_bgr_colors if np.sum(off_bgr_colors) > np.sum(on_bgr_colors) else off_bgr_colors


def to_difference_image(diff_bgr_colors, bgr_image):
    """
    画像全体のBGR値から消灯セグメントのBGR値を差分する。
    消灯セグメントが点灯セグメントと誤認識されないようにするため

    :param diff_bgr_colors:UIで設定された消灯セグメントのBGR値
    :param bgr_image:カラー画像
    :return:カラー画像から消灯セグメントのBGR値を差分した画像
    """
    # Ensure diff_color is an array for efficient operations
    diff_bgr_colors = np.array(diff_bgr_colors)

    # Vectorized operation to apply the difference color to the image
    # The np.clip function ensures the result stays within valid color range
    return np.clip(bgr_image - diff_bgr_colors, 0, 255).astype(np.uint8)


def normalize_image(bgr_image):
    """
    ２値化の前処理としてカラー画像の輝度を正規化する。
    :param bgr_image: カラー画像
    :return: 輝度が正規化されたカラー画像
    """
    # 各チャネルを分割する
    b, g, r = cv2.split(bgr_image)
    # 各チャネルを正規化する
    norm_b = cv2.normalize(b, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX)
    norm_g = cv2.normalize(g, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX)
    norm_r = cv2.normalize(r, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX)

    # 正規化されたチャネルを結合して新しい画像を作成
    normalized_image = cv2.merge([norm_b, norm_g, norm_r])
    return normalized_image


def to_gray_image(bgr_image):
    """
    カラー画像を白黒画像にする
    :param bgr_image: カラー画像
    :return: 白黒画像
    """
    if bgr_image.all() != 0:
        bgr_image, _ = cv2.decolor(bgr_image)
    else:
        bgr_image = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2GRAY)
    return bgr_image


def normalize_gray_image(gray_image):
    """
    ２値化を適切にするために、白黒画像の輝度を正規化する
    :param gray_image: 白黒画像
    :return: 輝度が正規化された白黒画像
    """
    mi, ma = np.min(gray_image), np.max(gray_image)
    #
    normalized_gray_image = (255.0 * (gray_image - mi) / (ma - mi)).astype(np.uint8)
    return normalized_gray_image


def binarize_gray_image_by_adaptive(gray_image):
    """
    適応的２値化で白黒画像を２値化する
    :param gray_image: 白黒画像
    :return: ２値化画像
    """
    height, width = gray_image.shape[:2]
    kernel_size = height if height < width else width
    if kernel_size % 2 == 0:
        kernel_size += 1
    gray_image = cv2.adaptiveThreshold(gray_image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, kernel_size,
                                       0)
    return gray_image


def binarize_gray_image_by_otsu(gray_image):
    """
    大津の２値化で白黒画像を２値化する
    :param gray_image: 白黒画像
    :return: ２値化画像
    """
    th, binary_image = cv2.threshold(gray_image, 0, 255, cv2.THRESH_OTSU)
    return binary_image


def roi_image(image, p_left_x, p_left_y, p_right_x, p_right_y):
    """
    画像imageから左上点p_leftと右下点p_rightで指定される長方形領域を切り出す
    :param image: 画像
    :param p_left:左上点(x,y)
    :param p_right: 右上点(x,y)
    :return: 左上点p_leftと右下点p_rightで指定される長方形領域の画像
    """
    image = image.copy()
    return image[p_left_y: p_right_y, p_left_x: p_right_x]


def blur_image(image):
    height, width = image.shape[:2]
    kernel_size = int(height // 10) if height < width else int(width // 10)
    if kernel_size % 2 == 0:
        kernel_size += 1
    return cv2.medianBlur(image, kernel_size)


def save_image(image, path):
    cv2.imwrite(path, image)


class TesseractOCREngine:

    def __init__(self, ocr_config, tesseract_path):
        """
        :param ocr_config: tesseractのOCR用設定文字列
        :param tesseract_path: tesseractの実行ファイルのパス
        :param display_region: ７セグ表示領域座標
        :param on_color: 点灯セグメントBGR値
        :param off_color: 消灯セグメントBGR値
        :param segment_regions: 桁数分の７セグメントの領域座標
        """
        self._ocr_config = ocr_config
        self._tesseract_path = tesseract_path

    def recognize_string(self, image):
        """
        セグメント画像をOCRして認識文字を返す

        :param segment_image: 一桁セグメントの画像
        :return: 一桁セグメントの画像のOCR文字
        """
        try:
            if os.name == 'nt':
                pytesseract.pytesseract.tesseract_cmd = self._tesseract_path
            ocr_string = pytesseract.image_to_string(Image.fromarray(image), config=self._ocr_config)
            return ocr_string.strip().replace(" ", "").replace("\n", "") if len(ocr_string) > 1 else "NaN"
        except Exception as e:
            print(f"Error during OCR extraction: {e}")
            return "Error"

    def _ocr(self, segment_image):
        """
        セグメント画像をOCRして認識文字を返す

        :param segment_image: 一桁セグメントの画像
        :return: 一桁セグメントの画像のOCR文字
        """
        try:
            # pytesseract.pytesseract.tesseract_cmd = self._tesseract_path
            ocr_string = pytesseract.image_to_string(Image.fromarray(segment_image), config=self._ocr_config)
            return ocr_string.strip().replace(" ", "").replace("\n", "") if len(ocr_string) > 1 else "NaN"
        except Exception as e:
            print(f"Error during OCR extraction: {e}")
            return "Error"


class SegmentOCREngine:
    """
    ７セグメントの点灯状態を判別し、７セグ画像をOCRするエンジン
    """
    matching_pattern = {"0000000": "", "1011111": "0", "0000011": "1", "1110110": "2", "1110011": "3", "0101011": "4",
                        "1111001": "5", "1111101": "6", "1000011": "7",  "1001011": "7","1111111": "8", "1101011": "9", "1111011": "9",
                        "0100000": "-"}

    def __init__(self, segment_color):
        self._segment_color = segment_color

    def _calculate_7seg_state(self, binary_image, ocr_points):
        """
        7つのセグメントの認識点のON,OFFを配列で返す
        :param binary_image: 2値化画像
        :param ocr_points:１セグメントの７つのＯＣＲ認識点座標
        :param display_region:1セグメントの画像領域(左上座標,右下座標)
        :return:
        """
        result = []
        # print(ocr_points)
        for point in ocr_points:
            x = point.x
            y = point.y
            segment_value = binary_image[y, x]
            result.append(self._calculate_segment_state(segment_value))
        print(self._segment_color)
        print(result)
        return result

    def _calculate_segment_state(self, segment_value):
        if segment_value > 0:
            return "1"
        return "0"

    def recognize_string(self, preprocessed_image, ocr_points):
        """
        セグメント画像をOCRして認識文字を返す

        :param segment_image: 一桁セグメントの画像
        :return: 一桁セグメントの画像のOCR文字
        """
        # cv2.imwrite(f"{str(uuid.uuid4())}_test.jpg",preprocessed_image)
        segment_state = self._calculate_7seg_state(preprocessed_image, ocr_points)
        result = "".join(segment_state)
        if result in self.matching_pattern:
            return self.matching_pattern[result]
        else:
            return "NaN"


class DecimalPointOCREngine:
    def __init__(self, ocr_points, decimal_point_positions):
        """
        Initialize the Decimal Point OCR Engine.

        :param ocr_points: Points defining the segments for decimal points.
        :param display_region: Region of the image to be displayed.
        :param on_color: The 'on' color used for processing.
        :param off_color: The 'off' color used for processing.
        :param segment_regions: Regions of the image to segment for OCR.
        :param decimal_point_positions: Corresponding digits for the OCR points.
        """
        self._ocr_points = ocr_points
        self._decimal_point_positions = decimal_point_positions

    def recognize_digit(self, binary_image):
        """
        入力画像をＯＣＲして、結果を一桁ずつ配列に入れて返す

        :param bgr_image: カラー画像
        :return: OCR結果配列
        """

        result = self.calculate_decimal_point_states(binary_image)
        return result

    def calculate_decimal_point_states(self, binary_image):
        """
        点灯している小数点位置を返す
        :param binary_image: ２値化画像
        :return: 小数点の位置or"NaN"
        """
        result = []
        for point, digit in zip(self._ocr_points, self._decimal_point_positions):
            segment_value = binary_image[point.y, point.x]
            if segment_value > 0:
                result.append(digit)

        return self._presume_decimal_point_position(result)

    @staticmethod
    def _presume_decimal_point_position(decimal_point_state):
        """
        小数点の点灯状態の配列から、小数点位置を推測する
        :param decimal_point_state:
        :return: 小数点位置or"NaN"
        """
        if not decimal_point_state:
            return 0
        elif len(decimal_point_state) == 1:
            return decimal_point_state[0]
        else:
            return "NaN"


class OCRHandler:
    segment_number = {"": 0, "0": 6, "1": 2, "2": 5, "3": 5, "4": 4, "5": 5, "6": 5, "7": 4, "8": 7, "9": 6, "-": 1}

    def __init__(self, ocr_points, display_region, on_color, off_color, segment_regions, segment_ocr_engine,
                 tesseract_ocr_engine, decimal_point_ocr_engine, is_off_segment_color):
        """
        :param ocr_points: 桁数分の７セグメントの認識点座標
        :param display_region: ７セグ表示領域
        :param on_color: 点灯セグメントBGR値
        :param off_color: 消灯セグメントBGR値
        :param segment_regions: 桁数分の７セグメントの領域座標
        """
        self._ocr_points = ocr_points
        self._display_region = display_region
        self._on_color = on_color
        self._off_color = off_color
        self._segment_regions = segment_regions
        self._segment_ocr_engine = segment_ocr_engine
        self._tesseract_ocr_engine = tesseract_ocr_engine
        self._decimal_point_ocr_engine = decimal_point_ocr_engine
        self._is_off_segment_color = is_off_segment_color

    def to_normalized_gray_image(self, bgr_image):
        """
        入力画像をOCR用に前処理する

        :param bgr_image: 入力カラー画像
        :return:前処理された画像
        """
        # 表示領域を抽出
        perspective_image = get_perspective_image(self._display_region, bgr_image)
        # cv2.imwrite("raw_img.jpg", perspective_image)
        # 差分画素値の取得
        diff_image = perspective_image
        if self._is_off_segment_color:
            diff_color = calculate_difference_color(self._on_color, self._off_color)
            # 差分画像の取得
            diff_image = to_difference_image(diff_color, perspective_image)
            # cv2.imwrite("diff_img.jpg", diff_image)
        # 正規化画像の取得
        normalized_image = normalize_image(diff_image)

        if np.sum(self._off_color) > np.sum(self._on_color):
            normalized_image = cv2.bitwise_not(normalized_image)
        # cv2.imwrite("norm_img.jpg", normalized_image)
        # グレースケール画像の取得
        gray_image = to_gray_image(normalized_image)

        blurred_image = blur_image(gray_image)
        # cv2.imwrite("gray_img.jpg", gray_image)
        # 正規化したグレースケール画像の取得
        normalized_gray_image = normalize_gray_image(blurred_image)
        cv2.imwrite("norm_gray_img.jpg", normalized_gray_image)
        return normalized_gray_image

    def image_to_string(self, bgr_image):
        normalized_gray_image = self.to_normalized_gray_image(bgr_image)

        tesseract_result = self.calculate_tesseract_result(normalized_gray_image)
        segment_result = None
        if self._segment_ocr_engine is not None:
            segment_result = self.calculate_segment_result(normalized_gray_image)
        merged_segment_result = self._merge_results(tesseract_result,
                                                    segment_result) if segment_result else tesseract_result

        ocr_string = self._join_result(merged_segment_result)
        if ocr_string == "NaN":
            return "NaN"

        decimal_point = self.calculate_decimal_point(normalized_gray_image)

        return float(ocr_string) / (10 ** decimal_point) if decimal_point != "NaN" else "NaN"

    def calculate_ocr_value(self, images):
        majority_vote = OCRMajorityVote()
        for image_path in images:
            image = load_image(image_path)
            ocr_string = self.image_to_string(image)
            majority_vote.add(ocr_string, image_path)
        ocr_value, image_path = majority_vote.select()
        return ocr_value, image_path

    def _merge_results(self, tesseract_ocr_result, segment_point_ocr_result):
        """
        tesseractとセグメント認識のＯＣＲ配列を１桁毎に比較し、より適切な方の結果を１桁ずつ返却用の配列に入れる

        :param tesseract_ocr_result: tesseractのOCR結果配列
        :param segment_point_ocr_result: セグメント認識のOCR結果配列
        :return: OCR結果配列
        """
        best_result = []
        for tesseract_string, segment_point_string in zip(tesseract_ocr_result, segment_point_ocr_result):
            if tesseract_string == "NaN" and segment_point_string != "NaN":
                best_result.append(segment_point_string)
            elif tesseract_string != "NaN" and segment_point_string == "NaN":
                best_result.append(tesseract_string)
            elif tesseract_string == "NaN" and segment_point_string == "NaN":
                best_result.append("NaN")
            else:
                best_result.append(segment_point_string)
        return best_result

    def _join_result(self, ocr_result):
        """
        OCR結果配列を文字列にする。

        :param ocr_result: ＯＣＲ結果配列
        :return: 数値or"NaN"
        """
        ocr_string = "".join(ocr_result)
        return int(ocr_string) if ocr_string.isdigit() else "NaN"

    def calculate_segment_result(self, normalized_gray_image):
        result = []
        # print(self._ocr_points)
        for segment_region, ocr_points in zip(self._segment_regions, self._ocr_points):
            p_left_x = int(segment_region["region_left_x"])
            p_left_y = int(segment_region["region_left_y"])
            p_right_x = int(segment_region["region_right_x"])
            p_right_y = int(segment_region["region_right_y"])
            clipped_image = roi_image(image=normalized_gray_image,
                                      p_left_x=p_left_x,
                                      p_left_y=p_left_y,
                                      p_right_x=p_right_x,
                                      p_right_y=p_right_y)
            cv2.imwrite(f"clipped/{str(p_left_x)}_gray_img.jpg", clipped_image)
            averaged_img = cv2.blur(clipped_image, (9, 9))
            adaptive_binary_image = binarize_gray_image_by_adaptive(averaged_img)
            otsu_binary_image = binarize_gray_image_by_otsu(averaged_img)
            cv2.imwrite(f"clipped/{str(p_left_x)}_apaptive.jpg", adaptive_binary_image)
            cv2.imwrite(f"clipped/{str(p_left_x)}_otsu.jpg", otsu_binary_image)
            # print(ocr_points)
            adaptive_ocr_string = self._segment_ocr_engine.recognize_string(adaptive_binary_image, ocr_points)
            otsu_ocr_string = self._segment_ocr_engine.recognize_string(otsu_binary_image, ocr_points)

            ocr_string = self.select_proper_ocr_string(adaptive_ocr_string, otsu_ocr_string)
            result.append(ocr_string)
        print(f"segment_result:{result}")
        return result

    def calculate_tesseract_result(self, normalized_gray_image):
        """
        入力画像をＯＣＲして、結果を一桁ずつ配列に入れて返す
        :param bgr_image: カラー画像
        :return: OCR結果配列
         """
        result = []
        for region in self._segment_regions:
            p_left_x = int(region["region_left_x"])
            p_left_y = int(region["region_left_y"])
            p_right_x = int(region["region_right_x"])
            p_right_y = int(region["region_right_y"])
            clipped_image = roi_image(image=normalized_gray_image,
                                      p_left_x=p_left_x,
                                      p_left_y=p_left_y,
                                      p_right_x=p_right_x,
                                      p_right_y=p_right_y)

            adaptive_binary_image = binarize_gray_image_by_adaptive(clipped_image)
            otsu_binary_image = binarize_gray_image_by_otsu(clipped_image)

            adaptive_ocr_string = self._tesseract_ocr_engine.recognize_string(adaptive_binary_image)
            otsu_ocr_string = self._tesseract_ocr_engine.recognize_string(otsu_binary_image)

            ocr_string = self.select_proper_ocr_string(adaptive_ocr_string, otsu_ocr_string)
            result.append(ocr_string)
        print(f"tesseract_result:{result}")
        return result

    def calculate_decimal_point(self, normalized_gray_image):

        adaptive_binary_image = binarize_gray_image_by_adaptive(normalized_gray_image)
        otsu_binary_image = binarize_gray_image_by_otsu(normalized_gray_image)

        adaptive_result = self._decimal_point_ocr_engine.recognize_digit(adaptive_binary_image)
        otsu_result = self._decimal_point_ocr_engine.recognize_digit(otsu_binary_image)

        return self._select_proper_digit_result(adaptive_result, otsu_result)

    @staticmethod
    def _select_proper_digit_result(adaptive_ocr_result, otsu_ocr_result):
        """
        大津の２値化または適応的２値化画像でOCRした結果を比較し、適切な方の結果を返す
        :param adaptive_ocr_result: 適応的２値化画像でOCRした小数点位置
        :param otsu_ocr_result: 大津の２値化画像でOCRした小数点位置
        :return: 小数点位置
        """
        print(adaptive_ocr_result, otsu_ocr_result)

        if adaptive_ocr_result != "NaN":
            return adaptive_ocr_result
        if otsu_ocr_result != "NaN":
            return otsu_ocr_result
        return "NaN"

    def select_proper_ocr_string(self, s1, s2):
        """
        照明の映り込みなどの影響で消灯セグメントが点灯セグメントと認識されないようにするため
        大津の２値化と適応的２値化で２値化された文字画像のOCR結果を比較し、２つの文字が７セグ表示パターンだった場合、
        画数の少ない方を適切な文字列として返す
        :param s1: OCR文字1
        :param s2: OCR文字2
        :return: OCR文字1またはOCR文字2
        """
        segment_number = self.segment_number
        if (s1 not in segment_number) and (s2 not in segment_number):
            return "NaN"

        if (s1 in segment_number) and (s2 not in segment_number):
            return s1

        if (s2 in segment_number) and (s1 not in segment_number):
            return s2

        if segment_number[s1] > segment_number[s2]:
            return s2
        return s1

    def save(self, image_path, save_path):

        bgr_image = load_image(image_path)
        region_image = get_perspective_image(self._display_region, bgr_image)
        save_image(image=region_image, path=save_path)


class OCRMajorityVote:

    def __init__(self):
        self._ocr_results = []

    def add(self, ocr_string, image_path):
        self._ocr_results.append([ocr_string, image_path])

    def initialize(self):
        self._ocr_results = []

    def select(self):
        ocr_results = [ocr_result[0] for ocr_result in self._ocr_results]
        result_count = collections.Counter(ocr_results)
        most_common = result_count.most_common()
        print(most_common)
        mode_string = most_common[0][0]
        if mode_string == "NaN" and len(most_common) > 1:
            mode_string = result_count.most_common()[1][0]

        mode_index = ocr_results.index(mode_string)
        mode_image_path = self._ocr_results[mode_index][1]
        return mode_string, mode_image_path
        # [('a', 4), ('c', 2), ('b', 1)]
