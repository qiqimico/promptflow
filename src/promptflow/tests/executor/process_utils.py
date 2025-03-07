import contextlib
import multiprocessing

from promptflow.executor._line_execution_process_pool import _process_wrapper
from promptflow.executor._process_manager import create_spawned_fork_process_manager


SpawnProcess = multiprocessing.Process
if "spawn" in multiprocessing.get_all_start_methods():
    SpawnProcess = multiprocessing.get_context("spawn").Process


ForkServerProcess = multiprocessing.Process
if "forkserver" in multiprocessing.get_all_start_methods():
    ForkServerProcess = multiprocessing.get_context("forkserver").Process


current_process_wrapper = _process_wrapper
current_process_manager = create_spawned_fork_process_manager


class BaseMockProcess:
    # Base class for the mock process; This class is mainly used as the placeholder for the target mocking logic
    def modify_target(self, target):
        # Method to modify the target of the mock process
        # This shall be the place to hold the target mocking logic
        if target == _process_wrapper:
            return current_process_wrapper
        if target == create_spawned_fork_process_manager:
            return current_process_manager
        return target


class MockSpawnProcess(SpawnProcess, BaseMockProcess):
    def __init__(self, group=None, target=None, *args, **kwargs):
        modified_target = self.modify_target(target)
        super().__init__(group, modified_target, *args, **kwargs)


class MockForkServerProcess(ForkServerProcess, BaseMockProcess):
    def __init__(self, group=None, target=None, *args, **kwargs):
        modified_target = self.modify_target(target)
        super().__init__(group, modified_target, *args, **kwargs)


@contextlib.contextmanager
def enable_mock_in_process(process_wrapper=None, process_manager=None):
    global current_process_wrapper, current_process_manager

    if process_wrapper is not None:
        current_process_wrapper = process_wrapper
    if process_manager is not None:
        current_process_manager = process_manager

    start_methods_mocks = {"spawn": MockSpawnProcess, "forkserver": MockForkServerProcess}
    original_process_class = {}
    for start_method, MockProcessClass in start_methods_mocks.items():
        if start_method in multiprocessing.get_all_start_methods():
            original_process_class[start_method] = multiprocessing.get_context(start_method).Process
            multiprocessing.get_context(start_method).Process = MockProcessClass
            if start_method == multiprocessing.get_start_method():
                multiprocessing.Process = MockProcessClass
    try:
        yield
    finally:
        for start_method, MockProcessClass in start_methods_mocks.items():
            if start_method in multiprocessing.get_all_start_methods():
                multiprocessing.get_context(start_method).Process = original_process_class[start_method]
                if start_method == multiprocessing.get_start_method():
                    multiprocessing.Process = original_process_class[start_method]
