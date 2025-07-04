#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库管理模块 - 负责SQLite数据库的所有操作
"""

import sqlite3
import json
import logging
from datetime import datetime
from typing import List, Dict, Any

# 导入时区相关模块
try:
    import pytz
    PYTZ_AVAILABLE = True
except ImportError:
    PYTZ_AVAILABLE = False

try:
    from zoneinfo import ZoneInfo
    ZONEINFO_AVAILABLE = True
except ImportError:
    ZONEINFO_AVAILABLE = False


def get_china_time() -> str:
    """
    获取当前的中国时区时间字符串

    Returns:
        str: 格式化的中国时区时间字符串 (YYYY-MM-DD HH:MM:SS)
    """
    try:
        # 优先使用pytz，因为它更稳定
        if PYTZ_AVAILABLE:
            china_tz = pytz.timezone('Asia/Shanghai')
            china_time = datetime.now(china_tz)
            return china_time.strftime('%Y-%m-%d %H:%M:%S')
        elif ZONEINFO_AVAILABLE:
            # 使用zoneinfo (Python 3.9+)
            china_time = datetime.now(ZoneInfo("Asia/Shanghai"))
            return china_time.strftime('%Y-%m-%d %H:%M:%S')
        else:
            # 如果都不可用，使用本地时间
            logging.info("时区库不可用，使用本地时间")
            return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    except Exception as e:
        logging.warning(f"获取中国时区时间失败，使用本地时间: {e}")
        # 如果时区设置失败，使用本地时间
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


class DatabaseManager:
    """数据库管理类，负责订单数据的存储和查询"""
    
    def __init__(self, db_path: str = "orders.db"):
        """
        初始化数据库管理器
        
        Args:
            db_path (str): 数据库文件路径，默认为 orders.db
        """
        self.db_path = db_path
        self.connection = None
        
        try:
            # 连接到SQLite数据库
            self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self.connection.row_factory = sqlite3.Row  # 使查询结果可以像字典一样访问
            
            # 创建数据表
            self._create_table()
            
            logging.info(f"数据库管理器初始化完成，数据库文件: {self.db_path}")
            
        except Exception as e:
            logging.error(f"数据库初始化失败: {e}")
            raise
    
    def _create_table(self):
        """创建订单数据表"""
        try:
            cursor = self.connection.cursor()
            
            # 创建orders表
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id TEXT UNIQUE NOT NULL,
                bidding_price REAL NOT NULL,
                seat_count INTEGER NOT NULL,
                city TEXT NOT NULL,
                cinema_name TEXT NOT NULL,
                hall_type TEXT NOT NULL,
                movie_name TEXT NOT NULL,
                show_timestamp TEXT,
                platform TEXT NOT NULL,
                raw_data TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
            
            cursor.execute(create_table_sql)
            
            # 创建索引以提高查询性能
            index_sqls = [
                "CREATE INDEX IF NOT EXISTS idx_order_id ON orders(order_id)",
                "CREATE INDEX IF NOT EXISTS idx_created_at ON orders(created_at)",
                "CREATE INDEX IF NOT EXISTS idx_cinema_name ON orders(cinema_name)",
                "CREATE INDEX IF NOT EXISTS idx_city ON orders(city)"
            ]
            
            for index_sql in index_sqls:
                cursor.execute(index_sql)
            
            self.connection.commit()
            logging.info("数据表创建完成")
            
        except Exception as e:
            logging.error(f"创建数据表失败: {e}")
            raise
    
    def save_orders(self, orders: List[Dict[str, Any]], platform_name: str) -> int:
        """
        保存订单列表到数据库

        Args:
            orders (List[Dict[str, Any]]): 标准化后的订单列表
            platform_name (str): 平台名称

        Returns:
            int: 成功插入的订单数量
        """
        if not orders:
            return 0
        
        try:
            cursor = self.connection.cursor()
            
            # 准备插入语句
            insert_sql = """
            INSERT OR IGNORE INTO orders (
                order_id, bidding_price, seat_count, city, cinema_name,
                hall_type, movie_name, show_timestamp, platform, raw_data, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            inserted_count = 0
            
            for order in orders:
                try:
                    # 提取订单数据
                    order_id = order.get('order_id', '')
                    bidding_price = float(order.get('bidding_price', 0.0))
                    seat_count = int(order.get('seat_count', 1))
                    city = order.get('city', '')
                    cinema_name = order.get('cinema_name', '')
                    hall_type = order.get('hall_type', '')
                    movie_name = order.get('movie_name', '')
                    show_timestamp = order.get('show_time', order.get('timestamp', ''))

                    # 将原始数据转换为JSON字符串
                    raw_data = json.dumps(order.get('raw_data', {}), ensure_ascii=False)

                    # 获取当前的中国时区时间
                    china_time = get_china_time()

                    # 执行插入
                    cursor.execute(insert_sql, (
                        order_id, bidding_price, seat_count, city, cinema_name,
                        hall_type, movie_name, show_timestamp, platform_name, raw_data, china_time
                    ))
                    
                    # 检查是否实际插入了数据（rowcount > 0 表示插入成功）
                    if cursor.rowcount > 0:
                        inserted_count += 1
                        
                except Exception as e:
                    logging.warning(f"插入订单 {order.get('order_id', 'unknown')} 失败: {e}")
                    continue
            
            # 提交事务
            self.connection.commit()
            
            if inserted_count > 0:
                logging.info(f"✅ 成功保存 {inserted_count} 条新订单到数据库")
            else:
                logging.info("ℹ️ 本次轮询无新订单，未更新数据库")
            
            return inserted_count
            
        except Exception as e:
            logging.error(f"保存订单到数据库失败: {e}")
            # 回滚事务
            if self.connection:
                self.connection.rollback()
            return 0
    
    def get_recent_orders(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取最近的订单记录
        
        Args:
            limit (int): 返回的记录数量限制
            
        Returns:
            List[Dict[str, Any]]: 订单记录列表
        """
        try:
            cursor = self.connection.cursor()
            
            query_sql = """
            SELECT * FROM orders 
            ORDER BY created_at DESC 
            LIMIT ?
            """
            
            cursor.execute(query_sql, (limit,))
            rows = cursor.fetchall()
            
            # 转换为字典列表
            orders = []
            for row in rows:
                order_dict = dict(row)
                # 解析raw_data JSON字符串
                try:
                    order_dict['raw_data'] = json.loads(order_dict['raw_data'])
                except:
                    order_dict['raw_data'] = {}
                orders.append(order_dict)
            
            return orders
            
        except Exception as e:
            logging.error(f"查询最近订单失败: {e}")
            return []
    
    def get_orders_count(self) -> int:
        """
        获取数据库中的订单总数

        Returns:
            int: 订单总数
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT COUNT(*) FROM orders")
            count = cursor.fetchone()[0]
            return count

        except Exception as e:
            logging.error(f"查询订单总数失败: {e}")
            return 0

    def get_all_orders_as_dicts(self) -> List[Dict[str, Any]]:
        """
        获取数据库中的所有订单数据，并转换为字典列表

        Returns:
            List[Dict[str, Any]]: 包含所有订单数据的字典列表
        """
        try:
            cursor = self.connection.cursor()

            # 查询所有订单数据，按创建时间倒序排列
            query_sql = """
            SELECT id, order_id, bidding_price, seat_count, city, cinema_name,
                   hall_type, movie_name, show_timestamp, platform, raw_data, created_at
            FROM orders
            ORDER BY created_at DESC
            """

            cursor.execute(query_sql)
            rows = cursor.fetchall()

            # 转换为字典列表
            orders = []
            for row in rows:
                order_dict = {
                    'id': row[0],
                    'order_id': row[1],
                    'bidding_price': row[2],
                    'seat_count': row[3],
                    'city': row[4],
                    'cinema_name': row[5],
                    'hall_type': row[6],
                    'movie_name': row[7],
                    'show_timestamp': row[8],
                    'platform': row[9],
                    'raw_data': row[10],
                    'created_at': row[11]
                }

                # 解析raw_data JSON字符串
                try:
                    order_dict['raw_data'] = json.loads(order_dict['raw_data'])
                except:
                    order_dict['raw_data'] = {}

                orders.append(order_dict)

            logging.info(f"成功查询到 {len(orders)} 条订单数据")
            return orders

        except Exception as e:
            logging.error(f"查询所有订单数据失败: {e}")
            return []
    
    def close(self):
        """关闭数据库连接"""
        if self.connection:
            try:
                self.connection.close()
                logging.info("数据库连接已关闭")
            except Exception as e:
                logging.error(f"关闭数据库连接失败: {e}")
    
    def __del__(self):
        """析构函数，确保数据库连接被正确关闭"""
        self.close()
