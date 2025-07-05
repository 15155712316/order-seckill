#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置文件 - 存放敏感和可变的配置信息
"""

# --- 麻花平台配置 ---
MAHUA_DEV_CODE = "b2b4378b42df47518fc3511488d6d555"
MAHUA_SECRET_KEY = "69eaf6b39da442809644dc2e3e233cf5"
MAHUA_CHANNEL_ID = 'OP0002'
MAHUA_LOGIN_URL = "https://openapi.quanma51.com/api/user-server/user/dev/login"
MAHUA_ORDER_LIST_URL = "https://openapi.quanma51.com/api/movie-server/movie/bidding/info/list"

# --- 哈哈平台配置 ---
API_URL = 'https://hahapiao.cn/api/Synchro/pcToList'
API_TOKEN = "64932f01040374d3a7dc9438a48c5178"

# 从curl命令中提取的Cookie字符串
API_COOKIE = "_c_WBKFRo=CbkeIVy2jCMFQKiSKiNZIOjL0rfGmOzcfROYTyCm; PHPSESSID=e2vnuucrt8qnts3ul9b13aabr3"

API_HEADERS = {
    'accept': 'application/json, text/plain, */*',
    'accept-language': 'zh-CN,zh;q=0.9',
    'content-type': 'application/x-www-form-urlencoded',
    'origin': 'https://hahapiao.cn',
    'priority': 'u=1, i',
    'referer': 'https://hahapiao.cn/pc/',
    'sec-ch-ua': '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
    'token': API_TOKEN,  # 将token也放入headers
    'Cookie': API_COOKIE  # 将cookie字符串放入headers
}

API_DATA_PAYLOAD = 'limit=200'

# 应用程序配置
APP_NAME = "抢单提醒系统"
APP_VERSION = "1.0.0"

# 平台名称配置
HAHA_PLATFORM_NAME = "哈哈"
MAHUA_PLATFORM_NAME = "麻花"

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

# 语音提醒配置
TTS_CACHE_DIR = "tts_cache"  # 语音缓存文件夹
ALERT_TEXT_TEMPLATE = "新机会，利润约为{profit}元"  # 语音播报的文本模板
