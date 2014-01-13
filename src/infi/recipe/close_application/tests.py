from infi.unittest import TestCase
from infi.execute import execute_async
from . import close_application
import os
import time

class CloseApplicationTestCase(TestCase):
    def test_python_is_running(self):
        extension = '.exe' if os.name == 'nt' else ''
        basename = 'python' + extension
        python = os.path.abspath(os.path.join(os.path.curdir, 'bin', basename))
        pid = execute_async([python, '-c', 'import time; time.sleep(60)'])
        time.sleep(1)
        self.assertFalse(pid.is_finished())
        close_application()
        pid.poll()
        self.assertTrue(pid.is_finished())
