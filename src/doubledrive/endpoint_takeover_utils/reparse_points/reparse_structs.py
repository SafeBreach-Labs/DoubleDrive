from ctypes import *
from ctypes.wintypes import *

class GENERIC_REPARSE_BUFFER(Structure):
    _fields_ = (('DataBuffer', BYTE * 1),)

class SYMBOLIC_LINK_REPARSE_BUFFER(Structure):
    _fields_ = (('SubstituteNameOffset', USHORT),
                ('SubstituteNameLength', USHORT),
                ('PrintNameOffset', USHORT),
                ('PrintNameLength', USHORT),
                ('Flags', ULONG),
                ('PathBuffer', WCHAR * 1))


class MOUNT_POINT_REPARSE_BUFFER(Structure):
    _fields_ = (('SubstituteNameOffset', USHORT),
                ('SubstituteNameLength', USHORT),
                ('PrintNameOffset', USHORT),
                ('PrintNameLength', USHORT),
                ('PathBuffer', WCHAR * 1))


class REPARSE_DATA_BUFFER(Structure):
    class REPARSE_BUFFER(Union):
        _fields_ = (('SymbolicLinkReparseBuffer',
                        SYMBOLIC_LINK_REPARSE_BUFFER),
                    ('MountPointReparseBuffer',
                        MOUNT_POINT_REPARSE_BUFFER),
                    ('GenericReparseBuffer',
                        GENERIC_REPARSE_BUFFER))
    _fields_ = (('ReparseTag', ULONG),
                ('ReparseDataLength', USHORT),
                ('Reserved', USHORT),
                ('ReparseBuffer', REPARSE_BUFFER))
    _anonymous_ = ('ReparseBuffer',)


dummy_object = REPARSE_DATA_BUFFER()