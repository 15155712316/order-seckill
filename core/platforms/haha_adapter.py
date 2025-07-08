#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
哈哈平台适配器 - 负责处理哈哈平台的API请求、解密和数据处理
"""

import json
import logging
import collections
import aiohttp
import hashlib
import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from .base_adapter import BaseAdapter
from ..database import DatabaseManager
from config import API_URL, API_HEADERS, API_DATA_PAYLOAD, API_TOKEN, MAX_ORDERS_CACHE
from PyQt6.QtCore import QObject, pyqtSignal


class CredentialSignalEmitter(QObject):
    """凭证失效信号发射器"""
    platform_credential_expired = pyqtSignal(str)  # 参数为平台名称


class HahaAdapter(BaseAdapter):
    """哈哈平台适配器类"""

    def __init__(self, name: str):
        """初始化哈哈平台适配器"""
        super().__init__(name)

        # 用于去重的双端队列，最多保存指定数量的已见过的订单ID
        self.seen_order_ids = collections.deque(maxlen=MAX_ORDERS_CACHE)

        # 初始化数据库管理器
        self.db_manager = DatabaseManager()

        # 【新增】凭证失效检测
        self.auth_failure_count = 0  # 连续认证失败次数
        self.max_auth_failures = 5   # 最大允许的连续认证失败次数
        self.credential_expired = False  # 凭证是否已失效

        # 【新增】信号发射器
        self.signal_emitter = CredentialSignalEmitter()

        logging.info(f"{self.name}平台适配器初始化完成")
    
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

                async with session.post(API_URL, data=API_DATA_PAYLOAD) as response:
                    # 获取返回的响应文本
                    response_text = await response.text()
                    logging.info(f"API响应状态码: {response.status}")

                    # 检查HTTP状态码
                    if response.status != 200:
                        logging.error(f"HTTP请求失败，状态码: {response.status}")

                        # 【新增】检查是否为认证相关错误
                        if response.status in [401, 403]:
                            self._handle_auth_failure()

                        return {
                            'name': self.name,
                            'success': False,
                            'orders': []
                        }

            # 解析JSON响应并提取数据
            try:
                # 1. 解析JSON响应
                api_response = json.loads(response_text)

                # 检查响应状态（根据实际API响应结构调整）
                if isinstance(api_response, dict):
                    status = api_response.get('status') or api_response.get('code')
                    if status and status != 200:
                        logging.error(f"API返回错误状态: {api_response}")

                        # 【新增】检查是否为认证相关错误
                        error_msg = api_response.get('message', '').lower()
                        if any(keyword in error_msg for keyword in ['auth', 'token', 'login', 'unauthorized', 'forbidden']):
                            self._handle_auth_failure()

                        return {
                            'name': self.name,
                            'success': False,
                            'orders': []
                        }

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
                    return {
                        'name': self.name,
                        'success': False,
                        'orders': []
                    }

                # 3. 判断是否需要解密
                if isinstance(raw_data, str):
                    # 如果是字符串，可能是加密数据
                    decrypted_orders = await self._decrypt_data(raw_data)
                    if not decrypted_orders:
                        logging.warning("解密后没有获得有效的订单数据")
                        return {
                            'name': self.name,
                            'success': True,  # 解密成功但没有数据，仍然算作成功
                            'orders': []
                        }
                elif isinstance(raw_data, list):
                    # 如果是列表，可能是直接的订单数据
                    logging.info("检测到列表数据，直接处理...")
                    decrypted_orders = raw_data
                else:
                    logging.warning(f"未知的数据格式: {type(raw_data)}")
                    return {
                        'name': self.name,
                        'success': False,
                        'orders': []
                    }

            except json.JSONDecodeError as e:
                logging.error(f"解析API响应JSON失败: {e}")
                logging.error(f"原始响应内容: {response_text}")
                return {
                    'name': self.name,
                    'success': False,
                    'orders': []
                }

            # 4. 精确预过滤：只保留 is_from != '5' 的订单
            filtered_orders = []
            for order in decrypted_orders:
                if order.get('is_from') != '5':
                    filtered_orders.append(order)

            logging.info(f"精确预过滤完成，从 {len(decrypted_orders)} 条订单中筛选出 {len(filtered_orders)} 条有效订单（排除is_from='5'）")

            # 5. 数据标准化
            standardized_orders = self._standardize_orders(filtered_orders)

            # 6. 去重处理
            new_orders = self._deduplicate_orders(standardized_orders)

            # 7. 保存新订单到数据库
            self.db_manager.save_orders(new_orders, self.name)

            # 8. 调试信息：统计 is_lock=1 的订单
            locked_orders_count = 0
            for order in new_orders:
                if order.get('raw_data', {}).get('is_lock') == '1':
                    locked_orders_count += 1

            # 记录调试信息到控制台日志
            if locked_orders_count > 0:
                logging.debug(f"🔒 发现 {locked_orders_count} 条 is_lock=1 订单")

            # 9. 记录处理统计信息
            logging.debug(f"📋 本次处理了 {len(decrypted_orders)} 条原始订单，过滤后 {len(filtered_orders)} 条，新增 {len(new_orders)} 条")

            logging.info(f"成功处理 {len(new_orders)} 个新订单")

            # 【新增】成功处理数据，重置认证失败计数器
            self._reset_auth_failure_count()

            # 返回新的统一格式
            return {
                'name': self.name,
                'success': True,
                'orders': new_orders
            }

        except Exception as e:
            logging.error(f"🚨 {self.name}平台获取订单数据时发生错误: {e}")
            logging.error(f"错误类型: {type(e).__name__}")
            import traceback
            logging.error(f"错误堆栈: {traceback.format_exc()}")
            return {
                'name': self.name,
                'success': False,
                'orders': []
            }

    def _aes_decrypt(self, ciphertext: str, token: str) -> str:
        """
        根据已知算法，解密哈哈平台返回的、经过Base64编码的加密数据。

        Args:
            ciphertext (str): Base64编码的加密数据
            token (str): 用于生成密钥的token

        Returns:
            str: 解密后的JSON字符串，如果解密失败返回None
        """
        try:
            # 步骤 1: 根据Token和约定的"盐值"生成Key和IV
            key_material = f"{token}piaofan@123".encode('utf-8')
            key = hashlib.md5(key_material).hexdigest().encode('utf-8')

            iv_material = f"{token}piaofan@456".encode('utf-8')
            iv = hashlib.md5(iv_material).hexdigest()[:16].encode('utf-8')

            # 步骤 2: 执行解密流程
            encrypted_data_bytes = base64.b64decode(ciphertext)
            cipher = AES.new(key, AES.MODE_CBC, iv)
            decrypted_padded_data = cipher.decrypt(encrypted_data_bytes)
            unpadded_data = unpad(decrypted_padded_data, AES.block_size, style='pkcs7')
            result = unpadded_data.decode('utf-8')

            return result

        except Exception as e:
            logging.error(f"AES解密失败: {e}")
            logging.error(f"错误类型: {type(e).__name__}")
            return None

    async def _decrypt_data(self, encrypted_data):
        """
        解密加密的订单数据

        Args:
            encrypted_data (str): Base64编码的加密数据

        Returns:
            list: 解密后的订单列表，如果解密失败返回空列表
        """
        try:
            # 调用经过验证的AES解密函数
            decrypted_json_str = self._aes_decrypt(encrypted_data, API_TOKEN)

            if decrypted_json_str is None:
                logging.error("AES解密失败，返回None")
                return []

            # 解析JSON数据
            decrypted_data = json.loads(decrypted_json_str)

            # 检查解密后的数据格式
            if isinstance(decrypted_data, list):
                logging.info(f"✅ 解密成功，获得 {len(decrypted_data)} 条订单数据")
                return decrypted_data
            elif isinstance(decrypted_data, dict):
                # 如果是字典，尝试提取订单列表
                orders = decrypted_data.get('data', decrypted_data.get('list', []))
                if isinstance(orders, list):
                    logging.info(f"✅ 解密成功，从字典中提取 {len(orders)} 条订单数据")
                    return orders
                else:
                    logging.warning("解密后的字典中没有找到订单列表")
                    return []
            else:
                logging.warning(f"解密后的数据格式不正确: {type(decrypted_data)}")
                return []

        except json.JSONDecodeError as e:
            logging.error(f"解密后JSON解析失败: {e}")
            logging.error(f"解密后的字符串前200字符: {decrypted_json_str[:200] if 'decrypted_json_str' in locals() else 'N/A'}")
            return []
        except Exception as e:
            logging.error(f"解密数据失败: {e}")
            logging.error(f"错误类型: {type(e).__name__}")
            return []
    
    def _standardize_orders(self, filtered_orders: list) -> list:
        """
        标准化订单数据格式 - v1.0最终版本

        接收经过预过滤的订单列表，进行字段映射和数据类型转换

        Args:
            filtered_orders (list): 经过预过滤的订单数据列表（is_from != '5'）

        Returns:
            list: 标准化后的订单列表
        """
        standardized = []

        for order in filtered_orders:
            try:
                # 提取订单ID
                order_id = order.get('order_id', '')

                # 验证必要字段
                if not order_id:
                    logging.warning(f"订单缺少order_id字段，跳过此订单: {order}")
                    continue

                # 安全地转换bidding_price字段 - 从 order.get('maxPrice', 0.0) 获取
                bidding_price = 0.0
                try:
                    price_value = order.get('maxPrice', 0.0)
                    bidding_price = float(price_value) if price_value else 0.0
                except (ValueError, TypeError):
                    logging.warning(f"订单 {order_id} 的maxPrice字段转换失败，使用默认值0.0")
                    bidding_price = 0.0

                # 安全地转换seat_count字段
                seat_count = 1
                try:
                    seat_value = order.get('seat_num', 1)
                    seat_count = int(seat_value) if seat_value else 1
                except (ValueError, TypeError):
                    logging.warning(f"订单 {order_id} 的seat_num字段转换失败，使用默认值1")
                    seat_count = 1

                # 安全地转换original_price字段 - 从 maoyanPrice 获取
                original_price = 0.0
                try:
                    price_value = order.get('maoyanPrice', 0.0)
                    original_price = float(price_value) if price_value else 0.0
                except (ValueError, TypeError):
                    logging.warning(f"订单 {order_id} 的maoyanPrice字段转换失败，使用默认值0.0")
                    original_price = 0.0

                # 提取字符串字段（提供默认值）
                city = order.get('cityName', '')
                cinema_name = order.get('cinemaName', '')
                hall_type = order.get('hallName', '')
                movie_name = order.get('movieName', '')

                # 【新增】提取时间字段 - 哈哈平台使用'time'字段（格式：2025-07-08 14:10）
                show_time = order.get('time', order.get('showTime', order.get('show_time', '')))

                # 构建标准化订单对象
                standardized_order = {
                    'order_id': order_id,
                    'bidding_price': bidding_price,
                    'seat_count': seat_count,
                    'original_price': original_price,
                    'city': city,
                    'cinema_name': cinema_name,
                    'hall_type': hall_type,
                    'movie_name': movie_name,
                    'show_time': show_time,  # 【新增】放映时间
                    # 保留原始数据以备后用
                    'raw_data': order
                }

                standardized.append(standardized_order)

            except Exception as e:
                logging.warning(f"标准化订单数据失败，跳过此订单: {e}")
                logging.warning(f"有问题的原始订单数据: {order}")
                continue

        logging.info(f"数据标准化完成，成功处理 {len(standardized)} 条订单")
        return standardized
    
    def _deduplicate_orders(self, standardized_orders: list) -> list:
        """
        去重处理，过滤掉已经见过的订单

        Args:
            standardized_orders (list): 标准化后的订单列表

        Returns:
            list: 去重后的新订单列表
        """
        new_orders = []

        for order in standardized_orders:
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

    def _handle_auth_failure(self):
        """
        【新增】处理认证失败
        连续失败次数达到阈值时发射凭证失效信号
        """
        self.auth_failure_count += 1
        logging.warning(f"{self.name}平台认证失败，连续失败次数: {self.auth_failure_count}/{self.max_auth_failures}")

        if self.auth_failure_count >= self.max_auth_failures and not self.credential_expired:
            self.credential_expired = True
            logging.error(f"{self.name}平台凭证已失效，连续失败{self.auth_failure_count}次")

            # 发射凭证失效信号
            self.signal_emitter.platform_credential_expired.emit(self.name)

    def _reset_auth_failure_count(self):
        """
        【新增】重置认证失败计数器
        成功处理数据时调用
        """
        if self.auth_failure_count > 0:
            logging.info(f"{self.name}平台认证恢复正常，重置失败计数器")
            self.auth_failure_count = 0
            self.credential_expired = False
