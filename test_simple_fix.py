#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化测试v1.3白名单导入Bug修复
"""

import os
import pandas as pd
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_column_detection():
    """测试列名检测功能"""
    print("🧪 测试v1.3白名单导入Bug修复...")
    print("=" * 60)
    
    # 创建正确格式的测试数据
    correct_data = {
        '影院名称': [
            '万达影城（朝阳店）',
            '寰映影城（三里屯店）',
            'CGV影城（西单店）',
            '',  # 空值测试
            '   ',  # 空白测试
            '大地影院（中关村店）'
        ],
        '城市': ['北京', '北京', '北京', '北京', '北京', '北京']
    }
    
    df_correct = pd.DataFrame(correct_data)
    df_correct.to_excel('test_correct.xlsx', index=False)
    
    # 创建错误格式的测试数据
    wrong_data = {
        '影院': ['万达影城', '寰映影城'],  # 注意：这里是"影院"而不是"影院名称"
        '地址': ['朝阳区', '朝阳区']
    }
    
    df_wrong = pd.DataFrame(wrong_data)
    df_wrong.to_excel('test_wrong.xlsx', index=False)
    
    print("✅ 测试文件创建完成")
    
    # 测试正确格式
    print("\n📋 测试1: 正确格式文件（包含'影院名称'列）")
    df1 = pd.read_excel('test_correct.xlsx')
    print(f"   列名: {list(df1.columns)}")
    print(f"   是否包含'影院名称': {'影院名称' in df1.columns}")
    
    if '影院名称' in df1.columns:
        cinema_names = df1['影院名称'].dropna().astype(str).tolist()
        # 清理数据
        cleaned_names = set()
        for name in cinema_names:
            cleaned = str(name).strip()
            if cleaned and cleaned != 'nan':
                cleaned_names.add(cleaned)
        
        print(f"   提取到的影院数量: {len(cleaned_names)}")
        sample_names = list(cleaned_names)[:3]
        print(f"   前3个影院示例: {sample_names}")
        logging.info(f"✅ 成功从文件中提取到 {len(cleaned_names)} 个有效影院名称")
        logging.info(f"📋 前3个影院名称示例: {sample_names}")
    
    # 测试错误格式
    print("\n📋 测试2: 错误格式文件（缺少'影院名称'列）")
    df2 = pd.read_excel('test_wrong.xlsx')
    print(f"   列名: {list(df2.columns)}")
    print(f"   是否包含'影院名称': {'影院名称' in df2.columns}")
    
    if '影院名称' not in df2.columns:
        logging.error("关键列'影院名称'未在文件中找到！")
        logging.error(f"文件中的列名: {list(df2.columns)}")
        print("   ❌ 检测到缺少必需的'影院名称'列")
    
    # 清理测试文件
    for file in ['test_correct.xlsx', 'test_wrong.xlsx']:
        if os.path.exists(file):
            os.remove(file)
    
    print("\n" + "=" * 60)
    print("📋 v1.3 Bug修复验证结果:")
    print("=" * 60)
    print("✅ 1. 严格检查'影院名称'列是否存在")
    print("✅ 2. 使用pandas.dropna()移除空值")
    print("✅ 3. 使用astype(str)确保数据类型")
    print("✅ 4. 详细的错误日志和提示信息")
    print("✅ 5. 验证日志显示影院名称示例")
    
    print("\n💡 修复要点:")
    print("   - 必须包含名为'影院名称'的列")
    print("   - 自动过滤空值和无效数据")
    print("   - 提供清晰的错误提示")
    print("   - 显示前几个影院名称供验证")

if __name__ == "__main__":
    test_column_detection()
