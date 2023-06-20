import requests
import os
import time
from http import HTTPStatus
from seleniumwire import webdriver
from selenium.webdriver.common.by import By

from .onedrive_item import OneDriveItem, OneDriveFileItem, OneDriveFolderItem, OneDrivePackageItem
from doubledrive.cloud_drive.cloud_drive import *

class OneDrive(ICloudDriveSession):

    def __init__(self) -> None:
        self.__drive_id = None
        self.__http_session = requests.Session()

    def __item_json_to_onedrive_item(self, item_json: dict):
        parent_path = item_json["parentReference"]["path"].replace("/drive/root:", "")
        parent_id = item_json["parentReference"]["id"]
        item_name = item_json["name"]
        item_id = item_json["id"]
        item_path = f"{parent_path}/{item_name}"
        
        if None != item_json.get("file", None):
            onedrive_item = OneDriveFileItem(item_path, parent_id, item_id, item_json["size"])
        elif None != item_json.get("folder", None):
            onedrive_item = OneDriveFolderItem(item_path, parent_id, item_id)
        elif None != item_json.get("package", None):
            onedrive_item = OneDrivePackageItem(item_path, parent_id, item_id)
        else:
            raise RuntimeError("OneDrive element type is unfamiliar")
        
        return onedrive_item

    def __login_with_selenium(self, username, password):
        options = {
            "suppress_connection_errors": True,
            "verify_ssl": False
        }
        driver = webdriver.Chrome(seleniumwire_options=options)
        driver.get(f"https://login.live.com?username={username}")
        time.sleep(3)
        password_element = driver.find_element(By.CSS_SELECTOR, "input[type=password]")
        password_element.send_keys(password)
        password_element.submit()
        try:
            driver.find_element(By.ID, "idSIButton9").click()
        except:
            pass
        driver.get("https://onedrive.live.com?id=root")
        time.sleep(5)
        for request in driver.requests:
            if request.url.startswith("https://api.onedrive.com/") and "operations" in request.url:
                self.__update_token(request.headers.get("authorization"))
        
        driver.quit()

    def __update_token(self, token):
        self.__session_token = token
        self.__http_session.headers.update({"Authorization": self.__session_token})

    def __safe_http_request(self, *args, **kwargs) -> requests.Response:
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
        
        if 409 == res.status_code:
            print(res.json())
        res.raise_for_status()
        return res

    def __upload_file_content(self, onedrive_file_path: str, file_content: bytes, req_data: dict):
        res = self.__safe_http_request("POST", f"https://api.onedrive.com/v1.0/drives/me/items/root:{onedrive_file_path}:/oneDrive.createUploadSession", json=req_data)
        res_json = res.json()
        upload_url = res_json["uploadUrl"]
        
        headers = {"Content-Length": str(len(file_content))}
        res = self.__safe_http_request("PUT", upload_url, data=file_content, headers=headers)
        
        return res

    def __delete_item_by_id(self, item_id):
        res = self.__safe_http_request("DELETE", f"https://api.onedrive.com/v1.0/drives/me/items/{item_id}")

    def login_using_creds(self, username: str, password: str):
        self.__login_with_selenium(username, password)

    def login_using_token(self, token: str):
        self.__update_token(token)

    def get_token(self):
        return self.__session_token
    
    def rename_item(self, onedrive_item: OneDriveItem, new_name: str):
        params = {
            "@name.conflictBehavior":"replace",
            "name": new_name,
            "select": "*, path"
        }
        res = self.__safe_http_request("PATCH", f"https://api.onedrive.com/v1.0/drives/me/items/{onedrive_item.id}", json=params)
        return self.__item_json_to_onedrive_item(res.json())  
    
    def cancel_all_onedrive_changes_subscriptions(self):
        res = self.__safe_http_request("GET", "https://api.onedrive.com/v1.0/drive/root/subscriptions")
        for subscription in res.json()["value"]:
            subscription_id = subscription["id"]
            res = self.__safe_http_request("DELETE", f"https://api.onedrive.com/v1.0/drive/root/subscriptions/{subscription_id}")

    def send_item_to_email(self, onedrive_item: OneDriveItem, email: str):
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
        res = self.__safe_http_request("GET", f"https://api.onedrive.com/v1.0/drive/userPreferences/email")
        return res.json()
    
    def patch_user_preferences(self, new_preferences):
        res = self.__safe_http_request("PATCH", f"https://api.onedrive.com/v1.0/drive/userPreferences/email", json=new_preferences)

    def delete_from_recycle_bin(self, onedrive_item_id_list):
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
        if None != self.__drive_id:
            return self.__drive_id
        
        res = self.__safe_http_request("GET", "https://api.onedrive.com/v1.0/drives/me")
        self.__drive_id = res.json()["id"]

        return self.__drive_id

    def get_item_by_path(self, item_path: str) -> OneDriveItem:
        if "/" != item_path:
            onedrive_parent_item = self.get_onedrive_item_by_path(os.path.dirname(item_path))
            path_parent_children = self.list_children(onedrive_parent_item)
            path_basename = os.path.basename(item_path)
            for child_onedrive_item in path_parent_children:
                if path_basename == child_onedrive_item.name:
                    return child_onedrive_item
            raise RuntimeError("Could not find OneDrive item")
        else:
            return self.get_root_onedrive_folder_item()

    def read_shared_file_content(self, onedrive_drive_id: str, onedrive_item_id: str, auth_key: str) -> bytes:
        req_data = {
            "select": "id,@content.downloadUrl",
            "authkey": auth_key,
        }

        res = self.__safe_http_request("GET", f"https://api.onedrive.com/v1.0/drives/{onedrive_drive_id}/items/{onedrive_item_id}", params=req_data)
        res = self.__safe_http_request("GET", res.json()["@content.downloadUrl"])
        return res.content
    
    def read_file_content(self, onedrive_item: OneDriveItem) -> bytes:
        req_data = {"select": "@content.downloadUrl"}

        res = self.__safe_http_request("GET", f"https://api.onedrive.com/v1.0/drives/me/items/{onedrive_item.id}", json=req_data)
        res = self.__safe_http_request("GET", res.json()["@content.downloadUrl"])
        return res.content

    def create_file(self, onedrive_file_path: str, file_content: bytes, modify_if_exists: bool = False) -> OneDriveFileItem:
        conflict_behavior = "replace" if modify_if_exists else "fail"
        req_data = {"item":{"@name.conflictBehavior":conflict_behavior}}
        upload_response = self.__upload_file_content(onedrive_file_path, file_content, req_data)
        upload_response_json = upload_response.json()
        return self.__item_json_to_onedrive_item(upload_response_json)

    def modify_file_content(self, onedrive_item: OneDriveItem, new_content: bytes):
        req_data = {"item":{"@name.conflictBehavior":"replace"}}
        self.__upload_file_content(onedrive_item.full_path, new_content, req_data)

    def delete_item(self, onedrive_item: OneDriveItem):
        self.__delete_item_by_id(onedrive_item.id)

    def get_root_onedrive_folder_item(self) -> OneDriveFolderItem:
        return OneDriveFolderItem("/", None, "root")

    def list_children(self, onedrive_folder: OneDriveFolderItem) -> list[OneDriveItem]:
        req_params = {
            "$top": 100,
            "$select": "*,ocr,webDavUrl,sharepointIds,isRestricted,commentSettings,specialFolder"
        }

        # OneDrive returns 200 OK for listing of some folders just without the value parameter that
        # lists the children so we need to check that and renew the token if that happens
        next_page_request_url = f"https://api.onedrive.com/v1.0/drives/me/items/{onedrive_folder.id}/children"
        while next_page_request_url:
            res = self.__safe_http_request("GET", next_page_request_url, json=req_params)
            res_json = res.json()
            res_children_list = res_json["value"]
            next_page_request_url = res_json.get("@odata.nextLink", None)

        childern_list = []
        for child_element in res_children_list:
            onedrive_item = self.__item_json_to_onedrive_item(child_element)
            childern_list.append(onedrive_item)

        return childern_list

    
    def list_children_recursively(self, onedrive_folder_item: OneDriveFolderItem) -> list[OneDriveItem]:
        all_children_items = []
        try:
            first_level_children = self.list_children(onedrive_folder_item)
        except PermissionError:
            return []
        all_children_items.extend(first_level_children)
        for onedrive_child_item in first_level_children:
            if isinstance(onedrive_child_item, OneDriveFolderItem):
                all_children_items.extend(self.list_children_recursively(onedrive_child_item))

        return all_children_items

