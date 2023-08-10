from dataclasses import dataclass

from doubledrive.cloud_drive.cloud_drive import CloudDriveItem, CloudDriveFolderItem, CloudDriveFileItem

@dataclass
class OneDriveItem(CloudDriveItem):
    """
    A general item that is stored on OneDrive storage
    """
    id: str
    
    def __init__(self, full_path: str, parent_id: str, id: str) -> None:
        super().__init__(full_path)
        self.id = id
        self.parent_id = parent_id

@dataclass
class OneDriveFolderItem(OneDriveItem, CloudDriveFolderItem):
    """
    A folder that is stored on OneDrive storage
    """
    def __init__(self, full_path: str, parent_id: str, id: str) -> None:
        OneDriveItem.__init__(self, full_path, parent_id, id)

@dataclass
class OneDriveFileItem(OneDriveItem, CloudDriveFileItem):
    """
    A file that is stored on OneDrive storage 
    """
    def __init__(self, full_path: str, parent_id: str, id: str) -> None:
        OneDriveItem.__init__(self, full_path, parent_id, id)

@dataclass
class OneDrivePackageItem(OneDriveItem, CloudDriveFileItem):
    """
    A 'package' file that is stored on OneDrive storage. That is a file that
    OneDrive has a more advanced support for on the web OneDrive version.
    Files such as Word documents, PowerPoint slides, OneNote documents, etc.. 
    """
    def __init__(self, full_path: str, parent_id: str, id: str) -> None:
        OneDriveItem.__init__(self, full_path, parent_id, id)
