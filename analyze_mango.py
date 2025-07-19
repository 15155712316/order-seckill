#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
芒果平台匹配问题详细分析脚本
"""

import sqlite3
import json
import os
from datetime import datetime, timedelta

def analyze_mango_matching():
    """分析芒果平台匹配问题"""
    
    print("=" * 80)
    print("芒果平台订单匹配问题详细分析")
    print("=" * 80)
    
    db_path = "orders.db"
    if not os.path.exists(db_path):
        print("❌ 数据库文件不存在")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. 查看启用的策略
        print("\n1. 分析启用的策略配置...")
        cursor.execute("SELECT id, name, type, config, is_enabled FROM policies WHERE is_enabled = 1")
        policies = cursor.fetchall()
        
        print(f"✅ 找到 {len(policies)} 个启用的策略:")
        
        active_policies = []
        for policy in policies:
            policy_id, name, policy_type, config_str, enabled = policy
            
            try:
                config = json.loads(config_str) if config_str else {}
                active_policies.append({
                    'id': policy_id,
                    'name': name,
                    'type': policy_type,
                    'config': config
                })
                
                print(f"\n--- 策略: {name} ---")
                print(f"类型: {policy_type}")
                
                # 匹配条件分析
                match_conditions = config.get('match_conditions', {})
                city = match_conditions.get('city', '')
                print(f"城市要求: '{city}' (空表示任意)")
                
                if policy_type == 'keywords':
                    keywords = match_conditions.get('cinema_keywords', [])
                    print(f"影院关键词: {keywords}")
                elif policy_type == 'whitelist':
                    # 查询白名单影院
                    cursor.execute("SELECT COUNT(*) FROM whitelist_cinemas WHERE policy_id = ?", (policy_id,))
                    cinema_count = cursor.fetchone()[0]
                    print(f"白名单影院数量: {cinema_count}")
                
                # 影厅和利润要求
                hall_logic = config.get('hall_logic', {})
                profit_logic = config.get('profit_logic', {})
                print(f"影厅模式: {hall_logic.get('mode', 'ALL')}")
                print(f"影厅成本: {hall_logic.get('cost', 0)}")
                print(f"最低利润: {profit_logic.get('min_profit_threshold', 0)}")
                
            except json.JSONDecodeError as e:
                print(f"❌ 策略 {name} 配置解析失败: {e}")
        
        # 2. 分析芒果平台最近的订单
        print("\n2. 分析芒果平台最近的订单...")
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        cursor.execute("""
            SELECT order_id, city, cinema_name, hall_type, movie_name, 
                   bidding_price, seat_count, raw_data, created_at
            FROM orders 
            WHERE platform = '芒果' AND created_at >= ? 
            ORDER BY created_at DESC 
            LIMIT 10
        """, (yesterday,))
        
        mango_orders = cursor.fetchall()
        print(f"✅ 找到芒果平台最近 {len(mango_orders)} 条订单:")
        
        if not mango_orders:
            print("❌ 没有找到芒果平台的订单数据")
            conn.close()
            return
        
        # 分析订单字段
        print("\n3. 分析订单字段质量...")
        field_stats = {
            'empty_city': 0,
            'empty_cinema': 0,
            'empty_hall': 0,
            'empty_movie': 0,
            'zero_price': 0,
            'zero_seats': 0
        }
        
        for order in mango_orders[:5]:  # 分析前5个订单
            order_id, city, cinema_name, hall_type, movie_name, bidding_price, seat_count, raw_data_str, created_at = order
            
            print(f"\n--- 订单: {order_id} ({created_at}) ---")
            print(f"城市: '{city}' {'(空)' if not city else ''}")
            print(f"影院: '{cinema_name}' {'(空)' if not cinema_name else ''}")
            print(f"影厅: '{hall_type}' {'(空)' if not hall_type else ''}")
            print(f"电影: '{movie_name}' {'(空)' if not movie_name else ''}")
            print(f"价格: {bidding_price}")
            print(f"座位: {seat_count}")
            
            # 统计空字段
            if not city: field_stats['empty_city'] += 1
            if not cinema_name: field_stats['empty_cinema'] += 1
            if not hall_type: field_stats['empty_hall'] += 1
            if not movie_name: field_stats['empty_movie'] += 1
            if bidding_price <= 0: field_stats['zero_price'] += 1
            if seat_count <= 0: field_stats['zero_seats'] += 1
            
            # 分析原始数据
            if raw_data_str:
                try:
                    raw_data = json.loads(raw_data_str)
                    print("原始数据字段:")
                    print(f"  city_name: '{raw_data.get('city_name', 'N/A')}'")
                    print(f"  cinema_name: '{raw_data.get('cinema_name', 'N/A')}'")
                    print(f"  hall_name: '{raw_data.get('hall_name', 'N/A')}'")
                    print(f"  film_name: '{raw_data.get('film_name', 'N/A')}'")
                    print(f"  point_sec_kill_price: {raw_data.get('point_sec_kill_price', 'N/A')}")
                    print(f"  maoyan_price: {raw_data.get('maoyan_price', 'N/A')}")
                    print(f"  ticket_num: {raw_data.get('ticket_num', 'N/A')}")
                except:
                    print("  原始数据解析失败")
        
        print(f"\n字段质量统计 (总计{len(mango_orders)}条订单):")
        print(f"  空城市: {field_stats['empty_city']}")
        print(f"  空影院: {field_stats['empty_cinema']}")
        print(f"  空影厅: {field_stats['empty_hall']}")
        print(f"  空电影: {field_stats['empty_movie']}")
        print(f"  零价格: {field_stats['zero_price']}")
        print(f"  零座位: {field_stats['zero_seats']}")
        
        # 4. 手动匹配测试
        print("\n4. 手动匹配测试...")
        if mango_orders and active_policies:
            test_order = mango_orders[0]  # 使用最新的订单
            order_id, city, cinema_name, hall_type, movie_name, bidding_price, seat_count, _, _ = test_order
            
            print(f"测试订单: {order_id}")
            print(f"  城市: '{city}'")
            print(f"  影院: '{cinema_name}'")
            print(f"  影厅: '{hall_type}'")
            print(f"  价格: {bidding_price}")
            print(f"  座位: {seat_count}")
            
            # 针对每个策略进行匹配测试
            for policy in active_policies:
                policy_name = policy['name']
                config = policy['config']
                
                print(f"\n  测试策略: {policy_name}")
                
                # 城市匹配
                match_conditions = config.get('match_conditions', {})
                required_cities = match_conditions.get('city', '').split(',')
                required_cities = [c.strip() for c in required_cities if c.strip()]
                
                city_match = not required_cities or city in required_cities
                print(f"    城市匹配: {city_match} (要求: {required_cities}, 订单: '{city}')")
                
                if not city_match:
                    print(f"    ❌ 城市不匹配，跳过")
                    continue
                
                # 关键词匹配
                if policy['type'] == 'keywords':
                    keywords = match_conditions.get('cinema_keywords', [])
                    if keywords:
                        cinema_lower = cinema_name.lower()
                        keyword_matches = []
                        for keyword in keywords:
                            if keyword.lower() in cinema_lower:
                                keyword_matches.append(keyword)
                        
                        keyword_match = len(keyword_matches) == len(keywords)
                        print(f"    关键词匹配: {keyword_match}")
                        print(f"      要求所有: {keywords}")
                        print(f"      匹配的: {keyword_matches}")
                        
                        if not keyword_match:
                            print(f"    ❌ 关键词不匹配，跳过")
                            continue
                
                # 利润计算
                hall_logic = config.get('hall_logic', {})
                profit_logic = config.get('profit_logic', {})
                
                hall_cost = hall_logic.get('cost', 0)
                min_profit = profit_logic.get('min_profit_threshold', 0)
                
                single_profit = bidding_price - hall_cost
                total_profit = single_profit * seat_count
                
                profit_match = total_profit >= min_profit
                print(f"    利润计算:")
                print(f"      单票利润: {bidding_price} - {hall_cost} = {single_profit}")
                print(f"      总利润: {single_profit} × {seat_count} = {total_profit}")
                print(f"      要求最低: {min_profit}")
                print(f"      利润匹配: {profit_match}")
                
                if profit_match:
                    print(f"    ✅ 策略 {policy_name} 匹配成功!")
                else:
                    print(f"    ❌ 利润不足，跳过")
        
        # 5. 查看匹配记录
        print("\n5. 查看芒果平台匹配记录...")
        cursor.execute("""
            SELECT rule_name, match_result, order_data, created_at
            FROM match_records 
            WHERE platform_name = '芒果' 
            ORDER BY created_at DESC 
            LIMIT 5
        """)
        match_records = cursor.fetchall()
        
        if match_records:
            print(f"最近 {len(match_records)} 条匹配记录:")
            for record in match_records:
                rule_name, result, order_data_str, created_at = record
                print(f"  {created_at}: {rule_name} -> {result}")
        else:
            print("❌ 没有找到芒果平台的匹配记录")
        
        conn.close()
        
        print("\n" + "=" * 80)
        print("分析完成")
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ 分析失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    analyze_mango_matching()