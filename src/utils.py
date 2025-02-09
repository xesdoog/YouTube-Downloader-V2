import logging
import logging.handlers
import os
import platform
import sys


def executable_path():
    return os.path.dirname(os.path.abspath(sys.argv[0]))


class LOGGER:
    def __init__(self):
        self.logger = logging.getLogger("YTD")
        log_handler = logging.handlers.RotatingFileHandler('./ytd.log',
                                                maxBytes = 524288,
                                                backupCount = 3
                                                )
        logging.basicConfig(encoding = 'utf-8',
                        level    = logging.INFO,
                        format   = '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
                        datefmt  = '%H:%M:%S',
                        handlers = [log_handler]
                    )

    def debug(self, msg: str):
        self.logger.debug(msg)

    def info(self, msg: str):
        self.logger.info(msg)

    def warning(self, msg: str):
        self.logger.warning(msg)

    def error(self, msg: str):
        self.logger.error(msg)

    def critical(self, msg: str):
        self.logger.critical(msg)

    def OnStart(self, parent_path):
        LOCAL_VERSION = "v1.0.0"
        userOS        = platform.system()
        userOSarch    = platform.architecture()
        userOSrel     = platform.release()
        userOSver     = platform.version()
        workDir       = parent_path
        exeDir        = executable_path() + '\\'
        logfile = open("./ytd.log", "a")
        logfile.write("\n--- YouTube Downloader ---\n\n")
        logfile.write(f"    ¤ Version: {LOCAL_VERSION}\n")
        logfile.write(f"    ¤ Operating System: {userOS} {userOSrel} x{userOSarch[0][:2]} v{userOSver}\n")
        logfile.write(f"    ¤ Working Directory: {workDir}\n")
        logfile.write(f"    ¤ Executable Directory: {exeDir}\n\n\n")
        logfile.flush()
        logfile.close()

