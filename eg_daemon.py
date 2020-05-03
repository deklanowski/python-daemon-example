#!/usr/bin/env python3
import argparse
import functools
import logging
import os
import subprocess
import sys
import threading
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path
import schedule

import daemon
from daemon import pidfile

debug_p = True

HOME = os.environ["HOME"]

working_dir = Path("/home/dc/eg_daemon")
eg_pidfile = working_dir / "eg_daemon.pid"
eg_logfile = working_dir / "eg_daemon.log"


def start_daemon():
    print(f"eg_daemon: entered start_daemon()")
    print(f"eg_daemon: pid = {eg_pidfile} log = {eg_logfile}")
    print(f"eg_daemon: about to daemonize...")

    fh = get_file_handler(eg_logfile, FORMATTER)
    logger = get_logger("eg_daemon", fh)

    dctx = daemon.DaemonContext(
        working_directory=working_dir,
        stdout=fh.stream,
        stderr=fh.stream,
        umask=0,
        pidfile=pidfile.TimeoutPIDLockFile(eg_pidfile),
    )

    print(f"working_dir={dctx.working_directory}\nuid={dctx.uid}\ngid={dctx.gid}\nchroot={dctx.chroot_directory}")
    print(f"preserved={dctx.files_preserve}\nstdout={dctx.stdout}\n")
    print(f"signal_map={dctx.signal_map}\n")

    with dctx as context:
        do_something(logger)


def do_something(logger):
    """
    This is the actual process doing the work
    :param logf:
    :return:
    """

    provisioning_thread = threading.Thread(target=run_script_periodically, args=(logger,))
    provisioning_thread.daemon = True
    provisioning_thread.start()

    # print(f"starting scheduler: {provisioning_thread.is_alive()}")

    #
    while True:
        logger.debug("doing something..")
        time.sleep(10)


def run_script_periodically(logger):
    logger.debug("scheduling periodic script...")
    threading.current_thread().name = 'provisioning'
    schedule.every(5).seconds.do(functools.partial(run_script, logger)).tag("myscript")
    while True:
        schedule.run_pending()


def run_script(logger):
    logger.debug("running script..")

    try:
        output = subprocess.check_output(
            ["/home/dc/eg_daemon/my_script.bash"],
            cwd=working_dir
        )
        logger.debug(f"script output: {str(output)}")
        return 0
    except subprocess.CalledProcessError as err:
        logger.debug(f"error running script: {err}")
        return err.returncode


FORMATTER = logging.Formatter(
    "%(asctime)-15s %(levelname)-8s: %(filename)-10s:%(funcName)-30s:%(lineno)3i : [%(threadName)-12s]: %(message)s")


def get_file_handler(logfile, formatter):
    file_handler = RotatingFileHandler(
        logfile,
        mode='a',
        maxBytes=10 * 1024 * 1024,
        backupCount=2,
        encoding=None)
    file_handler.setFormatter(formatter)
    return file_handler


def get_logger(logger_name, file_handler):
    _logger = logging.getLogger(logger_name)
    _logger.setLevel(logging.DEBUG)  # better to have too much log than not enough
    _logger.addHandler(file_handler)
    # with this pattern, it's rarely necessary to propagate the error up to parent
    _logger.propagate = False
    return _logger


if __name__ == "__main__":
    start_daemon()
