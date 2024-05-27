from dataclasses import dataclass

from doubledrive.cloud_drive.cloud_drive import CloudDriveItem, CloudDriveFolderItem, CloudDriveFileItem

@dataclass
class GoogleDriveItem(CloudDriveItem):
    id: str
    
    def __init__(self, full_path: str, id: str, fields: dict) -> None:
        super().__init__(full_path)
        self.id = id
        self.fields = fields

@dataclass
class GoogleDriveFolderItem(GoogleDriveItem, CloudDriveFolderItem):
    def __init__(self, full_path: str, id: str, fields: dict) -> None:
        GoogleDriveItem.__init__(self, full_path, id, fields)

@dataclass
class GoogleDriveFileItem(GoogleDriveItem, CloudDriveFileItem):
    def __init__(self, full_path: str, id: str, fields: dict) -> None:
        GoogleDriveItem.__init__(self, full_path, id, fields)