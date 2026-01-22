import logging
from datetime import datetime


class MilliFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        dt = datetime.fromtimestamp(record.created)

        if datefmt:
            # manually handle milliseconds
            s = dt.strftime(datefmt.replace("%f", "{ms}"))
            s = s.format(ms=f"{int(record.msecs):03d}")
        else:
            s = dt.strftime("%d%B%Y_%H:%M:%S")
            s = f"{s},{int(record.msecs):03d}"

        return s.upper()
