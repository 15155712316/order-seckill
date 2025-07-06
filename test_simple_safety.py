#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单测试安全机制的脚本
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def test_simple_safety():
    """简单测试安全机制"""
    print("🛡️ 简单测试安全机制")
    print("=" * 40)
    
    try:
        # 测试数据库层
        print("📊 测试数据库层...")
        from core.database import DatabaseManager
        
        db_manager = DatabaseManager()
        policies = db_manager.load_all_policies()
        print(f"✅ 数据库中有 {len(policies)} 条策略")
        
        # 检查策略启用状态
        enabled_count = 0
        disabled_count = 0
        
        for policy in policies:
            is_enabled = policy.get('enabled', False)
            if is_enabled:
                enabled_count += 1
            else:
                disabled_count += 1
        
        print(f"📈 启用: {enabled_count} 条，禁用: {disabled_count} 条")
        
        # 测试引擎层
        print("\n🔧 测试引擎层...")
        from core.engine import RuleEngine
        
        engine = RuleEngine(db_manager=db_manager)
        print(f"✅ 引擎加载了 {len(engine.rules)} 条策略")
        
        # 测试引擎的安全检查
        test_order = {
            'city': '北京',
            'cinema_name': '万达影城',
            'hall_type': 'IMAX',
            'bidding_price': 50.0,
            'seat_count': 2
        }
        
        result = engine.check_order(test_order)
        if result:
            print(f"✅ 引擎找到匹配策略: {result.get('rule_name', '未知')}")
        else:
            print("ℹ️ 引擎未找到匹配策略")
        
        print("\n" + "=" * 40)
        print("🎉 基础测试完成！")
        print("📋 功能状态:")
        print(f"  🛡️ 数据库策略: {len(policies)} 条")
        print(f"  🔧 引擎策略: {len(engine.rules)} 条")
        print(f"  ✅ 启用策略: {enabled_count} 条")
        print(f"  ❌ 禁用策略: {disabled_count} 条")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    try:
        success = test_simple_safety()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
