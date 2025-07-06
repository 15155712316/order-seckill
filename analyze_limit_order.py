#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
哈哈平台限时订单识别分析脚本
"""

import json
import logging
from core.database import DatabaseManager

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def analyze_specific_order():
    """分析指定的订单数据"""
    print("🔍 分析哈哈平台限时订单识别问题...")
    print("=" * 80)
    
    # 目标订单ID
    target_order_id = "HH070521215469801"
    
    try:
        # 连接数据库
        db = DatabaseManager()
        
        # 查找指定订单
        print(f"📋 查找订单ID: {target_order_id}")
        
        # 使用直接SQL查询指定订单
        cursor = db.connection.cursor()
        query = "SELECT * FROM orders WHERE order_id = ?"
        cursor.execute(query, (target_order_id,))
        result = cursor.fetchone()

        if not result:
            print(f"❌ 未找到订单ID为 {target_order_id} 的订单")
            return None

        order = result
        print(f"✅ 找到订单，数据库ID: {order[0]}")

        # 解析raw_data
        raw_data_str = order[10]  # raw_data字段在第11列（索引10）
        raw_data = json.loads(raw_data_str)
        
        # 显示订单基本信息
        print("\n📊 订单基本信息:")
        print(f"   订单ID: {order[1]}")
        print(f"   城市: {order[4]}")
        print(f"   影院: {order[5]}")
        print(f"   影厅: {order[6]}")
        print(f"   电影: {order[7]}")
        print(f"   票数: {order[3]}")
        print(f"   竞标价: {order[2]}")
        print(f"   平台: {order[9]}")
        print(f"   创建时间: {order[11]}")
        
        return raw_data
        
    except Exception as e:
        print(f"❌ 查询订单失败: {e}")
        return None

def analyze_limit_time_fields(raw_data):
    """分析可能的限时字段"""
    print("\n🔍 分析可能的限时订单标识字段:")
    print("=" * 60)
    
    # 可能的限时相关字段
    potential_limit_fields = [
        'limit_time', 'order_limit_time', 'endDownTime', 'downTime',
        'biddingEndtime', 'invalidateDate', 'lapsed', 'lapsedEndtime',
        'is_lock', 'is_from', 'is_type', 'is_err', 'is_admin',
        'bid_time', 'entry_method', 'merchant_quote_type',
        'is_direct_give', 'isContractOrder', 'dispute',
        'has_payment', 'refresh_bidding_id', 'is_reward'
    ]
    
    found_fields = {}
    
    for field in potential_limit_fields:
        if field in raw_data:
            found_fields[field] = raw_data[field]
            print(f"   ✅ {field}: {raw_data[field]}")
        else:
            print(f"   ❌ {field}: 不存在")
    
    return found_fields

def analyze_time_related_fields(raw_data):
    """分析时间相关字段"""
    print("\n⏰ 分析时间相关字段:")
    print("=" * 60)
    
    time_fields = [
        'create_time', 'pay_time', 'bid_time', 'show_time',
        'startTime', 'invalidateDate', 'endDownTime', 'downTime'
    ]
    
    time_data = {}
    
    for field in time_fields:
        if field in raw_data:
            value = raw_data[field]
            time_data[field] = value
            
            # 尝试解析时间戳
            if isinstance(value, (int, str)) and str(value).isdigit():
                try:
                    from datetime import datetime
                    timestamp = int(value)
                    if timestamp > 1000000000:  # 看起来像时间戳
                        dt = datetime.fromtimestamp(timestamp)
                        print(f"   ✅ {field}: {value} -> {dt.strftime('%Y-%m-%d %H:%M:%S')}")
                    else:
                        print(f"   ✅ {field}: {value}")
                except:
                    print(f"   ✅ {field}: {value}")
            else:
                print(f"   ✅ {field}: {value}")
    
    return time_data

def compare_with_normal_orders():
    """对比正常订单和限时订单的差异"""
    print("\n📊 对比分析正常订单和限时订单:")
    print("=" * 60)
    
    try:
        db = DatabaseManager()
        
        # 获取最近的几个哈哈平台订单进行对比
        cursor = db.connection.cursor()
        query = """
        SELECT order_id, raw_data FROM orders
        WHERE platform = '哈哈'
        ORDER BY created_at DESC
        LIMIT 5
        """

        cursor.execute(query)
        results = cursor.fetchall()
        
        print(f"📋 分析最近的 {len(results)} 个哈哈平台订单:")
        
        limit_indicators = {}
        
        for i, (order_id, raw_data_str) in enumerate(results):
            try:
                raw_data = json.loads(raw_data_str)
                
                print(f"\n   订单 {i+1}: {order_id}")
                
                # 检查关键字段
                key_fields = ['limit_time', 'order_limit_time', 'endDownTime', 'downTime', 'is_lock']
                
                for field in key_fields:
                    if field in raw_data:
                        value = raw_data[field]
                        print(f"      {field}: {value}")
                        
                        # 统计字段值分布
                        if field not in limit_indicators:
                            limit_indicators[field] = {}
                        
                        if value not in limit_indicators[field]:
                            limit_indicators[field][value] = 0
                        limit_indicators[field][value] += 1
                
            except Exception as e:
                print(f"      ❌ 解析失败: {e}")
        
        # 显示统计结果
        print(f"\n📈 字段值分布统计:")
        for field, values in limit_indicators.items():
            print(f"   {field}:")
            for value, count in values.items():
                print(f"      {value}: {count}次")
        
        return limit_indicators
        
    except Exception as e:
        print(f"❌ 对比分析失败: {e}")
        return {}

def analyze_all_fields(raw_data):
    """分析所有字段，寻找可能的限时标识"""
    print("\n🔍 完整字段分析:")
    print("=" * 60)
    
    print("📋 所有字段及其值:")
    for key, value in raw_data.items():
        # 高亮可能相关的字段
        if any(keyword in key.lower() for keyword in ['limit', 'time', 'end', 'down', 'lock', 'bid']):
            print(f"   🔥 {key}: {value}")
        else:
            print(f"      {key}: {value}")
    
    return raw_data

def main():
    """主函数"""
    print("🚀 开始哈哈平台限时订单识别分析...")
    print("目标：分析订单 HH070521215469801 的限时单识别问题")
    print("=" * 80)
    
    # 1. 查找指定订单
    raw_data = analyze_specific_order()
    
    if raw_data is None:
        print("❌ 无法获取订单数据，分析终止")
        return
    
    # 2. 分析限时相关字段
    limit_fields = analyze_limit_time_fields(raw_data)
    
    # 3. 分析时间相关字段
    time_fields = analyze_time_related_fields(raw_data)
    
    # 4. 完整字段分析
    all_fields = analyze_all_fields(raw_data)
    
    # 5. 对比分析
    comparison = compare_with_normal_orders()
    
    # 6. 生成分析报告
    print("\n" + "=" * 80)
    print("📋 分析报告总结:")
    print("=" * 80)
    
    print("\n🎯 关键发现:")
    
    # 检查关键限时字段
    if 'limit_time' in limit_fields:
        print(f"   ✅ limit_time: {limit_fields['limit_time']}")
    
    if 'order_limit_time' in limit_fields:
        print(f"   ✅ order_limit_time: {limit_fields['order_limit_time']}")
    
    if 'endDownTime' in limit_fields:
        print(f"   ✅ endDownTime: {limit_fields['endDownTime']}")
    
    if 'downTime' in limit_fields:
        print(f"   ✅ downTime: {limit_fields['downTime']}")
    
    # 建议的识别逻辑
    print("\n💡 建议的限时单识别逻辑:")
    
    if limit_fields.get('limit_time', 0) != 0:
        print("   1. limit_time != 0 表示限时单")
    
    if limit_fields.get('order_limit_time', 0) != 0:
        print("   2. order_limit_time != 0 表示限时单")
    
    if 'endDownTime' in limit_fields and limit_fields['endDownTime'] != 0:
        print("   3. endDownTime > 0 表示有倒计时结束时间")
    
    if 'downTime' in limit_fields and limit_fields['downTime'] != 0:
        print("   4. downTime > 0 表示剩余倒计时秒数")
    
    print("\n🔧 建议的代码实现:")
    print("```python")
    print("def is_limit_order(raw_data):")
    print("    # 检查多个可能的限时标识字段")
    print("    limit_time = raw_data.get('limit_time', 0)")
    print("    order_limit_time = raw_data.get('order_limit_time', 0)")
    print("    end_down_time = raw_data.get('endDownTime', 0)")
    print("    down_time = raw_data.get('downTime', 0)")
    print("    ")
    print("    # 任一字段不为0则认为是限时单")
    print("    return (limit_time != 0 or order_limit_time != 0 or")
    print("            end_down_time != 0 or down_time != 0)")
    print("```")

if __name__ == "__main__":
    main()
