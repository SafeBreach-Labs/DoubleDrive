import yaml
import os
import sys
from enum import Enum

class ConfigKey(Enum):
    CMD_FILE = 1
    IS_TEMP_EMAIL = 2
    TARGET_PATHS = 3
    SHOULD_SYNC_STARTUP_FOLDER = 4
    EXFILTRATION_EMAIL_ADDRESS = 5
    VICTIM_INFO_FILE_NAME = 6


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