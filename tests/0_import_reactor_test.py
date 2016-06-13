# -*- coding: utf-8 -*-
import sys

import psutil


class TestTwistedReactorNotInitImportTime(object):
    """
    This class is trying to test that fido is (and stays) fork-safe.
    """

    @classmethod
    def setup_class(cls):
        cls.current_process = psutil.Process()
        # get the number of file descriptors open before the test class is run
        cls.pre_import_num_fds = cls.current_process.num_fds()

    @classmethod
    def _no_new_fds_open_after_swaggerpy_bravado_import(cls):
        """
        This test only checks for symptoms that something went wrong. If
        twisted.reactor was initialized in any of the previous tests then the
        number of file descriptors for the current process should be higher.
        It seems that reactor opens up 3 file descriptors.
        """

        post_import_num_fds = cls.current_process.num_fds()
        return cls.pre_import_num_fds >= post_import_num_fds - 2

    def test_twisted_reactor_not_imported_after_fetch_import(self):
        """
        Test that reactor is not imported (and initialized) as a result of
        importing fido modules and methods.
        """

        assert 'twisted.internet.reactor' not in sys.modules

        import fido
        from fido.fido import fetch

        assert 'twisted.internet.reactor' not in sys.modules
