#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置文件 - 存放敏感和可变的配置信息
"""

# 哈哈平台API配置
HAHA_API_URL = "https://piaofan.com/api/order/list"
HAHA_TOKEN = "64932f01040374d3a7dc9438a48c5178"
HAHA_HEADERS = {
    'token': HAHA_TOKEN,
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Content-Type': 'application/json',
    'Referer': 'https://piaofan.com/',
    'Origin': 'https://piaofan.com'
}

# 应用程序配置
APP_NAME = "抢单提醒系统"
APP_VERSION = "1.0.0"

# 日志配置
LOG_LEVEL = "DEBUG"
LOG_FILE = "app.log"
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"

# 音频配置
SOUND_FILE = "notification.wav"

# 数据处理配置
MAX_ORDERS_CACHE = 500  # 订单去重缓存最大数量
API_REQUEST_INTERVAL = 5  # API请求间隔（秒）

# 规则引擎配置
RULES_FILE = "rules.json"
