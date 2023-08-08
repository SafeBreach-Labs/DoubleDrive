import base64
import datetime
import glob
import gzip
import io
import json
import os
import re
import string
import struct
from datetime import date

from construct import *
from construct.core import Int32ul, Int64ul
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

control_chars = "".join(map(chr, range(0,32))) + "".join(map(chr, range(127,160)))
not_control_char_re = re.compile(f"[^{control_chars}]" + "{4,}")
# If  we only want ascii, use "ascii_chars_re" below
printable_chars_for_re = string.printable.replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]").encode()
ascii_chars_re = re.compile(b"[{" + printable_chars_for_re + b"}]" + b"{4,}")

def ReadUnixMsTime(unix_time_ms): # Unix millisecond timestamp
    """Returns datetime object, or empty string upon error"""
    if unix_time_ms not in ( 0, None, ""):
        try:
            if isinstance(unix_time_ms, str):
                unix_time_ms = float(unix_time_ms)
            return datetime.datetime(1970, 1, 1) + datetime.timedelta(seconds=unix_time_ms/1000)
        except (ValueError, OverflowError, TypeError) as ex:
            #print("ReadUnixMsTime() Failed to convert timestamp from value " + str(unix_time_ms) + " Error was: " + str(ex))
            pass
    return ""

CDEF = Struct(
    "signature" / Int64ul, # CCDDEEFF00000000
    "timestamp" / Int64ul,
    "unk1" / Int32ul,
    "unk2" / Int32ul,
    "unknown" / Byte[20],
    "one" / Int32ul,      # 1
    "data_len" / Int32ul,
    "reserved" / Int32ul  # 0
    # followed by Data
)

Odl_header = Struct(
    "signature" / Int64ul, # EBFGONED
    "unk_version" / Int32ul,
    "unknown_2" / Int32ul,
    "unknown_3" / Int64ul,
    "unknown_4" / Int32ul,
    "one_drive_version" / Byte[0x40],
    "windows_version" / Byte[0x40],
    "reserved" / Byte[0x64]
)

def read_string(data):
    """read string, return tuple (bytes_consumed, string)"""
    if (len(data)) >= 4:
        str_len = struct.unpack("<I", data[0:4])[0]
        if str_len:
            if str_len > len(data):
                print("Error in read_string()")
            else:
                return (4 + str_len, data[4:4 + str_len].decode("utf8", "ignore"))
    return (4, "")

def guess_encoding(obfuscation_map_path):
    """Returns either UTF8 or UTF16LE after checking the file"""
    encoding = "utf-16le" # on windows this is the default
    with open(obfuscation_map_path, "rb") as f:
        data = f.read(4)
        if len(data) == 4: 
            if data[1] == 0 and data[3] == 0 and data[0] != 0 and data[2] != 0:
                pass # confirmed utf-16le
            else:
                encoding = "utf8"
    return encoding

# UnObfuscation code
key = ""
utf_type = "utf16"

def decrypt(cipher_text):
    """cipher_text is expected to be base64 encoded"""
    global key
    global utf_type
    
    if key == "":
        return ""
    if len(cipher_text) < 22:
        return "" # invalid 
    # add proper base64 padding
    remainder = len(cipher_text) % 4
    if remainder == 1:
        return "" # invalid b64
    elif remainder in (2, 3):
        cipher_text += "="* (4 - remainder)
    try:
        cipher_text = cipher_text.replace("_", "/").replace("-", "+")
        cipher_text = base64.b64decode(cipher_text)
    except:
        return ""
    
    if len(cipher_text) % 16 != 0:
        return ""
    else:
        pass

    try:
        cipher = AES.new(key, AES.MODE_CBC, iv=b"\0"*16)
        raw = cipher.decrypt(cipher_text)
    except ValueError as ex:
        print("Exception while decrypting data", str(ex))
        return ""
    try:
        plain_text = unpad(raw, 16)
    except ValueError as ex:
        #print("Error in unpad!", str(ex), raw)
        return ""
    try:
        plain_text = plain_text.decode(utf_type)#, "ignore")
    except ValueError as ex:
        print(f"Error decoding {utf_type}", str(ex))
    return plain_text

def read_keystore(keystore_path):
    global key
    global utf_type
    encoding = guess_encoding(keystore_path)
    with open(keystore_path, "r", encoding=encoding) as f:
        try:
            j = json.load(f)
            key = j[0]["Key"]
            version = j[0]["Version"]
            utf_type = "utf32" if key.endswith("\\u0000\\u0000") else "utf16"
            print(f"Recovered Unobfuscation key {key}, version={version}, utf_type={utf_type}")
            key = base64.b64decode(key)
            if version != 1:
                print(f"WARNING: Key version {version} is unsupported. This may not work. Contact the author if you see this to add support for this version.")
        except ValueError as ex:
            print("JSON error " + str(ex))

def read_obfuscation_map(obfuscation_map_path, store_all_key_values):
    map = {}
    repeated_items_found = False
    encoding = guess_encoding(obfuscation_map_path)
    with open(obfuscation_map_path, "r", encoding=encoding) as f:
        for line in f.readlines():
            line = line.rstrip("\n")
            terms = line.split("\t")
            if len(terms) == 2:
                if terms[0] in map: #REPEATED item found!  
                    repeated_items_found = True
                    if not store_all_key_values:
                        continue # newer items are on top, skip older items found below.
                    old_val = map[terms[0]]
                    new_val = f"{old_val}|{terms[1]}"
                    map[terms[0]] = new_val
                    last_key = terms[0]
                    last_val = new_val
                else:
                    map[terms[0]] = terms[1]
                    last_key = terms[0]
                    last_val = terms[1]
            else:
                if terms[0] in map:
                    if not store_all_key_values:
                        continue
                last_val += "\n" + line
                map[last_key] = last_val
                #print("Error? " + str(terms))
    if repeated_items_found:
        print("WARNING: Multiple instances of some keys were found in the ObfuscationMap.")
    return map
    
def tokenized_replace(string, map):
    output = ""
    tokens = ":\\.@%#&*|{}!?<>;:~()//\"'"
    parts = [] # [ ("word", 1), (":", 0), ..] word=1, token=0
    last_word = ""
    last_token = ""
    for i, char in enumerate(string):
        if char in tokens:
            if last_word:
                parts.append((last_word, 1))
                last_word = ""
            if last_token:
                last_token += char
            else:
                last_token = char
        else:
            if last_token:
                parts.append((last_token, 0))
                last_token = ""
            if last_word:
                last_word += char
            else:
                last_word = char
    if last_token:
        parts.append((last_token, 0))
    if last_word:
        parts.append((last_word, 1))
    
    # now join all parts replacing the words
    for part in parts:
        if part[1] == 0: # token
            output += part[0]
        else: # word
            word = part[0]
            decrypted_word = decrypt(word)
            if decrypted_word:
                output += decrypted_word
            elif word in map:
                output += map[word]
            else:
                output += word
    return output

def extract_strings(data, map, unobfuscate=True):
    extracted = []
    #for match in not_control_char_re.finditer(data): # This gets all unicode chars, can include lot of garbage if you only care about English, will miss out other languages
    for match in ascii_chars_re.finditer(data): # Matches ONLY Ascii (old behavior) , good if you only care about English
        text = match.group()
        if match.start() >= 4:
            match_len = match.end() - match.start()
            y = data[match.start() - 4 : match.start()]
            stored_len = struct.unpack("<I", y)[0]
            if match_len - stored_len <= 5:
                x = text[0:stored_len].decode("utf8", "ignore")
                x = x.rstrip("\n").rstrip("\r")
                x.replace("\r", "").replace("\n", " ")
                if unobfuscate:
                    x = tokenized_replace(x, map)
                extracted.append(x)
            else:
                print("invalid match - not text ", match_len - stored_len, text)

    if len(extracted) == 0:
        extracted = ""
    elif len(extracted) == 1:
        extracted = extracted[0]
    return extracted

def process_odl(path, map, show_all_data):
    odl_rows = []
    basename = os.path.basename(path)
    with open(path, "rb") as f:
        i = 1
        header = f.read(8)
        if header[0:8] == b"EBFGONED": # Odl header
            f.seek(0x100)
            header = f.read(8)
            file_pos = 0x108
        else:
            file_pos = 8
        # Now either we have the gzip header here or the CDEF header (compressed or uncompressed handles both)
        if header[0:4] == b"\x1F\x8B\x08\x00": # gzip
            try:
                f.seek(file_pos - 8)
                file_data = gzip.decompress(f.read())
            except (gzip.BadGzipFile,OSError) as ex:
                print("..decompression error for file {path} " + str(ex))
                return
            f.close()
            f = io.BytesIO(file_data)
            header = f.read(8)
        if header != b"\xCC\xDD\xEE\xFF\0\0\0\0": # CDEF header
            print("wrong header! Did not find 0xCCDDEEFF")
            return
        else:
            f.seek(-8, io.SEEK_CUR)
            header = f.read(56) # odl complete header is 56 bytes
        while header:
            odl = {
                "Filename" : basename,
                "File_Index" : i,
                "Timestamp" : None,
                "Code_File" : "",
                "Function" : "",
                "Params_Decoded" : ""
            }
            header = CDEF.parse(header)
            timestamp = ReadUnixMsTime(header.timestamp)
            odl["Timestamp"] = timestamp
            data = f.read(header.data_len)
            data_pos, code_file_name = read_string(data)
            data_pos += 4
            temp_pos, code_function_name = read_string(data[data_pos:])
            data_pos += temp_pos
            if data_pos < header.data_len:
                params = data[data_pos:]
                try:
                    strings_decoded = extract_strings(params, map)
                    #strings_decoded_obfuscated = extract_strings(params, map, False) # for debug only
                    #print(strings)
                except Exception as ex:
                    print(ex)
            else:
                strings_decoded = ""
                # strings_decoded_obfuscated = "" # for debug only
            #odl["Params"] = strings
            odl["Code_File"] = code_file_name
            odl["Function"] = code_function_name
            odl["Params_Decoded"] = strings_decoded
            #odl["Params_Obfuscated"] = strings_decoded_obfuscated  # for debug only
            #print(basename, i, timestamp, code_file_name, code_function_name, strings)
            if show_all_data:
                odl_rows.append(odl)
            else: # filter out irrelevant
                # cache.cpp Find function provides no value, as search term or result is not present
                if code_function_name == "Find" and odl["Code_File"] == "cache.cpp":
                    pass
                elif code_function_name == "RecordCallTimeTaken" and odl["Code_File"] == "AclHelper.cpp":
                    pass
                elif code_function_name == "UpdateSyncStatusText" and odl["Code_File"] == "ActivityCenterHeaderModel.cpp":
                    pass
                elif code_function_name == "FireEvent" and odl["Code_File"] == "EventMachine.cpp":
                    pass
                elif odl["Code_File"] in ("LogUploader2.cpp", "LogUploader.cpp", "ServerRefreshState.cpp", "SyncTelemetry.cpp"):
                    pass
                elif strings_decoded == "":
                    pass
                else:
                    odl_rows.append(odl)
            i += 1
            file_pos += header.data_len
            header = f.read(56) # next cdef header
    return odl_rows

ODL_PER_USER_FOLDER = os.path.expandvars(r"%localappdata%\Microsoft\OneDrive\logs\Personal")

def get_odl_rows():
    odl_folder = os.path.abspath(ODL_PER_USER_FOLDER)
    obfuscation_map_path = os.path.join(odl_folder, "ObfuscationStringMap.txt")
    if not os.path.exists(obfuscation_map_path):
        print(f"ObfuscationStringMap.txt not found in {odl_folder}.")
        map = {}
    else:
        map = read_obfuscation_map(obfuscation_map_path, False)
        print(f"Read {len(map)} items from map")
    
    keystore_path = os.path.join(odl_folder, "general.keystore")
    if not os.path.exists(keystore_path):
        print(f"general.keystore not found in {odl_folder}. WARNING: Strings will not be decoded!!")
    else:
        read_keystore(keystore_path)

    glob_patterns = ("*.odl", "*.odlgz", "*.odlsent") #, "*.aodl")
    paths = []
    odl_rows = []
    for pattern in glob_patterns:
        paths.extend(glob.glob(os.path.join(odl_folder, pattern)))
    for path in paths:
        timestamp = date.fromtimestamp(os.path.getmtime(path))
        if date.today() == timestamp:
            odl_rows.extend(process_odl(path, map, False))

    return odl_rows
