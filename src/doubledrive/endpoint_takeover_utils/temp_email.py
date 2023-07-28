import random
import requests
import uuid
from dataclasses import dataclass

@dataclass
class EmailMessage:
    source_email: str
    subject: str
    content: str

class TempEmail:

    def __init__(self, email_address: str = None) -> None:
        self.domain = None
        self.username = None
        if None == email_address:
            self.generate_new_address()
        else:
            self.username = email_address[:email_address.index("@")]
            self.domain = email_address[email_address.index("@")+1:]

    def generate_new_address(self):
        res = requests.get("https://www.1secmail.com/api/v1/?action=getDomainList")
        self.domain = random.choice(res.json())
        self.username = uuid.uuid4()

    def get_messages(self) -> list[EmailMessage]:
        res = requests.get(f"https://www.1secmail.com/api/v1/?action=getMessages&login={self.username}&domain={self.domain}")
        messages_json = res.json()

        result_messages = []
        for message_json in messages_json:
            message_id = message_json["id"]
            res = requests.get(f"https://www.1secmail.com/api/v1/?action=readMessage&login={self.username}&domain={self.domain}&id={message_id}")
            full_message_json = res.json()
            new_message = EmailMessage(full_message_json["from"], full_message_json["subject"], full_message_json["body"])
            result_messages.append(new_message)

        return result_messages