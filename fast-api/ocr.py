# 標準ライブラリ
import glob
import json
import numpy as np
import os
import threading
import time
import collections
import logging
# サードパーティーライブラリ
import cv2
from PIL import Image
import pytesseract
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from watchdog.observers.polling import PollingObserver
# 自作モジュール
import config
from db_models import Base, DBCameraSetting, DBOCRSetting
from schema import SegmentColor, Coordinate

engine = create_engine('sqlite:///sample_db.sqlite3', echo=False)
# DBセッションを作るクラスを作成
SessionClass = sessionmaker(engine)
# DBテーブルを作成
Base.metadata.create_all(bind=engine)


# SQLiteに接続するたびに外部キー制約を有効にするためのリスナーを追加
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


# Dependency
def get_db():
    db = SessionClass()
    try:
        yield db
    except Exception:
        db.rollback()  # エラーがあればロールバック
    finally:
        db.close()


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


def roi_image(image, p_left, p_right):
    """
    画像imageから左上点p_leftと右下点p_rightで指定される長方形領域を切り出す
    :param image: 画像
    :param p_left:左上点(x,y)
    :param p_right: 右上点(x,y)
    :return: 左上点p_leftと右下点p_rightで指定される長方形領域の画像
    """
    image = image.copy()
    return image[p_left.y: p_right.y, p_left.x: p_right.x]


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
            pytesseract.pytesseract.tesseract_cmd = self._tesseract_path
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
                        "1111001": "5", "1111101": "6", "1000011": "7", "1111111": "8", "1101011": "9", "1111011": "9",
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
        for point in ocr_points:
            x = point.x
            y = point.y
            segment_value = binary_image[y, x]
            result.append(self._calculate_segment_state(segment_value))

        return result

    def _calculate_segment_state(self, segment_value):
        if self._segment_color == "white":
            if segment_value > 0:
                return "1"
            return "0"
        if self._segment_color == "black":
            if segment_value > 0:
                return "0"
            return "1"

    def recognize_string(self, preprocessed_image, ocr_points):
        """
        セグメント画像をOCRして認識文字を返す

        :param segment_image: 一桁セグメントの画像
        :return: 一桁セグメントの画像のOCR文字
        """
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
    segment_number = {"": 0, "0": 6, "1": 2, "2": 5, "3": 5, "4": 5, "5": 5, "6": 5, "7": 4, "8": 7, "9": 6, "-": 1}

    def __init__(self, ocr_points, display_region, on_color, off_color, segment_regions, segment_ocr_engine,
                 tesseract_ocr_engine, decimal_point_ocr_engine):
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

    def to_normalized_gray_image(self, bgr_image):
        """
        入力画像をOCR用に前処理する

        :param bgr_image: 入力カラー画像
        :return:前処理された画像
        """
        # 表示領域を抽出
        perspective_image = get_perspective_image(self._display_region, bgr_image)
        # 差分画素値の取得
        diff_color = calculate_difference_color(self._on_color, self._off_color)
        # 差分画像の取得
        diff_image = to_difference_image(diff_color, perspective_image)
        # 正規化画像の取得
        normalized_image = normalize_image(diff_image)
        if np.sum(self._off_color) > np.sum(self._on_color):
            normalized_image = cv2.bitwise_not(normalized_image)
        # グレースケール画像の取得
        gray_image = to_gray_image(normalized_image)
        # 正規化したグレースケール画像の取得
        normalized_gray_image = normalize_gray_image(gray_image)

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

    def _merge_results(self, tesseract_ocr_result, segment_point_ocr_result):
        """
        tesseractとセグメント認識のＯＣＲ配列を１桁毎に比較し、より適切な方の結果を１桁ずつ返却用の配列に入れる

        :param tesseract_ocr_result: tesseractのOCR結果配列
        :param segment_point_ocr_result: セグメント認識のOCR結果配列
        :return: OCR結果配列
        """
        best_result = []
        for tesseract_string, segment_point_string in zip(tesseract_ocr_result, segment_point_ocr_result):
            if tesseract_string == "NaN":
                best_result.append(segment_point_string)
            else:
                best_result.append(tesseract_string)
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
        for segment_region, ocr_points in zip(self._segment_regions, self._ocr_points):
            p_left = Coordinate(x=int(segment_region["region_left_x"]), y=int(segment_region["region_left_y"]))
            p_right = Coordinate(x=int(segment_region["region_right_x"]), y=int(segment_region["region_right_y"]))
            clipped_image = roi_image(normalized_gray_image, p_left, p_right)

            adaptive_binary_image = binarize_gray_image_by_adaptive(clipped_image)
            otsu_binary_image = binarize_gray_image_by_otsu(clipped_image)

            adaptive_ocr_string = self._segment_ocr_engine.recognize_string(adaptive_binary_image, ocr_points)
            otsu_ocr_string = self._segment_ocr_engine.recognize_string(otsu_binary_image, ocr_points)

            ocr_string = self.select_proper_ocr_string(adaptive_ocr_string, otsu_ocr_string)
            result.append(ocr_string)
        return result

    def calculate_tesseract_result(self, normalized_gray_image):
        """
        入力画像をＯＣＲして、結果を一桁ずつ配列に入れて返す
        :param bgr_image: カラー画像
        :return: OCR結果配列
         """
        result = []
        for region in self._segment_regions:
            p_left = Coordinate(x=int(region["region_left_x"]), y=int(region["region_left_y"]))
            p_right = Coordinate(x=int(region["region_right_x"]), y=int(region["region_right_y"]))
            clipped_image = roi_image(normalized_gray_image, p_left, p_right)

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


class OCRMajorityVote:

    def __init__(self):
        self._ocr_results = []

    def add(self, ocr_string):
        self._ocr_results.append(ocr_string)

    def initialize(self):
        self._ocr_results = []

    def select(self):
        result_count = collections.Counter(self._ocr_results)
        most_common = result_count.most_common()
        print(most_common)
        mode = most_common[0][0]
        if mode == "NaN" and len(most_common) > 2:
            mode = result_count.most_common()[1][0]
        return mode
        # [('a', 4), ('c', 2), ('b', 1)]


def load_setting_ids(camera_port):
    session = SessionClass()
    settings = session.query(DBOCRSetting.id).filter(DBOCRSetting.camera_port == camera_port).all()
    id_list = [setting[0] for setting in settings]
    return id_list


def generate_paths(directory):
    for dir1 in glob.glob(f"{directory}/*"):
        port = os.path.basename(dir1).split("_")[-1]
        for dir2 in glob.glob(f"{directory}/PORT_{port}/*"):
            timestamp = os.path.basename(dir2)
            for setting_id in load_setting_ids(port):
                for image_path in glob.glob(f"{directory}/PORT_{port}/{timestamp}/*.jpg"):
                    yield image_path, port, setting_id


class AbstractFactory:
    def load_ocr_setting(self, setting_id):
        session = SessionClass()
        setting = session.query(DBOCRSetting).filter(DBOCRSetting.id == setting_id).all()[0]
        return setting


class OCRHandlerFactory(AbstractFactory):
    def create_ocr_handler(self, setting_id):
        ocr_points = self._calculate_ocr_points(setting_id)
        display_region = self._load_display_region(setting_id)
        segment_regions = self._load_segment_regions(setting_id)
        on_color = self._load_on_color(setting_id)
        off_color = self._load_off_color(setting_id)
        tesseract_ocr_engine = self._create_tesseract_ocr_engine()
        decimal_point_ocr_engine = self._create_decimal_point_ocr_engine(setting_id)
        is_segment_points_detection = self._load_is_segment_points_detection(setting_id)
        if is_segment_points_detection:
            segment_ocr_engine = self._create_segment_ocr_engine(setting_id)
        else:
            segment_ocr_engine = None

        return OCRHandler(
            tesseract_ocr_engine=tesseract_ocr_engine, segment_ocr_engine=segment_ocr_engine,
            decimal_point_ocr_engine=decimal_point_ocr_engine, ocr_points=ocr_points, display_region=display_region,
            segment_regions=segment_regions, on_color=on_color, off_color=off_color)

    def _load_display_region(self, setting_id):
        display_region = json.loads(self.load_ocr_setting(setting_id).perspective_transformation_setting)
        return display_region

    def _load_on_color(self, setting_id):
        on_color = json.loads(self.load_ocr_setting(setting_id).segment_on_color)
        on_color = [on_color["b"], on_color["g"], on_color["r"]]

        return on_color

    def _load_off_color(self, setting_id):
        off_color = json.loads(self.load_ocr_setting(setting_id).segment_off_color)
        off_color = [off_color["b"], off_color["g"], off_color["r"]]
        return off_color

    def _calculate_segment_color(self, setting_id):
        on_color = self._load_on_color(setting_id)
        off_color = self._load_off_color(setting_id)
        if np.sum(off_color) > np.sum(on_color):
            return "black"
        return "white"

    def _create_tesseract_ocr_engine(self):
        tesseract_path = config.TESSERACT_PATH

        return TesseractOCREngine(ocr_config=config.OCR_CONFIG, tesseract_path=tesseract_path)

    def _create_segment_ocr_engine(self, setting_id):
        segment_color = self._calculate_segment_color(setting_id)
        return SegmentOCREngine(segment_color=segment_color)

    def _create_decimal_point_ocr_engine(self, setting_id):
        ocr_points = json.loads(self.load_ocr_setting(setting_id).decimal_point_setting)
        ocr_points = [Coordinate(x=int(point["decimal_x"]), y=int(point["decimal_y"])) for point in ocr_points]
        decimal_point_positions = json.loads(self.load_ocr_setting(setting_id).decimal_exponents)
        return DecimalPointOCREngine(ocr_points=ocr_points, decimal_point_positions=decimal_point_positions)

    def _load_segment_regions(self, setting_id):
        segment_region_settings = json.loads(self.load_ocr_setting(setting_id).segment_region_settings)
        return segment_region_settings

    def _load_is_segment_points_detection(self, setting_id):
        return self.load_ocr_setting(setting_id).is_segment_points_detection

    def _load_ocr_points(self, setting_id):
        return json.loads(self.load_ocr_setting(setting_id).segment_recognition_points)

    def _calculate_ocr_points(self, setting_id):
        segment_regions = self._load_segment_regions(setting_id)
        ocr_points = self._load_ocr_points(setting_id)
        int_ocr_points = []
        for segment_region, ocr_point in zip(segment_regions, ocr_points):
            offset_x = int(segment_region["region_left_x"])
            offset_y = int(segment_region["region_left_y"])
            int_ocr_points.append(
                [Coordinate(x=int(point[0]) - offset_x, y=int(point[1]) - offset_y) for point in ocr_point])

        return int_ocr_points


def calculate_ocr_value(images, ocr_handler):
    majority_vote = OCRMajorityVote()
    for image_path in images:
        image = load_image(image_path)
        ocr_string = ocr_handler.image_to_string(image)
        majority_vote.add(ocr_string)
    ocr_value = majority_vote.select()
    return ocr_value


def output_result(timestamp, setting_id, ocr_value):
    return {"timestamp": timestamp, "setting_id": setting_id, "value": ocr_value}


def load_images(directory):
    print(glob.glob(f"{directory}/*"))
    return glob.glob(f"{directory}/*")


def extract_timestamp(directory):
    return os.path.basename(directory)


def extract_port(directroy):
    port_name = directroy.split("/")[2]
    return port_name.split("_")[-1]


def process(directory):
    output = []
    timestamp = extract_timestamp(directory)
    print(timestamp)
    port = extract_port(directory)
    print(port)
    setting_ids = load_setting_ids(port)
    print(setting_ids)

    for setting_id in setting_ids:
        ocr_handler = OCRHandlerFactory().create_ocr_handler(setting_id=setting_id)
        print(directory)
        images = load_images(directory)
        print(images)
        ocr_value = calculate_ocr_value(images, ocr_handler)
        result = output_result(timestamp=timestamp, setting_id=setting_id, ocr_value=ocr_value)
        output.append(result)
    with open("output.txt", mode="w") as f:
        f.write(json.dumps(output))
    return output


class MyWatcher:

    def __init__(self, directory=".", handler=FileSystemEventHandler()):
        self.observer = PollingObserver()
        self.handler = handler
        self.directory = directory

    def run(self):
        self.observer.schedule(self.handler, self.directory, recursive=True)
        self.observer.start()
        print(f"MyWatcher Running in {self.directory}")
        try:
            while True:
                time.sleep(1)
        except:
            self.observer.stop()
        self.observer.join()
        print("\nMyWatcher Terminated\n")


class MyHandler(FileSystemEventHandler):

    def on_created(self, event):
        directory = event.src_path.replace(os.sep, '/')
        print(directory)
        if os.path.isdir(directory):
            process(directory)


if __name__ == "__main__":
    myhandler = MyHandler()
    w = MyWatcher("./images", myhandler)
    w.run()
