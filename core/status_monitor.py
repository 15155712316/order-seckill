#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
状态监控系统 V1.0 - 简单版本
提供系统运行状态、平台状态、性能指标的监控
"""

import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from core.logger import get_logger


@dataclass
class SystemStatus:
    """系统状态数据结构"""
    is_running: bool = False
    start_time: Optional[float] = None
    runtime_seconds: float = 0.0
    total_cycles: int = 0
    active_platforms: int = 0
    total_platforms: int = 0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0


@dataclass
class PlatformStatus:
    """平台状态数据结构"""
    name: str
    is_active: bool = False
    last_success_time: Optional[float] = None
    last_error_time: Optional[float] = None
    success_count: int = 0
    error_count: int = 0
    total_orders: int = 0
    avg_response_time: float = 0.0
    current_status: str = "idle"  # idle, running, error, disabled


@dataclass
class PerformanceMetrics:
    """性能指标数据结构"""
    requests_per_minute: float = 0.0
    orders_per_minute: float = 0.0
    success_rate: float = 100.0
    avg_response_time: float = 0.0
    memory_trend: List[float] = None
    cpu_trend: List[float] = None
    
    def __post_init__(self):
        if self.memory_trend is None:
            self.memory_trend = []
        if self.cpu_trend is None:
            self.cpu_trend = []


class StatusMonitor(QObject):
    """状态监控器 - 收集和管理系统状态信息"""
    
    # 状态更新信号
    status_updated = pyqtSignal(dict)  # 完整状态信息
    platform_status_changed = pyqtSignal(str, dict)  # platform_name, status
    performance_updated = pyqtSignal(dict)  # 性能指标
    alert_triggered = pyqtSignal(str, str, str)  # level, title, message
    
    def __init__(self, update_interval: int = 5):
        """
        初始化状态监控器
        
        Args:
            update_interval: 状态更新间隔（秒）
        """
        super().__init__()
        self.logger = get_logger()
        self.update_interval = update_interval
        
        # 状态数据
        self.system_status = SystemStatus()
        self.platform_statuses: Dict[str, PlatformStatus] = {}
        self.performance_metrics = PerformanceMetrics()
        
        # 历史数据（用于趋势分析）
        self.history_size = 60  # 保留60个数据点
        self.request_history = []
        self.order_history = []
        self.response_time_history = []
        
        # 计数器
        self.last_total_requests = 0
        self.last_total_orders = 0
        self.last_update_time = time.time()
        
        # 定时器
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_status)
        self.update_timer.setInterval(update_interval * 1000)
        
        # 报警阈值
        self.alert_thresholds = {
            'error_rate': 20.0,      # 错误率超过20%
            'response_time': 10.0,   # 响应时间超过10秒
            'memory_usage': 500.0,   # 内存使用超过500MB
            'platform_down_time': 300  # 平台离线超过5分钟
        }
        
        self.logger.info("状态监控器初始化完成")
    
    def start_monitoring(self):
        """开始监控"""
        self.system_status.is_running = True
        self.system_status.start_time = time.time()
        self.last_update_time = time.time()
        
        self.update_timer.start()
        self.logger.info(f"状态监控已启动，更新间隔: {self.update_interval}秒")
    
    def stop_monitoring(self):
        """停止监控"""
        self.system_status.is_running = False
        self.update_timer.stop()
        self.logger.info("状态监控已停止")
    
    def register_platform(self, platform_name: str):
        """注册平台"""
        if platform_name not in self.platform_statuses:
            self.platform_statuses[platform_name] = PlatformStatus(name=platform_name)
            self.system_status.total_platforms = len(self.platform_statuses)
            self.logger.debug(f"已注册平台: {platform_name}")
    
    def unregister_platform(self, platform_name: str):
        """注销平台"""
        if platform_name in self.platform_statuses:
            del self.platform_statuses[platform_name]
            self.system_status.total_platforms = len(self.platform_statuses)
            self.logger.debug(f"已注销平台: {platform_name}")
    
    def update_platform_status(self, platform_name: str, status_data: Dict[str, Any]):
        """更新平台状态"""
        if platform_name not in self.platform_statuses:
            self.register_platform(platform_name)
        
        platform_status = self.platform_statuses[platform_name]
        
        # 更新基本信息
        platform_status.is_active = status_data.get('success', False)
        platform_status.current_status = status_data.get('status', 'unknown')
        
        # 更新计数器
        if status_data.get('success', False):
            platform_status.success_count += 1
            platform_status.last_success_time = time.time()
            
            # 更新订单数
            order_count = len(status_data.get('orders', []))
            platform_status.total_orders += order_count
        else:
            platform_status.error_count += 1
            platform_status.last_error_time = time.time()
        
        # 更新响应时间
        metrics = status_data.get('metrics', {})
        if 'avg_response_time' in metrics:
            platform_status.avg_response_time = metrics['avg_response_time']
        
        # 发射平台状态变化信号
        self.platform_status_changed.emit(platform_name, asdict(platform_status))
        
        # 检查告警
        self._check_platform_alerts(platform_name, platform_status)
    
    def _update_status(self):
        """定时更新状态信息"""
        try:
            current_time = time.time()
            
            # 更新系统状态
            self._update_system_status(current_time)
            
            # 更新性能指标
            self._update_performance_metrics(current_time)
            
            # 发射状态更新信号
            status_data = self._get_complete_status()
            self.status_updated.emit(status_data)
            
            # 发射性能更新信号
            self.performance_updated.emit(asdict(self.performance_metrics))
            
            self.last_update_time = current_time
            
        except Exception as e:
            self.logger.error(f"更新状态信息失败: {e}")
    
    def _update_system_status(self, current_time: float):
        """更新系统状态"""
        if self.system_status.start_time:
            self.system_status.runtime_seconds = current_time - self.system_status.start_time
        
        # 统计活跃平台数
        active_count = sum(1 for status in self.platform_statuses.values() if status.is_active)
        self.system_status.active_platforms = active_count
        
        # 获取系统资源使用情况
        try:
            import psutil
            process = psutil.Process()
            self.system_status.memory_usage_mb = process.memory_info().rss / 1024 / 1024
            self.system_status.cpu_usage_percent = process.cpu_percent()
        except ImportError:
            # 如果没有psutil，使用简化版本
            self.system_status.memory_usage_mb = 0.0
            self.system_status.cpu_usage_percent = 0.0
    
    def _update_performance_metrics(self, current_time: float):
        """更新性能指标"""
        time_diff = current_time - self.last_update_time
        if time_diff <= 0:
            return
        
        # 计算当前请求数和订单数
        current_total_requests = sum(status.success_count + status.error_count 
                                   for status in self.platform_statuses.values())
        current_total_orders = sum(status.total_orders 
                                 for status in self.platform_statuses.values())
        
        # 计算每分钟速率
        requests_diff = current_total_requests - self.last_total_requests
        orders_diff = current_total_orders - self.last_total_orders
        
        self.performance_metrics.requests_per_minute = (requests_diff / time_diff) * 60
        self.performance_metrics.orders_per_minute = (orders_diff / time_diff) * 60
        
        # 计算成功率
        total_success = sum(status.success_count for status in self.platform_statuses.values())
        total_requests = current_total_requests
        if total_requests > 0:
            self.performance_metrics.success_rate = (total_success / total_requests) * 100
        
        # 计算平均响应时间
        active_platforms = [status for status in self.platform_statuses.values() 
                          if status.avg_response_time > 0]
        if active_platforms:
            self.performance_metrics.avg_response_time = sum(
                status.avg_response_time for status in active_platforms
            ) / len(active_platforms)
        
        # 更新趋势数据
        self._update_trends()
        
        # 更新计数器
        self.last_total_requests = current_total_requests
        self.last_total_orders = current_total_orders
    
    def _update_trends(self):
        """更新趋势数据"""
        # 添加当前数据点
        self.request_history.append(self.performance_metrics.requests_per_minute)
        self.order_history.append(self.performance_metrics.orders_per_minute)
        self.response_time_history.append(self.performance_metrics.avg_response_time)
        self.performance_metrics.memory_trend.append(self.system_status.memory_usage_mb)
        self.performance_metrics.cpu_trend.append(self.system_status.cpu_usage_percent)
        
        # 保持历史数据大小
        for history in [self.request_history, self.order_history, self.response_time_history,
                       self.performance_metrics.memory_trend, self.performance_metrics.cpu_trend]:
            if len(history) > self.history_size:
                history.pop(0)
    
    def _check_platform_alerts(self, platform_name: str, platform_status: PlatformStatus):
        """检查平台告警"""
        current_time = time.time()
        
        # 检查平台是否长时间离线
        if platform_status.last_success_time:
            offline_time = current_time - platform_status.last_success_time
            if offline_time > self.alert_thresholds['platform_down_time']:
                self.alert_triggered.emit(
                    "warning",
                    f"平台 {platform_name} 离线",
                    f"平台已离线 {offline_time:.0f} 秒"
                )
        
        # 检查错误率
        total_requests = platform_status.success_count + platform_status.error_count
        if total_requests >= 10:  # 至少有10次请求才检查错误率
            error_rate = (platform_status.error_count / total_requests) * 100
            if error_rate > self.alert_thresholds['error_rate']:
                self.alert_triggered.emit(
                    "error",
                    f"平台 {platform_name} 错误率过高",
                    f"错误率: {error_rate:.1f}%"
                )
    
    def _get_complete_status(self) -> Dict[str, Any]:
        """获取完整状态信息"""
        return {
            'system': asdict(self.system_status),
            'platforms': {name: asdict(status) for name, status in self.platform_statuses.items()},
            'performance': asdict(self.performance_metrics),
            'timestamp': time.time(),
            'update_interval': self.update_interval
        }
    
    # 公共接口方法
    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        return asdict(self.system_status)
    
    def get_platform_status(self, platform_name: str) -> Optional[Dict[str, Any]]:
        """获取指定平台状态"""
        if platform_name in self.platform_statuses:
            return asdict(self.platform_statuses[platform_name])
        return None
    
    def get_all_platform_status(self) -> Dict[str, Dict[str, Any]]:
        """获取所有平台状态"""
        return {name: asdict(status) for name, status in self.platform_statuses.items()}
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """获取性能指标"""
        return asdict(self.performance_metrics)
    
    def get_summary(self) -> Dict[str, Any]:
        """获取状态摘要"""
        runtime_str = "未启动"
        if self.system_status.start_time:
            runtime = time.time() - self.system_status.start_time
            hours, remainder = divmod(runtime, 3600)
            minutes, seconds = divmod(remainder, 60)
            runtime_str = f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"
        
        return {
            'is_running': self.system_status.is_running,
            'runtime': runtime_str,
            'platforms': f"{self.system_status.active_platforms}/{self.system_status.total_platforms}",
            'success_rate': f"{self.performance_metrics.success_rate:.1f}%",
            'requests_per_min': f"{self.performance_metrics.requests_per_minute:.1f}",
            'orders_per_min': f"{self.performance_metrics.orders_per_minute:.1f}",
            'avg_response_time': f"{self.performance_metrics.avg_response_time:.2f}s",
            'memory_usage': f"{self.system_status.memory_usage_mb:.1f}MB"
        }
    
    def set_alert_threshold(self, key: str, value: float):
        """设置告警阈值"""
        if key in self.alert_thresholds:
            self.alert_thresholds[key] = value
            self.logger.info(f"告警阈值已更新: {key} = {value}")
    
    def clear_platform_history(self, platform_name: str):
        """清除平台历史数据"""
        if platform_name in self.platform_statuses:
            status = self.platform_statuses[platform_name]
            status.success_count = 0
            status.error_count = 0
            status.total_orders = 0
            status.last_success_time = None
            status.last_error_time = None
            self.logger.info(f"已清除平台 {platform_name} 的历史数据")


# 全局监控器实例
_global_monitor = None

def get_status_monitor() -> StatusMonitor:
    """获取全局状态监控器实例"""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = StatusMonitor()
    return _global_monitor

def setup_monitoring(update_interval: int = 5) -> StatusMonitor:
    """设置全局状态监控器"""
    global _global_monitor
    _global_monitor = StatusMonitor(update_interval)
    return _global_monitor