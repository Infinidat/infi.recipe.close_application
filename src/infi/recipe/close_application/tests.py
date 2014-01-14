from infi.unittest import TestCase
from infi.execute import execute_async, execute_assert_success
from . import close_application, EXTENSION
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
        close_application()
        pid.poll()
        self.assertTrue(pid.is_finished())

    def test_via_buildout(self):
        pid = self.start_python()
        time.sleep(1)
        self.assertFalse(pid.is_finished())
        execute_assert_success([os.path.join('bin', 'buildout' + EXTENSION), 'install', 'close-application'])
        pid.poll()
        self.assertTrue(pid.is_finished())
