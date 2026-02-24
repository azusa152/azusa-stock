"""
Config — 從環境變數覆寫 domain 常數。
在應用程式啟動時呼叫一次 init_settings()。
"""

import os

from domain import constants


def init_settings() -> None:
    """Override domain constants from environment. Call once at startup."""
    data_dir = os.getenv("DATA_DIR")
    if data_dir:
        constants.DATA_DIR = data_dir
