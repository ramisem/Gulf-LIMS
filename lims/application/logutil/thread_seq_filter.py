import logging
import os
import socket
import threading

_thread_local = threading.local()

# read once at import time (fast)
HOSTNAME = socket.gethostname()
INSTANCE_ID = os.environ.get("INSTANCE_ID", HOSTNAME)
PID = os.getpid()


class ThreadSequenceFilter(logging.Filter):
    """
    Adds attributes to each LogRecord:
      - thread_seq : incrementing per-thread counter (int)
      - hostname   : host name
      - instance_id: environment-provided instance id or hostname
      - process_id : process id (pid)
    Lightweight and safe for production multi-process/multi-node deployments.
    """

    def filter(self, record):
        try:
            seq = getattr(_thread_local, "seq", 0) + 1
            _thread_local.seq = seq
        except Exception:
            seq = 0
        # attach attributes that formatter can reference
        record.thread_seq = seq
        record.hostname = HOSTNAME
        record.instance_id = INSTANCE_ID
        record.process_id = PID
        return True


def reset_thread_seq():
    """Reset the sequence counter for the current thread (call from middleware)."""
    try:
        delattr(_thread_local, "seq")
    except Exception:
        pass
