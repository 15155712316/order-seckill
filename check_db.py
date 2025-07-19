#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库表结构分析脚本
"""

import sqlite3
import os

def check_database_structure():
    """检查数据库表结构"""
    
    print("=" * 80)
    print("数据库表结构分析")
    print("=" * 80)
    
    db_path = "orders.db"
    if not os.path.exists(db_path):
        print("❌ 数据库文件不存在")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. 查看所有表
        print("\n1. 查看所有表...")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        print(f"数据库中的表: {[table[0] for table in tables]}")
        
        # 2. 查看每个表的结构
        for table in tables:
            table_name = table[0]
            print(f"\n--- 表: {table_name} ---")
            
            # 获取表结构
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            
            print("列结构:")
            for col in columns:
                cid, name, type_, notnull, default, pk = col
                print(f"  {name}: {type_} {'(主键)' if pk else ''}")
            
            # 获取记录数量
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"记录数量: {count}")
            
            # 如果是策略相关表，显示一些示例数据
            if 'polic' in table_name.lower() or 'strateg' in table_name.lower() or 'rule' in table_name.lower():
                print("示例数据:")
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 2")
                rows = cursor.fetchall()
                for row in rows:
                    print(f"  {row}")
        
        conn.close()
        
        print("\n" + "=" * 80)
        print("分析完成")
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ 数据库分析失败: {e}")

if __name__ == "__main__":
    check_database_structure()