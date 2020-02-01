import sys
import os
from contextlib import contextmanager

sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__),
                                                 "..")))
import rcGlobalEnv
import pytest


@pytest.fixture(scope='function')
def osvc_path_tests(tmpdir):
    test_dir = str(tmpdir)
    rcGlobalEnv.rcEnv.paths.pathetc = os.path.join(test_dir, 'etc')
    rcGlobalEnv.rcEnv.paths.pathetcns = os.path.join(test_dir, 'etc', 'namespaces')
    rcGlobalEnv.rcEnv.paths.pathlog = os.path.join(test_dir, 'log')
    rcGlobalEnv.rcEnv.paths.pathtmpv = os.path.join(test_dir, 'tmp')
    rcGlobalEnv.rcEnv.paths.pathvar = os.path.join(test_dir, 'var')
    rcGlobalEnv.rcEnv.paths.pathlock = os.path.join(test_dir, 'lock')
    rcGlobalEnv.rcEnv.paths.nodeconf = os.path.join(rcGlobalEnv.rcEnv.paths.pathetc, 'node.conf')
    rcGlobalEnv.rcEnv.paths.clusterconf = os.path.join(rcGlobalEnv.rcEnv.paths.pathetc, 'cluster.conf')
    return tmpdir


@pytest.fixture(scope='function')
def non_existing_file(tmp_path):
    return os.path.join(str(tmp_path), 'foo')


@pytest.fixture(scope='function')
def tmp_file(tmp_path):
    return os.path.join(str(tmp_path), 'tmp-file')


@pytest.fixture(scope='function')
def capture_stdout():
    try:
        # noinspection PyCompatibility
        from StringIO import StringIO
    except ImportError:
        from io import StringIO

    @contextmanager
    def func(filename):
        _stdout = sys.stdout
        try:
            with open(filename, 'w') as output_file:
                sys.stdout = output_file
                yield
        finally:
            sys.stdout = _stdout
    return func
