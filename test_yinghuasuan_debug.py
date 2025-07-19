#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
影划算平台API调试测试脚本
"""

import asyncio
import logging
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.platforms.yinghuasuan_adapter import YingHuaSuanAdapter
from core.database import DatabaseManager
import json

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

async def test_yinghuasuan_debug():
    """测试影划算平台API调试功能"""
    try:
        print("=" * 100)
        print("影划算平台API调试测试脚本启动")
        print("=" * 100)
        
        # 从数据库加载配置
        db_manager = DatabaseManager()
        credentials_json = db_manager.load_setting('platform_credentials')
        
        if not credentials_json:
            print("未找到平台配置，请先在主程序中配置影划算平台")
            return
            
        credentials = json.loads(credentials_json)
        yinghuasuan_config = credentials.get('yinghuasuan', {})
        
        if not yinghuasuan_config.get('bearer_token'):
            print("未找到影划算平台Bearer Token配置")
            return
            
        # 构建完整配置
        from config import YINGHUASUAN_API_URL, NETWORK_CONFIG, MAX_ORDERS_CACHE
        
        full_config = {
            'bearer_token': yinghuasuan_config['bearer_token'],
            'api_url': YINGHUASUAN_API_URL,
            'network_config': NETWORK_CONFIG,
            'max_orders_cache': MAX_ORDERS_CACHE
        }
        
        print(f"配置加载成功")
        print(f"   - Bearer Token长度: {len(full_config['bearer_token'])} 字符")
        print(f"   - API URL: {full_config['api_url']}")
        print(f"   - 网络配置: {full_config['network_config']}")
        print(f"   - 最大缓存订单数: {full_config['max_orders_cache']}")
        print(full_config['bearer_token'])
        # 创建适配器实例
        adapter = YingHuaSuanAdapter("影划算调试", full_config)
        
        # 执行调试测试
        print("\n开始执行API调试测试...")
        result = await adapter.debug_api_response()
        
        if result:
            print("\n调试测试完成！请查看上方的详细日志信息。")
        else:
            print("\n调试测试失败！请查看错误信息。")
            
    except Exception as e:
        print(f"\n测试脚本异常: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'db_manager' in locals():
            db_manager.close()

if __name__ == "__main__":
    # 运行异步测试
    asyncio.run(test_yinghuasuan_debug())