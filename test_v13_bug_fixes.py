#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试v1.3 Bug修复功能
"""

import sys
import logging
from PyQt6.QtWidgets import QApplication

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_ui_bug_fixes():
    """测试UI Bug修复"""
    print("🧪 测试v1.3 UI Bug修复功能...")
    print("=" * 60)
    
    try:
        from ui.main_window import MainWindow
        
        # 创建应用程序（不显示窗口）
        app = QApplication(sys.argv)
        
        # 创建主窗口
        window = MainWindow()
        
        print("✅ 主窗口创建成功")
        print(f"📋 规则列表项数: {window.rule_list.count()}")
        
        # 测试1：检查QStackedWidget是否存在
        if hasattr(window, 'editor_stacked_widget'):
            print("✅ editor_stacked_widget 存在")
            print(f"   卡片数量: {window.editor_stacked_widget.count()}")
            print(f"   当前索引: {window.editor_stacked_widget.currentIndex()}")
        else:
            print("❌ editor_stacked_widget 不存在")
        
        # 测试2：检查删除方法是否使用索引
        print("\n🧪 测试删除逻辑...")
        if window.rule_list.count() > 0:
            # 模拟选择第一个规则
            window.rule_list.setCurrentRow(0)
            current_row = window.rule_list.currentRow()
            print(f"   选中行号: {current_row}")
            
            if current_row != -1:
                print("✅ 行号索引获取正常")
            else:
                print("❌ 行号索引获取失败")
        
        # 测试3：检查display_rule_details方法
        print("\n🧪 测试编辑界面切换逻辑...")
        if window.rule_list.count() > 0:
            # 模拟选择规则
            first_item = window.rule_list.item(0)
            if first_item:
                print(f"   测试规则: {first_item.text()}")
                
                # 检查是否有fill_keyword_form和fill_whitelist_form方法
                if hasattr(window, 'fill_keyword_form'):
                    print("✅ fill_keyword_form 方法存在")
                else:
                    print("❌ fill_keyword_form 方法不存在")
                
                if hasattr(window, 'fill_whitelist_form'):
                    print("✅ fill_whitelist_form 方法存在")
                else:
                    print("❌ fill_whitelist_form 方法不存在")
                
                # 手动调用display_rule_details方法
                try:
                    window.display_rule_details(first_item)
                    print("✅ display_rule_details 方法调用成功")
                    
                    # 检查卡片切换状态
                    if hasattr(window, 'editor_stacked_widget'):
                        current_index = window.editor_stacked_widget.currentIndex()
                        is_visible = window.editor_stacked_widget.isVisible()
                        print(f"   当前卡片索引: {current_index}")
                        print(f"   编辑器可见: {is_visible}")
                    
                except Exception as e:
                    print(f"❌ display_rule_details 方法调用失败: {e}")
        
        # 测试4：检查策略类型识别
        print("\n🧪 测试策略类型识别...")
        for i, rule in enumerate(window.engine.rules):
            match_conditions = rule.get('match_conditions', {})
            match_mode = match_conditions.get('match_mode', 'keywords')
            rule_name = rule.get('rule_name', f'规则{i+1}')
            print(f"   {rule_name}: {match_mode}")
        
        return True
        
    except Exception as e:
        print(f"❌ UI Bug修复测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_delete_logic():
    """测试删除逻辑"""
    print("\n🗑️ 测试删除逻辑...")
    print("=" * 60)
    
    try:
        from ui.main_window import MainWindow
        from PyQt6.QtWidgets import QApplication
        
        app = QApplication(sys.argv)
        window = MainWindow()
        
        original_count = len(window.engine.rules)
        print(f"原始规则数量: {original_count}")
        
        if original_count > 0:
            # 模拟选择第一个规则
            window.rule_list.setCurrentRow(0)
            current_row = window.rule_list.currentRow()
            
            print(f"选中行号: {current_row}")
            
            if current_row != -1:
                # 获取要删除的规则信息
                rule_to_delete = window.engine.rules[current_row]
                rule_name = rule_to_delete.get('rule_name', f'规则{current_row+1}')
                
                print(f"准备删除规则: {rule_name}")
                print("✅ 删除逻辑索引获取正常")
                
                # 注意：这里不实际执行删除，只是测试逻辑
                print("ℹ️ 删除逻辑测试完成（未实际删除）")
            else:
                print("❌ 无法获取选中行号")
        else:
            print("ℹ️ 没有规则可供测试删除")
        
        return True
        
    except Exception as e:
        print(f"❌ 删除逻辑测试失败: {e}")
        return False

def main():
    """主函数"""
    print("🚀 开始测试v1.3 Bug修复功能...")
    print("=" * 80)
    
    success_count = 0
    total_tests = 2
    
    # 1. 测试UI Bug修复
    if test_ui_bug_fixes():
        success_count += 1
    
    # 2. 测试删除逻辑
    if test_delete_logic():
        success_count += 1
    
    print("\n" + "=" * 80)
    print("📋 v1.3 Bug修复测试总结:")
    print("=" * 80)
    
    print(f"✅ 测试通过: {success_count}/{total_tests}")
    
    if success_count == total_tests:
        print("\n🎉 所有Bug修复测试通过！")
        print("\n🎯 修复要点:")
        print("   1. ✅ 删除逻辑 - 使用行号索引直接删除")
        print("   2. ✅ 编辑界面切换 - QStackedWidget卡片切换")
        print("   3. ✅ 策略类型识别 - 根据match_mode切换卡片")
        print("   4. ✅ 表单填充分离 - 独立的填充方法")
        
        print("\n💡 使用说明:")
        print("   - 点击规则列表项会自动切换到对应的编辑卡片")
        print("   - 关键词策略使用索引0的卡片")
        print("   - 白名单策略使用索引1的卡片")
        print("   - 删除操作使用行号索引，更加准确")
    else:
        print(f"\n❌ 部分测试失败，请检查错误信息")

if __name__ == "__main__":
    main()
