#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
异步引擎 V3.0 - 重构版本
解决asyncio和Qt事件循环冲突，实现高性能异步架构
"""

import asyncio
import threading
import time
import logging
from typing import Dict, List, Any, Callable, Optional
from concurrent.futures import ThreadPoolExecutor
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QThread
from core.logger import get_logger


class AsyncBridge(QObject):
    """异步桥接器 - 连接asyncio和Qt信号系统"""
    
    # 平台数据信号
    platform_data_received = pyqtSignal(str, dict)  # platform_name, data
    platform_error = pyqtSignal(str, str)  # platform_name, error_message
    
    # 状态信号
    monitoring_started = pyqtSignal()
    monitoring_stopped = pyqtSignal()
    cycle_completed = pyqtSignal(dict)  # cycle_stats
    
    # 性能信号
    performance_update = pyqtSignal(dict)  # performance_data
    
    def __init__(self):
        super().__init__()
        self.logger = get_logger()


class PlatformWorker(QThread):
    """平台工作线程 - 每个平台一个独立线程"""
    
    data_ready = pyqtSignal(str, dict)  # platform_name, result
    error_occurred = pyqtSignal(str, str)  # platform_name, error
    
    def __init__(self, platform_name: str, adapter_instance, interval: float = 5.0):
        super().__init__()
        self.platform_name = platform_name
        self.adapter = adapter_instance
        self.interval = interval
        self.running = False
        self.logger = get_logger()
    
    def run(self):
        """线程主循环"""
        self.running = True
        self.logger.info(f"{self.platform_name}平台工作线程启动")
        
        # 创建新的事件循环
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            while self.running:
                try:
                    # 异步获取数据
                    result = loop.run_until_complete(self._fetch_data())
                    
                    if result and result.get('success'):
                        self.data_ready.emit(self.platform_name, result)
                    else:
                        error_msg = result.get('error', '未知错误') if result else '无数据返回'
                        self.error_occurred.emit(self.platform_name, error_msg)
                    
                    # 等待间隔
                    if self.running:
                        time.sleep(self.interval)
                        
                except Exception as e:
                    self.logger.error(f"{self.platform_name}平台数据获取异常: {e}")
                    self.error_occurred.emit(self.platform_name, str(e))
                    
                    if self.running:
                        time.sleep(self.interval)
                        
        except Exception as e:
            self.logger.error(f"{self.platform_name}平台工作线程异常: {e}")
        finally:
            loop.close()
            self.logger.info(f"{self.platform_name}平台工作线程停止")
    
    async def _fetch_data(self) -> Dict[str, Any]:
        """异步获取平台数据"""
        operation_id = self.logger.start_operation(f"fetch_{self.platform_name}")
        
        try:
            result = await self.adapter.fetch_and_process()
            
            # 确保返回标准格式
            if not isinstance(result, dict):
                result = {'success': False, 'error': '返回数据格式错误'}
            
            # 添加性能统计
            if 'orders' in result and isinstance(result['orders'], list):
                order_count = len(result['orders'])
                self.logger.end_operation(operation_id, {
                    'platform': self.platform_name,
                    'order_count': order_count,
                    'success': result.get('success', False)
                })
            
            return result
            
        except Exception as e:
            self.logger.end_operation(operation_id, {
                'platform': self.platform_name,
                'error': str(e),
                'success': False
            })
            return {'success': False, 'error': str(e)}
    
    def stop(self):
        """停止工作线程"""
        self.running = False


class AsyncEngine(QObject):
    """异步监控引擎 V3.0 - 重构版本"""
    
    # 主要信号
    data_received = pyqtSignal(str, dict)  # platform_name, data
    cycle_completed = pyqtSignal(dict)  # cycle_stats
    engine_started = pyqtSignal()
    engine_stopped = pyqtSignal()
    
    def __init__(self, platforms: Dict[str, Any] = None):
        super().__init__()
        self.platforms = platforms or {}
        self.workers = {}  # platform_name -> PlatformWorker
        self.bridge = AsyncBridge()
        self.logger = get_logger()
        
        # 状态管理
        self.is_running = False
        self.cycle_count = 0
        self.start_time = None
        
        # 统计定时器
        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self._emit_cycle_stats)
        self.stats_timer.setInterval(30000)  # 30秒统计一次
        
        # 性能监控
        self.performance_data = {
            'total_cycles': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'total_orders': 0,
            'platform_stats': {}
        }
        
        self.logger.info("异步引擎V3.0初始化完成")
    
    def update_platforms(self, platforms: Dict[str, Any]):
        """更新平台配置"""
        old_platforms = set(self.platforms.keys())
        new_platforms = set(platforms.keys())
        
        # 停止已删除的平台
        removed_platforms = old_platforms - new_platforms
        for platform_name in removed_platforms:
            self._stop_platform(platform_name)
        
        # 更新平台配置
        self.platforms = platforms
        
        # 启动新增的平台（如果引擎正在运行）
        if self.is_running:
            added_platforms = new_platforms - old_platforms
            for platform_name in added_platforms:
                self._start_platform(platform_name)
        
        self.logger.info(f"平台配置已更新，当前平台: {list(platforms.keys())}")
    
    def start_monitoring(self):
        """启动监控"""
        if self.is_running:
            self.logger.warning("监控已在运行中")
            return
        
        self.logger.info("启动异步监控引擎...")
        
        self.is_running = True
        self.start_time = time.time()
        self.cycle_count = 0
        
        # 启动所有平台
        for platform_name in self.platforms.keys():
            self._start_platform(platform_name)
        
        # 启动统计定时器
        self.stats_timer.start()
        
        self.engine_started.emit()
        self.logger.info(f"异步监控引擎已启动，监控平台: {list(self.platforms.keys())}")
    
    def stop_monitoring(self):
        """停止监控"""
        if not self.is_running:
            return
        
        self.logger.info("停止异步监控引擎...")
        
        self.is_running = False
        
        # 停止所有平台
        for platform_name in list(self.workers.keys()):
            self._stop_platform(platform_name)
        
        # 停止统计定时器
        self.stats_timer.stop()
        
        self.engine_stopped.emit()
        
        # 记录最终统计
        runtime = time.time() - self.start_time if self.start_time else 0
        self.logger.info(f"异步监控引擎已停止，运行时间: {runtime:.1f}秒，总周期: {self.cycle_count}")
    
    def _start_platform(self, platform_name: str):
        """启动单个平台监控"""
        if platform_name in self.workers:
            return
        
        platform_config = self.platforms.get(platform_name)
        if not platform_config or not platform_config.get('enabled', True):
            return
        
        try:
            # 获取适配器实例
            adapter = platform_config.get('adapter')
            if not adapter:
                self.logger.error(f"平台 {platform_name} 缺少适配器实例")
                return
            
            # 创建工作线程
            interval = platform_config.get('interval', 5.0)
            worker = PlatformWorker(platform_name, adapter, interval)
            
            # 连接信号
            worker.data_ready.connect(self._on_platform_data)
            worker.error_occurred.connect(self._on_platform_error)
            
            # 启动线程
            worker.start()
            self.workers[platform_name] = worker
            
            # 初始化平台统计
            self.performance_data['platform_stats'][platform_name] = {
                'requests': 0,
                'successes': 0,
                'failures': 0,
                'total_orders': 0,
                'last_success': None,
                'last_error': None
            }
            
            self.logger.info(f"平台 {platform_name} 监控已启动")
            
        except Exception as e:
            self.logger.error(f"启动平台 {platform_name} 监控失败: {e}")
    
    def _stop_platform(self, platform_name: str):
        """停止单个平台监控"""
        if platform_name in self.workers:
            worker = self.workers[platform_name]
            worker.stop()
            worker.wait(5000)  # 等待5秒
            
            if worker.isRunning():
                worker.terminate()
                worker.wait(2000)
            
            del self.workers[platform_name]
            self.logger.info(f"平台 {platform_name} 监控已停止")
    
    def _on_platform_data(self, platform_name: str, data: Dict[str, Any]):
        """处理平台数据"""
        try:
            # 更新统计
            platform_stats = self.performance_data['platform_stats'].get(platform_name, {})
            platform_stats['requests'] = platform_stats.get('requests', 0) + 1
            platform_stats['successes'] = platform_stats.get('successes', 0) + 1
            platform_stats['last_success'] = time.time()
            
            if 'orders' in data and isinstance(data['orders'], list):
                order_count = len(data['orders'])
                platform_stats['total_orders'] = platform_stats.get('total_orders', 0) + order_count
                self.performance_data['total_orders'] += order_count
            
            self.performance_data['successful_requests'] += 1
            
            # 发射数据信号
            self.data_received.emit(platform_name, data)
            
            # 记录日志
            order_count = len(data.get('orders', []))
            self.logger.platform_operation(
                platform_name, '数据获取', True, 
                order_count=order_count
            )
            
        except Exception as e:
            self.logger.error(f"处理平台 {platform_name} 数据失败: {e}")
    
    def _on_platform_error(self, platform_name: str, error_message: str):
        """处理平台错误"""
        try:
            # 更新统计
            platform_stats = self.performance_data['platform_stats'].get(platform_name, {})
            platform_stats['requests'] = platform_stats.get('requests', 0) + 1
            platform_stats['failures'] = platform_stats.get('failures', 0) + 1
            platform_stats['last_error'] = time.time()
            
            self.performance_data['failed_requests'] += 1
            
            # 记录日志
            self.logger.platform_operation(
                platform_name, '数据获取', False,
                error=error_message
            )
            
        except Exception as e:
            self.logger.error(f"处理平台 {platform_name} 错误失败: {e}")
    
    def _emit_cycle_stats(self):
        """发射周期统计信息"""
        try:
            self.cycle_count += 1
            self.performance_data['total_cycles'] = self.cycle_count
            
            runtime = time.time() - self.start_time if self.start_time else 0
            
            cycle_stats = {
                'cycle_count': self.cycle_count,
                'runtime': runtime,
                'active_platforms': len(self.workers),
                'performance': self.performance_data.copy(),
                'timestamp': time.time()
            }
            
            self.cycle_completed.emit(cycle_stats)
            
            # 记录性能统计到日志
            success_rate = 0
            total_requests = self.performance_data['successful_requests'] + self.performance_data['failed_requests']
            if total_requests > 0:
                success_rate = (self.performance_data['successful_requests'] / total_requests) * 100
            
            self.logger.info(
                f"监控统计 - 周期:{self.cycle_count}, 运行时间:{runtime:.1f}s, "
                f"成功率:{success_rate:.1f}%, 总订单:{self.performance_data['total_orders']}"
            )
            
        except Exception as e:
            self.logger.error(f"发射周期统计失败: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """获取引擎状态"""
        runtime = time.time() - self.start_time if self.start_time else 0
        
        return {
            'is_running': self.is_running,
            'runtime': runtime,
            'cycle_count': self.cycle_count,
            'active_platforms': list(self.workers.keys()),
            'platform_count': len(self.platforms),
            'performance': self.performance_data.copy()
        }
    
    def restart_platform(self, platform_name: str):
        """重启指定平台"""
        if platform_name in self.workers:
            self.logger.info(f"重启平台: {platform_name}")
            self._stop_platform(platform_name)
            time.sleep(1)  # 短暂等待
            self._start_platform(platform_name)
    
    def get_platform_performance(self, platform_name: str) -> Dict[str, Any]:
        """获取指定平台的性能数据"""
        return self.performance_data['platform_stats'].get(platform_name, {})


class EngineManager(QObject):
    """引擎管理器 - 单例模式管理异步引擎"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        
        super().__init__()
        self.engine = None
        self.logger = get_logger()
        self._initialized = True
    
    def get_engine(self) -> Optional[AsyncEngine]:
        """获取引擎实例"""
        return self.engine
    
    def create_engine(self, platforms: Dict[str, Any] = None) -> AsyncEngine:
        """创建新引擎实例"""
        if self.engine:
            self.engine.stop_monitoring()
        
        self.engine = AsyncEngine(platforms)
        self.logger.info("创建新的异步引擎实例")
        return self.engine
    
    def shutdown(self):
        """关闭引擎"""
        if self.engine:
            self.engine.stop_monitoring()
            self.engine = None
            self.logger.info("异步引擎已关闭")


# 便捷函数
def get_engine_manager() -> EngineManager:
    """获取引擎管理器实例"""
    return EngineManager()

def get_engine() -> Optional[AsyncEngine]:
    """获取当前引擎实例"""
    return get_engine_manager().get_engine()

def create_engine(platforms: Dict[str, Any] = None) -> AsyncEngine:
    """创建新引擎实例"""
    return get_engine_manager().create_engine(platforms)