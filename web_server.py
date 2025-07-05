#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web API服务器 - 提供订单数据的HTTP API接口
"""

from flask import Flask, jsonify, request
from core.database import DatabaseManager
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# 创建Flask应用实例
app = Flask(__name__)

# 全局数据库管理器实例
db_manager = None


def get_db_manager():
    """获取数据库管理器实例（单例模式）"""
    global db_manager
    if db_manager is None:
        db_manager = DatabaseManager()
    return db_manager


@app.route('/api/orders', methods=['GET'])
def get_orders():
    """
    获取所有订单数据的API端点
    
    Returns:
        JSON: 包含所有订单数据的JSON响应
    """
    try:
        # 获取数据库管理器实例
        db = get_db_manager()
        
        # 从数据库获取所有订单数据
        orders = db.get_all_orders_as_dicts()
        
        # 构建响应数据
        response_data = {
            'success': True,
            'message': f'成功获取 {len(orders)} 条订单数据',
            'total_count': len(orders),
            'data': orders
        }
        
        logging.info(f"API请求成功：返回 {len(orders)} 条订单数据")
        return jsonify(response_data)
        
    except Exception as e:
        # 错误处理
        error_message = f"获取订单数据失败: {str(e)}"
        logging.error(error_message)
        
        response_data = {
            'success': False,
            'message': error_message,
            'total_count': 0,
            'data': []
        }
        
        return jsonify(response_data), 500


@app.route('/api/orders/count', methods=['GET'])
def get_orders_count():
    """
    获取订单总数的API端点
    
    Returns:
        JSON: 包含订单总数的JSON响应
    """
    try:
        # 获取数据库管理器实例
        db = get_db_manager()
        
        # 获取订单总数
        total_count = db.get_orders_count()
        
        # 构建响应数据
        response_data = {
            'success': True,
            'message': '成功获取订单总数',
            'total_count': total_count
        }
        
        logging.info(f"API请求成功：订单总数 {total_count}")
        return jsonify(response_data)
        
    except Exception as e:
        # 错误处理
        error_message = f"获取订单总数失败: {str(e)}"
        logging.error(error_message)
        
        response_data = {
            'success': False,
            'message': error_message,
            'total_count': 0
        }
        
        return jsonify(response_data), 500


@app.route('/api/orders/recent', methods=['GET'])
def get_recent_orders():
    """
    获取最近订单数据的API端点
    
    Query Parameters:
        limit (int): 返回的订单数量限制，默认为10
    
    Returns:
        JSON: 包含最近订单数据的JSON响应
    """
    try:
        # 获取查询参数
        limit = request.args.get('limit', default=10, type=int)
        
        # 限制查询数量范围
        if limit < 1:
            limit = 10
        elif limit > 1000:
            limit = 1000
        
        # 获取数据库管理器实例
        db = get_db_manager()
        
        # 获取最近的订单数据
        orders = db.get_recent_orders(limit=limit)
        
        # 构建响应数据
        response_data = {
            'success': True,
            'message': f'成功获取最近 {len(orders)} 条订单数据',
            'total_count': len(orders),
            'limit': limit,
            'data': orders
        }
        
        logging.info(f"API请求成功：返回最近 {len(orders)} 条订单数据")
        return jsonify(response_data)
        
    except Exception as e:
        # 错误处理
        error_message = f"获取最近订单数据失败: {str(e)}"
        logging.error(error_message)
        
        response_data = {
            'success': False,
            'message': error_message,
            'total_count': 0,
            'limit': limit if 'limit' in locals() else 10,
            'data': []
        }
        
        return jsonify(response_data), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """
    健康检查API端点
    
    Returns:
        JSON: 服务器状态信息
    """
    try:
        # 获取数据库管理器实例并测试连接
        db = get_db_manager()
        total_count = db.get_orders_count()
        
        response_data = {
            'success': True,
            'message': 'Web API服务器运行正常',
            'database_status': 'connected',
            'total_orders': total_count
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        response_data = {
            'success': False,
            'message': f'服务器状态异常: {str(e)}',
            'database_status': 'error',
            'total_orders': 0
        }
        
        return jsonify(response_data), 500


@app.route('/', methods=['GET'])
def index():
    """
    根路径，提供API文档信息
    
    Returns:
        JSON: API文档信息
    """
    api_info = {
        'service': '抢单提醒系统 Web API',
        'version': '1.2.0',
        'description': '提供订单数据的HTTP API接口',
        'endpoints': {
            'GET /': '获取API文档信息',
            'GET /api/health': '健康检查',
            'GET /api/orders': '获取所有订单数据',
            'GET /api/orders/count': '获取订单总数',
            'GET /api/orders/recent?limit=N': '获取最近N条订单数据'
        },
        'example_usage': {
            'get_all_orders': 'http://localhost:5000/api/orders',
            'get_recent_orders': 'http://localhost:5000/api/orders/recent?limit=20',
            'get_orders_count': 'http://localhost:5000/api/orders/count',
            'health_check': 'http://localhost:5000/api/health'
        }
    }
    
    return jsonify(api_info)


if __name__ == '__main__':
    """
    启动Web API服务器
    """
    try:
        logging.info("正在启动Web API服务器...")
        
        # 测试数据库连接
        test_db = get_db_manager()
        total_orders = test_db.get_orders_count()
        logging.info(f"数据库连接成功，当前共有 {total_orders} 条订单数据")
        
        # 启动Flask应用
        logging.info("Web API服务器启动成功！")
        logging.info("API文档: http://localhost:5000/")
        logging.info("订单数据API: http://localhost:5000/api/orders")
        logging.info("健康检查API: http://localhost:5000/api/health")
        
        app.run(
            host='0.0.0.0',  # 允许外部访问
            port=5000,       # 端口号
            debug=True,      # 开启调试模式
            threaded=True    # 支持多线程
        )
        
    except Exception as e:
        logging.error(f"启动Web API服务器失败: {e}")
        print(f"错误: {e}")
