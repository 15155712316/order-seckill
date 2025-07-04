#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能抢单决策助手 - 主程序启动文件
重构后的简洁启动入口
"""

import sys
import logging
from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow
from config import LOG_LEVEL, LOG_FILE, LOG_FORMAT, APP_NAME

# 配置全局日志系统
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format=LOG_FORMAT,
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),  # 输出到文件
        logging.StreamHandler()  # 输出到控制台
    ]
)


if __name__ == "__main__":
    logging.info(f"{APP_NAME} 启动...")
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
