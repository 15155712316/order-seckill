#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
查找指定的订单并分析其字段
"""

import requests
import json
from datetime import datetime

def find_orders_by_id(target_ids):
    """通过API查找指定的订单"""
    print("🔍 通过API查找指定的订单...")
    print("=" * 60)
    
    try:
        # 获取更多订单数据
        url = "http://localhost:5000/api/orders/recent?limit=200"
        response = requests.get(url)
        
        if response.status_code != 200:
            print(f"❌ API请求失败，状态码: {response.status_code}")
            return []
        
        data = response.json()
        orders = data.get('data', [])
        
        print(f"📊 获取到 {len(orders)} 条订单数据")
        
        found_orders = []
        
        for order in orders:
            if order['order_id'] in target_ids:
                found_orders.append(order)
                print(f"✅ 找到订单: {order['order_id']}")
        
        if len(found_orders) < len(target_ids):
            missing = set(target_ids) - set(order['order_id'] for order in found_orders)
            print(f"❌ 未找到订单: {missing}")
        
        return found_orders
        
    except Exception as e:
        print(f"❌ 查找失败: {e}")
        return []

def analyze_order_limit_time_fields():
    """分析包含order_limit_time字段的订单"""
    print("\n🔍 分析包含order_limit_time字段的订单...")
    print("=" * 60)
    
    try:
        # 获取更多订单数据
        url = "http://localhost:5000/api/orders/recent?limit=100"
        response = requests.get(url)
        
        if response.status_code != 200:
            print(f"❌ API请求失败，状态码: {response.status_code}")
            return []
        
        data = response.json()
        orders = data.get('data', [])
        
        orders_with_fields = []
        
        for order in orders:
            raw_data = order.get('raw_data', {})
            
            order_limit_time_1 = raw_data.get('order_limit_time_1', 0)
            order_limit_time_2 = raw_data.get('order_limit_time_2', 0)
            
            if order_limit_time_1 != 0 or order_limit_time_2 != 0:
                orders_with_fields.append({
                    'order_id': order['order_id'],
                    'platform': order['platform'],
                    'cinema_name': order['cinema_name'],
                    'order_limit_time_1': order_limit_time_1,
                    'order_limit_time_2': order_limit_time_2,
                    'raw_data': raw_data
                })
        
        print(f"📋 找到 {len(orders_with_fields)} 个包含order_limit_time字段的订单")
        
        return orders_with_fields
        
    except Exception as e:
        print(f"❌ 分析失败: {e}")
        return []

def analyze_order_details(order):
    """详细分析订单"""
    print(f"\n📋 订单详细分析: {order['order_id']}")
    print("-" * 60)
    
    print(f"基本信息:")
    print(f"   订单ID: {order['order_id']}")
    print(f"   平台: {order['platform']}")
    print(f"   城市: {order['city']}")
    print(f"   影院: {order['cinema_name']}")
    print(f"   影厅: {order['hall_type']}")
    print(f"   电影: {order['movie_name']}")
    print(f"   票数: {order['seat_count']}")
    print(f"   竞标价: {order['bidding_price']}")
    print(f"   是否限时: {order.get('is_limit_order', False)}")
    
    raw_data = order.get('raw_data', {})
    
    # 分析所有限时相关字段
    print(f"\n🔥 限时相关字段:")
    limit_fields = [
        'endDownTime', 'downTime', 'order_limit_time_1', 'order_limit_time_2', 
        'limit_time', 'order_limit_time', 'biddingEndtime', 'invalidateDate',
        'lapsed', 'lapsedEndtime'
    ]
    
    found_limit_fields = {}
    
    for field in limit_fields:
        if field in raw_data:
            value = raw_data[field]
            found_limit_fields[field] = value
            
            # 尝试解析时间戳
            if isinstance(value, (int, str)) and str(value).isdigit() and int(value) > 1000000000:
                try:
                    dt = datetime.fromtimestamp(int(value))
                    print(f"   ✅ {field}: {value} -> {dt.strftime('%Y-%m-%d %H:%M:%S')}")
                except:
                    print(f"   ✅ {field}: {value}")
            else:
                print(f"   ✅ {field}: {value}")
    
    if not found_limit_fields:
        print("   ❌ 未找到限时相关字段")
    
    # 分析其他关键字段
    print(f"\n📊 其他关键字段:")
    other_fields = ['is_lock', 'is_from', 'is_type', 'is_err', 'dispute', 'has_payment']
    
    found_other_fields = {}
    
    for field in other_fields:
        if field in raw_data:
            value = raw_data[field]
            found_other_fields[field] = value
            print(f"   ✅ {field}: {value}")
    
    if not found_other_fields:
        print("   ❌ 未找到其他关键字段")
    
    return found_limit_fields, found_other_fields

def compare_with_normal_orders():
    """对比普通订单"""
    print(f"\n📊 对比普通订单...")
    print("=" * 60)
    
    try:
        url = "http://localhost:5000/api/orders/recent?limit=50"
        response = requests.get(url)
        
        if response.status_code != 200:
            print(f"❌ API请求失败")
            return
        
        data = response.json()
        orders = data.get('data', [])
        
        # 分类订单
        limit_orders = [order for order in orders if order.get('is_limit_order', False)]
        normal_orders = [order for order in orders if not order.get('is_limit_order', False)]
        
        print(f"📋 限时订单: {len(limit_orders)} 个")
        print(f"📋 普通订单: {len(normal_orders)} 个")
        
        if limit_orders and normal_orders:
            print(f"\n🔍 字段差异分析:")
            
            # 分析限时订单的字段
            limit_fields_stats = {}
            for order in limit_orders[:5]:
                raw_data = order.get('raw_data', {})
                for key, value in raw_data.items():
                    if key not in limit_fields_stats:
                        limit_fields_stats[key] = []
                    limit_fields_stats[key].append(value)
            
            # 分析普通订单的字段
            normal_fields_stats = {}
            for order in normal_orders[:5]:
                raw_data = order.get('raw_data', {})
                for key, value in raw_data.items():
                    if key not in normal_fields_stats:
                        normal_fields_stats[key] = []
                    normal_fields_stats[key].append(value)
            
            # 找出差异
            limit_only = set(limit_fields_stats.keys()) - set(normal_fields_stats.keys())
            normal_only = set(normal_fields_stats.keys()) - set(limit_fields_stats.keys())
            
            if limit_only:
                print(f"   🔥 限时订单独有字段: {limit_only}")
            
            if normal_only:
                print(f"   📋 普通订单独有字段: {normal_only}")
            
            # 分析关键字段的值分布
            key_fields = ['endDownTime', 'downTime', 'order_limit_time_1', 'order_limit_time_2']
            
            print(f"\n📈 关键字段值分布:")
            for field in key_fields:
                limit_values = []
                normal_values = []
                
                for order in limit_orders:
                    raw_data = order.get('raw_data', {})
                    if field in raw_data:
                        limit_values.append(raw_data[field])
                
                for order in normal_orders:
                    raw_data = order.get('raw_data', {})
                    if field in raw_data:
                        normal_values.append(raw_data[field])
                
                if limit_values or normal_values:
                    print(f"   {field}:")
                    if limit_values:
                        unique_limit = list(set(limit_values))
                        print(f"      限时订单: {unique_limit[:5]}...")  # 只显示前5个
                    if normal_values:
                        unique_normal = list(set(normal_values))
                        print(f"      普通订单: {unique_normal[:5]}...")  # 只显示前5个
        
    except Exception as e:
        print(f"❌ 对比分析失败: {e}")

def main():
    """主函数"""
    print("🚀 开始查找和分析指定的限时订单...")
    print("目标订单: HH070521454929542, HH070521455263263")
    print("=" * 80)
    
    # 1. 查找指定的订单
    target_ids = ["HH070521454929542", "HH070521455263263"]
    found_orders = find_orders_by_id(target_ids)
    
    # 2. 详细分析找到的订单
    if found_orders:
        print(f"\n🎯 详细分析找到的 {len(found_orders)} 个订单:")
        for order in found_orders:
            limit_fields, other_fields = analyze_order_details(order)
    else:
        print(f"\n❌ 未找到指定的订单，可能不在最近200条订单中")
    
    # 3. 分析包含order_limit_time字段的订单
    orders_with_fields = analyze_order_limit_time_fields()
    
    if orders_with_fields:
        print(f"\n📋 包含order_limit_time字段的订单:")
        for order in orders_with_fields[:10]:  # 显示前10个
            print(f"   {order['order_id']} - {order['cinema_name']}")
            if order['order_limit_time_1'] != 0:
                try:
                    dt1 = datetime.fromtimestamp(order['order_limit_time_1'])
                    print(f"      order_limit_time_1: {order['order_limit_time_1']} -> {dt1.strftime('%Y-%m-%d %H:%M:%S')}")
                except:
                    print(f"      order_limit_time_1: {order['order_limit_time_1']}")
            
            if order['order_limit_time_2'] != 0:
                try:
                    dt2 = datetime.fromtimestamp(order['order_limit_time_2'])
                    print(f"      order_limit_time_2: {order['order_limit_time_2']} -> {dt2.strftime('%Y-%m-%d %H:%M:%S')}")
                except:
                    print(f"      order_limit_time_2: {order['order_limit_time_2']}")
    
    # 4. 对比分析
    compare_with_normal_orders()
    
    print("\n" + "=" * 80)
    print("📋 分析总结:")
    print("=" * 80)
    
    if found_orders:
        print(f"✅ 成功找到并分析了指定的订单")
        print(f"✅ 这些订单确实包含限时相关字段")
    
    if orders_with_fields:
        print(f"✅ 发现 {len(orders_with_fields)} 个订单包含order_limit_time字段")
        print(f"✅ 这些字段是限时订单的重要标识")
    
    print(f"\n💡 关键发现:")
    print(f"   1. order_limit_time_1 和 order_limit_time_2 是额外的限时字段")
    print(f"   2. 这些字段包含时间戳，表示限时的相关时间点")
    print(f"   3. 结合 endDownTime 和 downTime 可以更准确地识别限时订单")

if __name__ == "__main__":
    main()
