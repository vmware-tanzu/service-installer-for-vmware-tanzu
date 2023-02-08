#  Copyright 2021 VMware, Inc
#  SPDX-License-Identifier: BSD-2-Clause

import errno
import os
import signal
import time
from functools import wraps

# Source: http://stackoverflow.com/questions/2281850/timeout-function-if-it-takes-too-long-to-finish

class CTimeoutError(Exception):
    pass

def timeout(seconds=10, error_message=os.strerror(errno.ETIME)):
    def decorator(func):
        def _handle_timeout(signum, frame):
            raise TimeoutError(error_message)

        def wrapper(*args, **kwargs):
            signal.signal(signal.SIGALRM, _handle_timeout)
            signal.alarm(seconds)
            try:
                result = func(*args, **kwargs)
            finally:
                signal.alarm(0)
            return result

        return wraps(func)(wrapper)

    return decorator
