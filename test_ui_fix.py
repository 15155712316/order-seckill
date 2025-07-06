#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试UI显示修复效果的简单脚本
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


def test_ui_fix():
    """测试UI显示修复效果"""
    print("🔧 测试UI显示修复效果")
    print("=" * 50)
    
    try:
        # 创建QApplication
        app = QApplication(sys.argv)
        
        # 导入并创建主窗口
        from ui.main_window_new import MainWindow
        
        window = MainWindow()
        print(f"✅ MainWindow初始化完成")
        
        # 检查策略数量
        engine_count = len(window.engine.rules)
        ui_count = window.rule_list.count()
        
        print(f"📊 引擎策略数: {engine_count}")
        print(f"📊 UI显示策略数: {ui_count}")
        
        if ui_count == engine_count and ui_count > 0:
            print("🎉 UI显示修复成功！")
            
            # 显示前几条策略
            print("\n📋 策略列表预览:")
            for i in range(min(5, ui_count)):
                item = window.rule_list.item(i)
                if item:
                    print(f"  {i+1:2d}. {item.text()}")
            
            if ui_count > 5:
                print(f"  ... 还有 {ui_count - 5} 条策略")
            
            # 显示窗口
            window.show()
            print(f"\n👁️ 窗口已显示，请检查左侧策略列表")
            
            # 设置定时器关闭应用
            def close_app():
                print("\n🔚 测试完成，关闭应用")
                app.quit()
            
            QTimer.singleShot(3000, close_app)  # 3秒后关闭
            
            # 运行应用
            app.exec()
            
            return True
        else:
            print(f"❌ UI显示仍有问题：引擎有{engine_count}条，UI显示{ui_count}条")
            return False
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    try:
        success = test_ui_fix()
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
