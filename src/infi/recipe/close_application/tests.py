from infi.unittest import TestCase
from infi.execute import execute_async, execute_assert_success

from . import (
    close_application,
    get_ignored_program_names,
    need_to_kill_process,
    normalize_path,
)

from munch import Munch

import os
import time


EXECUTABLE_EXTENSION = '.exe' if os.name == 'nt' else ''


class CloseApplicationTestCase(TestCase):
    def start_python(self):
        basename = 'python' + EXECUTABLE_EXTENSION

        python = os.path.abspath(
            os.path.join(
                os.path.curdir,
                'bin',
                basename,
            )
        )

        return execute_async([
            python,
            '-c',
            'import time; time.sleep(60)',
        ])

    def stop_process(self, process):
        if not process.is_finished():
            process.kill()
            process.wait(timeout=5)

    def test_child_process_is_protected(self):
        process = self.start_python()
        self.addCleanup(self.stop_process, process)

        time.sleep(1)

        self.assertFalse(
            process.is_finished()
        )

        buildout_directory = os.path.abspath(
            os.path.curdir
        )

        close_application(
            buildout_directory
        )

        process.poll()

        # The process was started by the current test process,
        # so it is a protected child and must remain alive.
        self.assertFalse(
            process.is_finished()
        )

    def test_via_buildout(self):
        process = self.start_python()
        self.addCleanup(self.stop_process, process)

        time.sleep(1)

        self.assertFalse(
            process.is_finished()
        )

        buildout = os.path.join(
            'bin',
            'buildout' + EXECUTABLE_EXTENSION,
        )

        execute_assert_success([
            buildout,
            'install',
            'close-application',
        ])

        process.poll()

        # The sleeper and buildout are siblings. Therefore the
        # sleeper is not part of buildout's protected process tree.
        self.assertTrue(
            process.is_finished()
        )


class NeedToKillTestCase(TestCase):
    def make_process(
        self,
        pid=1,
        name='python',
        exe='',
        cmdline=None,
        cwd='',
    ):
        if cmdline is None:
            cmdline = []

        return Munch(
            pid=pid,
            name=lambda: name,
            exe=lambda: exe,
            cmdline=lambda: cmdline,
            cwd=lambda: cwd,
        )

    def need_to_kill(
        self,
        buildout_directory,
        ignore_list,
        process,
        protected_pids=None,
    ):
        if protected_pids is None:
            protected_pids = set()

        return need_to_kill_process(
            normalize_path(buildout_directory),
            protected_pids,
            get_ignored_program_names(ignore_list),
            process,
        )

    def test_absolute_python_script_from_different_directory(self):
        buildout_directory = os.path.abspath(
            os.path.curdir
        )

        python = os.path.join(
            buildout_directory,
            'parts',
            'python',
            'bin',
            'python',
        )

        script = os.path.join(
            buildout_directory,
            'bin',
            'nosetests',
        )

        directory = os.path.dirname(
            buildout_directory
        )

        process = self.make_process(
            exe=python,
            cmdline=[python, script],
            cwd=directory,
        )

        self.assertTrue(
            self.need_to_kill(
                buildout_directory,
                [],
                process,
            )
        )

    def test_absolute_python_script_from_root_directory(self):
        buildout_directory = os.path.abspath(
            os.path.curdir
        )

        python = os.path.join(
            buildout_directory,
            'parts',
            'python',
            'bin',
            'python',
        )

        script = os.path.join(
            buildout_directory,
            'bin',
            'nosetests',
        )

        process = self.make_process(
            exe=python,
            cmdline=[python, script],
            cwd=buildout_directory,
        )

        self.assertTrue(
            self.need_to_kill(
                buildout_directory,
                [],
                process,
            )
        )

    def test_relative_python_script_from_root_directory(self):
        buildout_directory = os.path.abspath(
            os.path.curdir
        )

        python = os.path.join(
            buildout_directory,
            'parts',
            'python',
            'bin',
            'python',
        )

        script = os.path.join(
            'bin',
            'nosetests',
        )

        process = self.make_process(
            exe=python,
            cmdline=[python, script],
            cwd=buildout_directory,
        )

        self.assertTrue(
            self.need_to_kill(
                buildout_directory,
                [],
                process,
            )
        )

    def test_relative_python_script_from_other_directory(self):
        buildout_directory = os.path.abspath(
            os.path.curdir
        )

        parent_directory = os.path.dirname(
            buildout_directory
        )

        python = os.path.join(
            parent_directory,
            'external-python',
        )

        script = os.path.join(
            os.path.basename(buildout_directory),
            'bin',
            'nosetests',
        )

        process = self.make_process(
            exe=python,
            cmdline=[python, script],
            cwd=parent_directory,
        )

        self.assertTrue(
            self.need_to_kill(
                buildout_directory,
                [],
                process,
            )
        )

    def test_process_matched_by_exe_inside_eggs(self):
        buildout_directory = os.path.abspath(
            os.path.curdir
        )

        nw_exe = os.path.join(
            buildout_directory,
            'eggs',
            'infi.node_webkit-0.2.3.egg',
            'infi',
            'node_webkit',
            'nwjs',
            'nw.exe',
        )

        outside_directory = os.path.dirname(
            buildout_directory
        )

        process = self.make_process(
            name='nw.exe',
            exe=nw_exe,
            cmdline=[nw_exe],
            cwd=outside_directory,
        )

        self.assertTrue(
            self.need_to_kill(
                buildout_directory,
                [],
                process,
            )
        )

    def test_process_matched_by_cwd(self):
        buildout_directory = os.path.abspath(
            os.path.curdir
        )

        cwd = os.path.join(
            buildout_directory,
            'src',
        )

        process = self.make_process(
            name='some-process',
            exe='some-process',
            cwd=cwd,
        )

        self.assertTrue(
            self.need_to_kill(
                buildout_directory,
                [],
                process,
            )
        )

    def test_process_matched_by_later_cmdline_item(self):
        buildout_directory = os.path.abspath(
            os.path.curdir
        )

        script = os.path.join(
            buildout_directory,
            'bin',
            'script',
        )

        outside_directory = os.path.dirname(
            buildout_directory
        )

        process = self.make_process(
            name='python',
            exe='python',
            cmdline=[
                'python',
                '--some-option',
                script,
            ],
            cwd=outside_directory,
        )

        self.assertTrue(
            self.need_to_kill(
                buildout_directory,
                [],
                process,
            )
        )

    def test_protected_process(self):
        buildout_directory = os.path.abspath(
            os.path.curdir
        )

        process = self.make_process(
            pid=123,
            exe=os.path.join(
                buildout_directory,
                'bin',
                'python',
            ),
            cwd=buildout_directory,
        )

        self.assertFalse(
            self.need_to_kill(
                buildout_directory,
                [],
                process,
                protected_pids=set([123]),
            )
        )

    def test_myself_is_protected(self):
        buildout_directory = os.path.abspath(
            os.path.curdir
        )

        process = self.make_process(
            pid=os.getpid(),
            exe=os.path.join(
                buildout_directory,
                'bin',
                'python',
            ),
            cwd=buildout_directory,
        )

        self.assertFalse(
            self.need_to_kill(
                buildout_directory,
                [],
                process,
                protected_pids=set([os.getpid()]),
            )
        )

    def test_ignore_list_by_script_name(self):
        buildout_directory = os.path.abspath(
            os.path.curdir
        )

        python = os.path.join(
            buildout_directory,
            'parts',
            'python',
            'bin',
            'python',
        )

        script = os.path.join(
            buildout_directory,
            'bin',
            'nosetests',
        )

        process = self.make_process(
            name='python',
            exe=python,
            cmdline=[python, script],
            cwd=buildout_directory,
        )

        self.assertFalse(
            self.need_to_kill(
                buildout_directory,
                ['nosetests'],
                process,
            )
        )

    def test_ignore_list_by_executable_name(self):
        buildout_directory = os.path.abspath(
            os.path.curdir
        )

        python = os.path.join(
            buildout_directory,
            'parts',
            'python',
            'bin',
            'python',
        )

        process = self.make_process(
            name='python',
            exe=python,
            cmdline=[python],
            cwd=buildout_directory,
        )

        self.assertFalse(
            self.need_to_kill(
                buildout_directory,
                ['python'],
                process,
            )
        )

    def test_non_related_process(self):
        buildout_directory = os.path.abspath(
            os.path.curdir
        )

        outside_directory = os.path.dirname(
            buildout_directory
        )

        process = self.make_process(
            name='some-process',
            exe='some-process',
            cmdline=[],
            cwd=outside_directory,
        )

        self.assertFalse(
            self.need_to_kill(
                buildout_directory,
                [],
                process,
            )
        )

    def test_absolute_process_from_other_package(self):
        buildout_directory = os.path.abspath(
            os.path.curdir
        )

        other_directory = os.path.abspath(
            os.path.join(
                buildout_directory,
                os.path.pardir,
                'x',
            )
        )

        python = os.path.join(
            other_directory,
            'parts',
            'python',
            'bin',
            'python',
        )

        script = os.path.join(
            other_directory,
            'bin',
            'nosetests',
        )

        process = self.make_process(
            exe=python,
            cmdline=[python, script],
            cwd=other_directory,
        )

        self.assertFalse(
            self.need_to_kill(
                buildout_directory,
                [],
                process,
            )
        )

    def test_relative_process_from_other_package(self):
        buildout_directory = os.path.abspath(
            os.path.curdir
        )

        other_directory = os.path.abspath(
            os.path.join(
                buildout_directory,
                os.path.pardir,
                'x',
            )
        )

        python = os.path.join(
            other_directory,
            'parts',
            'python',
            'bin',
            'python',
        )

        script = os.path.join(
            'bin',
            'nosetests',
        )

        process = self.make_process(
            exe=python,
            cmdline=[python, script],
            cwd=other_directory,
        )

        self.assertFalse(
            self.need_to_kill(
                buildout_directory,
                [],
                process,
            )
        )

    def test_process_of_target_directory(self):
        project_directory = os.path.abspath(
            os.path.curdir
        )

        buildout_directory = os.path.join(
            project_directory,
            'x',
        )

        python = os.path.join(
            buildout_directory,
            'parts',
            'python',
            'bin',
            'python',
        )

        script = os.path.join(
            buildout_directory,
            'bin',
            'sleep',
        )

        process = self.make_process(
            exe=python,
            cmdline=[python, script],
            cwd=project_directory,
        )

        self.assertTrue(
            self.need_to_kill(
                buildout_directory,
                [],
                process,
            )
        )
