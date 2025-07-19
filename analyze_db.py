#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化的芒果平台调试脚本 - 只分析配置和数据结构
"""

import sys
import os
import json
import sqlite3

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def analyze_database():
    """分析数据库中的策略配置"""
    
    print("=" * 80)
    print("芒果平台规则匹配分析")
    print("=" * 80)
    
    db_path = "orders.db"
    if not os.path.exists(db_path):
        print("❌ 数据库文件不存在")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. 查看启用的策略
        print("\n1. 查看启用的策略...")
        cursor.execute("SELECT rule_id, rule_name, enabled, match_conditions, hall_logic, profit_logic FROM strategies WHERE enabled = 1")
        strategies = cursor.fetchall()
        
        print(f"✅ 找到 {len(strategies)} 个启用的策略:")
        
        for strategy in strategies:
            rule_id, rule_name, enabled, match_conditions_str, hall_logic_str, profit_logic_str = strategy
            
            try:
                match_conditions = json.loads(match_conditions_str) if match_conditions_str else {}
                hall_logic = json.loads(hall_logic_str) if hall_logic_str else {}
                profit_logic = json.loads(profit_logic_str) if profit_logic_str else {}
                
                print(f"\n--- 策略: {rule_name} (ID: {rule_id}) ---")
                print(f"启用状态: {enabled}")
                
                # 匹配条件
                print("匹配条件:")
                city = match_conditions.get('city', '')
                match_mode = match_conditions.get('match_mode', 'keywords')
                print(f"  城市: '{city}' (空表示任意城市)")
                print(f"  匹配模式: {match_mode}")
                
                if match_mode == 'keywords':
                    keywords = match_conditions.get('cinema_keywords', [])
                    print(f"  影院关键词: {keywords}")
                else:
                    print(f"  白名单策略")
                    # 查询白名单影院数量
                    cursor.execute("SELECT COUNT(*) FROM whitelist_cinemas WHERE policy_id = ?", (rule_id,))
                    cinema_count = cursor.fetchone()[0]
                    print(f"  白名单影院数量: {cinema_count}")
                
                # 影厅逻辑
                print("影厅逻辑:")
                hall_mode = hall_logic.get('mode', 'ALL')
                hall_cost = hall_logic.get('cost', 0)
                hall_list = hall_logic.get('hall_list', [])
                print(f"  模式: {hall_mode}")
                print(f"  成本: {hall_cost}")
                print(f"  影厅列表: {hall_list}")
                
                # 利润逻辑
                print("利润逻辑:")
                min_profit = profit_logic.get('min_profit_threshold', 0)
                print(f"  最低利润阈值: {min_profit}")
                
            except json.JSONDecodeError as e:
                print(f"❌ 策略 {rule_name} 的JSON数据解析失败: {e}")
        
        # 2. 查看芒果平台配置
        print("\n2. 查看芒果平台配置...")
        cursor.execute("SELECT setting_key, setting_value FROM settings WHERE setting_key LIKE '%mango%'")
        mango_settings = cursor.fetchall()
        
        if mango_settings:
            print("芒果平台配置:")
            for key, value in mango_settings:
                if 'token' in key.lower():
                    print(f"  {key}: {value[:10] if value else 'None'}...")
                else:
                    print(f"  {key}: {value}")
        else:
            print("❌ 未找到芒果平台配置")
        
        # 3. 分析最近的匹配记录
        print("\n3. 分析最近的匹配记录...")
        cursor.execute("""
            SELECT platform_name, rule_name, rule_type, match_result, 
                   order_data, match_details, profit_calculation, created_at 
            FROM match_records 
            WHERE platform_name = '芒果' 
            ORDER BY created_at DESC 
            LIMIT 5
        """)
        match_records = cursor.fetchall()
        
        if match_records:
            print(f"找到 {len(match_records)} 条芒果平台匹配记录:")
            for record in match_records:
                platform, rule_name, rule_type, result, order_data_str, match_details_str, profit_calc_str, created_at = record
                print(f"\n--- 匹配记录 ({created_at}) ---")
                print(f"策略: {rule_name} ({rule_type})")
                print(f"结果: {result}")
                
                try:
                    if order_data_str:
                        order_data = json.loads(order_data_str)
                        print(f"订单信息:")
                        print(f"  城市: '{order_data.get('city', 'N/A')}'")
                        print(f"  影院: '{order_data.get('cinema_name', 'N/A')}'")
                        print(f"  影厅: '{order_data.get('hall_type', 'N/A')}'")
                        print(f"  电影: '{order_data.get('movie_name', 'N/A')}'")
                        print(f"  价格: {order_data.get('bidding_price', 'N/A')}")
                        print(f"  座位: {order_data.get('seat_count', 'N/A')}")
                    
                    if profit_calc_str:
                        profit_calc = json.loads(profit_calc_str)
                        print(f"利润计算: {profit_calc.get('calculation_formula', 'N/A')}")
                        
                except json.JSONDecodeError:
                    print("  数据解析失败")
        else:
            print("❌ 未找到芒果平台的匹配记录")
        
        conn.close()
        
        print("\n" + "=" * 80)
        print("分析完成")
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ 数据库分析失败: {e}")

if __name__ == "__main__":
    analyze_database()