#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
平台适配器基类 - 定义所有平台适配器必须实现的接口
"""

from abc import ABC, abstractmethod


class BaseAdapter(ABC):
    """
    平台适配器基类
    
    所有平台适配器都必须继承此类并实现其抽象方法
    """
    
    def __init__(self, name: str):
        """
        初始化基类适配器

        Args:
            name (str): 平台名称
        """
        self.name = name
    
    @abstractmethod
    async def fetch_and_process(self):
        """
        获取并处理订单数据的抽象方法
        
        此方法必须被子类实现，用于完成以下工作：
        1. 请求平台API获取原始数据
        2. 解密数据（如果需要）
        3. 解析和清洗数据
        4. 去重处理
        5. 返回标准化的订单列表
        
        Returns:
            list: 标准化的订单列表，每个订单包含以下字段：
                - order_id: 订单唯一标识
                - city: 城市名称
                - cinema_name: 影院名称
                - hall_type: 影厅类型
                - bidding_price: 竞价价格
                - seat_count: 票数
                - 其他平台特有字段...
        
        Raises:
            NotImplementedError: 如果子类没有实现此方法
        """
        raise NotImplementedError("子类必须实现 fetch_and_process 方法")
