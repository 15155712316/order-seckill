#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
麻花平台适配器 - 负责麻花平台的数据获取和处理
"""

import json
import logging
import time
import hashlib
import aiohttp
from .base_adapter import BaseAdapter, OrderData
from PyQt6.QtCore import QObject, pyqtSignal
from config import PLATFORM_MAX_AUTH_FAILURES


class CredentialSignalEmitter(QObject):
    """凭证失效信号发射器"""
    platform_credential_expired = pyqtSignal(str)  # 参数为平台名称


class MahuaAdapter(BaseAdapter):
    """麻花平台适配器类"""

    def __init__(self, name: str, config: dict = None):
        """初始化麻花平台适配器"""
        super().__init__(name, config)

        # 【V3.5升级】配置注入机制
        self.dev_code = self.config.get('dev_code', '')
        self.secret_key = self.config.get('secret_key', '')
        self.channel_id = self.config.get('channel_id', '')
        self.login_url = self.config.get('login_url', '')
        self.order_list_url = self.config.get('order_list_url', '')

        # Token缓存机制
        self.token = None
        self.token_expiry_time = 0

        # 【新增】凭证失效检测
        self.auth_failure_count = 0  # 连续认证失败次数
        self.max_auth_failures = PLATFORM_MAX_AUTH_FAILURES   # 【修复】使用全局配置的最大失败次数阈值
        self.credential_expired = False  # 凭证是否已失效

        # 【修复】平台自动停止机制
        self.is_stopped = False  # 平台是否已停止请求

        # 【新增】信号发射器
        self.signal_emitter = CredentialSignalEmitter()

        logging.info(f"{self.name}平台适配器初始化完成")

    async def _fetch_raw_data(self):
        """
        获取麻花平台原始数据
        
        Returns:
            dict: 原始API响应数据
        """
        # 1. 检查Token是否有效或过期
        current_time = time.time()
        if not self.token or current_time >= self.token_expiry_time:
            logging.info(f"{self.name}平台Token无效或已过期，正在重新获取...")
            token = await self._get_token()
            if not token:
                raise Exception("Token获取失败，可能是认证问题")
        
        # 2. 构建请求体
        body_data = {"pageNum": 1, "pageLimit": 1000}
        body_json_str = json.dumps(body_data, separators=(',', ':'))
        txntime_ms = str(int(time.time() * 1000))
        
        # 3. 检查配置完整性
        if not self.secret_key or not self.dev_code or not self.order_list_url:
            raise Exception(f"{self.name}平台配置不完整")

        # 4. 生成签名
        string_to_sign = body_json_str + self.secret_key + txntime_ms
        md5 = hashlib.md5()
        md5.update(string_to_sign.encode('utf-8'))
        sign = md5.hexdigest()

        # 5. 构建请求头
        headers = {
            'channelid': self.channel_id,
            'txntime': txntime_ms,
            'devCode': self.dev_code,
            'token': self.token,
            'sign': sign,
            'Content-Type': 'application/json; charset=utf-8'
        }

        # 6. 使用网络配置进行SSL和超时设置
        import ssl
        network_config = self.config.get('network_config', {})
        
        ssl_context = None
        if not network_config.get("verify_ssl", True):
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

        timeout = aiohttp.ClientTimeout(total=network_config.get("timeout", 30))
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        
        async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
            async with session.post(
                self.order_list_url,
                data=body_json_str.encode('utf-8'),
                headers=headers
            ) as response:
                response_text = await response.text()
                response_data = json.loads(response_text)
                
                logging.info(f"{self.name}平台API响应状态码: {response.status}")
                
                if response_data.get("rtnCode") != "000000":
                    error_msg = response_data.get('rtnMsg', '')
                    # 检查是否为认证相关错误
                    if any(keyword in error_msg.lower() for keyword in ['auth', 'token', 'login', 'unauthorized', 'forbidden']):
                        self._handle_auth_failure()
                    raise Exception(f"API返回错误: {error_msg}")
                
                return response_data
    
    async def _process_raw_data(self, raw_data) -> list[OrderData]:
        """
        处理麻花平台原始数据
        
        Args:
            raw_data: 原始API响应数据
            
        Returns:
            List[OrderData]: 标准化订单数据列表
        """
        raw_orders = raw_data.get('rtnData', [])
        logging.info(f"✅ {self.name}平台解析成功，获得 {len(raw_orders)} 条订单数据")
        
        return self._standardize_orders(raw_orders)
    
    def _validate_raw_data(self, raw_data) -> bool:
        """验证原始数据"""
        if not isinstance(raw_data, dict):
            return False
        
        if raw_data.get("rtnCode") != "000000":
            return False
            
        rtn_data = raw_data.get('rtnData')
        return isinstance(rtn_data, list)

    def _standardize_orders(self, raw_orders) -> list[OrderData]:
        """
        标准化麻花平台的订单数据

        字段映射关系：
        - order_id: id 或 orderId
        - bidding_price: discountPriceUp (主要) 或 salePrice (备选)
        - seat_count: buyNum 或 seatCount
        - city: movieCityName
        - cinema_name: movieCinemaName
        - hall_type: movieHallName
        - movie_name: movieName

        Args:
            raw_orders (list): 原始订单数据列表

        Returns:
            List[OrderData]: 标准化后的订单列表
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
                
                # 安全地转换bidding_price字段（使用discountPriceUp作为麻花平台的正确竞标价格字段）
                bidding_price = 0.0
                try:
                    # 优先使用discountPriceUp字段，如果不存在则回退到salePrice
                    price_value = order.get('discountPriceUp')
                    if price_value is None:
                        price_value = order.get('salePrice', 0.0)
                        logging.debug(f"麻花平台订单 {order_id} 未找到discountPriceUp字段，使用salePrice: {price_value}")

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

                # 安全地转换original_price字段 - 从 salePrice 获取
                original_price = 0.0
                try:
                    price_value = order.get('salePrice', 0.0)
                    original_price = float(price_value) if price_value else 0.0
                except (ValueError, TypeError):
                    logging.warning(f"麻花平台订单 {order_id} 的salePrice字段转换失败，使用默认值0.0")
                    original_price = 0.0

                # 提取字符串字段（根据麻花平台官方文档字段映射）
                city = order.get('movieCityName', '')
                cinema_name = order.get('movieCinemaName', '')
                hall_type = order.get('movieHallName', '')
                movie_name = order.get('movieName', '')

                # 【新增】提取时间字段
                show_time = order.get('showTime', order.get('movieShowTime', order.get('playTime', '')))

                # 数据验证：确保关键字段存在且有效
                if not cinema_name and not movie_name:
                    logging.warning(f"麻花平台订单 {order_id} 缺少关键信息（影院名和电影名），但仍保留此订单")

                # 验证价格字段的有效性
                if bidding_price <= 0:
                    logging.debug(f"麻花平台订单 {order_id} 的竞标价格为0或负数: {bidding_price}")

                # 构建标准化订单对象
                standardized_order = OrderData(
                    order_id=order_id,
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
                logging.warning(f"标准化麻花平台订单数据失败，跳过此订单: {e}")
                logging.warning(f"有问题的原始订单数据: {order}")
                continue
        
        logging.info(f"麻花平台数据标准化完成，成功处理 {len(standardized)} 条订单")
        return standardized

    async def test_credentials(self) -> tuple[bool, str]:
        """【V3.5新增】测试凭证有效性"""
        try:
            # 【调试】记录test_credentials方法接收到的配置
            logging.info("=" * 60)
            logging.info("🔍 MahuaAdapter.test_credentials - 配置验证")
            logging.info("=" * 60)
            logging.info(f"📋 适配器实例配置:")
            logging.info(f"  self.dev_code: '{self.dev_code}'")
            logging.info(f"  self.secret_key: '{self.secret_key}'")
            logging.info(f"  self.channel_id: '{self.channel_id}'")
            logging.info(f"  self.login_url: '{self.login_url}'")
            logging.info(f"  self.order_list_url: '{self.order_list_url}'")

            if not self.dev_code or not self.secret_key:
                logging.warning("❌ 配置信息不完整")
                return False, "配置信息不完整，请检查开发者代码和密钥"

            # 尝试获取Token来测试凭证
            logging.info("📋 开始调用_get_token方法...")
            token = await self._get_token()
            logging.info(f"📋 _get_token返回结果: {token if token else 'None'}")

            if token:
                logging.info("✅ 凭证验证成功")
                return True, "凭证有效，连接成功！"
            else:
                logging.warning("❌ 凭证验证失败")
                return False, "凭证无效，请检查开发者代码和密钥后重试"

        except Exception as e:
            logging.error(f"❌ 测试{self.name}平台凭证异常: {e}")
            return False, f"连接测试异常: {str(e)}"

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
            
            # 【V3.5升级】检查配置完整性
            if not self.secret_key or not self.dev_code or not self.login_url:
                logging.error(f"{self.name}平台配置不完整，无法获取Token")
                return None

            # 【调试】生成签名过程
            string_to_sign = body_json_str + self.secret_key + txntime_ms
            logging.info(f"📋 签名生成过程:")
            logging.info(f"  body_json_str: '{body_json_str}'")
            logging.info(f"  secret_key: '{self.secret_key}'")
            logging.info(f"  txntime_ms: '{txntime_ms}'")
            logging.info(f"  string_to_sign: '{string_to_sign}'")

            md5 = hashlib.md5()
            md5.update(string_to_sign.encode('utf-8'))
            sign = md5.hexdigest()
            logging.info(f"  生成的签名: '{sign}'")

            # 【调试】构建请求头
            headers = {
                'channelid': self.channel_id,
                'txntime': txntime_ms,
                'devCode': self.dev_code,
                'sign': sign,
                'Content-Type': 'application/json; charset=utf-8'
            }
            logging.info(f"📋 请求头构建完成:")
            for key, value in headers.items():
                logging.info(f"    {key}: '{value}'")

            # 【修复】使用网络配置进行SSL和超时设置
            import ssl

            # 从config字典获取网络配置
            network_config = self.config.get('network_config', {})

            # 创建SSL上下文
            ssl_context = None
            if not network_config.get("verify_ssl", True):
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE

            # 创建超时配置
            timeout = aiohttp.ClientTimeout(total=network_config.get("timeout", 30))

            connector = aiohttp.TCPConnector(ssl=ssl_context)
            async with aiohttp.ClientSession(
                timeout=timeout,
                connector=connector
            ) as session:
                async with session.post(
                    self.login_url,
                    data=body_json_str.encode('utf-8'),
                    headers=headers
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

    def _handle_auth_failure(self):
        """
        【新增】处理认证失败
        连续失败次数达到阈值时发射凭证失效信号
        """
        self.auth_failure_count += 1
        logging.warning(f"{self.name}平台认证失败，连续失败次数: {self.auth_failure_count}/{self.max_auth_failures}")

        if self.auth_failure_count >= self.max_auth_failures and not self.credential_expired:
            self.credential_expired = True
            # 【修复】设置平台停止状态
            self.is_stopped = True
            logging.error(f"{self.name}平台凭证已失效，连续失败{self.auth_failure_count}次，已自动停止API请求")

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
            # 【修复】重置停止状态
            self.is_stopped = False

    async def quick_kill_bidding(self, put_order_id: str, bidding_price: float = 0.01) -> dict:
        """
        麻花平台秒杀竞价接口 - 使用积分抢单模式
        
        Args:
            put_order_id: 放单号
            bidding_price: 竞价单价（积分模式下可以是任意有效价格）
            
        Returns:
            dict: 竞价结果
        """
        try:
            # 检查平台状态
            if self.is_stopped or self.credential_expired:
                return {
                    "success": False, 
                    "message": "平台已停止或凭证失效",
                    "rtnCode": "ERROR"
                }
            
            # 确保登录状态
            if not self.token:
                await self.login()
                if not self.token:
                    return {
                        "success": False,
                        "message": "登录失败，无法执行秒杀",
                        "rtnCode": "LOGIN_FAILED"
                    }
            
            # 构建竞价请求URL
            bidding_url = "https://openapi.quanma51.com/api/movie-server/movie/bidding/order/add"
            
            # 构建请求体 - 使用积分抢单模式
            request_data = {
                "putOrderId": int(put_order_id),
                "biddingPrice": float(bidding_price),
                "isDirectGetOrder": "1"  # 积分抢单，立即获得订单
            }
            
            # 【关键】使用与现有接口完全相同的JSON序列化方式
            request_body_str = json.dumps(request_data, separators=(',', ':'))
            
            # 构建请求头
            current_time = str(int(time.time() * 1000))
            headers = {
                "channelid": self.channel_id,
                "txntime": current_time,
                "devCode": self.dev_code,
                "token": self.token,
                "sign": self._generate_sign_for_bidding(request_body_str, current_time),
                "Content-Type": "application/json; charset=utf-8"  # 【修复】明确指定UTF-8编码
            }
            
            logging.info(f"🚀 执行麻花平台秒杀竞价: 订单{put_order_id}, 价格{bidding_price}, 积分模式")
            
            # 【调试】输出请求详细信息
            logging.info(f"📤 请求详情:")
            logging.info(f"   - URL: {bidding_url}")
            logging.info(f"   - 请求头: {headers}")
            logging.info(f"   - 请求体: {request_data}")
            
            # 发送请求
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    bidding_url,
                    headers=headers,
                    data=request_body_str,  # 【修复】使用data而不是json，确保精确控制JSON格式
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        
                        # 解析响应
                        rtn_code = result.get('rtnCode', '')
                        rtn_msg = result.get('rtnMsg', '')
                        
                        if rtn_code == "000000":
                            logging.info(f"✅ 麻花平台秒杀成功: 订单{put_order_id}")
                            return {
                                "success": True,
                                "message": f"秒杀成功! {rtn_msg}",
                                "rtnCode": rtn_code,
                                "data": result.get('rtnData', {})
                            }
                        else:
                            logging.warning(f"⚠️ 麻花平台秒杀失败: {rtn_msg} (代码: {rtn_code})")
                            return {
                                "success": False,
                                "message": f"秒杀失败: {rtn_msg}",
                                "rtnCode": rtn_code
                            }
                    else:
                        error_msg = f"HTTP错误: {response.status}"
                        logging.error(f"❌ 麻花平台秒杀请求失败: {error_msg}")
                        return {
                            "success": False,
                            "message": error_msg,
                            "rtnCode": f"HTTP_{response.status}"
                        }
                        
        except asyncio.TimeoutError:
            error_msg = "请求超时"
            logging.error(f"❌ 麻花平台秒杀超时: 订单{put_order_id}")
            return {"success": False, "message": error_msg, "rtnCode": "TIMEOUT"}
            
        except Exception as e:
            error_msg = f"秒杀异常: {str(e)}"
            logging.error(f"❌ 麻花平台秒杀异常: {error_msg}")
            return {"success": False, "message": error_msg, "rtnCode": "EXCEPTION"}

    def _generate_sign_for_bidding(self, request_body: str, txntime: str) -> str:
        """
        为竞价接口生成请求签名（严格按照麻花平台文档）
        签名方式：MD5(bodyjson+key+txntime)
        """
        try:
            # 严格按照文档：bodyjson + key + txntime
            string_to_sign = request_body + self.secret_key + txntime
            
            # 确保使用UTF-8编码
            sign_result = hashlib.md5(string_to_sign.encode('utf-8')).hexdigest()
            
            # 【调试】输出签名详细信息
            logging.info(f"🔐 竞价接口签名生成详情（按官方文档）:")
            logging.info(f"   - bodyjson: {request_body}")
            logging.info(f"   - key: {self.secret_key[:4]}****{self.secret_key[-4:] if len(self.secret_key) > 8 else '****'}")
            logging.info(f"   - txntime: {txntime}")
            logging.info(f"   - 完整拼接: {request_body}{self.secret_key[:4]}****{txntime}")
            logging.info(f"   - MD5签名: {sign_result}")
            
            # 【验证】使用官方示例验证签名算法
            self._test_sign_algorithm()
            
            return sign_result
        except Exception as e:
            logging.error(f"生成竞价签名失败: {e}")
            return ""
    
    def _test_sign_algorithm(self):
        """
        使用官方文档示例验证签名算法
        """
        try:
            # 官方示例1: bodyjson={"a":"1"}, key=123, txntime=1535791021891
            # 期望结果: 1723a12a71accf4b82239b9100dc3cd9
            test_body = '{"a":"1"}'
            test_key = "123"
            test_time = "1535791021891"
            test_string = test_body + test_key + test_time
            test_result = hashlib.md5(test_string.encode('utf-8')).hexdigest()
            
            expected = "1723a12a71accf4b82239b9100dc3cd9"
            if test_result == expected:
                logging.info(f"✅ 签名算法验证成功: {test_result}")
            else:
                logging.error(f"❌ 签名算法验证失败:")
                logging.error(f"   期望: {expected}")
                logging.error(f"   实际: {test_result}")
                logging.error(f"   测试字符串: {test_string}")
                
        except Exception as e:
            logging.error(f"签名算法验证异常: {e}")