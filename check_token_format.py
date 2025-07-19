#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查影划算平台Bearer Token格式的脚本
比较yinghuasuan.py中的工作token与数据库中存储的token格式
"""

import sys
import os
import json
import logging

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.database import DatabaseManager

def check_token_formats():
    """检查token格式差异"""
    print("=" * 80)
    print("影划算平台Bearer Token格式检查")
    print("=" * 80)
    
    # 1. 从yinghuasuan.py文件中提取working token
    try:
        with open('yinghuasuan.py', 'r', encoding='utf-8') as f:
            content = f.read()
            
        # 查找Authorization行
        for line in content.split('\n'):
            if 'Authorization' in line and 'Bearer' in line:
                # 提取Bearer token
                start = line.find("'Bearer ") + len("'Bearer ")
                end = line.find("'", start)
                working_token = line[start:end]
                print(f"📋 yinghuasuan.py中的工作Token:")
                print(f"   - 完整Authorization头: {line.strip()}")
                print(f"   - 纯Token部分: {working_token}")
                print(f"   - Token长度: {len(working_token)} 字符")
                print(f"   - Token前20字符: {working_token[:20]}...")
                print(f"   - Token后10字符: ...{working_token[-10:]}")
                break
                
    except Exception as e:
        print(f"❌ 读取yinghuasuan.py失败: {e}")
        return
    
    print("\n" + "=" * 80)
    
    # 2. 从数据库中读取存储的token
    try:
        db_manager = DatabaseManager()
        credentials_json = db_manager.load_setting('platform_credentials')
        
        if credentials_json:
            credentials = json.loads(credentials_json)
            yinghuasuan_config = credentials.get('yinghuasuan', {})
            stored_token = yinghuasuan_config.get('bearer_token', '')
            
            print(f"📋 数据库中存储的Token:")
            print(f"   - 存储的Token: {stored_token}")
            print(f"   - Token长度: {len(stored_token)} 字符")
            if stored_token:
                print(f"   - Token前20字符: {stored_token[:20]}...")
                print(f"   - Token后10字符: ...{stored_token[-10:]}")
                print(f"   - 是否包含'Bearer '前缀: {'是' if stored_token.startswith('Bearer ') else '否'}")
                
                # 分析token格式
                if stored_token.startswith('Bearer '):
                    pure_token = stored_token[7:]  # 去掉"Bearer "前缀
                    print(f"   - 去掉Bearer前缀后: {pure_token[:20]}...{pure_token[-10:]}")
                    print(f"   - 纯Token长度: {len(pure_token)} 字符")
                
            else:
                print("   - 未找到存储的Bearer Token")
        else:
            print("📋 数据库中未找到平台配置")
            
    except Exception as e:
        print(f"❌ 读取数据库配置失败: {e}")
        return
    
    print("\n" + "=" * 80)
    
    # 3. 比较分析
    print("📋 格式对比分析:")
    try:
        if 'working_token' in locals() and 'stored_token' in locals():
            print(f"   - 工作Token长度: {len(working_token)} 字符")
            print(f"   - 存储Token长度: {len(stored_token)} 字符")
            
            # 如果存储的token包含Bearer前缀，去掉它再比较
            if stored_token.startswith('Bearer '):
                pure_stored_token = stored_token[7:]
                print(f"   - 存储Token(去掉Bearer前缀)长度: {len(pure_stored_token)} 字符")
                
                if working_token == pure_stored_token:
                    print("   ✅ Token内容一致！(存储的token包含Bearer前缀)")
                elif working_token == stored_token:
                    print("   ✅ Token内容一致！(存储的token不包含Bearer前缀)")
                else:
                    print("   ❌ Token内容不一致")
                    print(f"      工作Token: {working_token[:30]}...{working_token[-20:]}")
                    print(f"      存储Token: {pure_stored_token[:30]}...{pure_stored_token[-20:]}")
            else:
                if working_token == stored_token:
                    print("   ✅ Token内容一致！")
                else:
                    print("   ❌ Token内容不一致")
                    print(f"      工作Token: {working_token[:30]}...{working_token[-20:]}")
                    print(f"      存储Token: {stored_token[:30]}...{stored_token[-20:]}")
                    
    except Exception as e:
        print(f"   ❌ 比较分析失败: {e}")
    
    print("\n" + "=" * 80)
    
    # 4. 提供修复建议
    print("📋 格式分析和建议:")
    print("   1. yinghuasuan.py中的格式: Authorization: 'Bearer <token>'")
    print("   2. 数据库存储应该只存储纯token，不包含'Bearer '前缀")
    print("   3. 在API调用时，由adapter动态添加'Bearer '前缀")
    print("   4. UI保存时应该确保去掉用户输入中可能包含的'Bearer '前缀")
    
    # 5. 检查adapter中的token处理逻辑
    print("\n📋 Adapter中的Token处理逻辑:")
    print("   YingHuaSuanAdapter在_fetch_raw_data方法中:")
    print("   - 检查token是否已包含'Bearer '前缀")
    print("   - 如果没有，则添加'Bearer '前缀")
    print("   - 这样可以兼容两种存储格式")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    check_token_formats()