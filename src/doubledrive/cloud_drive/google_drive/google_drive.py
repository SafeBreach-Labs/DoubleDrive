import os
import requests

from doubledrive.cloud_drive.cloud_drive import CloudDriveFolderItem, CloudDriveItem, ICloudDriveSession
from doubledrive.cloud_drive.google_drive.google_drive_item import GoogleDriveItem, GoogleDriveFolderItem, GoogleDriveFileItem


class GoogleDrive(ICloudDriveSession):

    def __init__(self) -> None:
        self.__http_session = requests.Session()
        self.__session_token = None
        self.__root_folder_id = None
        self.__root_folder_item = None
        self.__ids_to_paths_cache = {}

    def __safe_http_request(self, *args, **kwargs) -> requests.Response:
        res = self.__http_session.request(*args, **kwargs)
        res.raise_for_status()
        return res

    def __update_token(self, token):
        self.__session_token = token
        self.__http_session.headers.update({"authorization": self.__session_token})

    def __get_item_json_fields(self, item_id):
        if item_id == self.__root_folder_id and None != self.__root_folder_item:
            return self.__root_folder_item.fields
        res = self.__safe_http_request("GET", f"https://www.googleapis.com/drive/v2internal/files/{item_id}")
        return res.json()
    
    def __item_json_to_path(self, google_drive_json_item: dict):
        if self.__get_root_folder_id() == google_drive_json_item["id"]:
            return "/"
        elif 0 == len(google_drive_json_item["parents"]):
            return "COMPUTERS:" + google_drive_json_item["title"]
        elif google_drive_json_item["id"] in self.__ids_to_paths_cache.keys():
            return self.__ids_to_paths_cache[google_drive_json_item["id"]]
        else:
            path = self.__item_json_to_path(self.__get_item_json_fields(google_drive_json_item["parents"][0]["id"])) + "/" + google_drive_json_item["title"]
            path = path.replace("//", "/")
            self.__ids_to_paths_cache[google_drive_json_item["id"]] = path
            return path
        
    def __item_json_to_google_drive_item(self, google_drive_json_item) -> GoogleDriveItem:
        item_path = self.__item_json_to_path(google_drive_json_item)

        if google_drive_json_item["mimeType"] == "application/vnd.google-apps.folder":
            return GoogleDriveFolderItem(item_path, google_drive_json_item["id"], google_drive_json_item)
        else:
            return GoogleDriveFileItem(item_path, google_drive_json_item["id"], google_drive_json_item)
        
    def __query_files(self, string_query: str):
        params = {
            "q": string_query
        }
        res = self.__safe_http_request("GET", "https://www.googleapis.com/drive/v2internal/files", params=params)
        res_json = res.json()
        children_google_drive_items = []
        next_page_exists = True
        while next_page_exists:
            for json_item in res_json["items"]:
                children_google_drive_items.append(self.__item_json_to_google_drive_item(json_item))

            next_page_exists = None != res_json.get("nextLink", None)

        return children_google_drive_items
    
    def __get_root_folder_id(self) -> str:
        if None != self.__root_folder_id:
            return self.__root_folder_id
        
        res = self.__safe_http_request("GET", "https://www.googleapis.com/drive/v2internal/about")
        res_json = res.json()
        self.__root_folder_id = res_json["rootFolderId"]
        return self.__root_folder_id

    def login_using_token(self, token: str):
        self.__update_token(token)

    def list_children(self, google_drive_folder_item: GoogleDriveFolderItem) -> list[GoogleDriveItem]:
        return self.__query_files(f"trashed=false and '{google_drive_folder_item.id}' in parents")
    
    def create_file(self, file_path: str, file_content: bytes,  modify_if_exists: bool = False) -> GoogleDriveFileItem:
        res = self.__safe_http_request("GET", "https://www.googleapis.com/drive/v2internal/files/generateIds?maxResults=1")
        res_json = res.json()
        new_file_id = res_json["ids"][0]

        parent_folder_item = self.get_item_by_path(os.path.dirname(file_path))
        new_file_name = os.path.basename(file_path)
        params = {
            "id": new_file_id,
            "title": new_file_name,
            "parents": [
                {
                    "id": parent_folder_item.id
                }
            ]
        }
        res = self.__safe_http_request("POST", "https://www.googleapis.com/upload/drive/v2internal/files?uploadType=resumable", json=params)
        upload_url = res.headers["Location"]
        res = self.__safe_http_request("POST", upload_url, data=file_content)
        res_json = res.json()

        # Fixing a bug in GoogleDrive API, a bad downloadUrl is returned after file creation
        if "downloadUrl" in res_json.keys():
            res_json["downloadUrl"] = res_json["downloadUrl"].replace("www.googleapis.comhttps:", "www.googleapis.com")

        return self.__item_json_to_google_drive_item(res_json)
    

    def modify_file_content(self, google_drive_item: GoogleDriveFileItem, new_content: bytes):
        parent_folder_item = self.get_item_by_id(google_drive_item.fields["parents"][0]["id"])
        params = {
            "originalFilename": google_drive_item.name,
            "parents": [
                {
                    "id": parent_folder_item.id
                }
            ]
        }
        res = self.__safe_http_request("PUT", f"https://www.googleapis.com/upload/drive/v2internal/files/{google_drive_item.id}?uploadType=resumable&convert=false", json=params)
        upload_url = res.headers["Location"]
        res = self.__safe_http_request("POST", upload_url, data=new_content)
        res_json = res.json()

        # Fixing a bug in GoogleDrive API, a bad downloadUrl is returned after file creation
        if "downloadUrl" in res_json.keys():
            res_json["downloadUrl"] = res_json["downloadUrl"].replace("www.googleapis.comhttps:", "www.googleapis.com")

        return self.__item_json_to_google_drive_item(res_json)

    def read_file_content(self, google_drive_file_item: GoogleDriveFileItem) -> bytes:
        if "downloadUrl" in google_drive_file_item.fields.keys():
            return self.__safe_http_request("GET", google_drive_file_item.fields["downloadUrl"]).content
        elif "exportLinks" in google_drive_file_item.fields.keys():
            for export_type, export_link in google_drive_file_item.fields["exportLinks"].items():
                if export_type.startswith("application/vnd.openxmlformats"):
                    return self.__safe_http_request("GET", export_link).content

        raise RuntimeError(f"Could not find a download link for file {google_drive_file_item.full_path}")
    
    def rename_item(self, google_drive_item: GoogleDriveItem, new_name: str):
        params = {
            "title": new_name
        }
        res = self.__safe_http_request("PATCH", f"https://www.googleapis.com/drive/v2internal/files/{google_drive_item.id}", json=params)

    def delete_item(self, google_drive_item: GoogleDriveItem):
        self.__ids_to_paths_cache.pop(google_drive_item.id)
        res = self.__safe_http_request("DELETE", f"https://www.googleapis.com/drive/v2internal/files/{google_drive_item.id}")
    
    def trash_item(self, google_drive_item: GoogleDriveItem) -> GoogleDriveItem:
        res = self.__safe_http_request("POST", f"https://www.googleapis.com/drive/v2internal/files/{google_drive_item.id}/trash")
        return self.__item_json_to_google_drive_item(res.json())

    def make_item_public(self, google_drive_item: GoogleDriveItem) -> str:
        params = {
            "role" : "writer",
            "type" : "anyone"
        }
        res = self.__safe_http_request("POST", f"https://www.googleapis.com/drive/v2internal/files/{google_drive_item.id}/permissions", json=params)

    def send_item_to_email(self, google_drive_item: GoogleDriveItem, email: str, role: str = "write"):
        params = {
            "value": email,
            "role" : "writer",
            "type" : "user"
        }
        res = self.__safe_http_request("POST", f"https://www.googleapis.com/drive/v2internal/files/{google_drive_item.id}/permissions", json=params)

    def list_children_recursively(self, google_drive_folder_item: GoogleDriveFolderItem) -> list[CloudDriveItem]:
        all_children_items = []
        first_level_children = self.list_children(google_drive_folder_item)

        all_children_items.extend(first_level_children)
        for google_drive_child_item in first_level_children:
            if isinstance(google_drive_child_item, GoogleDriveFolderItem):
                all_children_items.extend(self.list_children_recursively(google_drive_child_item))

        return all_children_items

    def get_item_by_path(self, item_path: str) -> GoogleDriveItem:
        if "/" == item_path:
            return self.get_root_folder_item()
        elif item_path.startswith("COMPUTERS:") and "/" not in item_path:
            return self.get_computer_folder_item_by_name(item_path)
        else:
            google_drive_parent_item = self.get_item_by_path(os.path.dirname(item_path))
            path_parent_children = self.list_children(google_drive_parent_item)
            path_basename = os.path.basename(item_path)
            for child_item in path_parent_children:
                if path_basename == child_item.name:
                    return child_item
            raise RuntimeError("Could not find Google Drive item")
        
    def get_all_items_by_path(self, item_path: str) -> list[GoogleDriveItem]:
        if "/" == item_path:
            return self.get_root_folder_item()
        else:
            found_items = []
            all_google_drive_parent_items = self.get_all_items_by_path(os.path.dirname(item_path))
            for google_drive_parent_item in all_google_drive_parent_items:
                path_parent_children = self.list_children(google_drive_parent_item)
                path_basename = os.path.basename(item_path)
                for child_item in path_parent_children:
                    if path_basename == child_item.name:
                        found_items.append[child_item]
                
            if 0 == len(found_items):
                raise RuntimeError("Could not find Google Drive item")
            else:
                return found_items
            
    def get_item_by_id(self, id: str) -> GoogleDriveItem:
        return self.__item_json_to_google_drive_item(self.__get_item_json_fields(id))

    def get_root_folder_item(self) -> GoogleDriveFolderItem:
        if None != self.__root_folder_item:
            return self.__root_folder_item
        
        self.__root_folder_item = self.__item_json_to_google_drive_item(self.__get_item_json_fields(self.__get_root_folder_id()))
        return self.__root_folder_item
    
    def get_computer_folders(self) -> list[GoogleDriveFolderItem]:
        return self.__query_files(f"trashed=false and 'machineRoot' in folderFeatures")
    
    def get_computer_folder_item_by_name(self, name: str) -> GoogleDriveFolderItem:
        for computer_folder in self.get_computer_folders():
            if computer_folder.name == name:
                return computer_folder
        
        raise RuntimeError("Could not find the computer folder")
    
    def empty_trash(self):
        res = self.__safe_http_request("DELETE", "https://www.googleapis.com/drive/v2/files/trash")


