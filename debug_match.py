#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试匹配逻辑 - 测试万达测试规则的EXCLUDE逻辑
"""

def test_exclude_logic(order_hall_type, exclude_list):
    """
    测试EXCLUDE模式的匹配逻辑
    """
    print(f"测试订单厅型: '{order_hall_type}'")
    print(f"排除列表: {exclude_list}")
    
    # 模拟引擎中的逻辑
    order_hall_type_lower = order_hall_type.lower().strip()
    hall_matched = False
    
    for hall_type in exclude_list:
        hall_type_lower = hall_type.lower().strip()
        print(f"  检查排除项: '{hall_type}' (小写: '{hall_type_lower}')")
        
        # 双向包含检查
        condition1 = hall_type_lower in order_hall_type_lower
        condition2 = order_hall_type_lower in hall_type_lower
        
        print(f"    '{hall_type_lower}' in '{order_hall_type_lower}': {condition1}")
        print(f"    '{order_hall_type_lower}' in '{hall_type_lower}': {condition2}")
        
        if condition1 or condition2:
            hall_matched = True
            print(f"    ✅ 匹配到排除项: {hall_type}")
            break
        else:
            print(f"    ❌ 未匹配排除项: {hall_type}")
    
    if hall_matched:
        print("🚫 结果: 订单被排除，规则不匹配")
        return False
    else:
        print("✅ 结果: 订单未被排除，规则可能匹配")
        return True

# 测试用例
exclude_list = ['IMAX', 'VIP', '4DX', '情侣厅', '4D']

print("=== 测试案例 ===\n")

# 测试1: 标准IMAX
print("1. 标准IMAX测试:")
test_exclude_logic("IMAX", exclude_list)
print()

# 测试2: 小写imax
print("2. 小写imax测试:")
test_exclude_logic("imax", exclude_list)
print()

# 测试3: IMAX厅
print("3. IMAX厅测试:")
test_exclude_logic("IMAX厅", exclude_list)
print()

# 测试4: 普通厅
print("4. 普通厅测试:")
test_exclude_logic("普通厅", exclude_list)
print()

# 测试5: 数字厅
print("5. 数字厅测试:")
test_exclude_logic("数字厅", exclude_list)
print()

# 测试6: 空字符串
print("6. 空字符串测试:")
test_exclude_logic("", exclude_list)
print()

# 测试7: 可能的问题案例
print("7. 可能的问题案例:")
test_exclude_logic("激光厅", exclude_list)
print()