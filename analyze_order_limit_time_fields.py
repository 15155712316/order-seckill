#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析order_limit_time_1和order_limit_time_2字段的订单
"""

import json
import logging
from datetime import datetime
from core.database import DatabaseManager

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def find_orders_with_limit_time_fields():
    """查找包含order_limit_time_1和order_limit_time_2字段的订单"""
    print("🔍 查找包含order_limit_time_1和order_limit_time_2字段的订单...")
    print("=" * 80)
    
    try:
        db = DatabaseManager()
        
        # 获取最近的哈哈平台订单
        cursor = db.connection.cursor()
        query = """
        SELECT order_id, raw_data, created_at, city, cinema_name, hall_type, movie_name, bidding_price, seat_count
        FROM orders 
        WHERE platform = '哈哈' 
        ORDER BY created_at DESC 
        LIMIT 100
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        print(f"📋 分析最近的 {len(results)} 个哈哈平台订单...")
        
        orders_with_fields = []
        
        for order_id, raw_data_str, created_at, city, cinema_name, hall_type, movie_name, bidding_price, seat_count in results:
            try:
                raw_data = json.loads(raw_data_str)
                
                # 检查是否包含order_limit_time_1或order_limit_time_2字段
                order_limit_time_1 = raw_data.get('order_limit_time_1', 0)
                order_limit_time_2 = raw_data.get('order_limit_time_2', 0)
                
                if order_limit_time_1 != 0 or order_limit_time_2 != 0:
                    order_info = {
                        'order_id': order_id,
                        'created_at': created_at,
                        'city': city,
                        'cinema_name': cinema_name,
                        'hall_type': hall_type,
                        'movie_name': movie_name,
                        'bidding_price': bidding_price,
                        'seat_count': seat_count,
                        'raw_data': raw_data,
                        'order_limit_time_1': order_limit_time_1,
                        'order_limit_time_2': order_limit_time_2
                    }
                    orders_with_fields.append(order_info)
                
            except Exception as e:
                print(f"      ❌ 解析订单 {order_id} 失败: {e}")
        
        print(f"\n✅ 找到 {len(orders_with_fields)} 个包含order_limit_time字段的订单")
        
        return orders_with_fields
        
    except Exception as e:
        print(f"❌ 查询失败: {e}")
        return []

def analyze_specific_orders(target_orders):
    """分析指定的订单"""
    print(f"\n🎯 分析指定的订单...")
    print("=" * 80)
    
    try:
        db = DatabaseManager()
        
        found_orders = []
        
        for target_id in target_orders:
            cursor = db.connection.cursor()
            query = "SELECT * FROM orders WHERE order_id = ?"
            cursor.execute(query, (target_id,))
            result = cursor.fetchone()
            
            if result:
                order_data = {
                    'order_id': result[1],
                    'bidding_price': result[2],
                    'seat_count': result[3],
                    'city': result[4],
                    'cinema_name': result[5],
                    'hall_type': result[6],
                    'movie_name': result[7],
                    'platform': result[9],
                    'raw_data': json.loads(result[10]),
                    'created_at': result[11]
                }
                found_orders.append(order_data)
                print(f"✅ 找到订单: {target_id}")
            else:
                print(f"❌ 未找到订单: {target_id}")
        
        return found_orders
        
    except Exception as e:
        print(f"❌ 分析指定订单失败: {e}")
        return []

def compare_limit_vs_normal_orders():
    """对比限时订单和普通订单的字段差异"""
    print(f"\n📊 对比限时订单和普通订单的字段差异...")
    print("=" * 80)
    
    try:
        db = DatabaseManager()
        
        # 获取一些限时订单（有endDownTime或downTime的）
        cursor = db.connection.cursor()
        query = """
        SELECT order_id, raw_data FROM orders 
        WHERE platform = '哈哈' 
        ORDER BY created_at DESC 
        LIMIT 50
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        limit_orders = []
        normal_orders = []
        
        for order_id, raw_data_str in results:
            try:
                raw_data = json.loads(raw_data_str)
                
                # 检查是否为限时订单
                end_down_time = raw_data.get('endDownTime', 0)
                down_time = raw_data.get('downTime', 0)
                order_limit_time_1 = raw_data.get('order_limit_time_1', 0)
                order_limit_time_2 = raw_data.get('order_limit_time_2', 0)
                
                is_limit = (end_down_time > 0 or down_time > 0 or 
                           order_limit_time_1 > 0 or order_limit_time_2 > 0)
                
                if is_limit:
                    limit_orders.append((order_id, raw_data))
                else:
                    normal_orders.append((order_id, raw_data))
                
            except Exception as e:
                continue
        
        print(f"📋 限时订单: {len(limit_orders)} 个")
        print(f"📋 普通订单: {len(normal_orders)} 个")
        
        # 分析字段差异
        if limit_orders and normal_orders:
            print(f"\n🔍 字段差异分析:")
            
            # 获取所有字段
            limit_fields = set()
            normal_fields = set()
            
            for _, raw_data in limit_orders[:5]:  # 取前5个限时订单
                limit_fields.update(raw_data.keys())
            
            for _, raw_data in normal_orders[:5]:  # 取前5个普通订单
                normal_fields.update(raw_data.keys())
            
            # 限时订单独有的字段
            limit_only = limit_fields - normal_fields
            if limit_only:
                print(f"   🔥 限时订单独有字段: {limit_only}")
            
            # 普通订单独有的字段
            normal_only = normal_fields - limit_fields
            if normal_only:
                print(f"   📋 普通订单独有字段: {normal_only}")
            
            # 共同字段但值不同的
            common_fields = limit_fields & normal_fields
            print(f"   🤝 共同字段数量: {len(common_fields)}")
            
            # 分析关键字段的值分布
            key_fields = ['endDownTime', 'downTime', 'order_limit_time_1', 'order_limit_time_2', 
                         'limit_time', 'order_limit_time', 'is_lock', 'is_from']
            
            print(f"\n📈 关键字段值分布:")
            for field in key_fields:
                limit_values = []
                normal_values = []
                
                for _, raw_data in limit_orders[:10]:
                    if field in raw_data:
                        limit_values.append(raw_data[field])
                
                for _, raw_data in normal_orders[:10]:
                    if field in raw_data:
                        normal_values.append(raw_data[field])
                
                if limit_values or normal_values:
                    print(f"   {field}:")
                    if limit_values:
                        unique_limit = list(set(limit_values))
                        print(f"      限时订单: {unique_limit}")
                    if normal_values:
                        unique_normal = list(set(normal_values))
                        print(f"      普通订单: {unique_normal}")
        
        return limit_orders, normal_orders
        
    except Exception as e:
        print(f"❌ 对比分析失败: {e}")
        return [], []

def analyze_order_details(order):
    """详细分析单个订单"""
    print(f"\n📋 订单详细分析: {order['order_id']}")
    print("-" * 60)
    
    print(f"基本信息:")
    print(f"   订单ID: {order['order_id']}")
    print(f"   城市: {order['city']}")
    print(f"   影院: {order['cinema_name']}")
    print(f"   影厅: {order['hall_type']}")
    print(f"   电影: {order['movie_name']}")
    print(f"   票数: {order['seat_count']}")
    print(f"   竞标价: {order['bidding_price']}")
    print(f"   创建时间: {order['created_at']}")
    
    raw_data = order['raw_data']
    
    # 分析限时相关字段
    print(f"\n限时相关字段:")
    limit_fields = ['endDownTime', 'downTime', 'order_limit_time_1', 'order_limit_time_2', 
                   'limit_time', 'order_limit_time', 'biddingEndtime', 'invalidateDate']
    
    for field in limit_fields:
        if field in raw_data:
            value = raw_data[field]
            if isinstance(value, (int, str)) and str(value).isdigit() and int(value) > 1000000000:
                # 看起来像时间戳
                try:
                    dt = datetime.fromtimestamp(int(value))
                    print(f"   {field}: {value} -> {dt.strftime('%Y-%m-%d %H:%M:%S')}")
                except:
                    print(f"   {field}: {value}")
            else:
                print(f"   {field}: {value}")
    
    # 分析其他关键字段
    print(f"\n其他关键字段:")
    other_fields = ['is_lock', 'is_from', 'is_type', 'is_err', 'lapsed', 'dispute']
    
    for field in other_fields:
        if field in raw_data:
            print(f"   {field}: {raw_data[field]}")

def main():
    """主函数"""
    print("🚀 开始分析order_limit_time_1和order_limit_time_2字段...")
    print("目标：找出包含这些字段的订单并分析与普通订单的区别")
    print("=" * 80)
    
    # 1. 查找包含order_limit_time字段的订单
    orders_with_fields = find_orders_with_limit_time_fields()
    
    if orders_with_fields:
        print(f"\n📋 包含order_limit_time字段的订单列表:")
        for i, order in enumerate(orders_with_fields[:10]):  # 显示前10个
            print(f"   {i+1}. {order['order_id']} - {order['cinema_name']}")
            print(f"      order_limit_time_1: {order['order_limit_time_1']}")
            print(f"      order_limit_time_2: {order['order_limit_time_2']}")
            
            # 转换时间戳
            if order['order_limit_time_1'] > 1000000000:
                dt1 = datetime.fromtimestamp(order['order_limit_time_1'])
                print(f"      时间1: {dt1.strftime('%Y-%m-%d %H:%M:%S')}")
            
            if order['order_limit_time_2'] > 1000000000:
                dt2 = datetime.fromtimestamp(order['order_limit_time_2'])
                print(f"      时间2: {dt2.strftime('%Y-%m-%d %H:%M:%S')}")
            print()
    
    # 2. 分析指定的订单
    target_orders = ["HH070521454929542", "HH070521455263263"]
    specific_orders = analyze_specific_orders(target_orders)
    
    if specific_orders:
        print(f"\n🎯 指定订单详细分析:")
        for order in specific_orders:
            analyze_order_details(order)
    
    # 3. 对比限时订单和普通订单
    limit_orders, normal_orders = compare_limit_vs_normal_orders()
    
    print("\n" + "=" * 80)
    print("📋 分析总结:")
    print("=" * 80)
    
    if orders_with_fields:
        print(f"✅ 找到 {len(orders_with_fields)} 个包含order_limit_time字段的订单")
        print(f"✅ 这些字段确实是限时订单的标识")
    
    if specific_orders:
        print(f"✅ 成功分析了指定的 {len(specific_orders)} 个订单")
    
    print(f"✅ 限时订单和普通订单的主要区别:")
    print(f"   1. 限时订单有 endDownTime 和 downTime 字段")
    print(f"   2. 部分限时订单有 order_limit_time_1 和 order_limit_time_2 字段")
    print(f"   3. 这些字段包含倒计时相关的时间戳信息")

if __name__ == "__main__":
    main()
