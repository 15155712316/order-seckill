#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库管理模块 - 负责SQLite数据库的所有操作
V2.0 重构版本：添加连接池优化、事务管理、性能监控
"""

import sqlite3
import json
import logging
import threading
import time
from datetime import datetime
from typing import List, Dict, Any
from queue import Queue, Empty
from contextlib import contextmanager

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


class ConnectionPool:
    """简化版SQLite连接池"""
    
    def __init__(self, db_path: str, max_size: int = 5):
        self.db_path = db_path
        self.max_size = max_size
        self.pool = Queue(maxsize=max_size)
        self.lock = threading.Lock()
        self._create_connections()
    
    def _create_connections(self):
        """创建初始连接"""
        for _ in range(self.max_size):
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            # SQLite性能优化设置
            conn.execute("PRAGMA journal_mode=WAL")  # WAL模式提高并发性
            conn.execute("PRAGMA synchronous=NORMAL")  # 平衡安全性和性能
            conn.execute("PRAGMA cache_size=10000")  # 增加缓存大小
            conn.execute("PRAGMA temp_store=MEMORY")  # 临时表使用内存
            self.pool.put(conn)
    
    def get_connection(self, timeout: float = 5.0):
        """获取连接"""
        try:
            return self.pool.get(timeout=timeout)
        except Empty:
            raise RuntimeError("数据库连接池已满，无法获取连接")
    
    def return_connection(self, conn):
        """归还连接"""
        if conn:
            self.pool.put(conn)
    
    def close_all(self):
        """关闭所有连接"""
        while not self.pool.empty():
            try:
                conn = self.pool.get_nowait()
                conn.close()
            except Empty:
                break


class PerformanceMonitor:
    """数据库性能监控器"""
    
    def __init__(self):
        self.query_times = []
        self.slow_query_threshold = 1.0  # 1秒
        self.lock = threading.Lock()
    
    def record_query(self, query: str, duration: float):
        """记录查询性能"""
        with self.lock:
            self.query_times.append((query, duration, time.time()))
            # 只保留最近100条记录
            if len(self.query_times) > 100:
                self.query_times.pop(0)
            
            # 记录慢查询
            if duration > self.slow_query_threshold:
                logging.warning(f"慢查询检测: {query[:100]}... 耗时 {duration:.2f}秒")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        with self.lock:
            if not self.query_times:
                return {"avg_time": 0, "total_queries": 0, "slow_queries": 0}
            
            times = [t[1] for t in self.query_times]
            slow_count = sum(1 for t in times if t > self.slow_query_threshold)
            
            return {
                "avg_time": sum(times) / len(times),
                "total_queries": len(times),
                "slow_queries": slow_count,
                "max_time": max(times),
                "min_time": min(times)
            }


class DatabaseManager:
    """数据库管理类V2.0 - 优化版本，负责订单数据的存储和查询"""
    
    def __init__(self, db_path: str = "orders.db", pool_size: int = 5):
        """
        初始化数据库管理器
        
        Args:
            db_path (str): 数据库文件路径，默认为 orders.db
            pool_size (int): 连接池大小，默认为5
        """
        self.db_path = db_path
        self.pool = ConnectionPool(db_path, pool_size)
        self.monitor = PerformanceMonitor()
        
        try:
            # 创建数据表
            self._create_tables()
            logging.info(f"数据库管理器V2.0初始化完成，数据库文件: {self.db_path}，连接池大小: {pool_size}")
            
        except Exception as e:
            logging.error(f"数据库初始化失败: {e}")
            raise
    
    @contextmanager
    def get_connection(self):
        """连接管理上下文管理器"""
        conn = None
        start_time = time.time()
        try:
            conn = self.pool.get_connection()
            yield conn
        finally:
            duration = time.time() - start_time
            self.monitor.record_query("get_connection", duration)
            if conn:
                self.pool.return_connection(conn)
    
    def execute_query(self, query: str, params: tuple = None, fetch: str = None):
        """执行SQL查询的通用方法"""
        start_time = time.time()
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                
                if fetch == 'all':
                    result = cursor.fetchall()
                elif fetch == 'one':
                    result = cursor.fetchone()
                elif fetch == 'count':
                    result = cursor.rowcount
                else:
                    result = cursor.rowcount
                
                conn.commit()
                return result
        finally:
            duration = time.time() - start_time
            self.monitor.record_query(query[:100], duration)
    
    def execute_many(self, query: str, params_list: List[tuple]):
        """批量执行SQL查询"""
        start_time = time.time()
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.executemany(query, params_list)
                conn.commit()
                return cursor.rowcount
        finally:
            duration = time.time() - start_time
            self.monitor.record_query(f"batch:{query[:50]}", duration)
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """获取数据库性能统计信息"""
        return self.monitor.get_stats()
    
    def _create_tables(self):
        """【中央仓储架构】创建所有数据表：订单表、白名单表、策略表"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # 创建orders表
                create_orders_table_sql = """
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

                cursor.execute(create_orders_table_sql)

                # 创建白名单影院表
                create_whitelist_table_sql = """
                CREATE TABLE IF NOT EXISTS whitelist_cinemas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    policy_id TEXT NOT NULL,
                    cinema_name TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """

                cursor.execute(create_whitelist_table_sql)

                # 【核心新增】创建策略表 - 取代rules.json的中央仓储
                create_policies_table_sql = """
                CREATE TABLE IF NOT EXISTS policies (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL,
                    policy_order INTEGER NOT NULL,
                    config TEXT NOT NULL,
                    is_enabled INTEGER NOT NULL DEFAULT 1,
                    created_at TIMESTAMP NOT NULL
                )
                """

                cursor.execute(create_policies_table_sql)

                # 【守护者之盾】创建用户设置表
                create_settings_table_sql = """
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
                """

                cursor.execute(create_settings_table_sql)

                # 创建索引以提高查询性能
                index_sqls = [
                    # orders表索引
                    "CREATE INDEX IF NOT EXISTS idx_order_id ON orders(order_id)",
                    "CREATE INDEX IF NOT EXISTS idx_created_at ON orders(created_at)",
                    "CREATE INDEX IF NOT EXISTS idx_cinema_name ON orders(cinema_name)",
                    "CREATE INDEX IF NOT EXISTS idx_city ON orders(city)",
                    # whitelist_cinemas表索引
                    "CREATE INDEX IF NOT EXISTS idx_policy_id ON whitelist_cinemas(policy_id)",
                    "CREATE UNIQUE INDEX IF NOT EXISTS idx_policy_cinema ON whitelist_cinemas(policy_id, cinema_name)",
                    # 【新增】policies表索引
                    "CREATE INDEX IF NOT EXISTS idx_policy_order ON policies(policy_order)",
                    "CREATE INDEX IF NOT EXISTS idx_policy_type ON policies(type)",
                    "CREATE INDEX IF NOT EXISTS idx_policy_enabled ON policies(is_enabled)"
                ]

                for index_sql in index_sqls:
                    cursor.execute(index_sql)

                conn.commit()
                logging.info("数据表创建完成")

        except Exception as e:
            logging.error(f"创建数据表失败: {e}")
            raise
    
    def save_orders(self, orders: List[Dict[str, Any]], platform_name: str) -> int:
        """
        保存订单列表到数据库 - 优化版本，使用批量插入

        Args:
            orders (List[Dict[str, Any]]): 标准化后的订单列表
            platform_name (str): 平台名称

        Returns:
            int: 成功插入的订单数量
        """
        if not orders:
            return 0
        
        try:
            # 准备批量插入数据
            insert_sql = """
            INSERT OR IGNORE INTO orders (
                order_id, bidding_price, seat_count, city, cinema_name,
                hall_type, movie_name, show_timestamp, platform, raw_data, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            insert_data = []
            china_time = get_china_time()
            
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

                    insert_data.append((
                        order_id, bidding_price, seat_count, city, cinema_name,
                        hall_type, movie_name, show_timestamp, platform_name, raw_data, china_time
                    ))
                        
                except Exception as e:
                    logging.warning(f"准备插入订单 {order.get('order_id', 'unknown')} 失败: {e}")
                    continue
            
            if not insert_data:
                return 0
            
            # 批量执行插入
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 获取插入前的订单总数
                cursor.execute("SELECT COUNT(*) FROM orders")
                count_before = cursor.fetchone()[0]
                
                # 批量插入
                cursor.executemany(insert_sql, insert_data)
                
                # 获取插入后的订单总数
                cursor.execute("SELECT COUNT(*) FROM orders")
                count_after = cursor.fetchone()[0]
                
                conn.commit()
                
                inserted_count = count_after - count_before
            
            if inserted_count > 0:
                logging.info(f"✅ 成功保存 {inserted_count} 条新订单到数据库")
            else:
                logging.info("ℹ️ 本次轮询无新订单，未更新数据库")
            
            return inserted_count
            
        except Exception as e:
            logging.error(f"保存订单到数据库失败: {e}")
            return 0
    
    def get_recent_orders(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取最近的订单记录 - 优化版本
        
        Args:
            limit (int): 返回的记录数量限制
            
        Returns:
            List[Dict[str, Any]]: 订单记录列表
        """
        try:
            query_sql = """
            SELECT * FROM orders 
            ORDER BY created_at DESC 
            LIMIT ?
            """
            
            rows = self.execute_query(query_sql, (limit,), fetch='all')
            
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
        获取数据库中的订单总数 - 优化版本

        Returns:
            int: 订单总数
        """
        try:
            result = self.execute_query("SELECT COUNT(*) FROM orders", fetch='one')
            return result[0] if result else 0

        except Exception as e:
            logging.error(f"查询订单总数失败: {e}")
            return 0

    def get_all_orders_as_dicts(self) -> List[Dict[str, Any]]:
        """
        获取数据库中的所有订单数据，并转换为字典列表 - 优化版本

        Returns:
            List[Dict[str, Any]]: 包含所有订单数据的字典列表
        """
        try:
            # 查询所有订单数据，按创建时间倒序排列
            query_sql = """
            SELECT id, order_id, bidding_price, seat_count, city, cinema_name,
                   hall_type, movie_name, show_timestamp, platform, raw_data, created_at
            FROM orders
            ORDER BY created_at DESC
            """

            rows = self.execute_query(query_sql, fetch='all')

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
    
    def add_cinemas_to_whitelist(self, policy_id: str, cinema_names: set) -> int:
        """
        将影院名称批量添加到白名单策略中

        Args:
            policy_id (str): 策略ID
            cinema_names (set): 影院名称集合

        Returns:
            int: 成功添加的影院数量
        """
        if not cinema_names:
            return 0

        try:
            cursor = self.connection.cursor()
            current_time = get_china_time()

            # 准备批量插入语句
            insert_sql = """
            INSERT OR IGNORE INTO whitelist_cinemas (policy_id, cinema_name, created_at)
            VALUES (?, ?, ?)
            """

            # 批量插入数据
            insert_data = [(policy_id, cinema_name.strip(), current_time)
                          for cinema_name in cinema_names if cinema_name.strip()]

            cursor.executemany(insert_sql, insert_data)
            self.connection.commit()

            inserted_count = cursor.rowcount
            logging.info(f"成功添加 {inserted_count} 个影院到白名单策略 {policy_id}")

            return inserted_count

        except Exception as e:
            logging.error(f"添加影院到白名单失败: {e}")
            return 0

    def load_cinemas_for_policy(self, policy_id: str) -> set:
        """
        加载指定策略的所有影院名称

        Args:
            policy_id (str): 策略ID

        Returns:
            set: 影院名称集合
        """
        try:
            cursor = self.connection.cursor()

            query_sql = """
            SELECT cinema_name FROM whitelist_cinemas
            WHERE policy_id = ?
            ORDER BY cinema_name
            """

            cursor.execute(query_sql, (policy_id,))
            rows = cursor.fetchall()

            cinema_names = {row[0] for row in rows}
            logging.info(f"从数据库加载策略 {policy_id} 的 {len(cinema_names)} 个影院")

            return cinema_names

        except Exception as e:
            logging.error(f"加载白名单影院失败: {e}")
            return set()

    def clear_cinemas_for_policy(self, policy_id: str) -> int:
        """
        清空指定策略的所有影院记录

        Args:
            policy_id (str): 策略ID

        Returns:
            int: 删除的记录数量
        """
        try:
            cursor = self.connection.cursor()

            delete_sql = "DELETE FROM whitelist_cinemas WHERE policy_id = ?"
            cursor.execute(delete_sql, (policy_id,))
            self.connection.commit()

            deleted_count = cursor.rowcount
            logging.info(f"清空策略 {policy_id} 的 {deleted_count} 个影院记录")

            return deleted_count

        except Exception as e:
            logging.error(f"清空白名单影院失败: {e}")
            return 0

    def get_whitelist_stats(self) -> dict:
        """
        获取白名单统计信息

        Returns:
            dict: 包含各策略的影院数量统计
        """
        try:
            cursor = self.connection.cursor()

            query_sql = """
            SELECT policy_id, COUNT(*) as cinema_count
            FROM whitelist_cinemas
            GROUP BY policy_id
            ORDER BY policy_id
            """

            cursor.execute(query_sql)
            rows = cursor.fetchall()

            stats = {row[0]: row[1] for row in rows}
            logging.info(f"白名单统计: {len(stats)} 个策略，总计 {sum(stats.values())} 个影院")

            return stats

        except Exception as e:
            logging.error(f"获取白名单统计失败: {e}")
            return {}

    # ========================================
    # 【中央仓储架构】策略管理核心方法
    # ========================================

    def load_all_policies(self) -> List[Dict[str, Any]]:
        """
        【核心方法】从数据库加载所有策略，按policy_order升序排序

        Returns:
            List[Dict[str, Any]]: 策略字典列表，config字段已从JSON字符串解析为字典
        """
        try:
            cursor = self.connection.cursor()

            query_sql = """
            SELECT id, name, type, policy_order, config, is_enabled, created_at
            FROM policies
            ORDER BY policy_order ASC
            """

            cursor.execute(query_sql)
            rows = cursor.fetchall()

            policies = []
            for row in rows:
                policy = {
                    'rule_id': row[0],  # 保持与现有代码兼容
                    'rule_name': row[1],  # 保持与现有代码兼容
                    'type': row[2],
                    'policy_order': row[3],
                    'enabled': bool(row[5]),  # 保持与现有代码兼容
                    'created_at': row[6]
                }

                # 解析config JSON字符串为字典
                try:
                    config = json.loads(row[4])
                    policy.update(config)  # 将config内容合并到策略字典中
                except json.JSONDecodeError as e:
                    logging.error(f"策略 {row[0]} 的config JSON解析失败: {e}")
                    continue

                policies.append(policy)

            logging.info(f"从数据库加载了 {len(policies)} 条策略")
            return policies

        except Exception as e:
            logging.error(f"加载策略失败: {e}")
            return []

    def save_policy(self, policy: Dict[str, Any]) -> bool:
        """
        【核心方法】保存或更新单个策略到数据库

        Args:
            policy (Dict[str, Any]): 策略字典

        Returns:
            bool: 是否保存成功
        """
        try:
            cursor = self.connection.cursor()

            # 提取基本字段
            policy_id = policy.get('rule_id')
            policy_name = policy.get('rule_name', '未命名策略')
            policy_type = policy.get('match_conditions', {}).get('match_mode', 'keywords')
            policy_order = policy.get('policy_order', 999)  # 默认排序值
            is_enabled = 1 if policy.get('enabled', True) else 0

            # 构建config字典（排除基本字段）
            config = policy.copy()
            excluded_fields = ['rule_id', 'rule_name', 'type', 'policy_order', 'enabled', 'created_at']
            for field in excluded_fields:
                config.pop(field, None)

            # 将config转换为JSON字符串
            config_json = json.dumps(config, ensure_ascii=False, indent=2)

            # 使用INSERT OR REPLACE INTO逻辑
            insert_sql = """
            INSERT OR REPLACE INTO policies
            (id, name, type, policy_order, config, is_enabled, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """

            # 如果是新策略，使用当前时间；如果是更新，保持原创建时间
            created_at = policy.get('created_at', get_china_time())

            cursor.execute(insert_sql, (
                policy_id, policy_name, policy_type, policy_order,
                config_json, is_enabled, created_at
            ))

            self.connection.commit()
            logging.info(f"策略 '{policy_name}' (ID: {policy_id}) 保存成功")
            return True

        except Exception as e:
            logging.error(f"保存策略失败: {e}")
            return False

    def delete_policy(self, policy_id: str) -> bool:
        """
        【核心方法】根据policy_id删除策略

        Args:
            policy_id (str): 策略ID

        Returns:
            bool: 是否删除成功
        """
        try:
            cursor = self.connection.cursor()

            # 删除策略
            delete_sql = "DELETE FROM policies WHERE id = ?"
            cursor.execute(delete_sql, (policy_id,))

            deleted_count = cursor.rowcount
            self.connection.commit()

            if deleted_count > 0:
                logging.info(f"策略 {policy_id} 删除成功")
                return True
            else:
                logging.warning(f"策略 {policy_id} 不存在，无法删除")
                return False

        except Exception as e:
            logging.error(f"删除策略 {policy_id} 失败: {e}")
            return False

    def update_policies_order(self, policies: List[Dict[str, Any]]) -> bool:
        """
        【可选方法】批量更新策略的policy_order字段

        Args:
            policies (List[Dict[str, Any]]): 包含rule_id和policy_order的策略列表

        Returns:
            bool: 是否更新成功
        """
        try:
            cursor = self.connection.cursor()

            update_sql = "UPDATE policies SET policy_order = ? WHERE id = ?"

            for i, policy in enumerate(policies):
                policy_id = policy.get('rule_id')
                new_order = i + 1  # 从1开始排序
                cursor.execute(update_sql, (new_order, policy_id))

            self.connection.commit()
            logging.info(f"批量更新了 {len(policies)} 个策略的排序")
            return True

        except Exception as e:
            logging.error(f"批量更新策略排序失败: {e}")
            return False

    def save_setting(self, key: str, value: str):
        """【守护者之盾】保存或更新用户设置"""
        try:
            cursor = self.connection.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                (key, value)
            )
            self.connection.commit()
            logging.debug(f"保存设置: {key} = {value}")
        except Exception as e:
            logging.error(f"保存设置失败: {e}")
            raise

    def load_setting(self, key: str, default_value: str = None) -> str:
        """【守护者之盾】加载用户设置"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
            result = cursor.fetchone()

            if result:
                return result[0]
            else:
                return default_value

        except Exception as e:
            logging.error(f"加载设置失败: {e}")
            return default_value

    def close(self):
        """关闭数据库连接池"""
        if hasattr(self, 'pool'):
            try:
                self.pool.close_all()
                logging.info("数据库连接池已关闭")
            except Exception as e:
                logging.error(f"关闭数据库连接池失败: {e}")

    def __del__(self):
        """析构函数，确保数据库连接被正确关闭"""
        self.close()
