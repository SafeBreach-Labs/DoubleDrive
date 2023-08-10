import requests
import os
import time
from http import HTTPStatus

from .onedrive_item import OneDriveItem, OneDriveFileItem, OneDriveFolderItem, OneDrivePackageItem
from doubledrive.cloud_drive.cloud_drive import *

class OneDrive(ICloudDriveSession):
    """
    A session with a OneDrive account 
    """

    def __init__(self) -> None:
        """
        Creates a OneDrive instance
        """
        self.__drive_id = None
        self.__http_session = requests.Session()

    def __item_json_to_onedrive_item(self, item_json: dict) -> OneDriveItem:
        """
        Converts the JSON structure that is usually returned from OneDrive's servers for
        Describing an item in the cloud storage to the specific sub-class of OneDriveItem
        that it matches to

        :param item_json: The JSON structure that is returned by OneDrive to describe an
            item on its storage

        :return: A OneDriveItem that represents the item described in the JSON structure
        """
        parent_path = item_json["parentReference"]["path"].replace("/drive/root:", "")
        parent_id = item_json["parentReference"]["id"]
        item_name = item_json["name"]
        item_id = item_json["id"]
        item_path = f"{parent_path}/{item_name}"
        
        if None != item_json.get("file", None):
            onedrive_item = OneDriveFileItem(item_path, parent_id, item_id)
        elif None != item_json.get("folder", None):
            onedrive_item = OneDriveFolderItem(item_path, parent_id, item_id)
        elif None != item_json.get("package", None):
            onedrive_item = OneDrivePackageItem(item_path, parent_id, item_id)
        else:
            raise RuntimeError("OneDrive element type is unfamiliar")
        
        return onedrive_item

    def __update_token(self, token):
        """
        Updates the token that the session of this object uses when it attempts to send API
        requests to OneDrive's servers

        :param token: The new token to use
        """
        self.__session_token = token
        self.__http_session.headers.update({"Authorization": self.__session_token})

    def __safe_http_request(self, *args, **kwargs) -> requests.Response:
        """
        Sends an http request using the self.__http_session object, retries
        up to 4 times if temporary exception occur and finally raises an
        exception if the status code is an error.

        Note - This method supports all the arguments of the requests.Session.request() method
        :return: The requests.Response option returned from the requests module
        """
        retries = 4
        for i in range(retries):
            try:
                res = self.__http_session.request(*args, **kwargs)
            except requests.exceptions.ChunkedEncodingError or requests.exceptions.Timeout:
                continue

            if HTTPStatus.SERVICE_UNAVAILABLE == res.status_code:
                time.sleep(0.5)
            else:
                break
        
        res.raise_for_status()
        return res

    def __upload_file_content(self, onedrive_file_path: str, file_content: bytes, req_data: dict) -> requests.Response:
        """
        Uploads a content of a file to the OneDrive cloud storage.

        :param onedrive_file_path: The path of the target file for the upload
        :param file_content: The content to upload
        :param req_data: A dict of OneDrive's upload settings
            by now, the parameter that I identified is meant to
            tell OneDrive's server whether to fail when a file with this
            path exists or to just modify it. Its name is '"@name.conflictBehavior'
            and it can be set to 'replace' or 'fail'
        :return: The respond from the server
        """
        res = self.__safe_http_request("POST", f"https://api.onedrive.com/v1.0/drives/me/items/root:{onedrive_file_path}:/oneDrive.createUploadSession", json=req_data)
        res_json = res.json()
        upload_url = res_json["uploadUrl"]
        
        headers = {"Content-Length": str(len(file_content))}
        res = self.__safe_http_request("PUT", upload_url, data=file_content, headers=headers)
        
        return res

    def __delete_item_by_id(self, item_id):
        """
        Deletes an item from the cloud storage.

        :param item_id: The ID of the item to delete
        """
        res = self.__safe_http_request("DELETE", f"https://api.onedrive.com/v1.0/drives/me/items/{item_id}")

    def login_using_token(self, token: str):
        """
        \"Logins\" into a OneDrive account using an access token for it.

        :param token: The token to login with. Should be given with its prefix. For example: \"Bearer ...\" or \"WLID1.1 t=...\"
        """
        self.__update_token(token)

    def get_token(self):
        """
        Returns the access token used for the authenticating with OneDrive.
        """
        return self.__session_token
    
    def rename_item(self, onedrive_item: OneDriveItem, new_name: str) -> OneDriveItem:
        """
        Renames an item in the cloud storage.

        :param onedrive_item: The OneDrive item to rename
        :param new_name: The new name
        :return: The new item after it was renamed
        """
        params = {
            "@name.conflictBehavior":"replace",
            "name": new_name,
            "select": "*, path"
        }
        res = self.__safe_http_request("PATCH", f"https://api.onedrive.com/v1.0/drives/me/items/{onedrive_item.id}", json=params)
        return self.__item_json_to_onedrive_item(res.json())  
    
    def cancel_all_onedrive_changes_subscriptions(self):
        """
        Cancels all the subscriptions for syncing with the OneDrive account. In other words, 
        all the OneDrive applications that sync local directories with the OneDrive account will
        stop syncing files with the account until they are restarted.
        """
        res = self.__safe_http_request("GET", "https://api.onedrive.com/v1.0/drive/root/subscriptions")
        for subscription in res.json()["value"]:
            subscription_id = subscription["id"]
            res = self.__safe_http_request("DELETE", f"https://api.onedrive.com/v1.0/drive/root/subscriptions/{subscription_id}")

    def send_item_to_email(self, onedrive_item: OneDriveItem, email: str):
        """
        Shares a OneDrive item with an email. This method can be used for sharing an item with an email
        address that does not belong to a Microsoft account.

        :param onedrive_item: The OneDrive item to share.
        :param email: The email to share the item with.
        """
        headers = {
            "AppId": "1276168582",
            "ClientAppId": "1276168582",
            "Platform": "Android Emulator",
            "Version": "6.74",
            "User-Agent": "okhttp/4.9.3",
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
        }

        params = {
            "entities":[{"email": email, "linkType":0, "role":2, "type":0}],
            "id": onedrive_item.id,
            "message": "",
            "requireSignIn": False,
            "userAction":0
        }
        res = self.__safe_http_request("POST", "https://skyapi.live.net/API/2/SetPermissions", json=params, headers=headers)

    def get_user_preferences(self):
        """
        Returns the user's email preferences.
        """
        res = self.__safe_http_request("GET", f"https://api.onedrive.com/v1.0/drive/userPreferences/email")
        return res.json()
    
    def patch_user_preferences(self, new_preferences: dict):
        """
        Changes the user's email preferences. Supported settings with example values:
        {
            ActivitiesDigest: true
            DocumentDigestEmail: true
            MassDelete: true
            PhotoStreamAccessGranted: true
            PhotoStreamComment: true
            PhotoStreamInviteAccepted: true
            PhotoStreamNewPost: true
            PhotoStreamReaction: true
            PremiumPositioning: true
            RansomwareDetection: true
            WeekendRecap: false
        }

        :param new_preferences: A dict of the new preferences
        """
        res = self.__safe_http_request("PATCH", f"https://api.onedrive.com/v1.0/drive/userPreferences/email", json=new_preferences)

    def delete_from_recycle_bin(self, onedrive_item_id_list: list[OneDriveItem]):
        """
        Delete specific OneDrive items from the recycle bin.

        :param onedrive_item_id_list: A list of the items to delete
        """
        headers = {
            "AppId": "1276168582",
            "ClientAppId": "1276168582",
            "Platform": "Android Emulator",
            "Version": "6.74",
            "User-Agent": "okhttp/4.9.3",
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
        }
        
        params = {
            "cid": self.get_drive_id(),
            "deletionType": 3,
            "items": onedrive_item_id_list
        }

        res = self.__safe_http_request("POST", f"https://skyapi.live.net/API/2/DeleteItems", headers=headers, json=params)

    def empty_recycle_bin(self):
        """
        Empties the recycle bin
        """
        headers = {
            "AppId": "1276168582",
            "ClientAppId": "1276168582",
            "Platform": "Android Emulator",
            "Version": "6.74",
            "User-Agent": "okhttp/4.9.3",
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
        }

        res = self.__safe_http_request("POST", f"https://skyapi.live.net/API/2/DeleteAll", headers=headers)

    def get_drive_id(self):
        """
        Returns the ID that identifies the drive of the OneDrive cloud storage
        """
        if None != self.__drive_id:
            return self.__drive_id
        
        res = self.__safe_http_request("GET", "https://api.onedrive.com/v1.0/drives/me")
        self.__drive_id = res.json()["id"]

        return self.__drive_id

    def get_item_by_path(self, item_path: str) -> OneDriveItem:
        """
        Returns an item by its path on the cloud storage.

        :param item_path: The item's path
        :raises RuntimeError: If the given path was not found
        """
        if "/" != item_path:
            onedrive_parent_item = self.get_item_by_path(os.path.dirname(item_path))
            path_parent_children = self.list_children(onedrive_parent_item)
            path_basename = os.path.basename(item_path)
            for child_onedrive_item in path_parent_children:
                if path_basename == child_onedrive_item.name:
                    return child_onedrive_item
            raise RuntimeError("Could not find OneDrive item")
        else:
            return self.get_root_folder_item()

    def read_shared_file_content(self, onedrive_drive_id: str, onedrive_item_id: str, auth_key: str) -> bytes:
        """
        Reads the content of a shared file by its ID, the ID of its OneDrive drive and using
        an authentication key that was issued specifically for the purpose of the share.

        The parameters of this call can all be extracted from an email that was sent as a result
        of sharing a file with OneDrive.

        Note - You do not have to be logged in in order to use this function.

        :param onedrive_drive_id: The ID of the OneDrive drive where that shared file is located
        :param onedrive_item_id: The ID of the shared file
        :param auth_key: The authentication key that was issued for the purpose of the share
        :return: The content of the shared file
        """
        req_data = {
            "select": "id,@content.downloadUrl",
            "authkey": auth_key,
        }

        res = self.__safe_http_request("GET", f"https://api.onedrive.com/v1.0/drives/{onedrive_drive_id}/items/{onedrive_item_id}", params=req_data)
        res = self.__safe_http_request("GET", res.json()["@content.downloadUrl"])
        return res.content
    
    def read_file_content(self, onedrive_item: OneDriveFileItem) -> bytes:
        """
        Read the content of a file in OneDrive

        :param onedrive_item: The file to read
        :return: The content of the file
        """
        req_data = {"select": "@content.downloadUrl"}

        res = self.__safe_http_request("GET", f"https://api.onedrive.com/v1.0/drives/me/items/{onedrive_item.id}", json=req_data)
        res = self.__safe_http_request("GET", res.json()["@content.downloadUrl"])
        return res.content

    def create_file(self, onedrive_file_path: str, file_content: bytes, modify_if_exists: bool = False) -> OneDriveFileItem:
        """
        Creates a file in OneDrive.

        :param onedrive_file_path: The path for the new file.
        :param file_content: The content of the new file
        :param modify_if_exists: True if this function should modify the path of the given file in case it already exists, defaults to False
        :return: The new file
        """
        conflict_behavior = "replace" if modify_if_exists else "fail"
        req_data = {"item":{"@name.conflictBehavior":conflict_behavior}}
        upload_response = self.__upload_file_content(onedrive_file_path, file_content, req_data)
        upload_response_json = upload_response.json()
        return self.__item_json_to_onedrive_item(upload_response_json)

    def modify_file_content(self, onedrive_item: OneDriveFileItem, new_content: bytes):
        """
        Modifies a file content in OneDrive.

        :param onedrive_item: The file to modify
        :param new_content: The new content to overwrite the file with
        """
        req_data = {"item":{"@name.conflictBehavior":"replace"}}
        self.__upload_file_content(onedrive_item.full_path, new_content, req_data)

    def delete_item(self, onedrive_item: OneDriveItem):
        """
        Deletes an item in OneDrive.

        :param onedrive_item: The item to delete
        """
        self.__delete_item_by_id(onedrive_item.id)

    def get_root_folder_item(self) -> OneDriveFolderItem:
        """
        Returns the root folder in OneDrive.
        """
        return OneDriveFolderItem("/", None, "root")

    def list_children(self, onedrive_folder: OneDriveFolderItem) -> list[OneDriveItem]:
        """
        Lists all the direct children of a folder in OneDrive (only at the first level).

        :param onedrive_folder: The folder to list
        :return: A list containing all the children of the given folder
        """
        req_params = {
            "$top": 100,
            "$select": "*,ocr,webDavUrl,sharepointIds,isRestricted,commentSettings,specialFolder"
        }

        children_list = []
        next_page_request_url = f"https://api.onedrive.com/v1.0/drives/me/items/{onedrive_folder.id}/children"
        while next_page_request_url:
            res = self.__safe_http_request("GET", next_page_request_url, json=req_params)
            res_json = res.json()
            res_children_list = res_json["value"]
            next_page_request_url = res_json.get("@odata.nextLink", None)

            for child_element in res_children_list:
                onedrive_item = self.__item_json_to_onedrive_item(child_element)
                children_list.append(onedrive_item)

        return children_list

    
    def list_children_recursively(self, onedrive_folder_item: OneDriveFolderItem) -> list[OneDriveItem]:
        """
        Lists all the children of a folder in OneDrive recursively (at all levels)

        :param onedrive_folder_item: The folder to list
        :return: A list of all the folder's children
        """
        all_children_items = []
        first_level_children = self.list_children(onedrive_folder_item)
        
        all_children_items.extend(first_level_children)
        for onedrive_child_item in first_level_children:
            if isinstance(onedrive_child_item, OneDriveFolderItem):
                all_children_items.extend(self.list_children_recursively(onedrive_child_item))

        return all_children_items

