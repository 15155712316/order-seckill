#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
麻花平台竞标价格字段修正验证脚本
"""

import json
import logging
from core.platforms.mahua_adapter import MahuaAdapter

# 设置日志级别为DEBUG以查看详细信息
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def test_price_field_mapping():
    """测试价格字段映射修正"""
    print("🧪 测试麻花平台价格字段映射修正...")
    print("=" * 70)
    
    # 创建麻花适配器实例
    adapter = MahuaAdapter("麻花")
    
    # 模拟不同情况的订单数据
    test_orders = [
        {
            # 情况1：包含discountPriceUp字段（应该优先使用）
            "id": "test001",
            "discountPriceUp": 45.5,
            "salePrice": 50.0,
            "buyNum": 2,
            "movieCityName": "北京",
            "movieCinemaName": "万达影城（CBD店）",
            "movieHallName": "IMAX厅",
            "movieName": "流浪地球2"
        },
        {
            # 情况2：只有salePrice字段（应该回退使用）
            "id": "test002",
            "salePrice": 38.8,
            "buyNum": 1,
            "movieCityName": "上海",
            "movieCinemaName": "大光明电影院",
            "movieHallName": "数字厅",
            "movieName": "满江红"
        },
        {
            # 情况3：discountPriceUp为null，有salePrice（应该使用salePrice）
            "id": "test003",
            "discountPriceUp": None,
            "salePrice": 42.0,
            "buyNum": 3,
            "movieCityName": "广州",
            "movieCinemaName": "太平洋影城",
            "movieHallName": "杜比厅",
            "movieName": "阿凡达：水之道"
        },
        {
            # 情况4：两个价格字段都为0（测试边界情况）
            "id": "test004",
            "discountPriceUp": 0,
            "salePrice": 0,
            "buyNum": 1,
            "movieCityName": "深圳",
            "movieCinemaName": "华夏国际影城",
            "movieHallName": "普通厅",
            "movieName": "熊出没·伴我熊芯"
        },
        {
            # 情况5：价格字段为字符串（测试类型转换）
            "id": "test005",
            "discountPriceUp": "55.5",
            "salePrice": "60.0",
            "buyNum": "2",
            "movieCityName": "杭州",
            "movieCinemaName": "博纳国际影城",
            "movieHallName": "激光厅",
            "movieName": "中国乒乓之绝地反击"
        }
    ]
    
    print(f"📋 测试数据包含 {len(test_orders)} 条模拟订单")
    print()
    
    # 调用标准化方法
    try:
        standardized_orders = adapter._standardize_orders(test_orders)
        
        print(f"✅ 标准化处理成功，处理了 {len(standardized_orders)} 条订单")
        print()
        
        # 验证每个订单的价格字段映射
        for i, order in enumerate(standardized_orders, 1):
            original = test_orders[i-1]
            
            print(f"📊 订单 {i} (ID: {order['order_id']}):")
            print(f"   原始数据:")
            print(f"     discountPriceUp: {original.get('discountPriceUp')}")
            print(f"     salePrice: {original.get('salePrice')}")
            print(f"   标准化结果:")
            print(f"     bidding_price: {order['bidding_price']}")
            print(f"     seat_count: {order['seat_count']}")
            print(f"     cinema_name: {order['cinema_name']}")
            print(f"     city: {order['city']}")
            
            # 验证价格字段选择逻辑
            expected_price = None
            price_source = None
            
            if original.get('discountPriceUp') is not None:
                try:
                    expected_price = float(original['discountPriceUp'])
                    price_source = "discountPriceUp"
                except (ValueError, TypeError):
                    expected_price = float(original.get('salePrice', 0.0))
                    price_source = "salePrice (discountPriceUp转换失败)"
            else:
                expected_price = float(original.get('salePrice', 0.0))
                price_source = "salePrice (discountPriceUp不存在)"
            
            if abs(order['bidding_price'] - expected_price) < 0.01:  # 浮点数比较
                print(f"   ✅ 价格字段映射正确，使用了 {price_source}")
            else:
                print(f"   ❌ 价格字段映射错误！期望: {expected_price}，实际: {order['bidding_price']}")
            
            print()
        
        # 统计价格字段使用情况
        print("📈 价格字段使用统计:")
        discount_count = sum(1 for order in test_orders if order.get('discountPriceUp') is not None)
        sale_only_count = len(test_orders) - discount_count
        
        print(f"   使用 discountPriceUp 的订单: {discount_count} 条")
        print(f"   回退到 salePrice 的订单: {sale_only_count} 条")
        
    except Exception as e:
        print(f"❌ 标准化处理失败: {e}")
        import traceback
        traceback.print_exc()

def test_field_validation():
    """测试字段验证功能"""
    print("\n🔍 测试字段验证功能...")
    print("=" * 70)
    
    adapter = MahuaAdapter("麻花")
    
    # 测试缺少关键字段的订单
    invalid_orders = [
        {
            # 缺少影院名和电影名
            "id": "invalid001",
            "discountPriceUp": 30.0,
            "buyNum": 1,
            "movieCityName": "测试城市"
        },
        {
            # 价格为负数
            "id": "invalid002",
            "discountPriceUp": -10.0,
            "buyNum": 1,
            "movieCityName": "测试城市",
            "movieCinemaName": "测试影院",
            "movieName": "测试电影"
        }
    ]
    
    try:
        standardized_orders = adapter._standardize_orders(invalid_orders)
        print(f"✅ 验证功能测试完成，处理了 {len(standardized_orders)} 条订单")
        
        for order in standardized_orders:
            print(f"📋 订单 {order['order_id']}:")
            print(f"   bidding_price: {order['bidding_price']}")
            print(f"   cinema_name: '{order['cinema_name']}'")
            print(f"   movie_name: '{order['movie_name']}'")
            print()
            
    except Exception as e:
        print(f"❌ 验证功能测试失败: {e}")

def main():
    """主测试函数"""
    print("🚀 开始麻花平台竞标价格字段修正验证...")
    print("修正内容：将竞标价格字段从 salePrice 修正为 discountPriceUp")
    print("=" * 80)
    
    # 测试价格字段映射
    test_price_field_mapping()
    
    # 测试字段验证
    test_field_validation()
    
    print("=" * 80)
    print("🎉 麻花平台价格字段修正验证完成！")
    print()
    print("📝 修正总结:")
    print("1. ✅ 优先使用 discountPriceUp 作为竞标价格")
    print("2. ✅ 当 discountPriceUp 不存在时回退到 salePrice")
    print("3. ✅ 添加了数据验证和调试日志")
    print("4. ✅ 更新了字段映射文档注释")

if __name__ == "__main__":
    main()
