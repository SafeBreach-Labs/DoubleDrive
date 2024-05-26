import json
import winreg
from dataclasses import dataclass


@dataclass
class GoogleDrivePerAccountPreferences:
    id: str
    machine_root_doc_id: str
    mount_point_path: str


class GoogleDriveInfo:
    def __init__(self) -> None:
        self.all_accounts_preferences: list[GoogleDrivePerAccountPreferences] = []

        hkcu_key = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
        with winreg.OpenKey(hkcu_key, "Software\\Google\\DriveFS") as onedrive_personal_reg_key:
            all_accounts_preferences_string = winreg.QueryValueEx(onedrive_personal_reg_key, "PerAccountPreferences")[0]
            json_all_accounts_preferences = json.loads(all_accounts_preferences_string)["per_account_preferences"]

        for json_account_preferences in json_all_accounts_preferences:
            account_preferences = GoogleDrivePerAccountPreferences(json_account_preferences["key"], json_account_preferences["value"].get("machine_root_doc_id", None), json_account_preferences["value"].get("mount_point_path", None))
            self.all_accounts_preferences.append(account_preferences)


g_google_drive_info_single_instance = None
def get_google_drive_info():
    global g_google_drive_info_single_instance
    if None == g_google_drive_info_single_instance:
        g_google_drive_info_single_instance = GoogleDriveInfo()
    return g_google_drive_info_single_instance
