#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
麻花平台适配器 - 负责麻花平台的数据获取和处理
"""

import json
import logging
import time
import hashlib
import collections
import aiohttp
from datetime import datetime
from .base_adapter import BaseAdapter
from ..database import DatabaseManager
from config import (
    MAHUA_DEV_CODE, MAHUA_SECRET_KEY, MAHUA_CHANNEL_ID,
    MAHUA_LOGIN_URL, MAHUA_ORDER_LIST_URL, MAX_ORDERS_CACHE
)


class MahuaAdapter(BaseAdapter):
    """麻花平台适配器类"""
    
    def __init__(self, name: str):
        """初始化麻花平台适配器"""
        super().__init__(name)

        # Token缓存机制
        self.token = None
        self.token_expiry_time = 0

        # 用于去重的双端队列，最多保存指定数量的已见过的订单ID
        self.seen_order_ids = collections.deque(maxlen=MAX_ORDERS_CACHE)

        # 初始化数据库管理器
        self.db_manager = DatabaseManager()

        logging.info(f"{self.name}平台适配器初始化完成")
    
    async def _get_token(self):
        """
        获取麻花平台的访问Token
        
        Returns:
            str: 成功时返回token，失败时返回None
        """
        try:
            logging.info(f"正在获取{self.name}平台Token...")
            
            # 构建请求体
            body_json_str = "{}"
            txntime_ms = str(int(time.time() * 1000))
            
            # 生成签名
            string_to_sign = body_json_str + MAHUA_SECRET_KEY + txntime_ms
            md5 = hashlib.md5()
            md5.update(string_to_sign.encode('utf-8'))
            sign = md5.hexdigest()
            
            # 构建请求头
            headers = {
                'channelid': MAHUA_CHANNEL_ID,
                'txntime': txntime_ms,
                'devCode': MAHUA_DEV_CODE,
                'sign': sign,
                'Content-Type': 'application/json; charset=utf-8'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    MAHUA_LOGIN_URL,
                    data=body_json_str.encode('utf-8'),
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    response_text = await response.text()
                    response_data = json.loads(response_text)
                    
                    if response_data.get("rtnCode") == "000000":
                        token = response_data.get("rtnData", {}).get("token")
                        if token:
                            # 更新token和过期时间（30分钟后过期）
                            self.token = token
                            self.token_expiry_time = time.time() + 30 * 60  # 30分钟
                            
                            logging.info(f"✅ 成功获取{self.name}平台Token")
                            return token
                    
                    logging.error(f"❌ 获取{self.name}平台Token失败: {response_data.get('rtnMsg')}")
                    return None
                    
        except Exception as e:
            logging.error(f"❌ 获取{self.name}平台Token时发生错误: {e}")
            return None
    
    def _standardize_orders(self, raw_orders):
        """
        标准化麻花平台的订单数据
        
        Args:
            raw_orders (list): 原始订单数据列表
            
        Returns:
            list: 标准化后的订单列表
        """
        standardized = []
        
        for order in raw_orders:
            try:
                # 提取订单ID
                order_id = order.get('id', order.get('orderId', ''))
                
                # 验证必要字段
                if not order_id:
                    logging.warning(f"麻花平台订单缺少ID字段，跳过此订单: {order}")
                    continue
                
                # 安全地转换bidding_price字段（根据官方文档使用salePrice）
                bidding_price = 0.0
                try:
                    price_value = order.get('salePrice', 0.0)
                    bidding_price = float(price_value) if price_value else 0.0
                except (ValueError, TypeError):
                    logging.warning(f"麻花平台订单 {order_id} 的价格字段转换失败，使用默认值0.0")
                    bidding_price = 0.0
                
                # 安全地转换seat_count字段
                seat_count = 1
                try:
                    seat_value = order.get('buyNum', order.get('seatCount', 1))
                    seat_count = int(seat_value) if seat_value else 1
                except (ValueError, TypeError):
                    logging.warning(f"麻花平台订单 {order_id} 的座位数字段转换失败，使用默认值1")
                    seat_count = 1
                
                # 提取字符串字段（根据麻花平台官方文档字段映射）
                city = order.get('movieCityName', '')
                cinema_name = order.get('movieCinemaName', '')
                hall_type = order.get('movieHallName', '')
                movie_name = order.get('movieName', '')
                
                # 构建标准化订单对象
                standardized_order = {
                    'order_id': order_id,
                    'bidding_price': bidding_price,
                    'seat_count': seat_count,
                    'city': city,
                    'cinema_name': cinema_name,
                    'hall_type': hall_type,
                    'movie_name': movie_name,
                    # 保留原始数据以备后用
                    'raw_data': order
                }
                
                standardized.append(standardized_order)
                
            except Exception as e:
                logging.warning(f"标准化麻花平台订单数据失败，跳过此订单: {e}")
                logging.warning(f"有问题的原始订单数据: {order}")
                continue
        
        logging.info(f"麻花平台数据标准化完成，成功处理 {len(standardized)} 条订单")
        return standardized
    
    async def fetch_and_process(self):
        """
        获取并处理麻花平台的订单数据
        
        Returns:
            dict: 包含平台名称、成功状态和订单列表的字典
        """
        try:
            # 1. 检查Token是否有效或过期
            current_time = time.time()
            if not self.token or current_time >= self.token_expiry_time:
                logging.info(f"{self.name}平台Token无效或已过期，正在重新获取...")
                token = await self._get_token()
                if not token:
                    return {'name': self.name, 'success': False, 'orders': []}
            
            # 2. 使用有效的Token调用订单列表接口
            logging.info(f"正在请求{self.name}平台API...")
            
            # 构建请求体
            body_data = {"pageNum": 1, "pageLimit": 200}  # 获取更多订单
            body_json_str = json.dumps(body_data, separators=(',', ':'))
            txntime_ms = str(int(time.time() * 1000))
            
            # 生成签名
            string_to_sign = body_json_str + MAHUA_SECRET_KEY + txntime_ms
            md5 = hashlib.md5()
            md5.update(string_to_sign.encode('utf-8'))
            sign = md5.hexdigest()
            
            # 构建请求头
            headers = {
                'channelid': MAHUA_CHANNEL_ID,
                'txntime': txntime_ms,
                'devCode': MAHUA_DEV_CODE,
                'token': self.token,
                'sign': sign,
                'Content-Type': 'application/json; charset=utf-8'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    MAHUA_ORDER_LIST_URL,
                    data=body_json_str.encode('utf-8'),
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as response:
                    response_text = await response.text()
                    response_data = json.loads(response_text)
                    
                    logging.info(f"{self.name}平台API响应状态码: {response.status}")
                    
                    if response_data.get("rtnCode") == "000000":
                        raw_orders = response_data.get('rtnData', [])
                        logging.info(f"✅ {self.name}平台解析成功，获得 {len(raw_orders)} 条订单数据")
                        
                        # 3. 标准化订单数据
                        standardized_orders = self._standardize_orders(raw_orders)

                        # 4. 去重处理 - 只返回新订单
                        new_orders = []
                        for order in standardized_orders:
                            order_id = order.get('order_id')
                            if order_id and order_id not in self.seen_order_ids:
                                # 添加到已见过的订单ID缓存
                                self.seen_order_ids.append(order_id)
                                new_orders.append(order)

                        logging.info(f"{self.name}平台去重完成，从 {len(standardized_orders)} 条订单中筛选出 {len(new_orders)} 条新订单")

                        # 5. 调试功能：保存麻花平台新订单的影院和厅信息
                        if len(new_orders) > 0:
                            try:
                                from datetime import datetime
                                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                                # 提取影院名和厅名信息
                                cinema_hall_info = []
                                for order in new_orders:
                                    cinema_info = {
                                        "cinema_name": order.get('cinema_name', ''),
                                        "hall_type": order.get('hall_type', '')
                                    }
                                    cinema_hall_info.append(cinema_info)

                                with open('mahua.log', 'a', encoding='utf-8') as f:
                                    f.write("=" * 60 + "\n")
                                    f.write(f"调试时间: {current_time}\n")
                                    f.write(f"麻花平台新订单数量: {len(new_orders)} 条\n")
                                    f.write("=" * 60 + "\n")
                                    f.write("麻花平台新订单影院和厅信息:\n")
                                    f.write(json.dumps(cinema_hall_info, ensure_ascii=False, indent=2))
                                    f.write("\n" + "=" * 60 + "\n\n")
                                logging.debug(f"🎬 已保存 {len(new_orders)} 条麻花平台新订单到调试文件 mahua.log")
                            except Exception as e:
                                logging.error(f"❌ 保存麻花平台新订单到调试文件失败: {e}")

                        # 6. 保存新订单到数据库
                        self.db_manager.save_orders(new_orders)

                        # 7. 返回成功结果
                        return {
                            'name': self.name,
                            'success': True,
                            'orders': new_orders
                        }
                    else:
                        logging.error(f"❌ {self.name}平台API返回错误: {response_data.get('rtnMsg')}")
                        return {'name': self.name, 'success': False, 'orders': []}
                        
        except Exception as e:
            logging.error(f"❌ {self.name}平台处理过程中发生错误: {e}")
            return {'name': self.name, 'success': False, 'orders': []}
