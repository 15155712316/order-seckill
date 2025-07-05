#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
麻花平台价格字段修正简单测试
"""

from core.platforms.mahua_adapter import MahuaAdapter

def test_price_mapping():
    """测试价格字段映射"""
    print("🧪 测试麻花平台价格字段映射...")
    
    # 创建适配器实例
    adapter = MahuaAdapter("麻花")
    
    # 测试数据
    test_orders = [
        {
            "id": "test001",
            "discountPriceUp": 45.5,
            "salePrice": 50.0,
            "buyNum": 2,
            "movieCityName": "北京",
            "movieCinemaName": "万达影城",
            "movieName": "测试电影"
        },
        {
            "id": "test002", 
            "salePrice": 38.8,
            "buyNum": 1,
            "movieCityName": "上海",
            "movieCinemaName": "大光明电影院",
            "movieName": "测试电影2"
        }
    ]
    
    # 标准化处理
    result = adapter._standardize_orders(test_orders)
    
    print(f"✅ 处理了 {len(result)} 条订单")
    
    for i, order in enumerate(result):
        original = test_orders[i]
        print(f"\n📋 订单 {i+1}:")
        print(f"   ID: {order['order_id']}")
        print(f"   原始 discountPriceUp: {original.get('discountPriceUp')}")
        print(f"   原始 salePrice: {original.get('salePrice')}")
        print(f"   标准化后 bidding_price: {order['bidding_price']}")
        
        # 验证逻辑
        if original.get('discountPriceUp') is not None:
            expected = float(original['discountPriceUp'])
            source = "discountPriceUp"
        else:
            expected = float(original.get('salePrice', 0.0))
            source = "salePrice"
            
        if abs(order['bidding_price'] - expected) < 0.01:
            print(f"   ✅ 正确使用了 {source}")
        else:
            print(f"   ❌ 价格映射错误")

if __name__ == "__main__":
    test_price_mapping()
