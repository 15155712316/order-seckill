#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试新的限时订单检测逻辑
"""

import requests
import json

def test_new_limit_logic():
    """测试新的限时订单检测逻辑"""
    print("🧪 测试新的限时订单检测逻辑...")
    print("目标：只检查 order_limit_time_1 字段")
    print("=" * 70)
    
    try:
        # 获取最近的订单数据
        url = "http://localhost:5000/api/orders/recent?limit=50"
        response = requests.get(url)
        
        if response.status_code != 200:
            print(f"❌ API请求失败，状态码: {response.status_code}")
            return
        
        data = response.json()
        orders = data.get('data', [])
        
        print(f"📊 获取到 {len(orders)} 条订单数据")
        
        # 分析限时订单
        limit_orders = []
        normal_orders = []
        
        for order in orders:
            if order.get('is_limit_order', False):
                limit_orders.append(order)
            else:
                normal_orders.append(order)
        
        print(f"🔥 限时订单: {len(limit_orders)} 条")
        print(f"📋 普通订单: {len(normal_orders)} 条")
        
        # 验证限时订单是否都包含 order_limit_time_1 字段
        print(f"\n🔍 验证限时订单的 order_limit_time_1 字段:")
        
        valid_limit_orders = 0
        invalid_limit_orders = 0
        
        for i, order in enumerate(limit_orders):
            raw_data = order.get('raw_data', {})
            order_limit_time_1 = raw_data.get('order_limit_time_1', 0)
            
            if order_limit_time_1 != 0:
                valid_limit_orders += 1
                print(f"   ✅ {order['order_id']} - order_limit_time_1: {order_limit_time_1}")
            else:
                invalid_limit_orders += 1
                print(f"   ❌ {order['order_id']} - order_limit_time_1: {order_limit_time_1} (应该不为0)")
        
        # 验证普通订单是否都不包含 order_limit_time_1 字段
        print(f"\n🔍 验证普通订单的 order_limit_time_1 字段:")
        
        valid_normal_orders = 0
        invalid_normal_orders = 0
        
        for order in normal_orders[:10]:  # 只检查前10个普通订单
            raw_data = order.get('raw_data', {})
            order_limit_time_1 = raw_data.get('order_limit_time_1', 0)
            
            if order_limit_time_1 == 0:
                valid_normal_orders += 1
                print(f"   ✅ {order['order_id']} - order_limit_time_1: {order_limit_time_1}")
            else:
                invalid_normal_orders += 1
                print(f"   ❌ {order['order_id']} - order_limit_time_1: {order_limit_time_1} (应该为0)")
        
        # 查找包含 order_limit_time_1 字段的所有订单
        print(f"\n📋 所有包含 order_limit_time_1 字段的订单:")
        
        orders_with_field = []
        
        for order in orders:
            raw_data = order.get('raw_data', {})
            order_limit_time_1 = raw_data.get('order_limit_time_1', 0)
            
            if order_limit_time_1 != 0:
                orders_with_field.append({
                    'order_id': order['order_id'],
                    'cinema_name': order['cinema_name'],
                    'order_limit_time_1': order_limit_time_1,
                    'is_limit_order': order.get('is_limit_order', False)
                })
        
        print(f"   找到 {len(orders_with_field)} 个包含 order_limit_time_1 字段的订单:")
        
        for order_info in orders_with_field:
            status = "✅ 正确识别" if order_info['is_limit_order'] else "❌ 识别错误"
            print(f"   {order_info['order_id']} - {order_info['cinema_name']} - {status}")
            
            # 转换时间戳
            try:
                from datetime import datetime
                timestamp = order_info['order_limit_time_1']
                dt = datetime.fromtimestamp(timestamp)
                print(f"      order_limit_time_1: {timestamp} -> {dt.strftime('%Y-%m-%d %H:%M:%S')}")
            except:
                print(f"      order_limit_time_1: {timestamp}")
        
        # 生成测试报告
        print(f"\n" + "=" * 70)
        print(f"📋 测试报告:")
        print(f"=" * 70)
        
        print(f"✅ 新检测逻辑验证结果:")
        print(f"   - 限时订单中有效的: {valid_limit_orders}/{len(limit_orders)}")
        print(f"   - 限时订单中无效的: {invalid_limit_orders}/{len(limit_orders)}")
        print(f"   - 普通订单中有效的: {valid_normal_orders}/10")
        print(f"   - 普通订单中无效的: {invalid_normal_orders}/10")
        
        print(f"\n📊 统计信息:")
        print(f"   - 总订单数: {len(orders)}")
        print(f"   - 限时订单数: {len(limit_orders)}")
        print(f"   - 普通订单数: {len(normal_orders)}")
        print(f"   - 包含 order_limit_time_1 字段的订单: {len(orders_with_field)}")
        
        # 检测逻辑准确性
        accuracy = (valid_limit_orders + valid_normal_orders) / (len(limit_orders) + 10) * 100
        print(f"\n🎯 检测逻辑准确性: {accuracy:.1f}%")
        
        if len(orders_with_field) == len(limit_orders) and invalid_limit_orders == 0:
            print(f"✅ 新的检测逻辑完全正确！")
        else:
            print(f"⚠️ 检测逻辑可能需要调整")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")

def main():
    """主函数"""
    print("🚀 开始测试新的限时订单检测逻辑...")
    print("=" * 80)
    
    test_new_limit_logic()
    
    print(f"\n🌐 Web界面验证:")
    print(f"   访问: http://localhost:5000/")
    print(f"   1. 查看限时订单标识是否正确")
    print(f"   2. 使用筛选功能验证限时订单")
    print(f"   3. 检查统计信息中的限时订单数量")

if __name__ == "__main__":
    main()
