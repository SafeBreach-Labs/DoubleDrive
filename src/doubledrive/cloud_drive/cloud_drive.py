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
        pass

    @abstractmethod
    def modify_file_content(self, cloud_file_item: CloudDriveFileItem, new_content: bytes):
        pass

    @abstractmethod
    def read_file_content(self, cloud_file_item: CloudDriveFileItem) -> bytes:
        pass

    @abstractmethod
    def delete_item(self, cloud_item: CloudDriveItem):
        pass

    @abstractmethod
    def list_children(self, cloud_folder_item: CloudDriveFolderItem) -> list[CloudDriveItem]:
        pass

    @abstractmethod
    def list_children_recursively(self, cloud_folder_item: CloudDriveFolderItem) -> list[CloudDriveItem]:
        pass

    @abstractmethod
    def get_item_by_path(self, item_path: str) -> CloudDriveItem:
        pass
