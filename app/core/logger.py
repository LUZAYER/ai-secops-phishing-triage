from datetime import datetime
from collections import deque

class MemoryLogger:
    def __init__(self, maxlen=500):
        self.logs = deque(maxlen=maxlen)

    def log(self, msg: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        line = f"[{timestamp}] {msg}"
        self.logs.append(line)
        print(msg) # ensure it still prints to standard output

    def get_logs(self):
        return list(self.logs)

    def clear(self):
        self.logs.clear()

global_logger = MemoryLogger()

def log(msg: str):
    global_logger.log(msg)
