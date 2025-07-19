#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
影划算平台日志监控脚本
"""

import os
import time

def monitor_yinghuasuan_log():
    """监控影划算平台日志文件"""
    log_file = "yinghuasuan.log"
    
    print("🔍 影划算平台日志监控")
    print("=" * 60)
    
    if not os.path.exists(log_file):
        print("❌ yinghuasuan.log 文件不存在")
        return
    
    print(f"✅ 找到日志文件: {log_file}")
    
    # 获取当前文件大小
    initial_size = os.path.getsize(log_file)
    print(f"📋 当前文件大小: {initial_size} 字节")
    
    # 读取并显示当前内容
    print("\n📄 当前日志内容:")
    print("-" * 60)
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read()
            if content.strip():
                print(content)
            else:
                print("(文件为空)")
    except Exception as e:
        print(f"❌ 读取文件失败: {e}")
    
    print("-" * 60)
    print("\n🔄 监控模式 (Ctrl+C 退出)")
    print("等待新的API调用日志...")
    
    try:
        last_size = initial_size
        while True:
            time.sleep(2)  # 每2秒检查一次
            
            current_size = os.path.getsize(log_file)
            if current_size > last_size:
                print(f"\n🆕 检测到新日志 ({current_size - last_size} 字节)")
                
                # 读取新增内容
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        f.seek(last_size)  # 跳到上次读取的位置
                        new_content = f.read()
                        if new_content.strip():
                            print("新增内容:")
                            print("-" * 40)
                            print(new_content)
                            print("-" * 40)
                except Exception as e:
                    print(f"❌ 读取新内容失败: {e}")
                
                last_size = current_size
                
    except KeyboardInterrupt:
        print("\n\n👋 监控已停止")

if __name__ == "__main__":
    monitor_yinghuasuan_log()