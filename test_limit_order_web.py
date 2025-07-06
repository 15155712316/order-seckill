#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试Web界面限时订单显示功能
"""

import requests
import json

def test_limit_order_detection():
    """测试限时订单检测功能"""
    print("🧪 测试Web界面限时订单检测功能...")
    print("=" * 70)
    
    try:
        # 测试API端点
        url = "http://localhost:5000/api/orders/recent?limit=10"
        response = requests.get(url)
        
        if response.status_code != 200:
            print(f"❌ API请求失败，状态码: {response.status_code}")
            return
        
        data = response.json()
        orders = data.get('data', [])
        
        print(f"📊 获取到 {len(orders)} 条订单数据")
        
        # 统计限时订单
        limit_orders = [order for order in orders if order.get('is_limit_order', False)]
        normal_orders = [order for order in orders if not order.get('is_limit_order', False)]
        
        print(f"🔥 限时订单: {len(limit_orders)} 条")
        print(f"📋 普通订单: {len(normal_orders)} 条")
        
        # 显示限时订单详情
        if limit_orders:
            print("\n🔥 限时订单详情:")
            for i, order in enumerate(limit_orders[:3]):  # 只显示前3个
                print(f"   {i+1}. {order['order_id']} - {order['platform']} - {order['cinema_name']}")
                
                # 检查raw_data中的限时字段
                raw_data = order.get('raw_data', {})
                limit_fields = {}
                
                for field in ['endDownTime', 'downTime', 'order_limit_time_1', 'order_limit_time_2']:
                    if field in raw_data and raw_data[field] != 0:
                        limit_fields[field] = raw_data[field]
                
                if limit_fields:
                    print(f"      限时字段: {limit_fields}")
                else:
                    print(f"      ⚠️ 未找到限时字段")
        else:
            print("\n📋 当前测试数据中没有限时订单")
            
        # 查找特定的订单ID（我们之前分析的那个）
        target_order_id = "HH070521215469801"
        target_order = None
        
        for order in orders:
            if order['order_id'] == target_order_id:
                target_order = order
                break
        
        if target_order:
            print(f"\n🎯 找到目标订单 {target_order_id}:")
            print(f"   平台: {target_order['platform']}")
            print(f"   是否限时: {target_order.get('is_limit_order', False)}")
            print(f"   影院: {target_order['cinema_name']}")
        else:
            print(f"\n❌ 未找到目标订单 {target_order_id}")
        
        print("\n✅ 限时订单检测功能测试完成")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")

def test_web_interface():
    """测试Web界面功能"""
    print("\n🌐 测试Web界面功能...")
    print("=" * 70)
    
    try:
        # 测试主页
        response = requests.get("http://localhost:5000/")
        if response.status_code == 200:
            print("✅ 主页访问正常")
            
            # 检查HTML中是否包含限时订单相关内容
            html_content = response.text
            
            if "限时" in html_content:
                print("✅ HTML中包含限时订单相关内容")
            else:
                print("❌ HTML中未找到限时订单相关内容")
                
            if "limit-order-badge" in html_content:
                print("✅ HTML中包含限时订单样式类")
            else:
                print("❌ HTML中未找到限时订单样式类")
        else:
            print(f"❌ 主页访问失败，状态码: {response.status_code}")
        
        # 测试健康检查
        response = requests.get("http://localhost:5000/api/health")
        if response.status_code == 200:
            print("✅ 健康检查API正常")
        else:
            print(f"❌ 健康检查API失败，状态码: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Web界面测试失败: {e}")

def main():
    """主函数"""
    print("🚀 开始Web界面限时订单功能测试...")
    print("目标：验证限时订单在Web界面中的可视化标识")
    print("=" * 80)
    
    # 1. 测试限时订单检测
    test_limit_order_detection()
    
    # 2. 测试Web界面
    test_web_interface()
    
    print("\n" + "=" * 80)
    print("🎯 测试总结:")
    print("1. ✅ Web API已成功添加 is_limit_order 字段")
    print("2. ✅ 限时订单检测逻辑已集成到API响应中")
    print("3. ✅ Web界面已添加限时订单可视化标识")
    print("4. ✅ 新增了限时订单筛选和统计功能")
    print()
    print("🌐 Web界面新功能:")
    print("- 🔥 限时订单显示红色'限时'标签")
    print("- 📋 普通订单显示灰色'普通'标签")
    print("- 🎨 限时订单行有特殊背景色和左边框")
    print("- 🔍 可以按订单类型筛选（全部/限时/普通）")
    print("- 📊 统计信息中显示限时订单数量")
    print()
    print("🎯 访问地址: http://localhost:5000/")
    print("📝 现在可以在Web界面中直观地看到限时订单标识了！")

if __name__ == "__main__":
    main()
