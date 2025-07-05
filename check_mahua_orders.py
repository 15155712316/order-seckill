#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查数据库中的麻花订单
"""

from core.database import DatabaseManager

def check_mahua_orders():
    """检查数据库中的麻花订单"""
    print("🔍 检查数据库中的麻花订单...")
    
    db = DatabaseManager()
    
    try:
        # 获取最近的订单
        orders = db.get_recent_orders(20)
        
        # 筛选麻花平台订单
        mahua_orders = [o for o in orders if o['platform'] == '麻花']
        
        print(f"📊 最近20条订单中，麻花订单数量: {len(mahua_orders)}")
        
        if mahua_orders:
            print("\n📋 麻花订单详情:")
            for i, order in enumerate(mahua_orders[:5], 1):
                print(f"   {i}. 订单ID: {order['order_id']}")
                print(f"      价格: ¥{order['bidding_price']}")
                print(f"      影院: {order['cinema_name']}")
                print(f"      城市: {order['city']}")
                print(f"      创建时间: {order['created_at']}")
                print()
        else:
            print("ℹ️ 暂无麻花订单数据")
            
    except Exception as e:
        print(f"❌ 检查失败: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_mahua_orders()
