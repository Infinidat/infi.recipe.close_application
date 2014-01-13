__import__("pkg_resources").declare_namespace(__name__)

import os
import sys
import time
import signal
import psutil
import logging

logger = logging.getLogger(__name__)


def get_bin_directory():
    extension = '.exe' if os.name == 'nt' else ''
    basename = 'buildout' + extension
    possible_buildout_locations = [os.path.abspath(os.path.join(os.path.curdir, 'bin')),
                                   os.path.abspath(os.path.dirname(sys.executable)),
                                   os.path.abspath(os.path.dirname(sys.argv[0]))]
    return [os.path.join(os.path.dirname(path), 'bin') for
            path in possible_buildout_locations if
            os.path.exists(os.path.join(path, basename))][0]


def get_processes():
    processes = []
    bin_abspath = get_bin_directory()
    logger.debug("looking for processes in {!r}".format(bin_abspath))
    for process in psutil.process_iter():
        try:
            if process.pid == os.getpid():
                continue
            logger.debug("found {!r}".format(process))
            logger.debug("exe {!r}".format(process.exe))
            logger.debug("cmdline {!r}".format(process.cmdline))
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


def close_application():
    for process in get_processes():
        kill_process(process)
    time.sleep(1)


class CloseApplication(object):
    def __init__(self, buildout, name, options):
        super(BuildoutLogging, self).__init__()
        self.buildout = buildout
        self.name = name
        self.options = options

    def update(self):
        close_application()
        return []

    def install(self):
        close_application()
        return []

