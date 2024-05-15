from git_mirror.dummies import Dummy

# ### Bugs
#
# I don't see any bugs in the provided code.
#
# ### Unit Test
#
# 1. Test that calling `__enter__` method of `Dummy` class does not raise an
#    exception.
# 2. Test that calling `__exit__` method of `Dummy` class with `None` arguments
#    does not raise an exception.
# 3. Test that calling `__exit__` method of `Dummy` class with specific arguments
#    does not raise an exception.


def test_dummy_enter():
    dummy = Dummy()
    try:
        dummy.__enter__()
    except Exception as e:
        assert False, f"Error: {e}"  # noqa: B011


def test_dummy_exit_none_args():
    dummy = Dummy()
    try:
        dummy.__exit__(None, None, None)
    except Exception as e:
        assert False, f"Error: {e}"  # noqa: B011


def test_dummy_exit_specific_args():
    dummy = Dummy()
    try:
        dummy.__exit__(ValueError, ValueError("Test"), "<traceback>")
    except Exception as e:
        assert False, f"Error: {e}"  # noqa: B011


#
#
# ### No more unit tests.
