import logging
import os
from datetime import datetime

from utilities.config_reader import ConfigReader

_LOGGERS = {}


def get_logger(name="intel_edge_ai"):
    if name in _LOGGERS:
        return _LOGGERS[name]

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    if logger.handlers:
        _LOGGERS[name] = logger
        return logger

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    reports_dir = ConfigReader.get_path("report_path", "reports")
    os.makedirs(reports_dir, exist_ok=True)

    session_log = os.environ.get("TEST_LOG_FILE")
    if not session_log:
        session_log = os.path.join(
            reports_dir,
            f"test_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
        )
        os.environ["TEST_LOG_FILE"] = session_log

    file_handler = logging.FileHandler(session_log, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    _LOGGERS[name] = logger
    return logger
