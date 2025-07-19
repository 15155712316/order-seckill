#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试Bearer Token前缀处理修复
"""

def test_token_processing():
    """测试token处理逻辑"""
    print("=== Bearer Token前缀处理测试 ===")
    
    # 测试用例
    test_cases = [
        # (输入token, 期望输出token, 描述)
        ("eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...", "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...", "纯token输入"),
        ("Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...", "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...", "包含Bearer前缀的输入"),
        ("bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...", "bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...", "小写bearer前缀（不处理）"),
        ("", "", "空输入"),
        ("Bearer ", "", "只有Bearer前缀"),
        ("Bearer", "Bearer", "不完整的Bearer前缀"),
    ]
    
    def process_bearer_token(input_token):
        """模拟修复后的token处理逻辑"""
        token = input_token.strip()
        if token.startswith('Bearer '):
            token = token[7:]  # 去掉"Bearer "前缀
            print(f"    ✅ 检测到Bearer前缀，已自动去除")
        return token
    
    def build_auth_header(stored_token):
        """模拟adapter中的Authorization头构建逻辑"""
        auth_header = stored_token
        if not auth_header.startswith('Bearer '):
            auth_header = f'Bearer {auth_header}'
        return auth_header
    
    # 运行测试用例
    for i, (input_token, expected_stored, description) in enumerate(test_cases, 1):
        print(f"\n测试用例 {i}: {description}")
        print(f"  输入: '{input_token}'")
        
        # 模拟UI保存逻辑
        stored_token = process_bearer_token(input_token)
        print(f"  存储: '{stored_token}'")
        print(f"  期望: '{expected_stored}'")
        
        # 验证存储结果
        if stored_token == expected_stored:
            print(f"  ✅ 存储正确")
        else:
            print(f"  ❌ 存储错误")
        
        # 模拟adapter构建Authorization头
        if stored_token:  # 只有非空token才构建Authorization头
            auth_header = build_auth_header(stored_token)
            print(f"  最终Authorization头: '{auth_header}'")
            
            # 验证最终结果
            if stored_token and auth_header == f"Bearer {stored_token}":
                print(f"  ✅ Authorization头正确")
            else:
                print(f"  ❌ Authorization头错误")
        
        print(f"  {'-' * 50}")

if __name__ == "__main__":
    test_token_processing()