#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能抢单决策助手 - 主程序启动文件
守护者之盾安全版 - 支持用户认证和设备绑定
"""

import sys
import os
import logging
from PyQt6.QtWidgets import QApplication, QMessageBox
from ui.main_window import MainWindow
from config import LOG_LEVEL, LOG_FILE, LOG_FORMAT, APP_NAME

def check_single_instance():
    """【守护者之盾】检查单例运行，确保只有一个程序实例"""
    try:
        import win32event
        import win32api
        import winerror

        # 创建唯一的互斥锁名称
        mutex_name = "Global\\SmartTicketGrabberMutex_UniqueInstance_2024"

        # 尝试创建互斥锁
        mutex = win32event.CreateMutex(None, False, mutex_name)

        # 检查是否已经存在
        if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
            # 程序已在运行
            app = QApplication(sys.argv)
            QMessageBox.warning(
                None,
                "程序已运行",
                "智能抢单决策助手已在运行中。",
                QMessageBox.StandardButton.Ok
            )
            sys.exit(1)

        return mutex

    except ImportError:
        # 如果没有win32api，使用文件锁作为备选方案
        lock_file = os.path.join(os.path.dirname(__file__), '.app_lock')
        try:
            # 尝试创建锁文件
            if os.path.exists(lock_file):
                app = QApplication(sys.argv)
                QMessageBox.warning(
                    None,
                    "程序已运行",
                    "智能抢单决策助手已在运行中。",
                    QMessageBox.StandardButton.Ok
                )
                sys.exit(1)

            # 创建锁文件
            with open(lock_file, 'w') as f:
                f.write(str(os.getpid()))

            return lock_file

        except Exception as e:
            logging.error(f"创建应用锁失败: {e}")
            return None

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
    # 【守护者之盾】检查单例运行
    app_lock = check_single_instance()

    logging.info(f"{APP_NAME} 守护者之盾安全系统启动...")

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()

    try:
        result = app.exec()
    finally:
        # 清理锁文件（如果使用文件锁）
        if isinstance(app_lock, str) and os.path.exists(app_lock):
            try:
                os.remove(app_lock)
            except:
                pass

    sys.exit(result)
