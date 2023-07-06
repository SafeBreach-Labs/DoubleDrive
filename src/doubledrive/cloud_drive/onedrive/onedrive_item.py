from dataclasses import dataclass

from doubledrive.cloud_drive.cloud_drive import CloudDriveItem, CloudDriveFolderItem, CloudDriveFileItem

@dataclass
class OneDriveItem(CloudDriveItem):
    id: str
    
    def __init__(self, full_path: str, parent_id: str, id: str) -> None:
        super().__init__(full_path)
        self.id = id
        self.parent_id = parent_id

@dataclass
class OneDriveFolderItem(OneDriveItem, CloudDriveFolderItem):
    def __init__(self, full_path: str, parent_id: str, id: str) -> None:
        OneDriveItem.__init__(self, full_path, parent_id, id)

@dataclass
class OneDriveFileItem(OneDriveItem, CloudDriveFileItem):
    def __init__(self, full_path: str, parent_id: str, id: str) -> None:
        OneDriveItem.__init__(self, full_path, parent_id, id)

@dataclass
class OneDrivePackageItem(OneDriveItem, CloudDriveFileItem):
    def __init__(self, full_path: str, parent_id: str, id: str) -> None:
        OneDriveItem.__init__(self, full_path, parent_id, id)
