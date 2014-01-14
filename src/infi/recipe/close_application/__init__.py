__import__("pkg_resources").declare_namespace(__name__)

import os
import sys
import time
import signal
import psutil
import logging

logger = logging.getLogger(__name__)
EXTENSION = '.exe' if os.name == 'nt' else ''



def get_processes(bin_dirpath, ignore_list):
    processes = []
    bin_abspath = os.path.abspath(bin_dirpath)
    logger.debug("looking for processes in {!r}".format(bin_abspath))
    for process in psutil.process_iter():
        try:
            if process.pid == os.getpid():
                logger.debug("this is me: {!r}".format(process))
                continue
            elif process.cmdline[:1] and os.path.basename(process.cmdline[0]).replace(EXTENSION, '') in ignore_list:
                continue
            elif process.cmdline[1:2] and os.path.basename(process.cmdline[1]).replace(EXTENSION, '') in ignore_list:
                continue
            logger.debug("found {!r}".format(process))
            logger.debug("exe {!r}".format(process.exe))
            logger.debug("cmdline {!r}".format(process.cmdline))
            if os.name == "nt" and process.exe.endswith("buildout.exe"):
                logger.debug("assuming is my child buildout, there's no getppid() on Windows")
                continue
            if os.path.abspath(os.path.dirname(process.exe)) == bin_abspath:
                processes.append(process)
            elif process.cmdline[:1] and os.path.abspath(os.path.dirname(process.cmdline[0])) == bin_abspath:
                processes.append(process)
            elif process.cmdline[1:2] and os.path.abspath(os.path.dirname(process.cmdline[1])) == bin_abspath:
                processes.append(process)
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            pass
    return processes


def kill_process(process):
    try:
        logger.info("killing {!r}".format(process))
        process.kill()
    except psutil.NoSuchProcess:
        logger.info("process already dead")
    except:
        logger.exception("kill process failed")


def close_application(bin_dirpath, ignore_list=()):
    for process in get_processes(bin_dirpath, ignore_list):
        kill_process(process)
    time.sleep(1)


class CloseApplication(object):
    def __init__(self, buildout, name, options):
        super(CloseApplication, self).__init__()
        self.buildout = buildout
        self.name = name
        self.options = options

    def close_application(self):
        bin_dirpath = os.path.join(self.buildout.get("buildout").get("directory"), "bin")
        ignore_list = self.options.get("ignore-list", '').split()
        close_application(bin_dirpath, ignore_list)
        return []

    def update(self):
        return self.close_application()

    def install(self):
        return self.close_application()

