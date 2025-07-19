#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复建议：EXCLUDE模式的空字符串匹配问题
"""

def fixed_exclude_logic(order_hall_type, exclude_list):
    """
    修复后的EXCLUDE模式匹配逻辑
    """
    print(f"订单厅型: '{order_hall_type}'")
    
    # 清理订单厅型
    order_hall_type_clean = order_hall_type.lower().strip() if order_hall_type else ""
    
    # 【修复】如果订单厅型为空，不应该被任何排除项匹配
    if not order_hall_type_clean:
        print("✅ 订单厅型为空，不被任何排除项匹配")
        return True  # 不排除，允许匹配
    
    hall_matched = False
    for hall_type in exclude_list:
        hall_type_lower = hall_type.lower().strip()
        
        # 【修复】确保两个字符串都不为空才进行包含检查
        if hall_type_lower and order_hall_type_clean:
            if hall_type_lower in order_hall_type_clean or order_hall_type_clean in hall_type_lower:
                hall_matched = True
                print(f"🚫 厅型匹配排除项: '{order_hall_type}' <-> '{hall_type}'")
                break
    
    if hall_matched:
        print("❌ 订单被排除")
        return False
    else:
        print("✅ 订单未被排除")
        return True

# 测试修复效果
exclude_list = ['IMAX', 'VIP', '4DX', '情侣厅', '4D']

print("=== 修复前后对比 ===\n")

test_cases = [
    "",           # 空字符串
    "   ",        # 空白字符串  
    "IMAX",       # 标准IMAX
    "普通厅",      # 普通厅
    "数字厅",      # 数字厅
    "激光厅"       # 激光厅
]

for case in test_cases:
    print(f"测试案例: '{case}'")
    fixed_exclude_logic(case, exclude_list)
    print()

print("=== 修复要点 ===")
print("1. 空字符串和空白字符串不应该被排除")
print("2. 只有明确包含排除关键词的厅型才被排除")
print("3. 这样可以确保空厅型的订单正常参与匹配")