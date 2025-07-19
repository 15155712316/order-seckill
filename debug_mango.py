#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
芒果平台调试脚本 - 分析字段映射和规则匹配问题
"""

import sys
import os
import json
import asyncio
import logging

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.platforms.mango_adapter import MangoAdapter
from core.engine import RuleEngine
from core.database import DatabaseManager

# 配置日志
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

async def debug_mango_platform():
    """调试芒果平台的数据处理和规则匹配"""
    
    print("=" * 80)
    print("芒果平台数据分析调试脚本")
    print("=" * 80)
    
    # 1. 初始化数据库管理器
    db_manager = DatabaseManager()
    
    # 2. 获取芒果平台配置
    print("\n1. 获取芒果平台配置...")
    settings = db_manager.load_settings()
    mango_config = {
        'user_token': settings.get('mango_user_token', ''),
        'api_url': 'https://supplier.mgmovie.net/v2/api/67d77db66adac'
    }
    
    if not mango_config['user_token']:
        print("❌ 芒果平台Token未配置，无法进行调试")
        return
    
    print(f"✅ 芒果平台配置: API_URL={mango_config['api_url']}")
    print(f"✅ Token已配置: {mango_config['user_token'][:10]}...")
    
    # 3. 初始化芒果适配器
    print("\n2. 初始化芒果适配器...")
    mango_adapter = MangoAdapter("芒果", mango_config)
    
    # 4. 获取芒果平台订单数据
    print("\n3. 获取芒果平台订单数据...")
    try:
        result = await mango_adapter.fetch_and_process()
        
        if result['success']:
            orders = result['orders']
            print(f"✅ 成功获取 {len(orders)} 条订单")
            
            # 分析前3个订单的字段结构
            if orders:
                print("\n4. 分析订单字段结构（前3个订单）...")
                for i, order in enumerate(orders[:3]):
                    print(f"\n--- 订单 {i+1} ---")
                    print(f"order_id: {order['order_id']}")
                    print(f"city: '{order['city']}'")
                    print(f"cinema_name: '{order['cinema_name']}'")
                    print(f"hall_type: '{order['hall_type']}'")
                    print(f"movie_name: '{order['movie_name']}'")
                    print(f"show_time: '{order['show_time']}'")
                    print(f"bidding_price: {order['bidding_price']}")
                    print(f"original_price: {order['original_price']}")
                    print(f"seat_count: {order['seat_count']}")
                    
                    # 显示原始数据的关键字段
                    raw_data = order['raw_data']
                    print(f"\n原始数据关键字段:")
                    print(f"  city_name: '{raw_data.get('city_name', 'N/A')}'")
                    print(f"  cinema_name: '{raw_data.get('cinema_name', 'N/A')}'")
                    print(f"  hall_name: '{raw_data.get('hall_name', 'N/A')}'")
                    print(f"  film_name: '{raw_data.get('film_name', 'N/A')}'")
                    print(f"  show_time: '{raw_data.get('show_time', 'N/A')}'")
                    print(f"  point_sec_kill_price: {raw_data.get('point_sec_kill_price', 'N/A')}")
                    print(f"  maoyan_price: {raw_data.get('maoyan_price', 'N/A')}")
                    print(f"  ticket_num: {raw_data.get('ticket_num', 'N/A')}")
                    
        else:
            print(f"❌ 获取芒果平台订单失败: {result.get('error', '未知错误')}")
            return
            
    except Exception as e:
        print(f"❌ 芒果平台请求异常: {e}")
        return
    
    # 5. 分析规则引擎
    print("\n5. 分析规则引擎配置...")
    rule_engine = RuleEngine(db_manager=db_manager)
    
    # 获取启用的策略
    enabled_rules = [rule for rule in rule_engine.rules if rule.get('enabled', False)]
    print(f"✅ 找到 {len(enabled_rules)} 个启用的策略")
    
    if not enabled_rules:
        print("❌ 没有启用的策略，无法进行匹配测试")
        return
    
    # 显示策略信息
    for i, rule in enumerate(enabled_rules[:3]):
        print(f"\n--- 策略 {i+1}: {rule.get('rule_name', '未命名')} ---")
        match_conditions = rule.get('match_conditions', {})
        print(f"城市: '{match_conditions.get('city', '任意')}'")
        print(f"匹配模式: {match_conditions.get('match_mode', 'keywords')}")
        
        if match_conditions.get('match_mode') == 'keywords':
            keywords = match_conditions.get('cinema_keywords', [])
            print(f"影院关键词: {keywords}")
        else:
            print(f"白名单策略ID: {rule.get('rule_id')}")
            cinema_count = rule_engine.get_whitelist_cinema_count(rule.get('rule_id', ''))
            print(f"白名单影院数量: {cinema_count}")
            
        hall_logic = rule.get('hall_logic', {})
        print(f"影厅模式: {hall_logic.get('mode', 'ALL')}")
        print(f"影厅成本: {hall_logic.get('cost', 0)}")
        
        profit_logic = rule.get('profit_logic', {})
        print(f"最低利润阈值: {profit_logic.get('min_profit_threshold', 0)}")
    
    # 6. 测试规则匹配
    print("\n6. 测试规则匹配...")
    if orders:
        matched_count = 0
        for i, order in enumerate(orders[:5]):  # 测试前5个订单
            print(f"\n--- 测试订单 {i+1} ---")
            print(f"城市: '{order['city']}', 影院: '{order['cinema_name']}', 影厅: '{order['hall_type']}'")
            print(f"电影: '{order['movie_name']}', 价格: {order['bidding_price']}, 座位: {order['seat_count']}")
            
            # 尝试匹配规则
            match_result = rule_engine.check_order(order, "芒果")
            
            if match_result:
                matched_count += 1
                print(f"✅ 匹配成功! 策略: {match_result['rule_name']}, 利润: {match_result['total_profit']}")
            else:
                print(f"❌ 未匹配任何规则")
                
                # 详细分析为什么不匹配
                print("  分析不匹配原因:")
                for rule in enabled_rules:
                    match_conditions = rule.get('match_conditions', {})
                    
                    # 检查城市
                    rule_city = match_conditions.get('city', '').lower().strip()
                    order_city = order['city'].lower().strip()
                    if rule_city and rule_city != order_city:
                        print(f"    策略'{rule['rule_name']}': 城市不匹配 (规则要求'{rule_city}' vs 订单'{order_city}')")
                        continue
                    
                    # 检查关键词匹配
                    if match_conditions.get('match_mode') == 'keywords':
                        keywords = match_conditions.get('cinema_keywords', [])
                        if keywords:
                            cinema_name = order['cinema_name'].lower().strip()
                            matched_keywords = []
                            for keyword in keywords:
                                if keyword.lower().strip() in cinema_name:
                                    matched_keywords.append(keyword)
                            
                            if len(matched_keywords) != len(keywords):
                                missing_keywords = [k for k in keywords if k.lower().strip() not in cinema_name]
                                print(f"    策略'{rule['rule_name']}': 关键词不匹配 (缺少: {missing_keywords})")
                                continue
                    
                    # 检查利润
                    hall_logic = rule.get('hall_logic', {})
                    profit_logic = rule.get('profit_logic', {})
                    hall_cost = hall_logic.get('cost', 0)
                    single_ticket_profit = order['bidding_price'] - hall_cost
                    total_profit = single_ticket_profit * order['seat_count']
                    min_profit_threshold = profit_logic.get('min_profit_threshold', 0)
                    
                    if total_profit < min_profit_threshold:
                        print(f"    策略'{rule['rule_name']}': 利润不足 ({total_profit} < {min_profit_threshold})")
                        continue
                    
                    print(f"    策略'{rule['rule_name']}': 似乎应该匹配，需要进一步分析...")
        
        print(f"\n🎯 匹配统计: {matched_count}/{len(orders[:5])} 个订单匹配成功")
    
    print("\n" + "=" * 80)
    print("调试分析完成")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(debug_mango_platform())