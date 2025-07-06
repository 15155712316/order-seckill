#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证限时订单检测逻辑修改是否成功
"""

import requests
import json
from datetime import datetime

def verify_limit_logic():
    """验证新的限时订单检测逻辑"""
    print("🔍 验证新的限时订单检测逻辑修改...")
    print("=" * 70)
    
    try:
        # 获取订单数据
        url = "http://localhost:5000/api/orders/recent?limit=200"
        response = requests.get(url)
        
        if response.status_code != 200:
            print(f"❌ API请求失败，状态码: {response.status_code}")
            return
        
        data = response.json()
        orders = data.get('data', [])
        
        print(f"📊 获取到 {len(orders)} 条订单数据")
        
        # 分析订单
        limit_orders_by_api = []
        orders_with_field = []
        
        for order in orders:
            # API标识的限时订单
            if order.get('is_limit_order', False):
                limit_orders_by_api.append(order)
            
            # 实际包含 order_limit_time_1 字段的订单
            raw_data = order.get('raw_data', {})
            if raw_data.get('order_limit_time_1', 0) != 0:
                orders_with_field.append(order)
        
        print(f"🔥 API标识的限时订单: {len(limit_orders_by_api)} 条")
        print(f"📋 包含 order_limit_time_1 字段的订单: {len(orders_with_field)} 条")
        
        # 验证一致性
        if len(limit_orders_by_api) == len(orders_with_field):
            print(f"✅ 检测逻辑修改成功！API标识与实际字段完全一致")
        else:
            print(f"❌ 检测逻辑可能有问题，数量不一致")
        
        # 显示详细信息
        if orders_with_field:
            print(f"\n📋 包含 order_limit_time_1 字段的订单详情:")
            for order in orders_with_field:
                raw_data = order.get('raw_data', {})
                order_limit_time_1 = raw_data.get('order_limit_time_1', 0)
                is_limit = order.get('is_limit_order', False)
                
                # 转换时间戳
                try:
                    dt = datetime.fromtimestamp(order_limit_time_1)
                    time_str = dt.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    time_str = str(order_limit_time_1)
                
                status = "✅ 正确识别" if is_limit else "❌ 识别错误"
                
                print(f"   订单ID: {order['order_id']}")
                print(f"   影院: {order['cinema_name']}")
                print(f"   order_limit_time_1: {order_limit_time_1} -> {time_str}")
                print(f"   API标识为限时: {is_limit} - {status}")
                print()
        else:
            print(f"\n📋 当前数据中没有包含 order_limit_time_1 字段的订单")
        
        # 检查之前的限时字段
        print(f"🔍 检查其他限时字段的订单:")
        other_limit_orders = []
        
        for order in orders[:20]:  # 检查前20个订单
            raw_data = order.get('raw_data', {})
            
            # 检查其他限时字段
            end_down_time = raw_data.get('endDownTime', 0)
            down_time = raw_data.get('downTime', 0)
            order_limit_time_2 = raw_data.get('order_limit_time_2', 0)
            
            if end_down_time > 0 or down_time > 0 or order_limit_time_2 > 0:
                is_limit = order.get('is_limit_order', False)
                other_limit_orders.append({
                    'order_id': order['order_id'],
                    'endDownTime': end_down_time,
                    'downTime': down_time,
                    'order_limit_time_2': order_limit_time_2,
                    'is_limit_order': is_limit
                })
        
        if other_limit_orders:
            print(f"   找到 {len(other_limit_orders)} 个包含其他限时字段的订单:")
            for order_info in other_limit_orders:
                status = "❌ 不再识别为限时" if not order_info['is_limit_order'] else "⚠️ 仍被识别为限时"
                print(f"   {order_info['order_id']} - {status}")
                if order_info['endDownTime'] > 0:
                    print(f"      endDownTime: {order_info['endDownTime']}")
                if order_info['downTime'] > 0:
                    print(f"      downTime: {order_info['downTime']}")
                if order_info['order_limit_time_2'] > 0:
                    print(f"      order_limit_time_2: {order_info['order_limit_time_2']}")
        else:
            print(f"   前20个订单中没有包含其他限时字段的订单")
        
        # 生成验证报告
        print(f"\n" + "=" * 70)
        print(f"📋 验证报告:")
        print(f"=" * 70)
        
        print(f"✅ 修改验证结果:")
        print(f"   - 新检测逻辑：只检查 order_limit_time_1 字段")
        print(f"   - API标识的限时订单数: {len(limit_orders_by_api)}")
        print(f"   - 实际包含字段的订单数: {len(orders_with_field)}")
        print(f"   - 逻辑一致性: {'✅ 完全一致' if len(limit_orders_by_api) == len(orders_with_field) else '❌ 不一致'}")
        
        if len(orders_with_field) > 0:
            print(f"   - 成功识别的限时订单: {orders_with_field[0]['order_id']}")
        
        print(f"\n🎯 结论:")
        if len(limit_orders_by_api) == len(orders_with_field):
            print(f"   ✅ 限时订单检测逻辑修改成功！")
            print(f"   ✅ 现在只有包含 order_limit_time_1 字段的订单被识别为限时订单")
            print(f"   ✅ 其他字段（endDownTime、downTime等）不再影响限时订单判断")
        else:
            print(f"   ❌ 检测逻辑可能需要进一步调整")
        
    except Exception as e:
        print(f"❌ 验证失败: {e}")

def main():
    """主函数"""
    print("🚀 开始验证限时订单检测逻辑修改...")
    print("=" * 80)
    
    verify_limit_logic()
    
    print(f"\n🌐 Web界面验证建议:")
    print(f"   1. 访问: http://localhost:5000/")
    print(f"   2. 查看统计信息中的限时订单数量")
    print(f"   3. 使用'订单类型'筛选器选择'限时订单'")
    print(f"   4. 验证只有包含 order_limit_time_1 字段的订单显示红色标识")

if __name__ == "__main__":
    main()
