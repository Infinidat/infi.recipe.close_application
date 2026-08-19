__import__('pkg_resources').declare_namespace(__name__)

import logging
import os
import sys

import psutil


logger = logging.getLogger(__name__)


def remove_windows_device_prefix(pathname):
    """
    Convert Windows device paths to regular Win32 paths.

    Examples:
        \\??\\C:\\Windows -> C:\\Windows
        \\\\?\\C:\\Windows -> C:\\Windows
        \\\\?\\UNC\\server\\share -> \\\\server\\share
    """
    if os.name != 'nt' or not pathname:
        return pathname

    lower_pathname = pathname.lower()

    unc_prefixes = (
        '\\\\?\\unc\\',
        '\\??\\unc\\',
    )

    for prefix in unc_prefixes:
        if lower_pathname.startswith(prefix):
            return '\\\\' + pathname[len(prefix):]

    device_prefixes = (
        '\\\\?\\',
        '\\??\\',
        '\\\\.\\',
    )

    for prefix in device_prefixes:
        if lower_pathname.startswith(prefix):
            return pathname[len(prefix):]

    return pathname


def normalize_path(pathname, cwd=None):
    """
    Return an absolute, case-normalized path.

    Relative paths are resolved against cwd.
    The path does not need to exist.
    """
    if not pathname:
        return None

    pathname = remove_windows_device_prefix(
        pathname
    )

    if not os.path.isabs(pathname):
        if not cwd:
            return None

        cwd = remove_windows_device_prefix(
            cwd
        )

        pathname = os.path.join(
            cwd,
            pathname,
        )

    return os.path.normcase(
        os.path.abspath(pathname)
    )


def is_under_directory(pathname, directory, cwd=None):
    """
    Return True if pathname is located inside directory.

    Directory boundaries are checked explicitly so that, for example:

        C:\\HPT-old

    does not match:

        C:\\HPT
    """
    pathname = normalize_path(
        pathname,
        cwd,
    )

    if pathname is None:
        return False

    directory = normalize_path(
        directory
    )

    if directory is None:
        return False

    if pathname == directory:
        return True

    if directory.endswith(os.sep):
        directory_prefix = directory
    else:
        directory_prefix = directory + os.sep

    return pathname.startswith(
        directory_prefix
    )


def normalize_program_name(name):
    """
    Normalize a program name for ignore-list comparison.

    On Windows:
        python.exe -> python
        PYTHON.EXE -> python
    """
    filename = os.path.basename(name)

    if os.name == 'nt':
        program_name, extension = os.path.splitext(
            filename
        )

        if extension.lower() == '.exe':
            filename = program_name

        filename = filename.lower()

    return filename


def get_ignored_program_names(ignore_list):
    """
    Normalize entries configured through ignore-list.

    Both 'python' and 'python.exe' match python.exe on Windows.
    """
    ignored_program_names = set()

    for name in ignore_list:
        if name:
            ignored_program_names.add(
                normalize_program_name(name)
            )

    return ignored_program_names


def get_protected_pids():
    """
    Return process IDs which must not be killed:

    - the current process;
    - all parents of the current process;
    - all descendants of the current process.
    """
    current = psutil.Process(os.getpid())
    protected_pids = set([current.pid])

    # Walk through the parent chain manually.
    # This is compatible with Python 2 and does not require
    # Process.parents().
    parent = current

    while True:
        try:
            parent = parent.parent()
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            logger.debug(
                'failed to get parent process',
                exc_info=True,
            )
            break

        if parent is None:
            break

        if parent.pid in protected_pids:
            break

        protected_pids.add(parent.pid)

    try:
        children = current.children(
            recursive=True
        )

        for child in children:
            protected_pids.add(
                child.pid
            )

    except (psutil.AccessDenied, psutil.NoSuchProcess):
        logger.debug(
            'failed to get descendants of pid=%s',
            current.pid,
            exc_info=True,
        )

    logger.debug(
        'protected process pids: %r',
        sorted(protected_pids),
    )

    return protected_pids


def get_process_value(process, attribute_name):
    """
    Read one process property.

    AccessDenied for one property does not prevent reading and
    logging the remaining properties.
    """
    getter = getattr(
        process,
        attribute_name,
        None,
    )

    if getter is None:
        return None

    try:
        return getter()
    except psutil.AccessDenied:
        return None


def get_process_program_names(name, exe, cmdline):
    """
    Return possible names for ignore-list matching.

    For compatibility with the original implementation,
    process name, exe, cmdline[0] and cmdline[1] are checked.
    """
    program_names = set()

    if name:
        program_names.add(
            normalize_program_name(name)
        )

    if exe:
        program_names.add(
            normalize_program_name(exe)
        )

    for item in cmdline[:2]:
        if item:
            program_names.add(
                normalize_program_name(item)
            )

    return program_names


def need_to_kill_process(
    buildout_directory,
    protected_pids,
    ignored_program_names,
    process,
):
    """
    Return True if the process belongs to the buildout directory.

    Process information is logged before applying any exclusions.
    """
    ppid = get_process_value(
        process,
        'ppid',
    )

    name = get_process_value(
        process,
        'name',
    )

    exe = get_process_value(
        process,
        'exe',
    )

    cwd = get_process_value(
        process,
        'cwd',
    )

    cmdline = get_process_value(
        process,
        'cmdline',
    ) or []

    # Log the process before checking pid=0, protected_pids
    # or ignore-list.
    logger.debug(
        'found process pid=%s ppid=%r name=%r '
        'exe=%r cwd=%r cmdline=%r',
        process.pid,
        ppid,
        name,
        exe,
        cwd,
        cmdline,
    )

    if process.pid == 0:
        logger.debug(
            'ignoring system idle process pid=0'
        )
        return False

    if process.pid in protected_pids:
        logger.debug(
            'ignoring protected process pid=%s',
            process.pid,
        )
        return False

    program_names = get_process_program_names(
        name,
        exe,
        cmdline,
    )

    ignored_matches = (
        program_names & ignored_program_names
    )

    if ignored_matches:
        logger.debug(
            'ignoring pid=%s from ignore-list: %r',
            process.pid,
            sorted(ignored_matches),
        )
        return False

    if is_under_directory(
        exe,
        buildout_directory,
    ):
        logger.debug(
            'pid=%s matched by exe: %r',
            process.pid,
            exe,
        )
        return True

    if is_under_directory(
        cwd,
        buildout_directory,
    ):
        logger.debug(
            'pid=%s matched by cwd: %r',
            process.pid,
            cwd,
        )
        return True

    for item in cmdline:
        if is_under_directory(
            item,
            buildout_directory,
            cwd=cwd,
        ):
            logger.debug(
                'pid=%s matched by cmdline item: %r',
                process.pid,
                item,
            )
            return True

    logger.debug(
        'pid=%s does not belong to buildout directory',
        process.pid,
    )

    return False


def get_processes_to_kill(
    buildout_directory,
    ignore_list=(),
):
    buildout_directory = normalize_path(
        buildout_directory
    )

    if buildout_directory is None:
        raise ValueError(
            'buildout directory is not configured'
        )

    protected_pids = get_protected_pids()

    ignored_program_names = get_ignored_program_names(
        ignore_list
    )

    logger.debug(
        'looking for processes under %r',
        buildout_directory,
    )

    logger.debug(
        'ignored program names: %r',
        sorted(ignored_program_names),
    )

    for process in psutil.process_iter():
        try:
            if need_to_kill_process(
                buildout_directory,
                protected_pids,
                ignored_program_names,
                process,
            ):
                yield process

        except (psutil.AccessDenied, psutil.NoSuchProcess) as error:
            logger.debug(
                'skipping pid=%s: %s: %s',
                process.pid,
                type(error).__name__,
                error,
            )


def kill_process(process):
    try:
        logger.info(
            'killing pid=%s process=%r',
            process.pid,
            process,
        )

        process.kill()

    except psutil.NoSuchProcess:
        logger.info(
            'process pid=%s is already dead',
            process.pid,
        )

    except psutil.AccessDenied:
        logger.exception(
            'access denied while killing pid=%s',
            process.pid,
        )

    except Exception:
        logger.exception(
            'failed to kill pid=%s',
            process.pid,
        )


def close_application(
    buildout_directory,
    ignore_list=(),
):
    logger.debug(
        'sys.executable: %r',
        sys.executable,
    )

    logger.debug(
        'sys.argv: %r',
        sys.argv,
    )

    processes = list(
        get_processes_to_kill(
            buildout_directory,
            ignore_list,
        )
    )

    for process in processes:
        kill_process(process)

    if not processes:
        logger.debug(
            'no processes found under %r',
            buildout_directory,
        )
        return

    # Wait until Windows has terminated the processes and released
    # their handles.
    gone, alive = psutil.wait_procs(
        processes,
        timeout=5,
    )

    logger.debug(
        'terminated process pids: %r',
        [process.pid for process in gone],
    )

    if alive:
        logger.warning(
            'processes still alive after timeout: %r',
            [process.pid for process in alive],
        )


class CloseApplication(object):
    def __init__(self, buildout, name, options):
        super(CloseApplication, self).__init__()

        self.buildout = buildout
        self.name = name
        self.options = options

    def close_application(self):
        buildout_config = self.buildout.get(
            'buildout'
        )

        buildout_directory = buildout_config.get(
            'directory'
        )

        ignore_list = self.options.get(
            'ignore-list',
            '',
        ).split()

        close_application(
            buildout_directory,
            ignore_list,
        )

        return []

    def update(self):
        return self.close_application()

    def install(self):
        return self.close_application()
