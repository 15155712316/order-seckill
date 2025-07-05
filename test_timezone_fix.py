#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
时区修复测试脚本
"""

from core.database import get_china_time
import pytz
from datetime import datetime

def test_timezone_fix():
    """测试时区修复"""
    print("🕐 测试时区修复...")
    print("=" * 50)
    
    # 测试pytz是否正常工作
    try:
        print("1. 测试pytz库...")
        china_tz = pytz.timezone('Asia/Shanghai')
        china_time = datetime.now(china_tz)
        formatted_time = china_time.strftime('%Y-%m-%d %H:%M:%S')
        print(f"   ✅ pytz正常工作: {formatted_time}")
        print(f"   📍 时区信息: {china_time.tzinfo}")
    except Exception as e:
        print(f"   ❌ pytz测试失败: {e}")
    
    # 测试get_china_time函数
    try:
        print("\n2. 测试get_china_time()函数...")
        china_time = get_china_time()
        print(f"   ✅ 函数返回: {china_time}")
        
        # 验证时间格式
        if len(china_time) == 19 and china_time[4] == '-' and china_time[7] == '-':
            print("   ✅ 时间格式正确")
        else:
            print("   ❌ 时间格式异常")
    except Exception as e:
        print(f"   ❌ 函数测试失败: {e}")
    
    # 比较本地时间和中国时间
    try:
        print("\n3. 比较本地时间和中国时间...")
        local_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        china_time = get_china_time()
        
        print(f"   🕐 本地时间: {local_time}")
        print(f"   🇨🇳 中国时间: {china_time}")
        
        if local_time == china_time:
            print("   ℹ️ 本地时间与中国时间相同（可能在中国时区）")
        else:
            print("   ℹ️ 本地时间与中国时间不同")
    except Exception as e:
        print(f"   ❌ 时间比较失败: {e}")

if __name__ == "__main__":
    test_timezone_fix()
