#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置文件 - 存放敏感和可变的配置信息
"""

# --- 网络与服务器配置 ---
API_BASE_URL = "http://47.117.162.183:5000"
NETWORK_CONFIG = {
    "timeout": 30,         # 请求超时时间（秒）
    "retry_count": 3,      # 失败重试次数
    "verify_ssl": False    # 是否验证SSL证书
}

# --- 麻花平台配置 ---
# 注意：敏感凭证信息（dev_code、secret_key）已移除，需要通过UI配置
MAHUA_CHANNEL_ID = 'OP0002'  # 固定渠道ID，非敏感信息
MAHUA_LOGIN_URL = "https://openapi.quanma51.com/api/user-server/user/dev/login"
MAHUA_ORDER_LIST_URL = "https://openapi.quanma51.com/api/movie-server/movie/bidding/info/list"

# --- 哈哈平台配置 ---
# 注意：敏感凭证信息（token）已移除，需要通过UI配置
API_URL = 'https://hahapiao.cn/api/Synchro/pcToList'


# 【修复】基础headers模板，不包含token（token将动态添加）
API_HEADERS_TEMPLATE = {
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
}

# 【重构】移除硬编码token，headers将在运行时动态构建
# API_HEADERS现在只是API_HEADERS_TEMPLATE的别名，用于向后兼容
API_HEADERS = API_HEADERS_TEMPLATE.copy()
# 注意：token字段将在适配器初始化时动态添加

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
ALERT_TEXT_TEMPLATE = "{platform}有{profit}元利润订单"  # 语音播报的文本模板
WHITELIST_ALERT_TEXT = "白名单影院来单"  # 白名单策略专用提醒文本
