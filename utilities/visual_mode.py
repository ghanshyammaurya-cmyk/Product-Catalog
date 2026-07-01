"""Visual demo mode: headed browser with slow actions and scroll."""

import os

from utilities.config_reader import ConfigReader


def is_enabled():
    return os.environ.get("VISUAL_MODE", "").lower() in ("1", "true", "yes")


def get_slow_mo():
    if os.environ.get("SLOW_MO"):
        return int(os.environ["SLOW_MO"])
    return ConfigReader.get("slow_mo", 500)


def get_scroll_step_pixels():
    return ConfigReader.get("scroll_step_pixels", 200)


def get_scroll_delay_ms():
    return ConfigReader.get("scroll_delay_ms", 350)


def enable(slow_mo=None):
    os.environ["VISUAL_MODE"] = "true"
    if slow_mo is not None:
        os.environ["SLOW_MO"] = str(slow_mo)


def disable():
    os.environ.pop("VISUAL_MODE", None)
    os.environ.pop("SLOW_MO", None)
