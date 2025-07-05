#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web API中文显示修复验证脚本
"""

import requests
import json
import re

def test_api_chinese_display():
    """测试API中文显示修复效果"""
    print("🧪 测试Web API中文显示修复效果...")
    print("=" * 70)
    
    base_url = "http://localhost:5000"
    
    # 测试所有API端点
    test_cases = [
        {
            'name': '健康检查API',
            'url': f'{base_url}/api/health',
            'expected_chinese': ['Web API服务器运行正常']
        },
        {
            'name': '订单总数API',
            'url': f'{base_url}/api/orders/count',
            'expected_chinese': ['成功获取订单总数']
        },
        {
            'name': '最近订单API',
            'url': f'{base_url}/api/orders/recent?limit=2',
            'expected_chinese': ['成功获取最近', '条订单数据']
        },
        {
            'name': '全部订单API',
            'url': f'{base_url}/api/orders',
            'expected_chinese': ['成功获取', '条订单数据']
        },
        {
            'name': 'API文档',
            'url': f'{base_url}/api/docs',
            'expected_chinese': ['抢单提醒系统']
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"{i}. 测试 {test_case['name']}...")
        
        try:
            response = requests.get(test_case['url'])
            
            if response.status_code == 200:
                print(f"   ✅ HTTP状态码: {response.status_code}")
                
                # 检查Content-Type
                content_type = response.headers.get('Content-Type', '')
                if 'application/json' in content_type and 'charset=utf-8' in content_type:
                    print(f"   ✅ Content-Type正确: {content_type}")
                else:
                    print(f"   ⚠️ Content-Type: {content_type}")
                
                # 检查原始响应中的中文字符
                raw_text = response.text
                has_unicode_escape = bool(re.search(r'\\u[0-9a-fA-F]{4}', raw_text))
                
                if has_unicode_escape:
                    print(f"   ❌ 原始响应包含Unicode转义序列")
                    # 显示一些Unicode转义的例子
                    unicode_matches = re.findall(r'\\u[0-9a-fA-F]{4}', raw_text)[:3]
                    print(f"   📝 示例: {unicode_matches}")
                else:
                    print(f"   ✅ 原始响应不包含Unicode转义序列")
                
                # 检查是否包含预期的中文内容
                chinese_found = []
                for expected in test_case['expected_chinese']:
                    if expected in raw_text:
                        chinese_found.append(expected)
                
                if chinese_found:
                    print(f"   ✅ 包含预期中文内容: {chinese_found}")
                else:
                    print(f"   ⚠️ 未找到预期中文内容: {test_case['expected_chinese']}")
                
                # 检查JSON解析
                try:
                    data = response.json()
                    print(f"   ✅ JSON解析成功")
                    
                    # 检查数据中的中文字段
                    if 'data' in data and isinstance(data['data'], list) and data['data']:
                        first_item = data['data'][0]
                        chinese_fields = []
                        
                        for field in ['cinema_name', 'city', 'movie_name', 'platform']:
                            if field in first_item and first_item[field]:
                                value = first_item[field]
                                # 检查是否包含中文字符
                                if any('\u4e00' <= char <= '\u9fff' for char in str(value)):
                                    chinese_fields.append(f"{field}: {value}")
                        
                        if chinese_fields:
                            print(f"   ✅ 数据中包含中文字段:")
                            for field in chinese_fields[:2]:  # 只显示前2个
                                print(f"      {field}")
                        else:
                            print(f"   ℹ️ 数据中暂无中文字段")
                    
                except json.JSONDecodeError as e:
                    print(f"   ❌ JSON解析失败: {e}")
                
            else:
                print(f"   ❌ HTTP状态码异常: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ 请求失败: {e}")
        
        print()  # 空行分隔

def test_curl_compatibility():
    """测试curl命令兼容性"""
    print("🌐 测试curl命令兼容性...")
    print("=" * 70)
    
    import subprocess
    
    try:
        # 使用curl测试API
        result = subprocess.run([
            'curl', '-s', 'http://localhost:5000/api/health'
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            response_text = result.stdout
            print("✅ curl请求成功")
            
            # 检查是否包含Unicode转义
            has_unicode_escape = bool(re.search(r'\\u[0-9a-fA-F]{4}', response_text))
            
            if has_unicode_escape:
                print("❌ curl响应包含Unicode转义序列")
                print(f"📝 响应内容: {response_text[:200]}...")
            else:
                print("✅ curl响应不包含Unicode转义序列")
                print(f"📝 响应内容: {response_text}")
        else:
            print(f"❌ curl请求失败: {result.stderr}")
            
    except subprocess.TimeoutExpired:
        print("❌ curl请求超时")
    except FileNotFoundError:
        print("ℹ️ curl命令不可用，跳过测试")
    except Exception as e:
        print(f"❌ curl测试失败: {e}")

def test_browser_display():
    """测试浏览器显示效果"""
    print("\n🌐 浏览器显示测试说明...")
    print("=" * 70)
    
    print("请在浏览器中访问以下URL，验证中文显示效果：")
    print()
    print("1. 健康检查API:")
    print("   http://localhost:5000/api/health")
    print("   应该看到: \"message\": \"Web API服务器运行正常\"")
    print()
    print("2. 最近订单API:")
    print("   http://localhost:5000/api/orders/recent?limit=2")
    print("   应该看到中文影院名、城市名等，而不是\\u转义字符")
    print()
    print("3. 前端页面:")
    print("   http://localhost:5000/")
    print("   应该正确显示所有中文内容")
    print()
    print("✅ 如果以上URL在浏览器中都能正确显示中文，说明修复成功！")

def main():
    """主测试函数"""
    print("🚀 开始Web API中文显示修复验证...")
    print("测试目标：确保API返回的JSON中中文字符以可读形式显示")
    print("=" * 80)
    
    # 测试API中文显示
    test_api_chinese_display()
    
    # 测试curl兼容性
    test_curl_compatibility()
    
    # 浏览器显示测试说明
    test_browser_display()
    
    print("=" * 80)
    print("🎉 Web API中文显示修复验证完成！")

if __name__ == "__main__":
    main()
