import winreg
import os

class OneDriveInfo:
    ONEDRIVE_PER_USER_FOLDER = os.path.expandvars(r"%localappdata%\Microsoft\OneDrive")
    PERSONAL_ODL_FOLDER = os.path.join(ONEDRIVE_PER_USER_FOLDER, "logs\\Personal")

    def __init__(self) -> None:
        hkcu_key = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
    
        with winreg.OpenKey(hkcu_key, "Software\\Microsoft\\OneDrive\\Accounts\\Personal") as onedrive_personal_reg_key:
            self.sync_folder = winreg.QueryValueEx(onedrive_personal_reg_key, "UserFolder")[0]

        with winreg.OpenKey(hkcu_key, "Software\\Microsoft\\OneDrive") as onedrive_reg_key:
            self.main_exe_path = winreg.QueryValueEx(onedrive_reg_key, "OneDriveTrigger")[0]
            onedrive_version = winreg.QueryValueEx(onedrive_reg_key, "Version")[0]
        
        self.program_folder = os.path.dirname(self.main_exe_path)
        self.version_installation_folder = os.path.join(self.program_folder, onedrive_version)


g_onedrive_info_single_instance = None
def get_onedrive_info():
    global g_onedrive_info_single_instance
    if None == g_onedrive_info_single_instance:
        g_onedrive_info_single_instance = OneDriveInfo()
    return g_onedrive_info_single_instance