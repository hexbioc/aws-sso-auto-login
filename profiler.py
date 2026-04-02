import csv
from functools import wraps
from datetime import datetime

from logger import logger


DT_FORMAT = r"%Y-%m-%dT%H:%M:%S.%f"


class FunctionProfiler:
    def __init__(self, *, enabled=True):
        self.enabled = enabled
        self.logs = []

    def profile(self, fn):
        @wraps(fn)
        def wrappedfn(*args, **kwargs):
            starttime = datetime.now()
            try:
                return fn(*args, **kwargs)
            finally:
                endtime = datetime.now()
                self.logs.append(
                    (
                        fn.__name__,
                        starttime.strftime(DT_FORMAT),
                        endtime.strftime(DT_FORMAT),
                        (endtime - starttime).total_seconds(),
                    )
                )

        return wrappedfn

    def write_csv(self, filepath):
        if not self.enabled:
            logger.warning("Will not write CSV as profiler is not enabled")
            return

        with open(filepath, "w") as f:
            csv.writer(f).writerows(
                [["function", "start", "end", "duration_seconds"]] + self.logs
            )


function_profiler = FunctionProfiler(enabled=False)
