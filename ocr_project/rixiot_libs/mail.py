import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


class EmailSender:
    def __init__(self, smtp_server, smtp_port, sender_email, sender_password, receiver_emails, subject):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.sender_email = sender_email
        self.sender_password = sender_password
        self.receiver_emails = receiver_emails
        self.subject = subject

    def send_email(self, message: str) -> None:
        if self.receiver_emails is not None:
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = self.receiver_emails
            msg['Subject'] = self.subject

            msg.attach(MIMEText(message, 'plain'))

            try:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
                server.quit()
                print("Email sent successfully!")
            except Exception as e:
                print(e)
                # import traceback
                # with open("/home/pi/ble/mail_exception.txt", 'a') as f:
                # traceback.print_exc(file=f)


class EmailMessageCreator:
    japanese_dict = {"normal": "正常値", "alert": "警報値", "abnormal": "異常", "ocr_error": "OCR異常"}

    def __init__(self, camera_name, setting_name):
        self.camera_name = camera_name
        self.setting_name = setting_name

    def create_message(self, value, event):
        return f"カメラ名{self.camera_name}の設定名{self.setting_name}が{self.japanese_dict[event]}になりました 値:{value}\n"


class EmailMessagePool:

    def __init__(self):
        self.messages=[]

    def add(self,message):
        self.messages.append(message)

    def merge_to_string(self):
        return "".join(self.messages)

    def clear(self):
        self.messages = []


