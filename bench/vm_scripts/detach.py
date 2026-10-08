"""Fully detach a command: double-fork into a new session so it survives shell recycling."""
import os
import subprocess
import sys

def detach(cmd, log_path):
    log = open(log_path, "ab")
    p = subprocess.Popen(
        cmd, stdout=log, stderr=log,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
        cwd="/path/to/DocProcess/ocr_benchmark",
    )
    print(f"detached pid {p.pid}: {' '.join(cmd)}")

if __name__ == "__main__":
    detach(sys.argv[1:], sys.argv[1].replace("/", "_") + ".detach.log")
