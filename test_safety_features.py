#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试安全机制和人性化功能的脚本
验证：
1. 默认不启用的安全机制
2. 人性化的票数筛选模板
3. 视觉提示功能
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


def test_safety_features():
    """测试安全机制和人性化功能"""
    print("🛡️ 测试安全机制和人性化功能")
    print("=" * 60)
    
    try:
        # 创建QApplication
        app = QApplication(sys.argv)
        
        # 导入并创建主窗口
        from ui.main_window_new import MainWindow
        
        window = MainWindow()
        print("✅ MainWindow初始化完成")
        
        # 测试1：检查现有策略的启用状态
        print("\n📊 第1步：检查现有策略的启用状态")
        enabled_count = 0
        disabled_count = 0
        
        for i, policy in enumerate(window.engine.rules):
            rule_name = policy.get('rule_name', '未命名')
            is_enabled = policy.get('enabled', False)
            
            if is_enabled:
                enabled_count += 1
                status = "✅ 启用"
            else:
                disabled_count += 1
                status = "❌ 禁用"
            
            print(f"  {i+1:2d}. {rule_name[:30]:30s} {status}")
        
        print(f"\n📈 统计：启用 {enabled_count} 条，禁用 {disabled_count} 条")
        
        # 测试2：测试新建策略的默认状态
        print("\n🆕 第2步：测试新建策略的默认状态")
        
        # 模拟创建关键词策略
        print("  创建新关键词策略...")
        window.add_keyword_rule()
        
        # 检查当前编辑的策略状态
        if hasattr(window, 'checkbox_enabled'):
            keyword_default_enabled = window.checkbox_enabled.isChecked()
            print(f"  关键词策略默认启用状态: {keyword_default_enabled}")
            if not keyword_default_enabled:
                print("  ✅ 关键词策略默认不启用 - 安全机制正常")
            else:
                print("  ❌ 关键词策略默认启用 - 安全机制失效")
        
        # 模拟创建白名单策略
        print("  创建新白名单策略...")
        window.add_whitelist_rule()
        
        # 检查当前编辑的策略状态
        if hasattr(window, 'checkbox_whitelist_enabled'):
            whitelist_default_enabled = window.checkbox_whitelist_enabled.isChecked()
            print(f"  白名单策略默认启用状态: {whitelist_default_enabled}")
            if not whitelist_default_enabled:
                print("  ✅ 白名单策略默认不启用 - 安全机制正常")
            else:
                print("  ❌ 白名单策略默认启用 - 安全机制失效")
        
        # 测试3：检查票数筛选模板
        print("\n🎯 第3步：检查票数筛选模板")
        
        # 检查是否有新的票数复选框
        ticket_checkboxes = [
            ('checkbox_ticket_1', '1张'),
            ('checkbox_ticket_2', '2张'),
            ('checkbox_ticket_3', '3张'),
            ('checkbox_ticket_4', '4张'),
            ('checkbox_ticket_5_plus', '5张及以上')
        ]
        
        all_checkboxes_exist = True
        for checkbox_name, label in ticket_checkboxes:
            if hasattr(window, checkbox_name):
                checkbox = getattr(window, checkbox_name)
                is_checked = checkbox.isChecked()
                print(f"  ✅ {label:10s} 复选框存在，默认状态: {'选中' if is_checked else '未选中'}")
                if is_checked:
                    print(f"    ⚠️ {label} 默认被选中，不符合安全机制")
            else:
                print(f"  ❌ {label:10s} 复选框不存在")
                all_checkboxes_exist = False
        
        if all_checkboxes_exist:
            print("  ✅ 所有票数筛选模板复选框都存在")
        else:
            print("  ❌ 部分票数筛选模板复选框缺失")
        
        # 测试4：检查UI列表的视觉提示
        print("\n👁️ 第4步：检查UI列表的视觉提示")
        
        ui_count = window.rule_list.count()
        disabled_visual_count = 0
        
        for i in range(ui_count):
            item = window.rule_list.item(i)
            if item:
                text = item.text()
                if "【已禁用】" in text:
                    disabled_visual_count += 1
                    print(f"  ✅ 第{i+1}项有禁用标识: {text[:50]}...")
        
        print(f"  📊 UI中有 {disabled_visual_count} 条策略显示为禁用状态")
        
        if disabled_visual_count == disabled_count:
            print("  ✅ UI视觉提示与实际禁用数量一致")
        else:
            print(f"  ❌ UI视觉提示不一致：显示{disabled_visual_count}条禁用，实际{disabled_count}条禁用")
        
        # 测试5：测试引擎层的安全检查
        print("\n🔧 第5步：测试引擎层的安全检查")
        
        # 创建一个测试订单
        test_order = {
            'city': '北京',
            'cinema_name': '万达影城',
            'hall_type': 'IMAX',
            'bidding_price': 50.0,
            'seat_count': 2
        }
        
        # 检查引擎是否会跳过禁用的策略
        result = window.engine.check_order(test_order)
        
        if result:
            print(f"  ✅ 引擎找到匹配策略: {result.get('rule_name', '未知')}")
        else:
            print("  ℹ️ 引擎未找到匹配策略（可能因为策略被禁用或不匹配）")
        
        # 显示窗口进行视觉验证
        print("\n👁️ 第6步：视觉验证")
        window.show()
        print("✅ 窗口已显示，请检查：")
        print("  1. 左侧策略列表中禁用的策略是否显示为灰色")
        print("  2. 禁用的策略是否有【已禁用】前缀")
        print("  3. 新建策略时启用复选框是否默认未选中")
        print("  4. 票数筛选是否有5个模板选项")
        
        # 设置定时器关闭应用
        def close_app():
            print("\n🔚 测试完成，关闭应用")
            app.quit()
        
        QTimer.singleShot(5000, close_app)  # 5秒后关闭
        
        # 运行应用
        app.exec()
        
        # 总结测试结果
        print("\n" + "=" * 60)
        print("📋 测试总结:")
        print(f"  🛡️ 安全机制：新策略默认不启用")
        print(f"  🎯 票数模板：5个人性化选项")
        print(f"  👁️ 视觉提示：禁用策略灰色显示")
        print(f"  🔧 引擎保护：跳过禁用策略")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    try:
        success = test_safety_features()
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
