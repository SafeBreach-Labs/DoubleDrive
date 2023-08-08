import os
from abc import ABC, abstractmethod, ABCMeta
from dataclasses import dataclass


@dataclass
class CloudDriveItem:
    """
    A generic item in a cloud drive service. Can be a file or a directory.
    """
    name: str
    full_path: str
    
    def __init__(self, full_path: str) -> None:
        self.full_path = full_path
        if "/" == full_path:
            self.name = "/"
        else:
            self.name = os.path.basename(full_path)

@dataclass
class CloudDriveFolderItem(CloudDriveItem):
    """
    A folder item in a cloud drive service.
    """
    def __init__(self, full_path: str) -> None:
        super().__init__(full_path)

@dataclass
class CloudDriveFileItem(CloudDriveItem):
    """
    A file item in a cloud drive service.
    """
    def __init__(self, full_path: str) -> None:
        super().__init__(full_path)


class ICloudDriveSession(ABC):
    """
    An interface that represents a session with a cloud drive service.
    """
    @abstractmethod
    def create_file(self, file_path: str, file_content: bytes, modify_if_exists: bool = False) -> CloudDriveFileItem:
        """
        Creates a file in the cloud storage of the service

        :param file_path: The path to create the file in on the cloud storage
        :param file_content: The content to write into the new file
        :param modify_if_exists: Whether to modify the file if it already exists
            If False and a file exists in the given path then exception is raised

        :return: An instance of the created CloudDriveFileItem
        """
        pass

    @abstractmethod
    def modify_file_content(self, cloud_file_item: CloudDriveFileItem, new_content: bytes):
        """
        Modifies a cotent of a file on the cloud storage

        :param cloud_file_item: The file to modify
        :param new_content: The new content that will overwrite the previous content of the give file
        """
        pass

    @abstractmethod
    def read_file_content(self, cloud_file_item: CloudDriveFileItem) -> bytes:
        """
        Reads the content of a file from the cloud storage

        :param cloud_file_item: The file to read

        :return: The content of the file in bytes
        """
        pass

    @abstractmethod
    def delete_item(self, cloud_item: CloudDriveItem):
        """
        Deletes an iten from the cloud storage

        :param cloud_item: The item to delete on the cloud storage
        """
        pass

    @abstractmethod
    def list_children(self, cloud_folder_item: CloudDriveFolderItem) -> list[CloudDriveItem]:
        """
        Lists all the direct children items of a folder on the cloud storage

        :param cloud_folder_item: The folder to list

        :return: A list of all the found direct children of the given folder
        """
        pass

    @abstractmethod
    def list_children_recursively(self, cloud_folder_item: CloudDriveFolderItem) -> list[CloudDriveItem]:
        """
        Lists all the children items of a folder recursively on the cloud storage

        :param cloud_folder_item: The folder to list

        :return: A list of all the found children of the given folder in any depth
        """    
        pass

    @abstractmethod
    def get_item_by_path(self, item_path: str) -> CloudDriveItem:
        """
        Returns the object of an item on the cloud storage by its path

        :param item_path: The path of the requested item
        """
        pass
