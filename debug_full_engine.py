#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
深度调试：完整模拟引擎的check_order逻辑
"""

import json
import sqlite3

def debug_full_check_order():
    """完整模拟check_order的执行流程"""
    
    conn = sqlite3.connect('orders.db')
    cursor = conn.cursor()
    
    # 加载所有启用的规则，按policy_order排序
    cursor.execute('SELECT * FROM policies WHERE is_enabled = 1 ORDER BY policy_order ASC')
    all_rules = cursor.fetchall()
    
    print(f"=== 加载了 {len(all_rules)} 个启用规则 ===\n")
    
    # 测试订单
    order = {
        'order_id': 'HH071223334138149',
        'bidding_price': 51.0,
        'seat_count': 2,
        'city': '深圳',
        'cinema_name': '万达影城（深圳龙岗万达广场IMAX激光店）',
        'hall_type': 'IMAX激光厅',
        'movie_name': 'F1：狂飙飞车'
    }
    
    print(f"测试订单: {order['order_id']}")
    print(f"影院: {order['cinema_name']}")
    print(f"厅型: \"{order['hall_type']}\"")
    print(f"竞价: {order['bidding_price']}, 票数: {order['seat_count']}")
    print()
    
    # 预处理订单数据
    order_city = order.get('city', '').lower().strip()
    order_cinema_name = order.get('cinema_name', '').lower().strip()
    order_hall_type = order.get('hall_type', '').lower().strip()
    order_bidding_price = order.get('bidding_price', 0)
    order_seat_count = order.get('seat_count', 1)
    
    # 遍历所有规则
    for rule_index, rule_row in enumerate(all_rules):
        rule_id = rule_row[0]
        rule_name = rule_row[1]
        
        print(f"\\n--- 检查规则 {rule_index + 1}: {rule_name} (ID: {rule_id[:8]}...) ---")
        
        # 解析规则配置
        try:
            config = json.loads(rule_row[4])
        except:
            print("❌ 配置解析失败，跳过")
            continue
        
        match_conditions = config.get('match_conditions', {})
        hall_logic = config.get('hall_logic', {})
        profit_logic = config.get('profit_logic', {})
        
        # 检查策略是否启用
        if not rule_row[5]:  # is_enabled
            print("❌ 策略未启用，跳过")
            continue
        
        print("✅ 策略已启用")
        
        # 1. 城市匹配
        rule_city = match_conditions.get('city', '').lower().strip()
        if rule_city and rule_city != order_city:
            print(f"❌ 城市不匹配: 规则要求'{rule_city}', 订单是'{order_city}'")
            continue
        print(f"✅ 城市匹配通过")
        
        # 2. 影院关键词匹配
        cinema_keywords = match_conditions.get('cinema_keywords', [])
        if cinema_keywords:
            keywords_matched = True
            for keyword in cinema_keywords:
                keyword_lower = keyword.lower().strip()
                if keyword_lower not in order_cinema_name:
                    keywords_matched = False
                    print(f"❌ 影院关键词不匹配: '{keyword}' 不在 '{order['cinema_name']}'")
                    break
            
            if not keywords_matched:
                continue
            print(f"✅ 影院关键词匹配: {cinema_keywords}")
        
        # 3. 厅型逻辑检查 - 关键部分
        hall_mode = hall_logic.get('mode', 'ALL').upper()
        hall_list = hall_logic.get('hall_list', [])
        hall_set = set(hall_list)  # 模拟引擎的预处理
        
        print(f"🎯 厅型逻辑: {hall_mode}, 列表: {hall_list}")
        
        # 重要：这里要完全按照引擎的逻辑执行
        if hall_mode == 'INCLUDE':
            print("   执行 INCLUDE 逻辑:")
            hall_matched = False
            for hall_type in hall_set:
                hall_type_lower = hall_type.lower().strip()
                if hall_type_lower in order_hall_type or order_hall_type in hall_type_lower:
                    hall_matched = True
                    print(f"   ✅ 匹配: '{hall_type}' <-> '{order['hall_type']}'")
                    break
                else:
                    print(f"   ❌ 不匹配: '{hall_type}' <-> '{order['hall_type']}'")
            
            if not hall_matched:
                print("   🚫 INCLUDE模式：无匹配厅型，跳过规则")
                continue
            else:
                print("   ✅ INCLUDE模式：厅型匹配成功")
        
        elif hall_mode == 'EXCLUDE':
            print("   执行 EXCLUDE 逻辑:")
            hall_matched = False  # 注意：这里重新定义了hall_matched
            for hall_type in hall_set:
                hall_type_lower = hall_type.lower().strip()
                print(f"     检查排除项: '{hall_type}' -> '{hall_type_lower}'")
                
                condition1 = hall_type_lower in order_hall_type
                condition2 = order_hall_type in hall_type_lower
                
                print(f"       '{hall_type_lower}' in '{order_hall_type}': {condition1}")
                print(f"       '{order_hall_type}' in '{hall_type_lower}': {condition2}")
                
                if condition1 or condition2:
                    hall_matched = True
                    print(f"       ✅ 匹配到排除项！")
                    break
            
            if hall_matched:
                print("   🚫 EXCLUDE模式：匹配到排除项，跳过规则")
                continue
            else:
                print("   ✅ EXCLUDE模式：未被排除，继续")
        
        else:
            print("   ✅ ALL模式：默认通过")
        
        # 4. 利润计算
        hall_cost = hall_logic.get('cost', 0)
        single_ticket_profit = order_bidding_price - hall_cost
        total_profit = single_ticket_profit * order_seat_count
        min_profit_threshold = profit_logic.get('min_profit_threshold', 0)
        
        print(f"💰 利润计算:")
        print(f"   竞价: {order_bidding_price}, 成本: {hall_cost}, 票数: {order_seat_count}")
        print(f"   单票利润: {single_ticket_profit}, 总利润: {total_profit}")
        print(f"   最低要求: {min_profit_threshold}")
        
        if total_profit >= min_profit_threshold:
            print(f"🎉 规则匹配成功！总利润 {total_profit} >= {min_profit_threshold}")
            print(f"匹配规则: {rule_name}")
            return {
                'rule_id': rule_id,
                'rule_name': rule_name,
                'total_profit': total_profit,
                'seat_count': order_seat_count
            }
        else:
            print(f"❌ 利润不达标: {total_profit} < {min_profit_threshold}")
            continue
    
    print("\\n❌ 没有任何规则匹配成功")
    return None

if __name__ == "__main__":
    result = debug_full_check_order()
    if result:
        print(f"\\n🔍 最终结果: {result}")
    else:
        print(f"\\n🔍 最终结果: 无匹配")