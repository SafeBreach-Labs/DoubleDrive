import subprocess
import sqlite3
import os
import pathlib
import win32con
import win32file
import win32api
import psutil


GOOGLE_DRIVE_DATA_PATH = os.path.expandvars(r"%localappdata%\Google\DriveFS")
GOOGLE_DRIVE_ROOT_PREFERENCES_DB_PATH = os.path.join(GOOGLE_DRIVE_DATA_PATH, "root_preference_sqlite.db")
GOOGLE_DRIVE_DB_MAX_IDS_TABLE = "max_ids"
GOOGLE_DRIVE_DB_ROOTS_TABLE = "roots"
GOOGLE_DRIVE_PROCESS_NAME = "GoogleDriveFS.exe"
GOOGLE_DRIVE_LAUNCH_SCRIPT_PATH = os.path.expandvars(r"%ProgramFiles%\Google\Drive File Stream\launch.bat")
SYNC_DELAY_AFTER_GOOGLE_DRIVE_RESTART = 3


def restart_google_drive():
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
            proc.kill()
    
    process = subprocess.Popen(f"\"{GOOGLE_DRIVE_LAUNCH_SCRIPT_PATH}\"", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    process.wait()
    

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

