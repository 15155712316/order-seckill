#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
平台适配器基类 V2.0 - 标准化接口和性能优化
"""

import time
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
from core.logger import get_logger


class AdapterStatus(Enum):
    """适配器状态枚举"""
    IDLE = "idle"
    RUNNING = "running"
    ERROR = "error"
    STOPPED = "stopped"


@dataclass
class AdapterMetrics:
    """适配器性能指标"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_orders: int = 0
    avg_response_time: float = 0.0
    last_success_time: Optional[float] = None
    last_error_time: Optional[float] = None
    last_error_message: str = ""


@dataclass
class OrderData:
    """标准化订单数据结构"""
    order_id: str
    bidding_price: float
    seat_count: int
    original_price: float
    city: str
    cinema_name: str
    hall_type: str
    movie_name: str
    show_time: str
    raw_data: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'order_id': self.order_id,
            'bidding_price': self.bidding_price,
            'seat_count': self.seat_count,
            'original_price': self.original_price,
            'city': self.city,
            'cinema_name': self.cinema_name,
            'hall_type': self.hall_type,
            'movie_name': self.movie_name,
            'show_time': self.show_time,
            'raw_data': self.raw_data
        }


class BaseAdapter(ABC):
    """
    平台适配器基类 V2.0
    
    提供标准化接口、性能监控、错误处理和缓存优化
    """
    
    def __init__(self, name: str, config: Dict[str, Any] = None):
        """
        初始化基类适配器

        Args:
            name (str): 平台名称
            config (Dict[str, Any]): 平台配置
        """
        self.name = name
        self.config = config or {}
        self.logger = get_logger()
        
        # 状态管理
        self.status = AdapterStatus.IDLE
        self.metrics = AdapterMetrics()
        
        # 缓存优化 - 使用set代替deque for O(1) lookup
        max_cache_size = self.config.get('max_orders_cache', 500)
        self.seen_order_ids = set()
        self.max_cache_size = max_cache_size
        self.cache_cleanup_counter = 0
        
        # 错误处理
        self.consecutive_errors = 0
        self.max_consecutive_errors = self.config.get('max_consecutive_errors', 5)
        self.is_disabled = False
        
        self.logger.info(f"{self.name}适配器V2.0初始化完成")
    
    async def fetch_and_process(self) -> Dict[str, Any]:
        """
        主要处理方法 - 获取并处理订单数据
        
        Returns:
            Dict[str, Any]: 标准化结果
                {
                    'name': str,           # 平台名称
                    'success': bool,       # 是否成功
                    'orders': List[Dict],  # 订单列表
                    'error': str,          # 错误信息（可选）
                    'metrics': Dict        # 性能指标
                }
        """
        if self.is_disabled:
            return self._create_result(False, [], "适配器已禁用")
        
        operation_id = self.logger.start_operation(f"{self.name}_fetch")
        start_time = time.time()
        self.status = AdapterStatus.RUNNING
        
        try:
            # 1. 获取原始数据
            raw_data = await self._fetch_raw_data()
            
            # 2. 验证数据
            if not self._validate_raw_data(raw_data):
                raise ValueError("原始数据验证失败")
            
            # 3. 处理和标准化数据
            processed_orders = await self._process_raw_data(raw_data)
            
            # 4. 去重处理
            new_orders = self._deduplicate_orders(processed_orders)
            
            # 5. 更新指标
            duration = time.time() - start_time
            self._update_success_metrics(len(new_orders), duration)
            
            self.logger.end_operation(operation_id, {
                'platform': self.name,
                'order_count': len(new_orders),
                'success': True,
                'duration': duration
            })
            
            self.status = AdapterStatus.IDLE
            return self._create_result(True, new_orders)
            
        except Exception as e:
            duration = time.time() - start_time
            self._update_error_metrics(str(e), duration)
            
            self.logger.end_operation(operation_id, {
                'platform': self.name,
                'error': str(e),
                'success': False,
                'duration': duration
            })
            
            self.status = AdapterStatus.ERROR
            return self._create_result(False, [], str(e))
    
    @abstractmethod
    async def _fetch_raw_data(self) -> Any:
        """
        获取原始数据的抽象方法
        
        子类必须实现此方法来获取平台特定的原始数据
        
        Returns:
            Any: 平台特定的原始数据格式
        """
        raise NotImplementedError("子类必须实现 _fetch_raw_data 方法")
    
    @abstractmethod
    async def _process_raw_data(self, raw_data: Any) -> List[OrderData]:
        """
        处理原始数据的抽象方法
        
        子类必须实现此方法来处理和标准化数据
        
        Args:
            raw_data: 原始数据
            
        Returns:
            List[OrderData]: 标准化订单数据列表
        """
        raise NotImplementedError("子类必须实现 _process_raw_data 方法")
    
    def _validate_raw_data(self, raw_data: Any) -> bool:
        """
        验证原始数据
        
        子类可以重写此方法来实现特定的验证逻辑
        
        Args:
            raw_data: 原始数据
            
        Returns:
            bool: 数据是否有效
        """
        return raw_data is not None
    
    def _deduplicate_orders(self, orders: List[OrderData]) -> List[OrderData]:
        """
        去重处理 - 使用优化的set查找
        
        Args:
            orders: 订单列表
            
        Returns:
            List[OrderData]: 去重后的新订单列表
        """
        new_orders = []
        
        for order in orders:
            if order.order_id not in self.seen_order_ids:
                # 添加到缓存
                self.seen_order_ids.add(order.order_id)
                new_orders.append(order)
                
                # 缓存大小控制
                if len(self.seen_order_ids) > self.max_cache_size:
                    self._cleanup_cache()
        
        return new_orders
    
    def _cleanup_cache(self):
        """清理缓存 - 移除最老的一半记录"""
        if len(self.seen_order_ids) > self.max_cache_size:
            # 简单策略：清理一半缓存
            ids_to_remove = list(self.seen_order_ids)[:len(self.seen_order_ids) // 2]
            for order_id in ids_to_remove:
                self.seen_order_ids.discard(order_id)
            
            self.logger.debug(f"{self.name}平台缓存清理完成，剩余{len(self.seen_order_ids)}条记录")
    
    def _create_result(self, success: bool, orders: List[OrderData], error: str = None) -> Dict[str, Any]:
        """创建标准化返回结果"""
        result = {
            'name': self.name,
            'success': success,
            'orders': [order.to_dict() for order in orders] if orders else [],
            'metrics': {
                'total_requests': self.metrics.total_requests,
                'success_rate': self._calculate_success_rate(),
                'avg_response_time': self.metrics.avg_response_time,
                'total_orders': self.metrics.total_orders
            },
            'timestamp': time.time()
        }
        
        if error:
            result['error'] = error
            
        return result
    
    def _update_success_metrics(self, order_count: int, duration: float):
        """更新成功指标"""
        self.metrics.total_requests += 1
        self.metrics.successful_requests += 1
        self.metrics.total_orders += order_count
        self.metrics.last_success_time = time.time()
        
        # 更新平均响应时间
        self._update_avg_response_time(duration)
        
        # 重置错误计数
        self.consecutive_errors = 0
    
    def _update_error_metrics(self, error_message: str, duration: float):
        """更新错误指标"""
        self.metrics.total_requests += 1
        self.metrics.failed_requests += 1
        self.metrics.last_error_time = time.time()
        self.metrics.last_error_message = error_message
        
        # 更新平均响应时间
        self._update_avg_response_time(duration)
        
        # 增加连续错误计数
        self.consecutive_errors += 1
        
        # 检查是否需要禁用适配器
        if self.consecutive_errors >= self.max_consecutive_errors:
            self.is_disabled = True
            self.logger.error(f"{self.name}平台连续{self.consecutive_errors}次错误，已自动禁用")
    
    def _update_avg_response_time(self, duration: float):
        """更新平均响应时间"""
        if self.metrics.total_requests == 1:
            self.metrics.avg_response_time = duration
        else:
            # 指数移动平均
            alpha = 0.1
            self.metrics.avg_response_time = (
                alpha * duration + (1 - alpha) * self.metrics.avg_response_time
            )
    
    def _calculate_success_rate(self) -> float:
        """计算成功率"""
        if self.metrics.total_requests == 0:
            return 0.0
        return (self.metrics.successful_requests / self.metrics.total_requests) * 100
    
    # 便捷方法
    def get_status(self) -> Dict[str, Any]:
        """获取适配器状态信息"""
        return {
            'name': self.name,
            'status': self.status.value,
            'is_disabled': self.is_disabled,
            'consecutive_errors': self.consecutive_errors,
            'cache_size': len(self.seen_order_ids),
            'metrics': {
                'total_requests': self.metrics.total_requests,
                'successful_requests': self.metrics.successful_requests,
                'failed_requests': self.metrics.failed_requests,
                'success_rate': self._calculate_success_rate(),
                'total_orders': self.metrics.total_orders,
                'avg_response_time': self.metrics.avg_response_time,
                'last_success_time': self.metrics.last_success_time,
                'last_error_time': self.metrics.last_error_time,
                'last_error_message': self.metrics.last_error_message
            }
        }
    
    def reset_error_count(self):
        """重置错误计数并重新启用适配器"""
        self.consecutive_errors = 0
        self.is_disabled = False
        self.logger.info(f"{self.name}平台错误计数已重置，适配器已重新启用")
    
    def clear_cache(self):
        """清空缓存"""
        self.seen_order_ids.clear()
        self.logger.info(f"{self.name}平台缓存已清空")
    
    async def test_credentials(self) -> Tuple[bool, str]:
        """
        测试凭证有效性
        
        子类可以重写此方法来实现特定的凭证测试逻辑
        
        Returns:
            Tuple[bool, str]: (是否有效, 消息)
        """
        return True, "基类适配器无需凭证测试"
