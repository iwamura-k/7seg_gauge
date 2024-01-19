from common_libs import utils
import datetime


class ValueEventCalculator:

    def __init__(self, alert_low_th, alert_high_th, abnormal_low_th, abnormal_high_th):
        self._alert_low_th = alert_low_th
        self._alert_high_th = alert_high_th
        self._abnormal_low_th = abnormal_low_th
        self._abnormal_high_th = abnormal_high_th

    def _is_on_alert(self, value) -> bool:
        if value < self._alert_low_th or value > self._alert_high_th:
            return True
        return False

    def _is_on_abnormal(self, value) -> bool:
        if value < self._abnormal_low_th or value > self._abnormal_high_th:
            return True
        return False

    def calculate_status(self, value):
        if value == "NaN":
            return "ocr_error"
        if self._is_on_abnormal(value):
            return "abnormal"
        if self._is_on_alert(value):
            return "alert"
        return "normal"


class EventPolicy:

    def __init__(self, dead_band_sec):
        self.dead_band_sec = dead_band_sec
        self.retention = None
        self.event_type = None
        self.event_time = None
        self.stable_event_type = None
        self.is_send_alert = False

    def update(self, event_type, event_time):
        pre_stable_event_type = self.stable_event_type
        if self.stable_event_type is None:
            self.event_type = event_type
            self.event_time = event_time
            self.stable_event_type = event_type
            self.retention = 0
            if event_type != "normal":
                self.is_send_alert = True
            print(self.event_type, self.retention, self.event_time, self.stable_event_type, self.is_send_alert)
            return

        td = (event_time - self.event_time).total_seconds()

        if event_type == self.event_type:
            self.retention += td
            self.event_time = event_time
            if self.retention > self.dead_band_sec:
                self.stable_event_type = self.event_type
        else:
            self.event_time = event_time
            self.event_type = event_type
            self.retention = td
            if td > self.dead_band_sec:
                self.stable_event_type = event_type

        if pre_stable_event_type != self.stable_event_type:
            self.is_send_alert = True
        else:
            self.is_send_alert = False
        print(self.event_type, self.retention, self.event_time, self.stable_event_type, self.is_send_alert)

    def get_event_type(self, event_type, event_time):
        self.update(event_type, event_time)
        return self.stable_event_type,self.is_send_alert



if __name__ == "__main__":
    now = utils.get_time()
    td = datetime.timedelta(seconds=3)
    test_data = [["a", "abnormal", now],
                 ["a", "abnormal", now + td],
                 ["a", "normal", now + td + td + td],
                 ["a", "abnormal", now + td + td + td + td],
                 ["a", "normal", now + td + td + td + td + td + td],
                 ["a", "ocr_error", now + td + td + td + td + td + td + td],
                 ["a", "ocr_error", now + td + td + td + td + td + td + td + td]
                 ]

    event_policy = EventPolicy(dead_band_sec=5)
    result = []
    for data in test_data:
        event_type = data[1]
        event_time = data[2]
        event = event_policy.get_event_type(event_time=event_time, event_type=event_type)
        result.append(event)
    print(result)
