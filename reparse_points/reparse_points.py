import win32file
import winioctlcon
import ctypes
from .reparse_structs import *
from file_utils import nt_path
import pywintypes

IO_REPARSE_TAG_SYMLINK = 0xA000000C
IO_REPARSE_TAG_MOUNT_POINT = 0xA0000003
REPARSE_DATA_BUFFER_HEADER_LENGTH = getattr(REPARSE_DATA_BUFFER, "GenericReparseBuffer").offset

def create_symlink_reparse_buffer(target_path: str, print_name: str, relative: bool):
    if not relative: target_path = nt_path(target_path)
    unicode_target_path = ctypes.create_unicode_buffer(target_path)
    unicode_target_path_byte_size = (len(unicode_target_path) - 1) * 2 # remove null terminator from size
    unicode_print_name = ctypes.create_unicode_buffer(print_name)
    unicode_print_name_byte_size = (len(unicode_print_name) - 1) * 2 # remove null terminator from size
    
    path_buffer_byte_size = unicode_target_path_byte_size + unicode_print_name_byte_size + 12 + 4
    total_size = path_buffer_byte_size + REPARSE_DATA_BUFFER_HEADER_LENGTH;

    reparse_data_buffer = ctypes.create_string_buffer(b"\x00" * (total_size-1))
    reparse_data_struct = ctypes.cast(reparse_data_buffer, ctypes.POINTER(REPARSE_DATA_BUFFER)).contents
    reparse_data_struct.ReparseTag = IO_REPARSE_TAG_SYMLINK
    reparse_data_struct.ReparseDataLength = path_buffer_byte_size

    reparse_data_struct.SymbolicLinkReparseBuffer.SubstituteNameOffset = 0
    reparse_data_struct.SymbolicLinkReparseBuffer.SubstituteNameLength = unicode_target_path_byte_size

    path_buffer_address = ctypes.addressof(reparse_data_struct) + REPARSE_DATA_BUFFER_HEADER_LENGTH + getattr(SYMBOLIC_LINK_REPARSE_BUFFER, "PathBuffer").offset
    path_buffer_pointer = ctypes.cast(path_buffer_address, ctypes.POINTER(ctypes.c_byte))
    ctypes.memmove(path_buffer_pointer, unicode_target_path, unicode_target_path_byte_size + 2)

    reparse_data_struct.SymbolicLinkReparseBuffer.PrintNameOffset = unicode_target_path_byte_size + 2
    reparse_data_struct.SymbolicLinkReparseBuffer.PrintNameLength = unicode_print_name_byte_size

    print_name_address = ctypes.addressof(reparse_data_struct) + REPARSE_DATA_BUFFER_HEADER_LENGTH + getattr(SYMBOLIC_LINK_REPARSE_BUFFER, "PathBuffer").offset + unicode_target_path_byte_size + 2
    print_name_pointer = ctypes.cast(print_name_address, ctypes.POINTER(ctypes.c_byte))
    ctypes.memmove(print_name_pointer, unicode_print_name, unicode_print_name_byte_size + 2)
    reparse_data_struct.SymbolicLinkReparseBuffer.Flags = 1 if relative else 0

    return bytes(reparse_data_buffer)

def create_mount_point_reparse_buffer(target_path: str, print_name: str, relative: bool):
    if not relative: target_path = nt_path(target_path)
    unicode_target_path = ctypes.create_unicode_buffer(target_path)
    unicode_target_path_byte_size = (len(unicode_target_path) - 1) * 2 # remove null terminator from size
    unicode_print_name = ctypes.create_unicode_buffer(print_name)
    unicode_print_name_byte_size = (len(unicode_print_name) - 1) * 2 # remove null terminator from size
    
    path_buffer_byte_size = unicode_target_path_byte_size + unicode_print_name_byte_size + 8 + 4
    total_size = path_buffer_byte_size + REPARSE_DATA_BUFFER_HEADER_LENGTH;

    reparse_data_buffer = ctypes.create_string_buffer(b"\x00" * (total_size-1))
    reparse_data_struct = ctypes.cast(reparse_data_buffer, ctypes.POINTER(REPARSE_DATA_BUFFER)).contents
    reparse_data_struct.ReparseTag = IO_REPARSE_TAG_MOUNT_POINT
    reparse_data_struct.ReparseDataLength = path_buffer_byte_size

    reparse_data_struct.MountPointReparseBuffer.SubstituteNameOffset = 0
    reparse_data_struct.MountPointReparseBuffer.SubstituteNameLength = unicode_target_path_byte_size

    path_buffer_address = ctypes.addressof(reparse_data_struct) + REPARSE_DATA_BUFFER_HEADER_LENGTH + getattr(MOUNT_POINT_REPARSE_BUFFER, "PathBuffer").offset
    path_buffer_pointer = ctypes.cast(path_buffer_address, ctypes.POINTER(ctypes.c_byte))
    ctypes.memmove(path_buffer_pointer, unicode_target_path, unicode_target_path_byte_size + 2)

    reparse_data_struct.MountPointReparseBuffer.PrintNameOffset = unicode_target_path_byte_size + 2
    reparse_data_struct.MountPointReparseBuffer.PrintNameLength = unicode_print_name_byte_size

    print_name_address = ctypes.addressof(reparse_data_struct) + REPARSE_DATA_BUFFER_HEADER_LENGTH + getattr(MOUNT_POINT_REPARSE_BUFFER, "PathBuffer").offset + unicode_target_path_byte_size + 2
    print_name_pointer = ctypes.cast(print_name_address, ctypes.POINTER(ctypes.c_byte))
    ctypes.memmove(print_name_pointer, unicode_print_name, unicode_print_name_byte_size + 2)

    return bytes(reparse_data_buffer)


def set_reparse_point(reparse_point_path, reparse_data_buffer, is_dir=False):
    file_flags = win32file.FILE_FLAG_OPEN_REPARSE_POINT
    if is_dir:
        try:
            win32file.CreateDirectoryW(reparse_point_path, None)
        except pywintypes.error:
            pass
        file_flags |= win32file.FILE_FLAG_BACKUP_SEMANTICS
    else:
        open(reparse_point_path, "wb").close()

    reparse_point_handle = win32file.CreateFile(reparse_point_path, win32file.GENERIC_READ | win32file.GENERIC_WRITE, 0, None, win32file.OPEN_EXISTING, file_flags, 0)
    win32file.DeviceIoControl(reparse_point_handle, winioctlcon.FSCTL_SET_REPARSE_POINT, reparse_data_buffer, None, None)

def create_ntfs_symlink(reparse_point_path, target_path, relative=False, print_name=None, is_dir=False):
    if None == print_name: print_name = target_path
    reparse_data_buffer = create_symlink_reparse_buffer(target_path, print_name, relative)
    set_reparse_point(reparse_point_path, reparse_data_buffer, is_dir)

def create_mount_point(reparse_point_path, target_path, relative=False, print_name=None):
    if None == print_name: print_name = target_path
    reparse_data_buffer = create_mount_point_reparse_buffer(target_path, print_name, relative)
    set_reparse_point(reparse_point_path, reparse_data_buffer, True)

