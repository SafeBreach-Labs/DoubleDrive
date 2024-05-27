import win32cred


CRED_TYPE_GENERIC = 1
GOOGLE_DRIVE_TOKEN_START_BYTES = b"ya29"
TOKEN_LEN_MULTIPLIERS_DISTANCE_FROM_TOKEN = -2
GOOGLE_DRIVE_CRED_NAME_PREFIX = "DriveFS_"


def extract_google_drive_account_token_by_id(account_id: str):
    cred_blob = win32cred.CredRead(f"{GOOGLE_DRIVE_CRED_NAME_PREFIX}{account_id}", CRED_TYPE_GENERIC)["CredentialBlob"]
    token_start_index = cred_blob.find(GOOGLE_DRIVE_TOKEN_START_BYTES)
    token_len_multipliers_index = token_start_index + TOKEN_LEN_MULTIPLIERS_DISTANCE_FROM_TOKEN
    token_len_byte1 = cred_blob[token_len_multipliers_index : token_len_multipliers_index+1]
    token_len_byte2 = cred_blob[token_len_multipliers_index+1 : token_len_multipliers_index+2]
    token_len_multiplier1 = int.from_bytes(token_len_byte1, byteorder="little")
    token_len_multiplier2 = int.from_bytes(token_len_byte2, byteorder="little")
    token_len = token_len_multiplier1 * token_len_multiplier2
    token = cred_blob[token_start_index : token_start_index+token_len].decode()
    return f"Bearer {token}"
