import yaml
import os
import sys
from enum import Enum

class ConfigKey(Enum):
    TOKEN_DST_EMAIL_ADDRESS = 1
    IS_TEMP_EMAIL = 2
    TOKEN_FILE_NAME = 3
    JUNCTION_NAMES_TO_TARGET_PATHS = 4
    SHOULD_CREATE_ONEDRIVE_BINARIES_JUNCTION = 5
    CMD_FILE_NAME = 6
    QUICK_DELETE = 7
    ONEDRIVE_VERSION_FOLDER_JUNCTION_NAME = 8


g_configs = None
def get_configs():
    global g_configs
    if None != g_configs:
        return g_configs
    
    bundle_dir = getattr(sys, '_MEIPASS', os.path.abspath(os.path.dirname(__file__)))
    path_to_config_file = os.path.abspath(os.path.join(bundle_dir, "config.yaml"))

    with open(path_to_config_file, "r") as f:
        configs = yaml.safe_load(f)
    g_configs = configs

    return g_configs