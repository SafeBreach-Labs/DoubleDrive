from dataclasses import dataclass
import os

@dataclass
class OneDriveItem:
    name: str
    full_path: str
    id: str
    
    def __init__(self, full_path: str, parent_id: str, id: str) -> None:
        self.id = id
        self.parent_id = parent_id
        self.full_path = full_path
        if "/" == full_path:
            self.name = "/"
        else:
            self.name = os.path.basename(full_path)

@dataclass
class OneDriveFolderItem(OneDriveItem):
    def __init__(self, full_path: str, parent_id: str, id: str) -> None:
        super().__init__(full_path, parent_id, id)

@dataclass
class OneDriveFileItem(OneDriveItem):
    size_in_bytes: int

    def __init__(self, full_path: str, parent_id: str, id: str, size_in_bytes: int) -> None:
        super().__init__(full_path, parent_id, id)
        self.size_in_bytes = size_in_bytes

@dataclass
class OneDrivePackageItem(OneDriveItem):
    def __init__(self, full_path: str, parent_id: str, id: str) -> None:
        super().__init__(full_path, parent_id, id)
