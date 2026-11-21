import ctypes
import logging
import sys
from pathlib import Path


# ============================================================
# Windows DLLs
# ============================================================

kernel32 = ctypes.WinDLL(
    "kernel32",
    use_last_error=True
)

wtsapi32 = ctypes.WinDLL(
    "wtsapi32",
    use_last_error=True
)

advapi32 = ctypes.WinDLL(
    "advapi32",
    use_last_error=True
)


# ============================================================
# Constants
# ============================================================

INVALID_SESSION_ID = 0xFFFFFFFF

CREATE_UNICODE_ENVIRONMENT = 0x00000400

STARTF_USESHOWWINDOW = 0x00000001

SW_HIDE = 0


# ============================================================
# Structures
# ============================================================

class STARTUPINFO(ctypes.Structure):

    _fields_ = [
        ("cb", ctypes.c_ulong),
        ("lpReserved", ctypes.c_wchar_p),
        ("lpDesktop", ctypes.c_wchar_p),
        ("lpTitle", ctypes.c_wchar_p),
        ("dwX", ctypes.c_ulong),
        ("dwY", ctypes.c_ulong),
        ("dwXSize", ctypes.c_ulong),
        ("dwYSize", ctypes.c_ulong),
        ("dwXCountChars", ctypes.c_ulong),
        ("dwYCountChars", ctypes.c_ulong),
        ("dwFillAttribute", ctypes.c_ulong),
        ("dwFlags", ctypes.c_ulong),
        ("wShowWindow", ctypes.c_ushort),
        ("cbReserved2", ctypes.c_ushort),
        ("lpReserved2", ctypes.POINTER(ctypes.c_ubyte)),
        ("hStdInput", ctypes.c_void_p),
        ("hStdOutput", ctypes.c_void_p),
        ("hStdError", ctypes.c_void_p),
    ]


class PROCESS_INFORMATION(ctypes.Structure):

    _fields_ = [
        ("hProcess", ctypes.c_void_p),
        ("hThread", ctypes.c_void_p),
        ("dwProcessId", ctypes.c_ulong),
        ("dwThreadId", ctypes.c_ulong),
    ]


# ============================================================
# Windows API definitions
# ============================================================

kernel32.WTSGetActiveConsoleSessionId.restype = (
    ctypes.c_ulong
)


wtsapi32.WTSQueryUserToken.argtypes = [
    ctypes.c_ulong,
    ctypes.POINTER(ctypes.c_void_p),
]

wtsapi32.WTSQueryUserToken.restype = ctypes.c_int


advapi32.CreateProcessAsUserW.argtypes = [
    ctypes.c_void_p,                       # hToken
    ctypes.c_wchar_p,                      # lpApplicationName
    ctypes.c_wchar_p,                      # lpCommandLine
    ctypes.c_void_p,                       # lpProcessAttributes
    ctypes.c_void_p,                       # lpThreadAttributes
    ctypes.c_int,                          # bInheritHandles
    ctypes.c_ulong,                        # dwCreationFlags
    ctypes.c_void_p,                       # lpEnvironment
    ctypes.c_wchar_p,                      # lpCurrentDirectory
    ctypes.POINTER(STARTUPINFO),           # lpStartupInfo
    ctypes.POINTER(PROCESS_INFORMATION),   # lpProcessInformation
]

advapi32.CreateProcessAsUserW.restype = ctypes.c_int


kernel32.CloseHandle.argtypes = [
    ctypes.c_void_p
]

kernel32.CloseHandle.restype = ctypes.c_int


# ============================================================
# Paths
# ============================================================

if getattr(sys, "frozen", False):

    # ========================================================
    # Packaged Supervisor
    #
    # Supervisor:
    # C:\Users\gariy\Desktop\screen_capture_agent\
    #     dist\
    #         System-D-Supervisor.exe
    #
    # Agent:
    # C:\Users\gariy\Desktop\screen_capture_agent\
    #     dist\
    #         System-D-Agent.exe
    # ========================================================

    BASE_DIR = (
        Path(sys.executable)
        .resolve()
        .parent
    )

    AGENT_EXE = (
        BASE_DIR
        / "System-D-Agent.exe"
    )

else:

    # ========================================================
    # Running Python source directly
    #
    # C:\Users\gariy\Desktop\screen_capture_agent\
    #     supervisor\
    #         session_launcher.py
    #
    # Agent:
    # C:\Users\gariy\Desktop\screen_capture_agent\
    #     dist\
    #         System-D-Agent.exe
    # ========================================================

    BASE_DIR = (
        Path(__file__)
        .resolve()
        .parent
        .parent
    )

    AGENT_EXE = (
        BASE_DIR
        / "dist"
        / "System-D-Agent.exe"
    )


# ============================================================
# Logging
# ============================================================

LOG_DIR = (
    BASE_DIR
    / "logs"
)

LOG_DIR.mkdir(
    parents=True,
    exist_ok=True
)


logging.basicConfig(
    filename=str(
        LOG_DIR
        / "session_launcher.log"
    ),
    level=logging.INFO,
    format=(
        "%(asctime)s "
        "%(levelname)s "
        "%(message)s"
    ),
)


# ============================================================
# Get active console session
# ============================================================

def get_active_session_id():

    session_id = (
        kernel32
        .WTSGetActiveConsoleSessionId()
    )

    logging.info(
        "Active console session ID: %s",
        session_id,
    )

    if (
        session_id
        == INVALID_SESSION_ID
    ):

        raise RuntimeError(
            "No active console session."
        )

    return session_id


# ============================================================
# Launch Agent
# ============================================================

def launch_agent():

    # --------------------------------------------------------
    # Verify Agent executable
    # --------------------------------------------------------

    logging.info(
        "Agent executable: %s",
        AGENT_EXE,
    )

    if not AGENT_EXE.exists():

        logging.error(
            "Agent not found: %s",
            AGENT_EXE,
        )

        raise FileNotFoundError(
            f"Agent not found: {AGENT_EXE}"
        )


    # --------------------------------------------------------
    # Get active interactive session
    # --------------------------------------------------------

    session_id = (
        get_active_session_id()
    )

    logging.info(
        "Attempting to launch Agent "
        "in session %s",
        session_id,
    )


    # --------------------------------------------------------
    # Get user token
    # --------------------------------------------------------

    user_token = ctypes.c_void_p()


    result = (
        wtsapi32.WTSQueryUserToken(
            session_id,
            ctypes.byref(
                user_token
            ),
        )
    )


    if not result:

        error = ctypes.get_last_error()

        logging.error(
            "WTSQueryUserToken failed. "
            "Error: %s",
            error,
        )

        raise ctypes.WinError(
            error
        )


    logging.info(
        "User token obtained successfully "
        "for session %s",
        session_id,
    )


    try:

        # ----------------------------------------------------
        # Startup information
        # ----------------------------------------------------

        startup = STARTUPINFO()

        startup.cb = ctypes.sizeof(
            STARTUPINFO
        )

        # Interactive Windows desktop

        startup.lpDesktop = (
            r"winsta0\default"
        )

        startup.dwFlags = (
            STARTF_USESHOWWINDOW
        )

        startup.wShowWindow = SW_HIDE


        # ----------------------------------------------------
        # Process information
        # ----------------------------------------------------

        process_info = (
            PROCESS_INFORMATION()
        )


        # ----------------------------------------------------
        # Command line
        # ----------------------------------------------------

        command_line = (
            f'"{AGENT_EXE}"'
        )


        # ----------------------------------------------------
        # Launch Agent as interactive user
        # ----------------------------------------------------

        result = (
            advapi32.CreateProcessAsUserW(

                user_token,

                None,

                command_line,

                None,

                None,

                False,

                CREATE_UNICODE_ENVIRONMENT,

                None,

                str(
                    AGENT_EXE.parent
                ),

                ctypes.byref(
                    startup
                ),

                ctypes.byref(
                    process_info
                ),
            )
        )


        if not result:

            error = ctypes.get_last_error()

            logging.error(
                "CreateProcessAsUserW failed. "
                "Error: %s",
                error,
            )

            raise ctypes.WinError(
                error
            )


        # ----------------------------------------------------
        # Success
        # ----------------------------------------------------

        logging.info(
            "Agent launched successfully."
        )

        logging.info(
            "Agent PID: %s",
            process_info.dwProcessId,
        )

        logging.info(
            "Agent session ID: %s",
            session_id,
        )


        return process_info


    finally:

        # ----------------------------------------------------
        # Close user token
        # ----------------------------------------------------

        if user_token:

            kernel32.CloseHandle(
                user_token
            )


# ============================================================
# Direct test
# ============================================================

if __name__ == "__main__":

    logging.info(
        "================================"
    )

    logging.info(
        "Session launcher test starting"
    )

    try:

        process_info = launch_agent()


        print(
            "Agent started successfully."
        )

        print(
            f"Agent PID: "
            f"{process_info.dwProcessId}"
        )

        print(
            f"Active Session ID: "
            f"{get_active_session_id()}"
        )


        # ----------------------------------------------------
        # Close process handles
        # ----------------------------------------------------

        if process_info.hThread:

            kernel32.CloseHandle(
                process_info.hThread
            )

        if process_info.hProcess:

            kernel32.CloseHandle(
                process_info.hProcess
            )


    except Exception as error:

        logging.exception(
            "Failed to launch Agent"
        )

        print(
            "ERROR:",
            error
        )

        raise