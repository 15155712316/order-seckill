#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据迁移脚本：将rules.json中的策略数据迁移到SQLite数据库
【中央仓储架构】第一阶段的数据迁移工具
"""

import json
import logging
import os
import sys
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.database import DatabaseManager

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


def migrate_rules_to_database():
    """将rules.json中的策略迁移到数据库"""
    
    print("🚀 开始数据迁移：rules.json → SQLite数据库")
    print("=" * 60)
    
    # 1. 检查rules.json文件是否存在
    rules_file = "rules.json"
    if not os.path.exists(rules_file):
        print(f"❌ 错误：{rules_file} 文件不存在")
        return False
    
    # 2. 读取rules.json文件
    try:
        with open(rules_file, 'r', encoding='utf-8') as f:
            rules_data = json.load(f)
        print(f"✅ 成功读取 {rules_file}，包含 {len(rules_data)} 条策略")
    except Exception as e:
        print(f"❌ 读取 {rules_file} 失败: {e}")
        return False
    
    # 3. 初始化数据库管理器
    try:
        db_manager = DatabaseManager()
        print("✅ 数据库管理器初始化成功")
    except Exception as e:
        print(f"❌ 数据库初始化失败: {e}")
        return False
    
    # 4. 检查数据库中是否已有策略数据
    existing_policies = db_manager.load_all_policies()
    if existing_policies:
        print(f"⚠️ 数据库中已存在 {len(existing_policies)} 条策略")
        response = input("是否要覆盖现有数据？(y/N): ").strip().lower()
        if response != 'y':
            print("❌ 迁移已取消")
            return False
    
    # 5. 开始迁移数据
    print(f"\n📦 开始迁移 {len(rules_data)} 条策略...")
    
    success_count = 0
    error_count = 0
    
    for i, rule in enumerate(rules_data):
        try:
            # 添加policy_order字段
            rule['policy_order'] = i + 1
            
            # 确保有created_at字段
            if 'created_at' not in rule:
                rule['created_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 保存到数据库
            success = db_manager.save_policy(rule)
            
            if success:
                success_count += 1
                rule_name = rule.get('rule_name', '未命名')
                rule_type = rule.get('match_conditions', {}).get('match_mode', 'keywords')
                print(f"  ✅ [{i+1:2d}] [{rule_type:8s}] {rule_name}")
            else:
                error_count += 1
                print(f"  ❌ [{i+1:2d}] 保存失败: {rule.get('rule_name', '未命名')}")
                
        except Exception as e:
            error_count += 1
            print(f"  ❌ [{i+1:2d}] 迁移失败: {e}")
    
    # 6. 迁移结果统计
    print("\n" + "=" * 60)
    print("📊 迁移结果统计:")
    print(f"  ✅ 成功迁移: {success_count} 条策略")
    print(f"  ❌ 迁移失败: {error_count} 条策略")
    print(f"  📈 成功率: {success_count/(success_count+error_count)*100:.1f}%")
    
    # 7. 验证迁移结果
    print("\n🔍 验证迁移结果...")
    try:
        migrated_policies = db_manager.load_all_policies()
        print(f"✅ 数据库中现有 {len(migrated_policies)} 条策略")
        
        # 显示前几条策略信息
        print("\n📋 策略列表预览:")
        for i, policy in enumerate(migrated_policies[:5]):
            rule_name = policy.get('rule_name', '未命名')
            rule_type = policy.get('match_conditions', {}).get('match_mode', 'keywords')
            enabled = "启用" if policy.get('enabled', True) else "禁用"
            print(f"  {i+1}. [{rule_type:8s}] {rule_name} ({enabled})")
        
        if len(migrated_policies) > 5:
            print(f"  ... 还有 {len(migrated_policies) - 5} 条策略")
            
    except Exception as e:
        print(f"❌ 验证迁移结果失败: {e}")
        return False
    
    # 8. 备份原文件
    if success_count > 0:
        backup_file = f"rules.json.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        try:
            import shutil
            shutil.copy2(rules_file, backup_file)
            print(f"\n💾 原文件已备份为: {backup_file}")
        except Exception as e:
            print(f"⚠️ 备份原文件失败: {e}")
    
    # 9. 关闭数据库连接
    db_manager.close()
    
    if success_count == len(rules_data):
        print("\n🎉 数据迁移完全成功！")
        print("\n📝 后续步骤:")
        print("  1. 验证应用程序能正常从数据库加载策略")
        print("  2. 测试策略的增删改查功能")
        print("  3. 确认无误后可以删除rules.json文件")
        return True
    else:
        print(f"\n⚠️ 数据迁移部分成功，有 {error_count} 条策略迁移失败")
        print("请检查错误日志并手动处理失败的策略")
        return False


def main():
    """主函数"""
    try:
        success = migrate_rules_to_database()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n❌ 迁移被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 迁移过程中发生未知错误: {e}")
        logging.error(f"迁移失败: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
