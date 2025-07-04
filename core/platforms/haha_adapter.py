#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
哈哈平台适配器 - 负责处理哈哈平台的API请求、解密和数据处理
"""

import json
import logging
import collections
import aiohttp
from .base_adapter import BaseAdapter
from config import API_URL, API_HEADERS, API_DATA_PAYLOAD, MAX_ORDERS_CACHE


class HahaAdapter(BaseAdapter):
    """哈哈平台适配器类"""
    
    def __init__(self):
        """初始化哈哈平台适配器"""
        super().__init__()
        # 用于去重的双端队列，最多保存指定数量的已见过的订单ID
        self.seen_order_ids = collections.deque(maxlen=MAX_ORDERS_CACHE)
    
    async def fetch_and_process(self):
        """
        获取并处理哈哈平台的订单数据

        完成以下工作：
        1. 请求哈哈平台API获取原始数据
        2. 解密数据（如果需要）
        3. 解析和清洗数据
        4. 去重处理
        5. 返回标准化的订单列表

        Returns:
            list: 标准化的订单列表
        """
        try:
            # 执行真实API请求，严格按照config.py中的配置
            async with aiohttp.ClientSession(headers=API_HEADERS) as session:
                logging.info("正在请求哈哈平台API...")
                logging.debug(f"请求URL: {API_URL}")
                logging.debug(f"请求数据: {API_DATA_PAYLOAD}")

                async with session.post(API_URL, data=API_DATA_PAYLOAD) as response:
                    # 获取返回的响应文本
                    response_text = await response.text()
                    logging.info(f"API响应状态码: {response.status}")
                    logging.debug(f"API返回响应长度: {len(response_text)}")

                    # 打印原始响应（用于调试）
                    logging.debug(f"原始API响应: {response_text[:200]}...")  # 只打印前200字符

                    # 检查HTTP状态码
                    if response.status != 200:
                        logging.error(f"HTTP请求失败，状态码: {response.status}")
                        return []

            # 解析JSON响应并提取数据
            try:
                # 1. 解析JSON响应
                logging.info("解析API返回的JSON响应...")
                api_response = json.loads(response_text)
                logging.debug(f"API响应结构: {list(api_response.keys()) if isinstance(api_response, dict) else type(api_response)}")

                # 检查响应状态（根据实际API响应结构调整）
                if isinstance(api_response, dict):
                    status = api_response.get('status') or api_response.get('code')
                    if status and status != 200:
                        logging.error(f"API返回错误状态: {api_response}")
                        return []

                # 2. 提取数据内容
                # 根据实际API响应结构提取数据，可能是加密数据或直接的订单数据
                if isinstance(api_response, dict):
                    # 如果是字典，尝试提取data字段
                    raw_data = api_response.get('data', api_response)
                else:
                    # 如果直接是列表或其他格式
                    raw_data = api_response

                if not raw_data:
                    logging.warning("API响应中没有找到有效数据")
                    return []

                logging.info(f"成功提取原始数据，类型: {type(raw_data)}")

                # 3. 判断是否需要解密
                if isinstance(raw_data, str):
                    # 如果是字符串，可能是加密数据
                    logging.info("检测到字符串数据，尝试解密...")
                    decrypted_orders = await self._decrypt_data(raw_data)
                    if not decrypted_orders:
                        logging.warning("解密后没有获得有效的订单数据")
                        return []
                elif isinstance(raw_data, list):
                    # 如果是列表，可能是直接的订单数据
                    logging.info("检测到列表数据，直接处理...")
                    decrypted_orders = raw_data
                else:
                    logging.warning(f"未知的数据格式: {type(raw_data)}")
                    return []

            except json.JSONDecodeError as e:
                logging.error(f"解析API响应JSON失败: {e}")
                logging.error(f"原始响应内容: {response_text}")
                return []

            # 4. 数据清洗和标准化
            standardized_orders = self._standardize_orders(decrypted_orders)

            # 5. 去重处理
            new_orders = self._deduplicate_orders(standardized_orders)

            logging.info(f"成功处理 {len(new_orders)} 个新订单")
            return new_orders

        except Exception as e:
            logging.error(f"🚨 获取订单数据时发生错误: {e}")
            logging.error(f"错误类型: {type(e).__name__}")
            import traceback
            logging.error(f"错误堆栈: {traceback.format_exc()}")
            return []
    
    async def _decrypt_data(self, encrypted_data):
        """
        解密加密的订单数据
        
        Args:
            encrypted_data (str): Base64编码的加密数据
            
        Returns:
            list: 解密后的订单列表，如果解密失败返回空列表
        """
        try:
            # TODO: 在这里添加具体的解密逻辑
            # 目前返回空列表，等待解密实现
            logging.info("需要添加解密逻辑来处理加密数据")
            return []
            
        except Exception as e:
            logging.error(f"解密数据失败: {e}")
            return []
    
    def _standardize_orders(self, raw_orders):
        """
        标准化订单数据格式
        
        Args:
            raw_orders (list): 原始订单数据列表
            
        Returns:
            list: 标准化后的订单列表
        """
        standardized = []
        
        for order in raw_orders:
            try:
                # 标准化订单字段
                standardized_order = {
                    'order_id': order.get('id', ''),
                    'city': order.get('city', ''),
                    'cinema_name': order.get('cinema_name', ''),
                    'hall_type': order.get('hall_type', ''),
                    'bidding_price': float(order.get('bidding_price', 0)),
                    'seat_count': int(order.get('seat_count', 1)),
                    # 保留原始数据以备后用
                    'raw_data': order
                }
                
                standardized.append(standardized_order)
                
            except (ValueError, TypeError) as e:
                logging.warning(f"标准化订单数据失败，跳过此订单: {e}")
                continue
        
        return standardized
    
    def _deduplicate_orders(self, orders):
        """
        去重处理，过滤掉已经见过的订单
        
        Args:
            orders (list): 订单列表
            
        Returns:
            list: 去重后的新订单列表
        """
        new_orders = []
        
        for order in orders:
            order_id = order.get('order_id', '')
            
            # 跳过没有ID的订单
            if not order_id:
                continue
            
            # 检查是否已经见过这个订单
            if order_id not in self.seen_order_ids:
                # 新订单，添加到结果列表和已见列表
                new_orders.append(order)
                self.seen_order_ids.append(order_id)
        
        return new_orders
