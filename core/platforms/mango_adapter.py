#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
芒果平台适配器 - 负责芒果平台的数据获取和处理
"""

import logging
import aiohttp
from .base_adapter import BaseAdapter, OrderData
from PyQt6.QtCore import QObject, pyqtSignal


def setup_mango_logger():
    """设置芒果平台专用调试日志"""
    mango_logger = logging.getLogger('mango_debug')
    mango_logger.setLevel(logging.DEBUG)
    
    # 避免重复添加handler
    if not mango_logger.handlers:
        # 创建文件处理器
        handler = logging.FileHandler('mango_debug.log', encoding='utf-8')
        handler.setLevel(logging.DEBUG)
        
        # 创建详细的格式化器
        formatter = logging.Formatter(
            '%(asctime)s [芒果平台] %(levelname)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        
        mango_logger.addHandler(handler)
        
        # 防止日志传播到根日志器
        mango_logger.propagate = False
    
    return mango_logger


class MangoAdapter(BaseAdapter):
    """芒果平台适配器类"""

    def __init__(self, name: str, config: dict = None):
        """初始化芒果平台适配器"""
        super().__init__(name, config)

        # 配置注入机制
        self.user_token = self.config.get('user_token', '')
        self.api_url = self.config.get('api_url', 'https://supplier.mgmovie.net/v2/api/67d77db66adac')
        
        # Token状态管理
        self.token_valid = bool(self.user_token)
        
        # 设置专用调试日志器
        self.mango_logger = setup_mango_logger()
        self.mango_logger.info(f"=== 芒果平台适配器初始化 ===")
        self.mango_logger.info(f"API地址: {self.api_url}")
        self.mango_logger.info(f"Token状态: {'已配置' if self.user_token else '未配置'}")
        

    async def _fetch_raw_data(self):
        """
        获取芒果平台原始数据 - 实现抽象方法
        
        Returns:
            dict: 原始API响应数据
        """
        if not self.user_token:
            raise Exception("User Token未配置")

        # 构建请求头
        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'zh-CN,zh;q=0.9',
            'content-type': 'application/json;charset=UTF-8',
            'origin': 'https://www.qianyinghui.net',
            'priority': 'u=1, i',
            'referer': 'https://www.qianyinghui.net/',
            'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'cross-site',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
            'user-token': self.user_token,
            'zhua-ch-ua': 'zh'
        }

        # 构建请求体
        request_data = {
            "page": 1,
            "page_size": 500,
            "sort_field": "created_at",
            "sort_order": "desc",
            "source": "pc"
        }

        logging.info(f"🎬 开始获取{self.name}平台订单数据")
        self.mango_logger.info(f"🎬 开始获取订单数据 - 请求参数: {request_data}")

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
                    
                    # 详细检查业务层面的响应
                    api_code = data.get('code')
                    api_msg = data.get('message', data.get('msg', ''))
                    
                    # 检查是否为认证错误
                    if api_code not in [0, 1, 200]:  # 芒果平台使用1表示成功
                        if "登录" in api_msg or "token" in api_msg.lower() or "auth" in api_msg.lower():
                            logging.error(f"❌ {self.name}平台认证失败: {api_msg}")
                            self.mango_logger.error(f"❌ 认证失败: {api_msg}")
                            raise Exception(f"认证失败: {api_msg}")
                        else:
                            logging.error(f"❌ {self.name}平台API业务错误: {api_msg}")
                            self.mango_logger.error(f"❌ API业务错误: 代码={api_code}, 消息={api_msg}")
                            raise Exception(f"API业务错误: {api_msg}")
                    
                    # 记录成功获取的订单数量
                    raw_data_field = data.get('data')
                    orders = raw_data_field
                    if isinstance(orders, dict):
                        # 如果data是字典，可能订单列表在其中的某个字段
                        possible_fields = ['list', 'items', 'records', 'orders', 'data']
                        for field in possible_fields:
                            if field in orders and isinstance(orders[field], list):
                                orders = orders[field]
                                break
                        else:
                            orders = []
                    
                    if isinstance(orders, list):
                        logging.info(f"📊 {self.name}平台从API获取 {len(orders)} 条原始订单")
                        self.mango_logger.info(f"📊 API成功返回 {len(orders)} 条原始订单")
                    
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
        处理芒果平台原始数据 - 实现抽象方法
        
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
        
        # 检查响应格式 - 芒果平台使用1表示成功
        api_code = raw_data.get('code')
        if api_code not in [0, 1, 200]:  # 允许0、1或200作为成功码
            return False
            
        data = raw_data.get('data')
        return isinstance(data, (list, dict))

    def _process_response_data(self, data):
        """
        处理芒果平台的响应数据
        
        Args:
            data: API响应数据
            
        Returns:
            List[OrderData]: 标准化的订单数据列表
        """
        try:
            standardized = []
            
            # 检查响应格式
            api_code = data.get('code')
            api_message = data.get('message', data.get('msg', ''))
            
            if api_code not in [0, 1, 200]:  # 芒果平台使用1表示成功
                logging.warning(f"{self.name}平台API返回错误: {api_message}")
                return []
            
            # 芒果平台的数据可能在不同字段中
            raw_data_field = data.get('data')
            orders = raw_data_field
            if isinstance(orders, dict):
                # 如果data是字典，可能订单列表在其中的某个字段
                possible_fields = ['list', 'items', 'records', 'orders', 'data']
                for field in possible_fields:
                    if field in orders and isinstance(orders[field], list):
                        orders = orders[field]
                        break
                else:
                    orders = []
            
            if not isinstance(orders, list):
                logging.warning(f"{self.name}平台响应数据格式异常")
                return []

            for order in orders:
                try:
                    # 根据实际响应数据进行字段映射 - 优先使用order_number字段
                    order_id = str(order.get('order_number', order.get('id', '')))  # 订单ID
                    
                    # 调试日志：记录订单ID提取情况
                    if order.get('order_number') and order.get('id'):
                        logging.debug(f"📋 芒果订单: order_number={order.get('order_number')}, id={order.get('id')}, 使用={order_id}")
                        self.mango_logger.debug(f"📋 订单ID提取: order_number={order.get('order_number')}, id={order.get('id')}, 最终使用={order_id}")
                    
                    # 座位数
                    seat_count = int(order.get('ticket_num', 1))  # 票数
                    
                    # 价格字段映射
                    bidding_price = float(order.get('point_sec_kill_price', 0))  # 积分秒杀价格作为竞价
                    
                    # 原价 = 猫眼总价 / 座位数
                    maoyan_total_price = float(order.get('maoyan_price', 0))
                    original_price = maoyan_total_price / seat_count if seat_count > 0 else maoyan_total_price
                    
                    # 调试：记录价格信息
                    if bidding_price == 0:
                        logging.warning(f"⚠️ 芒果订单 {order_id} 竞价价格为0，可能影响规则匹配")
                        self.mango_logger.warning(f"⚠️ 订单 {order_id} 竞价价格为0 (point_sec_kill_price={order.get('point_sec_kill_price')})")
                    
                    # 记录价格详情到专用日志
                    self.mango_logger.debug(f"💰 订单 {order_id} 价格信息: point_sec_kill_price={order.get('point_sec_kill_price')}, maoyan_price={order.get('maoyan_price')}, 竞价={bidding_price}, 原价={original_price}")
                    
                    # 基础信息字段
                    city = order.get('city_name', '')  # 城市名称
                    cinema_name = order.get('cinema_name', '')  # 影院名称
                    hall_type = order.get('hall_name', '')  # 影厅名称
                    movie_name = order.get('film_name', '')  # 电影名称
                    show_time = order.get('show_time', '')  # 放映时间

                    # 如果订单ID为空，跳过这个订单
                    if not order_id:
                        logging.warning(f"跳过无效订单，订单ID为空")
                        continue
                    
                    # 调试：记录关键字段信息
                    missing_fields = []
                    if not city: missing_fields.append('city')
                    if not cinema_name: missing_fields.append('cinema_name')
                    if not movie_name: missing_fields.append('movie_name')
                    
                    if missing_fields:
                        logging.warning(f"⚠️ 芒果订单 {order_id} 缺少关键字段: {', '.join(missing_fields)}")
                        self.mango_logger.warning(f"⚠️ 订单 {order_id} 缺少关键字段: {', '.join(missing_fields)}")
                    
                    # 调试：记录完整的订单信息
                    logging.debug(f"📋 芒果订单详情: {order_id} | 城市:{city} | 影院:{cinema_name} | 影厅:{hall_type} | 电影:{movie_name} | 竞价:{bidding_price} | 原价:{original_price}")
                    self.mango_logger.info(f"📋 订单标准化完成: {order_id}")
                    self.mango_logger.info(f"   城市: {city}")
                    self.mango_logger.info(f"   影院: {cinema_name}")
                    self.mango_logger.info(f"   影厅: {hall_type}")
                    self.mango_logger.info(f"   电影: {movie_name}")
                    self.mango_logger.info(f"   竞价: {bidding_price}")
                    self.mango_logger.info(f"   原价: {original_price}")
                    self.mango_logger.info(f"   座位数: {seat_count}")
                    self.mango_logger.info(f"   放映时间: {show_time}")
                    
                    # 记录原始数据到专用日志（用于调试）
                    self.mango_logger.debug(f"🔍 原始订单数据: {order}")

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
                    logging.warning(f"标准化{self.name}平台订单数据失败，跳过此订单: {e}")
                    self.mango_logger.warning(f"标准化订单失败: {e}, 订单数据: {order}")

            logging.info(f"成功处理 {len(standardized)} 个订单")
            self.mango_logger.info(f"✅ 芒果平台处理完成: 成功标准化 {len(standardized)} 个订单")
            return standardized

        except Exception as e:
            logging.error(f"❌ {self.name}平台处理响应数据失败: {e}")
            self.mango_logger.error(f"❌ 处理响应数据失败: {e}")
            return []

    def is_available(self) -> bool:
        """检查平台是否可用"""
        return bool(self.user_token) and self.token_valid

    async def test_credentials(self):
        """测试芒果平台凭证"""
        try:
            # 使用BaseAdapter的标准方法进行测试
            raw_data = await self._fetch_raw_data()
            processed_orders = await self._process_raw_data(raw_data)
            
            orders_count = len(processed_orders)
            return True, f"连接成功！获取到 {orders_count} 条订单数据"

        except Exception as e:
            logging.error(f"芒果平台凭证测试异常: {e}")
            error_msg = str(e)
            
            # 根据错误内容提供更友好的提示
            if "认证失败" in error_msg or "登录" in error_msg:
                return False, f"Token认证失败\n\n💡 请检查以下几点:\n1. User Token是否正确\n2. Token是否已过期\n3. 账号是否有权限访问API"
            elif "401" in error_msg or "unauthorized" in error_msg.lower():
                return False, "Token已过期或无效，请重新获取"
            elif "timeout" in error_msg.lower():
                return False, "连接超时，请检查网络"
            else:
                return False, f"连接测试失败: {error_msg}"