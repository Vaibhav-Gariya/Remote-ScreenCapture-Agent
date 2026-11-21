from pathlib import Path

import ctypes
from ctypes import wintypes


# ============================================================
# Windows DPAPI
# ============================================================

crypt32 = ctypes.WinDLL(
    "crypt32",
    use_last_error=True,
)

kernel32 = ctypes.WinDLL(
    "kernel32",
    use_last_error=True,
)


# ============================================================
# DATA_BLOB
# ============================================================

class DATA_BLOB(ctypes.Structure):

    _fields_ = [
        (
            "cbData",
            wintypes.DWORD,
        ),
        (
            "pbData",
            ctypes.POINTER(
                ctypes.c_byte
            ),
        ),
    ]


# ============================================================
# DPAPI definitions
# ============================================================

crypt32.CryptUnprotectData.argtypes = [
    ctypes.POINTER(DATA_BLOB),
    ctypes.POINTER(wintypes.LPWSTR),
    ctypes.POINTER(DATA_BLOB),
    wintypes.LPVOID,
    wintypes.LPVOID,
    wintypes.DWORD,
    ctypes.POINTER(DATA_BLOB),
]

crypt32.CryptUnprotectData.restype = (
    wintypes.BOOL
)


kernel32.LocalFree.argtypes = [
    wintypes.HLOCAL,
]

kernel32.LocalFree.restype = (
    wintypes.HLOCAL
)


# ============================================================
# Configuration
# ============================================================

SECRET_FILE = Path(
    r"D:\System-D\agent_secret.dat"
)


# ============================================================
# Decrypt API key
# ============================================================

def load_api_key() -> str:

    if not SECRET_FILE.exists():

        raise FileNotFoundError(
            f"API secret not found: "
            f"{SECRET_FILE}"
        )


    encrypted = (
        SECRET_FILE.read_bytes()
    )


    if not encrypted:

        raise RuntimeError(
            "API secret file is empty."
        )


    input_buffer = (
        ctypes.create_string_buffer(
            encrypted
        )
    )


    input_blob = DATA_BLOB(
        len(encrypted),
        ctypes.cast(
            input_buffer,
            ctypes.POINTER(
                ctypes.c_byte
            ),
        ),
    )


    output_blob = DATA_BLOB()


    result = (
        crypt32.CryptUnprotectData(
            ctypes.byref(
                input_blob
            ),
            None,
            None,
            None,
            None,
            0,
            ctypes.byref(
                output_blob
            ),
        )
    )


    if not result:

        error = ctypes.get_last_error()

        raise ctypes.WinError(
            error
        )


    try:

        decrypted = (
            ctypes.string_at(
                output_blob.pbData,
                output_blob.cbData,
            )
        )


        api_key = (
            decrypted
            .decode("utf-8")
        )


        if not api_key:

            raise RuntimeError(
                "Decrypted API key is empty."
            )


        return api_key


    finally:

        kernel32.LocalFree(
            output_blob.pbData
        )