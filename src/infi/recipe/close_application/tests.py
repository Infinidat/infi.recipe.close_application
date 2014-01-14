from infi.unittest import TestCase
from infi.execute import execute_async, execute_assert_success
from . import close_application, EXTENSION, need_to_kill_process
from chunk import Chunk
import os
import time


class CloseApplicationTestCase(TestCase):
    def start_python(self):
        basename = 'python' + EXTENSION
        python = os.path.abspath(os.path.join(os.path.curdir, 'bin', basename))
        pid = execute_async([python, '-c', 'import time; time.sleep(60)'])
        return pid

    def test_python_is_running(self):
        pid = self.start_python()
        time.sleep(1)
        self.assertFalse(pid.is_finished())
        close_application('bin')
        pid.poll()
        self.assertTrue(pid.is_finished())

    def test_via_buildout(self):
        pid = self.start_python()
        time.sleep(1)
        self.assertFalse(pid.is_finished())
        execute_assert_success([os.path.join('bin', 'buildout' + EXTENSION), 'install', 'close-application'])
        pid.poll()
        self.assertTrue(pid.is_finished())


class NeedToKillTestCase(TestCase):
    def test_absloute_python_script_running_from_different_directory(self):
        bindir = os.path.abspath(os.path.join(os.path.curdir, "bin"))
        python = os.path.abspath(os.path.join(os.path.curdir, "parts", "python", "bin", "python"))
        script = os.path.abspath(os.path.join(os.path.curdir, "bin", "nosetests"))
        directory = os.path.dirname(os.path.abspath(os.path.curdir))
        process = Chunk(pid=1, exe=python, cmdline=[python, script], getcwd=lambda: directory)
        self.assertTrue(need_to_kill_process(bindir, [], process))

    def test_absloute_python_script_running_from_root_directory(self):
        bindir = os.path.abspath(os.path.join(os.path.curdir, "bin"))
        python = os.path.abspath(os.path.join(os.path.curdir, "parts", "python", "bin", "python"))
        script = os.path.abspath(os.path.join(os.path.curdir, "bin", "nosetests"))
        directory = os.path.abspath(os.path.curdir)
        process = Chunk(pid=1, exe=python, cmdline=[python, script], getcwd=lambda: directory)
        self.assertTrue(need_to_kill_process(bindir, [], process))

    def test_relative_python_script_from_root_directory(self):
        bindir = os.path.abspath(os.path.join(os.path.curdir, "bin"))
        python = os.path.abspath(os.path.join(os.path.curdir, "parts", "python", "bin", "python"))
        script = os.path.join("bin", "nosetests")
        directory = os.path.abspath(os.path.curdir)
        process = Chunk(pid=1, exe=python, cmdline=[python, script], getcwd=lambda: directory)
        self.assertTrue(need_to_kill_process(bindir, [], process))

    def test_relative_python_script_from_other_directory(self):
        curdir = os.path.abspath(os.path.curdir)
        bindir = os.path.abspath(os.path.join(os.path.curdir, "bin"))
        python = os.path.abspath(os.path.join(os.path.curdir, "parts", "python", "bin", "python"))
        script = os.path.join(os.path.basename(curdir), "bin", "nosetests")
        directory = os.path.dirname(curdir)
        process = Chunk(pid=1, exe=python, cmdline=[python, script], getcwd=lambda: directory)
        self.assertTrue(need_to_kill_process(bindir, [], process))

    def test_myself(self):
        bindir = os.path.abspath(os.path.join(os.path.curdir, "bin"))
        process = Chunk(pid=os.getpid(), exe='', cmdline=[], getcwd=lambda: '')
        self.assertFalse(need_to_kill_process(bindir, [], process))

    def test_ignore_list(self):
        bindir = os.path.abspath(os.path.join(os.path.curdir, "bin"))
        python = os.path.abspath(os.path.join(os.path.curdir, "parts", "python", "bin", "python"))
        script = os.path.join("bin", "nosetests")
        directory = os.path.abspath(os.path.curdir)
        process = Chunk(pid=1, exe=python, cmdline=[python, script], getcwd=lambda: directory)
        self.assertFalse(need_to_kill_process(bindir, ["nosetests"], process))
        self.assertFalse(need_to_kill_process(bindir, ["python"], process))

    def test_non_related_process(self):
        bindir = os.path.abspath(os.path.join(os.path.curdir, "bin"))
        directory = os.path.abspath(os.path.curdir)
        process = Chunk(pid=1, exe="some-process", cmdline=[], getcwd=lambda: directory)
        self.assertFalse(need_to_kill_process(bindir, [], process))

    def test_absolute_buildout_from_other_package(self):
        bindir = os.path.abspath(os.path.join(os.path.curdir, "bin"))
        python = os.path.abspath(os.path.join(os.path.curdir, os.path.pardir, "x", "parts", "python", "bin", "python"))
        script = os.path.abspath(os.path.join(os.path.curdir, os.path.pardir, "x", "bin", "nosetests"))
        directory = os.path.dirname(os.path.abspath(os.path.join(os.path.curdir, os.path.pardir, "x", )))
        process = Chunk(pid=1, exe=python, cmdline=[python, script], getcwd=lambda: directory)
        self.assertFalse(need_to_kill_process(bindir, [], process))

    def test_relative_buildout_from_other_package(self):
        bindir = os.path.abspath(os.path.join(os.path.curdir, "bin"))
        python = os.path.abspath(os.path.join(os.path.curdir, os.path.pardir, "x", "parts", "python", "bin", "python"))
        script = os.path.join("bin", "nosetests")
        directory = os.path.abspath(os.path.join(os.path.curdir, os.path.pardir, "x"))
        process = Chunk(pid=1, exe=python, cmdline=[python, script], getcwd=lambda: directory)
        self.assertFalse(need_to_kill_process(bindir, [], process))

    def test_absolute_python_script_of_target_dir_from_project_root(self):
        bindir = os.path.abspath(os.path.join(os.path.curdir, "x", "bin"))
        python = os.path.abspath(os.path.join(os.path.curdir, "x", "parts", "python", "bin", "python"))
        script = os.path.abspath(os.path.join(os.path.curdir, "x", "bin", "sleep"))
        directory = os.path.abspath(os.path.curdir)
        process = Chunk(pid=1, exe=python, cmdline=[python, script], getcwd=lambda: directory)
        self.assertTrue(need_to_kill_process(bindir, [], process))
