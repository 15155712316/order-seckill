#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
影划算平台适配器 - 负责影划算平台的数据获取和处理
"""

import json
import logging
import time
import aiohttp
from .base_adapter import BaseAdapter, OrderData
from PyQt6.QtCore import QObject, pyqtSignal


class YingHuaSuanAdapter(BaseAdapter):
    """影划算平台适配器类"""

    def __init__(self, name: str, config: dict = None):
        """初始化影划算平台适配器"""
        super().__init__(name, config)

        # 配置注入机制
        self.bearer_token = self.config.get('bearer_token', '')
        self.api_url = self.config.get('api_url', 'https://merchant-api.yinghuasuan.com/broker/v1/invitation/list')
        
        # Token状态管理
        self.token_valid = bool(self.bearer_token)
        

    async def _fetch_raw_data(self):
        """
        获取影划算平台原始数据 - 实现抽象方法
        
        Returns:
            dict: 原始API响应数据
        """
        if not self.bearer_token:
            raise Exception("Bearer Token未配置")

        # 构建请求 - 修复Bearer Token重复问题
        # 检查token是否已经包含Bearer前缀
        auth_header = self.bearer_token
        if not auth_header.startswith('Bearer '):
            auth_header = f'Bearer {auth_header}'
        
        headers = {
            'Accept': '*/*',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Authorization': auth_header,  # 避免重复Bearer前缀
            'Connection': 'keep-alive',
            'Content-Type': 'application/json',
            'Origin': 'https://hub.yhs.cn',
            'Referer': 'https://hub.yhs.cn/',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
            'client-type': '3'
        }

        # 构建请求体
        request_data = {
            "city_name": "",
            "film_id": "",
            "seat_num": "",
            "accept_change_seat": "",
            "net_price": "",
            "keywords": "",
            "sort": "desc"
        }

        # 发送请求
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.api_url,
                headers=headers,
                json=request_data,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                
                if response.status == 200:
                    data = await response.json()
                    
                    # 检查是否为认证错误
                    api_code = data.get('code')
                    api_msg = data.get('msg', '')
                    
                    if api_code != 200:
                        if "登录" in api_msg or "token" in api_msg.lower() or "auth" in api_msg.lower():
                            logging.error(f"❌ {self.name}平台认证失败: {api_msg}")
                            raise Exception(f"认证失败: {api_msg}")
                        else:
                            logging.error(f"❌ {self.name}平台API业务错误: {api_msg}")
                            raise Exception(f"API业务错误: {api_msg}")
                    
                    # 记录成功获取的订单数量
                    orders = data.get('data', [])
                    logging.info(f"📊 {self.name}平台从API获取 {len(orders)} 条原始订单")
                    
                    return data
                else:
                    error_msg = f"HTTP {response.status}"
                    if response.status == 401:
                        error_msg = "Token已过期或无效"
                        self.token_valid = False
                    
                    logging.error(f"❌ {self.name}平台API请求失败: {error_msg}")
                    raise Exception(error_msg)

    async def _process_raw_data(self, raw_data) -> list[OrderData]:
        """
        处理影划算平台原始数据 - 实现抽象方法
        
        Args:
            raw_data: 原始API响应数据
            
        Returns:
            List[OrderData]: 标准化订单数据列表
        """
        # 调用响应数据处理方法
        return self._process_response_data(raw_data)

    def _validate_raw_data(self, raw_data) -> bool:
        """验证原始数据 - 重写基类方法"""
        if not isinstance(raw_data, dict):
            return False
        
        # 检查响应格式
        if raw_data.get('code') != 200:
            return False
            
        data = raw_data.get('data')
        return isinstance(data, list)

    def _process_response_data(self, data):
        """
        处理影划算平台的响应数据
        
        Args:
            data: API响应数据
            
        Returns:
            List[OrderData]: 标准化的订单数据列表
        """
        try:
            standardized = []
            
            # 检查响应格式
            if data.get('code') != 200:
                error_msg = data.get('msg', '未知错误')
                logging.warning(f"{self.name}平台API返回错误: {error_msg}")
                return []
            
            orders = data.get('data', [])
            if not isinstance(orders, list):
                logging.warning(f"{self.name}平台响应数据格式异常")
                return []

            for order in orders:
                try:
                    # 完整字段映射
                    order_id = str(order.get('inv_id', ''))  # 使用 inv_id 作为订单ID
                    demands_id = str(order.get('demands_id', ''))  # 需求ID
                    
                    # 价格字段映射
                    bidding_price = float(order.get('deal_price', 0))  # 成交价格作为竞价
                    original_price = float(order.get('net_price', 0))  # net_price是原价
                    
                    # 座位数
                    seat_count = int(order.get('seat_num', 1))  # 座位数量
                    
                    # 基础信息字段
                    city = order.get('city_name', '')  # 城市名称
                    cinema_name = order.get('cinema_name', '')  # 影院名称
                    hall_type = order.get('hall_name', '')  # 影厅名称
                    movie_name = order.get('film_name', '')  # 电影名称
                    show_time = order.get('show_time', '')  # 放映时间

                    # 构建标准化订单对象
                    standardized_order = OrderData(
                        order_id=f"{order_id}_{demands_id}",  # 组合ID确保唯一性
                        bidding_price=bidding_price,
                        seat_count=seat_count,
                        original_price=original_price,
                        city=city,
                        cinema_name=cinema_name,
                        hall_type=hall_type,
                        movie_name=movie_name,
                        show_time=show_time,
                        raw_data=order
                    )
                    
                    standardized.append(standardized_order)
                    
                except Exception as e:
                    logging.warning(f"标准化{self.name}平台订单数据失败，跳过此订单: {e}")

            return standardized

        except Exception as e:
            logging.error(f"❌ {self.name}平台处理响应数据失败: {e}")
            return []

    def is_available(self) -> bool:
        """检查平台是否可用"""
        return bool(self.bearer_token) and self.token_valid

