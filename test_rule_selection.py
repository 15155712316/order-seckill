#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试规则选择功能
"""

import sys
import logging
from PyQt6.QtWidgets import QApplication, QListWidgetItem
from PyQt6.QtCore import Qt

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_rule_selection():
    """测试规则选择功能"""
    print("🧪 测试规则选择功能...")
    
    try:
        from ui.main_window_new import MainWindow
        
        # 创建应用程序（不显示窗口）
        app = QApplication(sys.argv)
        
        # 创建主窗口
        window = MainWindow()
        
        print(f"✅ 主窗口创建成功")
        print(f"📋 规则列表项数: {window.rule_list.count()}")
        
        # 检查规则列表内容
        for i in range(window.rule_list.count()):
            item = window.rule_list.item(i)
            print(f"   {i}: {item.text()}")
        
        # 测试手动选择第一个规则
        if window.rule_list.count() > 0:
            print(f"\n🎯 测试选择第一个规则...")
            first_item = window.rule_list.item(0)
            print(f"   规则名称: {first_item.text()}")
            
            # 检查初始状态
            print(f"   初始状态:")
            print(f"     stacked_widget 可见: {window.stacked_widget.isVisible()}")
            print(f"     guide_label 可见: {window.guide_label.isVisible()}")
            print(f"     当前策略类型: {getattr(window, 'current_strategy_type', 'None')}")
            
            # 手动调用选择方法
            try:
                window.on_rule_selected(first_item)
                print(f"   ✅ 规则选择方法调用成功")
                
                # 检查状态变化
                print(f"   选择后状态:")
                print(f"     stacked_widget 可见: {window.stacked_widget.isVisible()}")
                print(f"     guide_label 可见: {window.guide_label.isVisible()}")
                print(f"     当前卡片索引: {window.stacked_widget.currentIndex()}")
                print(f"     当前策略类型: {getattr(window, 'current_strategy_type', 'None')}")
                
                # 检查当前规则
                if hasattr(window, 'current_rule') and window.current_rule:
                    print(f"     当前规则ID: {window.current_rule.get('rule_id', 'None')}")
                    print(f"     当前规则名称: {window.current_rule.get('rule_name', 'None')}")
                else:
                    print(f"     ❌ 当前规则未设置")
                
            except Exception as e:
                print(f"   ❌ 规则选择方法调用失败: {e}")
                import traceback
                traceback.print_exc()
        
        # 测试白名单规则（如果存在）
        whitelist_item = None
        for i in range(window.rule_list.count()):
            item = window.rule_list.item(i)
            if item.text().startswith('[白名单]'):
                whitelist_item = item
                break
        
        if whitelist_item:
            print(f"\n🎯 测试选择白名单规则...")
            print(f"   规则名称: {whitelist_item.text()}")
            
            try:
                window.on_rule_selected(whitelist_item)
                print(f"   ✅ 白名单规则选择成功")
                
                # 检查白名单特有的状态
                print(f"   白名单状态:")
                print(f"     当前策略类型: {getattr(window, 'current_strategy_type', 'None')}")
                print(f"     当前卡片索引: {window.stacked_widget.currentIndex()}")
                
                if hasattr(window, 'current_policy_id'):
                    print(f"     当前策略ID: {window.current_policy_id}")
                    cinema_count = window.engine.get_whitelist_cinema_count(window.current_policy_id)
                    print(f"     影院数量: {cinema_count}")
                
            except Exception as e:
                print(f"   ❌ 白名单规则选择失败: {e}")
                import traceback
                traceback.print_exc()
        
        print(f"\n📊 测试总结:")
        print(f"   规则总数: {len(window.engine.rules)}")
        print(f"   UI规则项数: {window.rule_list.count()}")
        print(f"   信号连接: {'✅' if hasattr(window, 'rule_list') else '❌'}")
        
        # 检查具体的规则类型
        keyword_count = 0
        whitelist_count = 0
        
        for rule in window.engine.rules:
            match_mode = rule.get('match_conditions', {}).get('match_mode', 'keywords')
            if match_mode == 'whitelist':
                whitelist_count += 1
            else:
                keyword_count += 1
        
        print(f"   关键词策略: {keyword_count} 个")
        print(f"   白名单策略: {whitelist_count} 个")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_rule_selection()
    if success:
        print(f"\n✅ 规则选择功能测试完成")
    else:
        print(f"\n❌ 规则选择功能测试失败")
