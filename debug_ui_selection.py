#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试UI规则选择功能
"""

import sys
import logging
from PyQt6.QtWidgets import QApplication
from ui.main_window_new import MainWindow

# 设置详细日志
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def debug_ui():
    """调试UI功能"""
    print("🔍 开始调试UI规则选择功能...")
    
    # 创建应用程序
    app = QApplication(sys.argv)
    
    # 创建主窗口
    window = MainWindow()
    
    # 添加调试信息
    print(f"📋 规则列表项数: {window.rule_list.count()}")
    
    # 检查规则列表内容
    for i in range(window.rule_list.count()):
        item = window.rule_list.item(i)
        print(f"   {i}: {item.text()}")
    
    # 检查信号连接
    print(f"🔗 信号连接检查:")
    try:
        receivers_count = window.rule_list.receivers(window.rule_list.itemClicked)
        print(f"   rule_list.itemClicked 连接数: {receivers_count}")
    except Exception as e:
        print(f"   无法检查信号连接: {e}")
    
    # 检查规则引擎
    print(f"⚙️ 规则引擎状态:")
    print(f"   规则数量: {len(window.engine.rules)}")
    
    for i, rule in enumerate(window.engine.rules):
        rule_name = rule.get('rule_name', '未命名')
        match_mode = rule.get('match_conditions', {}).get('match_mode', 'keywords')
        print(f"   {i}: {rule_name} - {match_mode}")
    
    # 检查UI组件
    print(f"🖥️ UI组件状态:")
    print(f"   stacked_widget 可见: {window.stacked_widget.isVisible()}")
    print(f"   guide_label 可见: {window.guide_label.isVisible()}")
    print(f"   当前卡片索引: {window.stacked_widget.currentIndex()}")
    
    # 手动测试规则选择
    if window.rule_list.count() > 0:
        print(f"\n🧪 手动测试规则选择...")
        first_item = window.rule_list.item(0)
        print(f"   选择第一个规则: {first_item.text()}")
        
        try:
            # 手动调用选择方法
            window.on_rule_selected(first_item)
            print(f"   ✅ 规则选择方法调用成功")
            
            # 检查状态变化
            print(f"   stacked_widget 可见: {window.stacked_widget.isVisible()}")
            print(f"   guide_label 可见: {window.guide_label.isVisible()}")
            print(f"   当前卡片索引: {window.stacked_widget.currentIndex()}")
            print(f"   当前策略类型: {getattr(window, 'current_strategy_type', 'None')}")
            
        except Exception as e:
            print(f"   ❌ 规则选择方法调用失败: {e}")
            import traceback
            traceback.print_exc()
    
    # 显示窗口
    window.show()
    
    print(f"\n💡 调试完成，窗口已显示")
    print(f"   请手动点击规则列表中的项目测试功能")
    print(f"   按 Ctrl+C 退出")
    
    # 运行应用程序
    try:
        sys.exit(app.exec())
    except KeyboardInterrupt:
        print(f"\n👋 用户中断，程序退出")

if __name__ == "__main__":
    debug_ui()
