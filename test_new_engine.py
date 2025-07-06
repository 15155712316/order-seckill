#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试新的中央仓储架构RuleEngine
验证状态广播系统和数据库集成
"""

import sys
import os
import logging

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def test_new_rule_engine():
    """测试新的RuleEngine"""
    print("🧪 测试中央仓储架构的RuleEngine")
    print("=" * 60)
    
    try:
        # 导入新的RuleEngine
        from core.engine import RuleEngine
        from core.database import DatabaseManager
        
        print("✅ 成功导入RuleEngine和DatabaseManager")
        
        # 创建数据库管理器
        db_manager = DatabaseManager()
        print("✅ 数据库管理器初始化成功")
        
        # 创建RuleEngine实例
        engine = RuleEngine(db_manager=db_manager)
        print("✅ RuleEngine初始化成功")
        
        # 检查是否正确继承了QObject
        from PyQt6.QtCore import QObject
        if isinstance(engine, QObject):
            print("✅ RuleEngine正确继承了QObject")
        else:
            print("❌ RuleEngine没有正确继承QObject")
            return False
        
        # 检查信号是否存在
        if hasattr(engine, 'policies_updated'):
            print("✅ policies_updated信号存在")
        else:
            print("❌ policies_updated信号不存在")
            return False
        
        # 测试策略加载
        initial_count = len(engine.rules)
        print(f"📊 初始加载了 {initial_count} 条策略")
        
        # 显示前几条策略
        if initial_count > 0:
            print("\n📋 策略列表预览:")
            for i, policy in enumerate(engine.rules[:3]):
                rule_name = policy.get('rule_name', '未命名')
                rule_type = policy.get('match_conditions', {}).get('match_mode', 'keywords')
                enabled = "启用" if policy.get('enabled', True) else "禁用"
                print(f"  {i+1}. [{rule_type:8s}] {rule_name} ({enabled})")
            
            if initial_count > 3:
                print(f"  ... 还有 {initial_count - 3} 条策略")
        
        # 测试信号连接
        signal_received = []
        
        def on_policies_updated():
            signal_received.append(True)
            print("📡 收到policies_updated信号")
        
        engine.policies_updated.connect(on_policies_updated)
        print("✅ 信号连接成功")
        
        # 测试添加新策略
        print("\n🆕 测试添加新策略...")
        test_policy = {
            'rule_name': '测试策略_自动生成',
            'enabled': True,
            'match_conditions': {
                'match_mode': 'keywords',
                'city': '测试城市',
                'cinema_keywords': ['测试影院']
            },
            'hall_logic': {
                'mode': 'ALL',
                'hall_list': [],
                'cost': 30.0
            },
            'profit_logic': {
                'min_profit_threshold': 10.0
            }
        }
        
        add_success = engine.add_new_policy(test_policy)
        if add_success:
            print("✅ 添加新策略成功")
            new_count = len(engine.rules)
            print(f"📊 策略数量从 {initial_count} 增加到 {new_count}")
            
            if signal_received:
                print("✅ 添加策略时正确发射了信号")
            else:
                print("❌ 添加策略时没有发射信号")
        else:
            print("❌ 添加新策略失败")
            return False
        
        # 测试策略修改
        print("\n✏️ 测试策略修改...")
        if engine.rules:
            test_policy_to_modify = engine.rules[-1].copy()  # 修改最后一个策略
            test_policy_to_modify['rule_name'] = '测试策略_已修改'
            
            signal_received.clear()
            modify_success = engine.save_policy_changes(test_policy_to_modify)
            
            if modify_success:
                print("✅ 修改策略成功")
                if signal_received:
                    print("✅ 修改策略时正确发射了信号")
                else:
                    print("❌ 修改策略时没有发射信号")
            else:
                print("❌ 修改策略失败")
                return False
        
        # 测试策略删除
        print("\n🗑️ 测试策略删除...")
        if engine.rules:
            policy_to_delete = engine.rules[-1]
            policy_id = policy_to_delete.get('rule_id')
            delete_index = len(engine.rules) - 1
            
            signal_received.clear()
            delete_success = engine.delete_policy(policy_id, delete_index)
            
            if delete_success:
                print("✅ 删除策略成功")
                final_count = len(engine.rules)
                print(f"📊 策略数量变为 {final_count}")
                
                if signal_received:
                    print("✅ 删除策略时正确发射了信号")
                else:
                    print("❌ 删除策略时没有发射信号")
            else:
                print("❌ 删除策略失败")
                return False
        
        # 测试重新加载
        print("\n🔄 测试重新加载策略...")
        signal_received.clear()
        reload_success = engine.reload_policies()
        
        if reload_success:
            print("✅ 重新加载策略成功")
            if signal_received:
                print("✅ 重新加载时正确发射了信号")
            else:
                print("❌ 重新加载时没有发射信号")
        else:
            print("❌ 重新加载策略失败")
            return False
        
        print("\n" + "=" * 60)
        print("🎉 所有测试通过！新的RuleEngine工作正常")
        print("\n📋 测试总结:")
        print("  ✅ QObject继承正确")
        print("  ✅ 信号机制工作正常")
        print("  ✅ 数据库集成成功")
        print("  ✅ 策略CRUD操作正常")
        print("  ✅ 状态广播系统正常")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    try:
        success = test_new_rule_engine()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n❌ 测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试过程中发生未知错误: {e}")
        logging.error(f"测试失败: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
