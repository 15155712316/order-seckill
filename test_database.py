#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库测试脚本 - 验证SQLite数据库功能
"""

from core.database import DatabaseManager

def test_database():
    """测试数据库功能"""
    try:
        # 创建数据库管理器实例
        db = DatabaseManager()
        
        # 获取订单总数
        total_count = db.get_orders_count()
        print(f"数据库中总订单数: {total_count}")
        
        # 获取最近的10条订单
        recent_orders = db.get_recent_orders(limit=10)
        print(f"\n最近的 {len(recent_orders)} 条订单:")
        print("=" * 80)
        
        for i, order in enumerate(recent_orders, 1):
            print(f"{i}. 订单ID: {order['order_id']}")
            print(f"   影院: {order['cinema_name']}")
            print(f"   影厅: {order['hall_type']}")
            print(f"   城市: {order['city']}")
            print(f"   电影: {order['movie_name']}")
            print(f"   价格: {order['bidding_price']}元")
            print(f"   票数: {order['seat_count']}张")
            print(f"   创建时间: {order['created_at']}")
            print("-" * 40)
        
        # 关闭数据库连接
        db.close()
        
    except Exception as e:
        print(f"测试数据库时发生错误: {e}")

if __name__ == "__main__":
    test_database()
