#!/usr/bin/env python3
"""
LinuxWave
A package manager for Linux jailbreak developers.
Version: 2.0RC
"""

import argparse
import json
import os
import sys
import platform
import time
import fcntl
import logging
import traceback
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, Union

# 绝对路径
CONFIG_FILE = Path("/opt/linuxwave_config/config.json")
VERSION_FILE = Path("/opt/linuxwave_config/VERSION.json")

# 引入分离的模块
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pkg"))
from versionparser import safe_parse_version, sort_versions, get_max_version
from help import print_custom_help

# ==========================================
# 颜色定义
# ==========================================

RED_BOLD = '\033[1;31m'
GREEN = '\033[32m'
YELLOW = '\033[33m'
RESET = '\033[0m'

# ==========================================
# 依赖库检查
# ==========================================

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    from urllib3.exceptions import InsecureRequestWarning
    import urllib3
except ImportError:
    print(f"{RED_BOLD}🌊 Error: 'requests' library is not installed.{RESET}")
    print(f"{RED_BOLD}🌊 Please install it using: pip3 install requests{RESET}")
    sys.exit(1)

try:
    from packaging.version import parse as parse_version, InvalidVersion
except ImportError:
    print(f"{RED_BOLD}🌊 Error: 'packaging' library is not installed.{RESET}")
    print(f"{RED_BOLD}🌊 Please install it using: pip3 install packaging{RESET}")
    sys.exit(1)

try:
    from rich.console import Console
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


# ==========================================
# 配置加载
# ==========================================

def load_config():
    """强制加载 /opt/linuxwave_config/config.json，解决无限循环问题"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                base_dir = config.get("base_dir")
                if base_dir:
                    return Path(base_dir)
        except Exception:
            pass
    # 如果配置文件缺失或损坏，直接报错退出，绝不写死 ~/.local
    print(f"{RED_BOLD}🌊 Error: Configuration file not found or invalid.{RESET}")
    print(f"{RED_BOLD}🌊 Please run the install script again to reinstall LinuxWave.{RESET}")
    sys.exit(1)

BASE_DIR = load_config()
# 根据新目录结构定义路径
INSTALL_DIR = BASE_DIR / "bin"                    # 存放第三方包
DOWNLOAD_TMP = BASE_DIR / "downloads" / "tmp"     # 临时下载目录
REPO_DIR = BASE_DIR / "pkg"                       # 存放解析器和包信息
REPO_CACHE = BASE_DIR / "pkg" / "repo_cache.json" # 缓存
INSTALLED_DB = BASE_DIR / "pkg" / "installed.json" # 安装记录
LIB_DIR = BASE_DIR / "lib"                        # 存放 wave 主程序
PROTECTED_PACKAGES = ["wave"]


# ==========================================
# 版本号获取（统一从 VERSION.json 读取）
