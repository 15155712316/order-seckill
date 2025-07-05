#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
前端功能测试脚本 - 验证Web前端页面和API功能
"""

import requests
import json

def test_frontend_apis():
    """测试前端相关的API接口"""
    base_url = "http://localhost:5000"
    
    print("🧪 开始测试前端相关API接口...")
    print("=" * 60)
    
    # 测试前端页面
    try:
        print("1. 测试前端页面 (GET /)...")
        response = requests.get(f"{base_url}/")
        if response.status_code == 200:
            if "抢单数据复盘中心" in response.text:
                print("   ✅ 前端页面加载成功")
            else:
                print("   ⚠️ 前端页面内容异常")
        else:
            print(f"   ❌ 前端页面加载失败: {response.status_code}")
    except Exception as e:
        print(f"   ❌ 前端页面测试失败: {e}")
    
    # 测试API文档
    try:
        print("2. 测试API文档 (GET /api/docs)...")
        response = requests.get(f"{base_url}/api/docs")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ API文档获取成功: {data['service']}")
        else:
            print(f"   ❌ API文档获取失败: {response.status_code}")
    except Exception as e:
        print(f"   ❌ API文档测试失败: {e}")
    
    # 测试健康检查
    try:
        print("3. 测试健康检查 (GET /api/health)...")
        response = requests.get(f"{base_url}/api/health")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ 健康检查成功: {data['total_orders']} 条订单")
        else:
            print(f"   ❌ 健康检查失败: {response.status_code}")
    except Exception as e:
        print(f"   ❌ 健康检查测试失败: {e}")
    
    # 测试订单总数API
    try:
        print("4. 测试订单总数 (GET /api/orders/count)...")
        response = requests.get(f"{base_url}/api/orders/count")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ 订单总数获取成功: {data['total_count']} 条")
        else:
            print(f"   ❌ 订单总数获取失败: {response.status_code}")
    except Exception as e:
        print(f"   ❌ 订单总数测试失败: {e}")
    
    # 测试最近订单API
    try:
        print("5. 测试最近订单 (GET /api/orders/recent?limit=5)...")
        response = requests.get(f"{base_url}/api/orders/recent?limit=5")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ 最近订单获取成功: {data['total_count']} 条")
            if data['data']:
                first_order = data['data'][0]
                print(f"   📋 最新订单: {first_order['platform']} - {first_order['cinema_name']}")
        else:
            print(f"   ❌ 最近订单获取失败: {response.status_code}")
    except Exception as e:
        print(f"   ❌ 最近订单测试失败: {e}")
    
    # 测试全部订单API（只获取前10条）
    try:
        print("6. 测试全部订单API (GET /api/orders)...")
        response = requests.get(f"{base_url}/api/orders")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ 全部订单获取成功: {data['total_count']} 条")
            
            # 统计平台分布
            platforms = {}
            for order in data['data']:
                platform = order.get('platform', '未知')
                platforms[platform] = platforms.get(platform, 0) + 1
            
            print("   📊 平台分布:")
            for platform, count in platforms.items():
                print(f"      {platform}: {count} 条")
                
        else:
            print(f"   ❌ 全部订单获取失败: {response.status_code}")
    except Exception as e:
        print(f"   ❌ 全部订单测试失败: {e}")
    
    print("=" * 60)
    print("🎉 前端API测试完成！")

def test_data_quality():
    """测试数据质量"""
    base_url = "http://localhost:5000"
    
    print("\n🔍 开始测试数据质量...")
    print("=" * 60)
    
    try:
        response = requests.get(f"{base_url}/api/orders/recent?limit=10")
        if response.status_code == 200:
            data = response.json()
            orders = data['data']
            
            print(f"📊 数据质量分析（基于最近 {len(orders)} 条订单）:")
            
            # 检查必要字段
            required_fields = ['order_id', 'platform', 'cinema_name', 'city', 'bidding_price']
            field_completeness = {}
            
            for field in required_fields:
                complete_count = sum(1 for order in orders if order.get(field))
                completeness = (complete_count / len(orders)) * 100 if orders else 0
                field_completeness[field] = completeness
                print(f"   {field}: {completeness:.1f}% 完整度")
            
            # 检查平台分布
            platforms = {}
            for order in orders:
                platform = order.get('platform', '未知')
                platforms[platform] = platforms.get(platform, 0) + 1
            
            print(f"\n   平台分布:")
            for platform, count in platforms.items():
                percentage = (count / len(orders)) * 100 if orders else 0
                print(f"   {platform}: {count} 条 ({percentage:.1f}%)")
            
            # 检查价格范围
            prices = [order.get('bidding_price', 0) for order in orders if order.get('bidding_price')]
            if prices:
                min_price = min(prices)
                max_price = max(prices)
                avg_price = sum(prices) / len(prices)
                print(f"\n   价格分析:")
                print(f"   最低价: ¥{min_price}")
                print(f"   最高价: ¥{max_price}")
                print(f"   平均价: ¥{avg_price:.2f}")
            
        else:
            print(f"❌ 数据获取失败: {response.status_code}")
            
    except Exception as e:
        print(f"❌ 数据质量测试失败: {e}")
    
    print("=" * 60)
    print("🎯 数据质量测试完成！")

if __name__ == "__main__":
    print("🚀 开始前端功能全面测试...")
    test_frontend_apis()
    test_data_quality()
    print("\n✨ 所有测试完成！")
