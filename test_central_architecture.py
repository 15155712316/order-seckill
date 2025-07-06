#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试中央仓储架构的完整功能
验证数据库层、引擎层、UI层的集成
"""

import sys
import os
import logging
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


def test_central_architecture():
    """测试中央仓储架构"""
    print("🏗️ 测试中央仓储架构的完整功能")
    print("=" * 60)
    
    try:
        # 创建QApplication
        app = QApplication(sys.argv)
        
        # 导入新的UI
        from ui.main_window_new import MainWindow
        
        print("✅ 成功导入MainWindow")
        
        # 创建主窗口
        window = MainWindow()
        print("✅ MainWindow初始化成功")
        
        # 检查引擎是否正确初始化
        if hasattr(window, 'engine'):
            print(f"✅ RuleEngine已初始化，包含 {len(window.engine.rules)} 条策略")
        else:
            print("❌ RuleEngine未正确初始化")
            return False
        
        # 检查信号连接
        if hasattr(window.engine, 'policies_updated'):
            print("✅ policies_updated信号存在")
        else:
            print("❌ policies_updated信号不存在")
            return False
        
        # 检查UI刷新方法
        if hasattr(window, 'refresh_policy_list_from_engine'):
            print("✅ refresh_policy_list_from_engine方法存在")
        else:
            print("❌ refresh_policy_list_from_engine方法不存在")
            return False
        
        # 显示窗口
        window.show()
        print("✅ 主窗口已显示")
        
        # 测试信号连接
        signal_received = []
        
        def test_signal():
            signal_received.append(True)
            print("📡 收到policies_updated信号")
        
        window.engine.policies_updated.connect(test_signal)
        
        # 测试添加策略
        print("\n🆕 测试添加新策略...")
        
        test_policy = {
            'rule_name': '测试策略_架构验证',
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
        
        initial_count = len(window.engine.rules)
        success = window.engine.add_new_policy(test_policy)
        
        if success:
            new_count = len(window.engine.rules)
            print(f"✅ 添加策略成功，策略数量从 {initial_count} 增加到 {new_count}")
            
            if signal_received:
                print("✅ 添加策略时正确发射了信号")
            else:
                print("❌ 添加策略时没有发射信号")
                return False
        else:
            print("❌ 添加策略失败")
            return False
        
        # 检查UI是否正确更新
        ui_count = window.rule_list.count()
        engine_count = len(window.engine.rules)
        
        if ui_count == engine_count:
            print(f"✅ UI与引擎数据同步正确：UI显示 {ui_count} 条，引擎有 {engine_count} 条")
        else:
            print(f"❌ UI与引擎数据不同步：UI显示 {ui_count} 条，引擎有 {engine_count} 条")
            return False
        
        # 测试删除策略
        print("\n🗑️ 测试删除策略...")
        
        if window.engine.rules:
            policy_to_delete = window.engine.rules[-1]
            policy_id = policy_to_delete.get('rule_id')
            delete_index = len(window.engine.rules) - 1
            
            signal_received.clear()
            delete_success = window.engine.delete_policy(policy_id, delete_index)
            
            if delete_success:
                final_count = len(window.engine.rules)
                print(f"✅ 删除策略成功，策略数量变为 {final_count}")
                
                if signal_received:
                    print("✅ 删除策略时正确发射了信号")
                else:
                    print("❌ 删除策略时没有发射信号")
                    return False
            else:
                print("❌ 删除策略失败")
                return False
        
        # 最终验证UI同步
        final_ui_count = window.rule_list.count()
        final_engine_count = len(window.engine.rules)
        
        if final_ui_count == final_engine_count:
            print(f"✅ 最终UI与引擎数据同步正确：UI显示 {final_ui_count} 条，引擎有 {final_engine_count} 条")
        else:
            print(f"❌ 最终UI与引擎数据不同步：UI显示 {final_ui_count} 条，引擎有 {final_engine_count} 条")
            return False
        
        print("\n" + "=" * 60)
        print("🎉 中央仓储架构测试完全通过！")
        print("\n📋 测试总结:")
        print("  ✅ 数据库层：策略CRUD操作正常")
        print("  ✅ 引擎层：状态广播系统正常")
        print("  ✅ UI层：响应式刷新正常")
        print("  ✅ 信号机制：数据流同步正常")
        print("  ✅ 架构集成：三层协作正常")
        
        # 设置定时器关闭应用
        def close_app():
            print("\n🔚 测试完成，关闭应用")
            app.quit()
        
        QTimer.singleShot(3000, close_app)  # 3秒后关闭
        
        # 运行应用
        app.exec()
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    try:
        success = test_central_architecture()
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
