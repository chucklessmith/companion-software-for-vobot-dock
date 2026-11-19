#!/usr/bin/env python3
"""Headless computer monitor that sends stats to a Vobot dock over UDP."""

import argparse
import configparser
import ipaddress
import json
import logging
import signal
import socket
import sys
import time
from pathlib import Path

import udp_client
from stats import CPU, Disk, Gpu, Memory, Net


APP_DIR = Path(__file__).resolve().parent
CONFIGURATION_FILE = APP_DIR / "configuration.ini"
LOG_DIR = Path.home() / "Library" / "Logs"
LOG_FILE = LOG_DIR / "VobotComputerMonitor.log"
DEFAULT_TARGET_IP = "192.168.0.10"
INTERVAL_SECONDS = 2
running = True


def stop(_signum, _frame):
    global running
    running = False


def load_target_ip():
    config = configparser.ConfigParser()
    config.read(CONFIGURATION_FILE)
    target = config.get("IP", "target", fallback=DEFAULT_TARGET_IP).strip()
    try:
        ipaddress.IPv4Address(target)
    except ipaddress.AddressValueError as exc:
        raise ValueError(
            f"Invalid IP address in {CONFIGURATION_FILE}: {target!r}"
        ) from exc
    return target


def collect_device_info(target):
    gpu_info = Gpu.stats()
    memory_info = Memory.stats()
    disk_info = Disk.stats()
    return {
        "Network": Net.stats(),
        "CPU": {"usage": CPU.percentage(), "temperature": CPU.temperature()},
        "GPU": {"usage": gpu_info[0], "temperature": gpu_info[1]},
        "Memory": {
            "swap": memory_info[0],
            "usage": memory_info[3],
            "free": memory_info[2],
            "used": memory_info[1],
        },
        "Disk": {
            "usage": disk_info[3],
            "total": disk_info[2],
            "used": disk_info[0],
            "free": disk_info[1],
        },
        "Target": target,
        "IP": socket.gethostbyname(socket.gethostname()),
    }


def main():
    global running
    parser = argparse.ArgumentParser(description="Send computer stats to a Vobot dock.")
    parser.add_argument(
        "--log",
        action="store_true",
        help=f"write application logs to {LOG_FILE}",
    )
    args = parser.parse_args()
    logger = logging.getLogger("vobot_computer_monitor")
    logger.propagate = False
    if args.log:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(LOG_FILE)
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    else:
        logger.addHandler(logging.NullHandler())
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    try:
        target = load_target_ip()
        udp_client.unicast_ip = target
        udp_client.init()
    except Exception:
        logger.exception("Could not start computer monitor")
        return 1

    logger.info("Started; sending computer stats to %s", target)
    while running:
        started = time.monotonic()
        try:
            payload = json.dumps(collect_device_info(target)).encode("utf-8")
            logger.info("%s", udp_client.send(payload))
        except Exception:
            logger.exception("Failed to collect or send computer stats")
        remaining = INTERVAL_SECONDS - (time.monotonic() - started)
        if running and remaining > 0:
            time.sleep(remaining)

    if udp_client.server:
        udp_client.server.close()
    logger.info("Stopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
