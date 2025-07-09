#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
删除数据库中哈哈平台的Token，保留其他配置
"""

import sys
import os
import json

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def remove_haha_token():
    """删除哈哈平台Token"""
    try:
        from core.database import DatabaseManager
        
        db_manager = DatabaseManager()
        
        # 获取当前配置
        credentials_json = db_manager.load_setting('platform_credentials')
        
        if credentials_json:
            credentials = json.loads(credentials_json)
            print(f"📋 当前配置: {credentials}")
            
            # 删除哈哈平台配置
            if 'haha' in credentials:
                del credentials['haha']
                print("✅ 已删除哈哈平台配置")
            else:
                print("⚠️ 哈哈平台配置不存在")
            
            # 保存更新后的配置
            updated_json = json.dumps(credentials, ensure_ascii=False)
            db_manager.save_setting('platform_credentials', updated_json)
            
            print(f"📋 更新后配置: {credentials}")
            print("✅ 数据库已更新")
            
        else:
            print("⚠️ 数据库中没有找到平台配置")
        
        return True
        
    except Exception as e:
        print(f"❌ 删除哈哈Token失败: {e}")
        return False

def verify_removal():
    """验证删除结果"""
    try:
        from core.database import DatabaseManager
        
        db_manager = DatabaseManager()
        credentials_json = db_manager.load_setting('platform_credentials')
        
        if credentials_json:
            credentials = json.loads(credentials_json)
            
            print("📋 验证结果:")
            print(f"  当前配置: {credentials}")
            
            if 'haha' not in credentials:
                print("  ✅ 哈哈平台配置已成功删除")
            else:
                print("  ❌ 哈哈平台配置仍然存在")
                return False
            
            if 'mahua' in credentials:
                print("  ✅ 麻花平台配置保持不变")
            else:
                print("  ⚠️ 麻花平台配置不存在（这是正常的，如果之前没有配置）")
            
            return True
        else:
            print("  ✅ 平台配置为空")
            return True
        
    except Exception as e:
        print(f"❌ 验证失败: {e}")
        return False

def main():
    """主函数"""
    print("🗑️ 删除数据库中哈哈平台Token")
    print("=" * 50)
    
    # 删除哈哈Token
    if remove_haha_token():
        print("\n🔍 验证删除结果")
        print("=" * 30)
        verify_removal()
        
        print("\n✅ 操作完成！")
        print("💡 现在您可以重新测试哈哈平台配置了")
    else:
        print("\n❌ 操作失败")

if __name__ == "__main__":
    main()
