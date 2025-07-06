#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
诊断UI显示问题的专用脚本
检查策略列表显示的各个环节
"""

import sys
import os
import logging
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 设置详细日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


def diagnose_ui_display():
    """诊断UI显示问题"""
    print("🔍 诊断策略列表显示问题")
    print("=" * 60)
    
    try:
        # 创建QApplication
        app = QApplication(sys.argv)
        
        # 1. 首先测试数据库层
        print("\n📊 第1步：检查数据库层")
        from core.database import DatabaseManager
        
        db_manager = DatabaseManager()
        policies = db_manager.load_all_policies()
        print(f"✅ 数据库中有 {len(policies)} 条策略")
        
        if policies:
            print("📋 前3条策略预览:")
            for i, policy in enumerate(policies[:3]):
                rule_name = policy.get('rule_name', '未命名')
                rule_type = policy.get('match_conditions', {}).get('match_mode', 'keywords')
                print(f"  {i+1}. [{rule_type}] {rule_name}")
        else:
            print("❌ 数据库中没有策略数据！")
            return False
        
        # 2. 测试引擎层
        print("\n🔧 第2步：检查引擎层")
        from core.engine import RuleEngine
        
        engine = RuleEngine(db_manager=db_manager)
        print(f"✅ 引擎加载了 {len(engine.rules)} 条策略")
        
        if len(engine.rules) != len(policies):
            print(f"⚠️ 数据不一致：数据库有{len(policies)}条，引擎有{len(engine.rules)}条")
        
        # 测试信号
        signal_received = []
        
        def test_signal():
            signal_received.append(True)
            print("📡 收到policies_updated信号")
        
        engine.policies_updated.connect(test_signal)
        
        # 手动触发信号
        engine.policies_updated.emit()
        
        if signal_received:
            print("✅ 信号机制工作正常")
        else:
            print("❌ 信号机制有问题")
            return False
        
        # 3. 测试UI层
        print("\n🎨 第3步：检查UI层")
        from ui.main_window_new import MainWindow
        
        window = MainWindow()
        print("✅ MainWindow初始化完成")
        
        # 检查UI组件
        if hasattr(window, 'rule_list'):
            ui_count = window.rule_list.count()
            print(f"📋 UI列表显示 {ui_count} 条策略")
            
            if ui_count > 0:
                print("📋 UI列表内容预览:")
                for i in range(min(3, ui_count)):
                    item = window.rule_list.item(i)
                    if item:
                        print(f"  {i+1}. {item.text()}")
            else:
                print("❌ UI列表为空！")
        else:
            print("❌ rule_list组件不存在")
            return False
        
        # 4. 测试响应式刷新方法
        print("\n🔄 第4步：测试响应式刷新")
        
        if hasattr(window, 'refresh_policy_list_from_engine'):
            print("✅ refresh_policy_list_from_engine方法存在")
            
            # 清空列表然后手动刷新
            window.rule_list.clear()
            print(f"清空后UI列表项数: {window.rule_list.count()}")
            
            # 手动调用刷新方法
            window.refresh_policy_list_from_engine()
            refreshed_count = window.rule_list.count()
            print(f"刷新后UI列表项数: {refreshed_count}")
            
            if refreshed_count == len(engine.rules):
                print("✅ 响应式刷新工作正常")
            else:
                print(f"❌ 响应式刷新有问题：期望{len(engine.rules)}条，实际{refreshed_count}条")
                return False
        else:
            print("❌ refresh_policy_list_from_engine方法不存在")
            return False
        
        # 5. 测试信号连接
        print("\n📡 第5步：测试信号连接")
        
        # 清空列表
        window.rule_list.clear()
        print(f"清空后UI列表项数: {window.rule_list.count()}")
        
        # 通过信号触发刷新
        engine.policies_updated.emit()
        signal_triggered_count = window.rule_list.count()
        print(f"信号触发后UI列表项数: {signal_triggered_count}")
        
        if signal_triggered_count == len(engine.rules):
            print("✅ 信号连接工作正常")
        else:
            print(f"❌ 信号连接有问题：期望{len(engine.rules)}条，实际{signal_triggered_count}条")
            return False
        
        # 6. 显示窗口进行视觉验证
        print("\n👁️ 第6步：视觉验证")
        window.show()
        print("✅ 窗口已显示，请检查左侧策略列表")
        
        # 最终统计
        final_ui_count = window.rule_list.count()
        final_engine_count = len(engine.rules)
        final_db_count = len(policies)
        
        print("\n" + "=" * 60)
        print("📊 最终统计:")
        print(f"  数据库策略数: {final_db_count}")
        print(f"  引擎策略数: {final_engine_count}")
        print(f"  UI显示策略数: {final_ui_count}")
        
        if final_ui_count == final_engine_count == final_db_count:
            print("🎉 所有层级数据一致，UI显示正常！")
            
            # 显示策略列表内容
            if final_ui_count > 0:
                print("\n📋 完整策略列表:")
                for i in range(final_ui_count):
                    item = window.rule_list.item(i)
                    if item:
                        print(f"  {i+1:2d}. {item.text()}")
            
            # 设置定时器关闭应用
            def close_app():
                print("\n🔚 诊断完成，关闭应用")
                app.quit()
            
            QTimer.singleShot(5000, close_app)  # 5秒后关闭
            
            # 运行应用
            app.exec()
            
            return True
        else:
            print("❌ 数据不一致，存在问题")
            return False
        
    except Exception as e:
        print(f"❌ 诊断失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    try:
        success = diagnose_ui_display()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n❌ 诊断被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 诊断过程中发生未知错误: {e}")
        logging.error(f"诊断失败: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
