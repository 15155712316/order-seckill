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
from datetime import datetime
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from .base_adapter import BaseAdapter
from config import API_URL, API_HEADERS, API_DATA_PAYLOAD, API_TOKEN, MAX_ORDERS_CACHE


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
            logging.debug(f"开始AES解密，token: {token}")

            # 步骤 1: 根据Token和约定的"盐值"生成Key和IV
            key_material = f"{token}piaofan@123".encode('utf-8')
            key = hashlib.md5(key_material).hexdigest().encode('utf-8')
            logging.debug(f"生成的密钥长度: {len(key)} bytes")

            iv_material = f"{token}piaofan@456".encode('utf-8')
            iv = hashlib.md5(iv_material).hexdigest()[:16].encode('utf-8')
            logging.debug(f"生成的IV长度: {len(iv)} bytes")

            # 步骤 2: 执行解密流程
            logging.debug("Base64解码...")
            encrypted_data_bytes = base64.b64decode(ciphertext)
            logging.debug(f"解码后数据长度: {len(encrypted_data_bytes)} bytes")

            logging.debug("AES-CBC解密...")
            cipher = AES.new(key, AES.MODE_CBC, iv)
            decrypted_padded_data = cipher.decrypt(encrypted_data_bytes)
            logging.debug(f"解密后数据长度: {len(decrypted_padded_data)} bytes")

            logging.debug("去除PKCS7填充...")
            unpadded_data = unpad(decrypted_padded_data, AES.block_size, style='pkcs7')
            logging.debug(f"去填充后数据长度: {len(unpadded_data)} bytes")

            logging.debug("UTF-8解码...")
            result = unpadded_data.decode('utf-8')
            logging.debug(f"UTF-8解码成功，字符串长度: {len(result)}")

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
            logging.info("开始解密加密数据...")

            # 调用经过验证的AES解密函数
            decrypted_json_str = self._aes_decrypt(encrypted_data, API_TOKEN)

            if decrypted_json_str is None:
                logging.error("AES解密失败，返回None")
                return []

            # 解析JSON数据
            logging.info("解析解密后的JSON数据...")
            decrypted_data = json.loads(decrypted_json_str)

            # 检查解密后的数据格式
            if isinstance(decrypted_data, list):
                logging.info(f"✅ 解密成功，获得 {len(decrypted_data)} 条订单数据")

                # 将解密后的订单数据保存到result.log
                try:
                    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    with open('result.log', 'w', encoding='utf-8') as f:
                        f.write("=" * 80 + "\n")
                        f.write(f"解密时间: {current_time}\n")
                        f.write(f"订单数量: {len(decrypted_data)} 条\n")
                        f.write("=" * 80 + "\n")
                        f.write("解密后的订单数据:\n")
                        f.write(json.dumps(decrypted_data, ensure_ascii=False, indent=2))
                        f.write("\n" + "=" * 80 + "\n")
                    logging.info("✅ 解密后的订单数据已保存到 result.log 文件")
                except Exception as e:
                    logging.error(f"❌ 保存解密数据到result.log失败: {e}")

                return decrypted_data
            elif isinstance(decrypted_data, dict):
                # 如果是字典，尝试提取订单列表
                orders = decrypted_data.get('data', decrypted_data.get('list', []))
                if isinstance(orders, list):
                    logging.info(f"✅ 解密成功，从字典中提取 {len(orders)} 条订单数据")

                    # 将解密后的订单数据保存到result.log
                    try:
                        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        with open('result.log', 'w', encoding='utf-8') as f:
                            f.write("=" * 80 + "\n")
                            f.write(f"解密时间: {current_time}\n")
                            f.write(f"订单数量: {len(orders)} 条\n")
                            f.write("=" * 80 + "\n")
                            f.write("解密后的订单数据:\n")
                            f.write(json.dumps(orders, ensure_ascii=False, indent=2))
                            f.write("\n" + "=" * 80 + "\n")
                        logging.info("✅ 解密后的订单数据已保存到 result.log 文件")
                    except Exception as e:
                        logging.error(f"❌ 保存解密数据到result.log失败: {e}")

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
