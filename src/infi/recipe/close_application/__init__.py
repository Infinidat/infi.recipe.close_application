__import__("pkg_resources").declare_namespace(__name__)

import os
import sys
import signal
import psutil
import logging

logger = logging.getLogger(__name__)


class BuildoutLogging(object):
    def __init__(self, buildout, name, options):
        super(BuildoutLogging, self).__init__()
        self.buildout = buildout
        self.name = name
        self.options = options


    def update(self):
        self.close_application()
        return []

    def install(self):
        self.close_application()
        return []

    def get_bin_directory(self):
        extension = '.exe' if os.name == 'nt' else ''
        basename = 'buildout' + extension
        possible_buildout_locations = [os.path.abspath(os.path.join(os.path.curdir, 'bin')),
                                   os.path.abspath(os.path.dirname(sys.executable)),
                                   os.path.abspath(os.path.dirname(sys.arg[0]))]
        return [os.path.dirname(path) for
                path in possible_buildout_locations if
                os.path.exists(os.path.join(path, basename))][0]

    def get_processes(self):
        processes = []
        bin_abspath = self.get_bin_directory()
        for process in psutil.process_iter():
            try:
                if os.path.dirname(process.exe) == bin_abspath:
                    processes.append(process)
                elif os.path.dirname(process.cmdline[0]) == bin_abspath:
                    processes.append(process)
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                pass
        return processes

    def kill_process(self, process):
        try:
            logger.info("killing {!r}".format(process))
            process.kill()
        except psutil.NoSuchProcess:
            logger.info("process already dead")
        except:
            logger.exception("kill process failed")

    def close_application(self):
        for process in get_processes():
            self.kill_process(process)
