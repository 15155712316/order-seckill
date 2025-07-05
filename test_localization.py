#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地化优化测试脚本 - 验证中文显示和时区功能
"""

import requests
import json
from core.database import DatabaseManager, get_china_time

def test_chinese_display():
    """测试中文显示功能"""
    print("🧪 测试中文显示功能...")
    print("=" * 60)
    
    base_url = "http://localhost:5000"
    
    # 测试健康检查API的中文显示
    try:
        print("1. 测试健康检查API中文显示...")
        response = requests.get(f"{base_url}/api/health")
        if response.status_code == 200:
            data = response.json()
            message = data.get('message', '')
            print(f"   ✅ API响应成功")
            print(f"   📝 消息内容: {message}")
            
            # 检查是否包含中文字符
            if any('\u4e00' <= char <= '\u9fff' for char in message):
                print("   ✅ 中文显示正常")
            else:
                print("   ❌ 中文显示异常")
        else:
            print(f"   ❌ API请求失败: {response.status_code}")
    except Exception as e:
        print(f"   ❌ 测试失败: {e}")
    
    # 测试订单数据的中文显示
    try:
        print("\n2. 测试订单数据中文显示...")
        response = requests.get(f"{base_url}/api/orders/recent?limit=2")
        if response.status_code == 200:
            data = response.json()
            orders = data.get('data', [])
            
            if orders:
                print(f"   ✅ 获取到 {len(orders)} 条订单数据")
                
                for i, order in enumerate(orders, 1):
                    cinema_name = order.get('cinema_name', '')
                    city = order.get('city', '')
                    movie_name = order.get('movie_name', '')
                    
                    print(f"   📋 订单 {i}:")
                    print(f"      影院: {cinema_name}")
                    print(f"      城市: {city}")
                    print(f"      电影: {movie_name}")
                    
                    # 检查中文字符
                    chinese_fields = [cinema_name, city, movie_name]
                    has_chinese = any(
                        any('\u4e00' <= char <= '\u9fff' for char in field)
                        for field in chinese_fields if field
                    )
                    
                    if has_chinese:
                        print(f"      ✅ 包含中文字符")
                    else:
                        print(f"      ⚠️ 未检测到中文字符")
            else:
                print("   ⚠️ 未获取到订单数据")
        else:
            print(f"   ❌ API请求失败: {response.status_code}")
    except Exception as e:
        print(f"   ❌ 测试失败: {e}")

def test_timezone_function():
    """测试时区功能"""
    print("\n🕐 测试时区功能...")
    print("=" * 60)
    
    try:
        print("1. 测试get_china_time()函数...")
        china_time = get_china_time()
        print(f"   ✅ 中国时区时间: {china_time}")
        
        # 验证时间格式
        if len(china_time) == 19 and china_time[4] == '-' and china_time[7] == '-':
            print("   ✅ 时间格式正确 (YYYY-MM-DD HH:MM:SS)")
        else:
            print("   ❌ 时间格式异常")
            
    except Exception as e:
        print(f"   ❌ 时区函数测试失败: {e}")

def test_database_timezone():
    """测试数据库时区功能"""
    print("\n2. 测试数据库时区功能...")
    
    try:
        # 创建数据库管理器实例
        db = DatabaseManager()
        
        # 获取最近的订单，检查created_at字段
        recent_orders = db.get_recent_orders(limit=3)
        
        if recent_orders:
            print(f"   ✅ 获取到 {len(recent_orders)} 条最近订单")
            
            for i, order in enumerate(recent_orders, 1):
                created_at = order.get('created_at', '')
                platform = order.get('platform', '')
                
                print(f"   📋 订单 {i}:")
                print(f"      平台: {platform}")
                print(f"      创建时间: {created_at}")
                
                # 检查时间格式
                if len(created_at) == 19 and created_at[4] == '-' and created_at[7] == '-':
                    print(f"      ✅ 时间格式正确")
                else:
                    print(f"      ❌ 时间格式异常")
        else:
            print("   ⚠️ 未获取到订单数据")
            
        # 关闭数据库连接
        db.close()
        
    except Exception as e:
        print(f"   ❌ 数据库时区测试失败: {e}")

def test_api_response_encoding():
    """测试API响应编码"""
    print("\n📝 测试API响应编码...")
    print("=" * 60)
    
    base_url = "http://localhost:5000"
    
    try:
        print("1. 测试API响应头...")
        response = requests.get(f"{base_url}/api/health")
        
        content_type = response.headers.get('Content-Type', '')
        print(f"   Content-Type: {content_type}")
        
        if 'application/json' in content_type:
            print("   ✅ 响应类型正确")
        else:
            print("   ❌ 响应类型异常")
        
        # 测试响应内容编码
        print("\n2. 测试响应内容编码...")
        response_text = response.text
        print(f"   响应长度: {len(response_text)} 字符")
        
        # 尝试解析JSON
        try:
            data = response.json()
            message = data.get('message', '')
            print(f"   JSON解析成功")
            print(f"   消息内容: {message}")
            
            # 检查是否正确显示中文
            if '服务器运行正常' in message:
                print("   ✅ 中文内容正确显示")
            else:
                print("   ⚠️ 中文内容可能有问题")
                
        except json.JSONDecodeError as e:
            print(f"   ❌ JSON解析失败: {e}")
            
    except Exception as e:
        print(f"   ❌ API编码测试失败: {e}")

def main():
    """主测试函数"""
    print("🚀 开始本地化优化测试...")
    print("测试项目：中文显示、时区功能、API编码")
    print("=" * 80)
    
    # 测试中文显示
    test_chinese_display()
    
    # 测试时区功能
    test_timezone_function()
    
    # 测试数据库时区
    test_database_timezone()
    
    # 测试API响应编码
    test_api_response_encoding()
    
    print("=" * 80)
    print("🎉 本地化优化测试完成！")

if __name__ == "__main__":
    main()
