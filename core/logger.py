#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强日志系统 V2.0 - 支持日期轮转、性能监控、结构化日志
"""

import logging
import logging.handlers
import os
import time
import threading
from datetime import datetime
from typing import Dict, Any, Optional
import json


class PerformanceLogger:
    """性能日志记录器"""
    
    def __init__(self):
        self.start_times = {}
        self.performance_data = []
        self.lock = threading.Lock()
        
    def start_timer(self, operation_id: str):
        """开始计时"""
        with self.lock:
            self.start_times[operation_id] = time.time()
    
    def end_timer(self, operation_id: str, extra_data: Optional[Dict] = None):
        """结束计时并记录"""
        with self.lock:
            if operation_id in self.start_times:
                duration = time.time() - self.start_times[operation_id]
                del self.start_times[operation_id]
                
                perf_record = {
                    'operation': operation_id,
                    'duration': duration,
                    'timestamp': datetime.now().isoformat(),
                    'thread': threading.current_thread().name
                }
                
                if extra_data:
                    perf_record.update(extra_data)
                
                self.performance_data.append(perf_record)
                
                # 只保留最近1000条记录
                if len(self.performance_data) > 1000:
                    self.performance_data = self.performance_data[-1000:]
                
                # 记录慢操作（超过2秒）
                if duration > 2.0:
                    logging.warning(f"慢操作检测: {operation_id} 耗时 {duration:.2f}秒")
                    
                return duration
            return None
    
    def get_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        with self.lock:
            if not self.performance_data:
                return {}
            
            durations = [p['duration'] for p in self.performance_data]
            operations = {}
            
            for perf in self.performance_data:
                op_name = perf['operation']
                if op_name not in operations:
                    operations[op_name] = []
                operations[op_name].append(perf['duration'])
            
            # 按操作类型统计
            op_stats = {}
            for op_name, times in operations.items():
                op_stats[op_name] = {
                    'count': len(times),
                    'avg': sum(times) / len(times),
                    'max': max(times),
                    'min': min(times)
                }
            
            return {
                'total_operations': len(self.performance_data),
                'avg_duration': sum(durations) / len(durations),
                'max_duration': max(durations),
                'min_duration': min(durations),
                'operations': op_stats
            }


class JSONFormatter(logging.Formatter):
    """JSON格式化器，用于结构化日志"""
    
    def format(self, record):
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'thread': threading.current_thread().name,
            'message': record.getMessage()
        }
        
        # 添加异常信息
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # 添加额外字段
        if hasattr(record, 'extra_data'):
            log_entry['extra'] = record.extra_data
            
        return json.dumps(log_entry, ensure_ascii=False)


class ColoredFormatter(logging.Formatter):
    """彩色控制台格式化器"""
    
    # ANSI颜色代码
    COLORS = {
        'DEBUG': '\033[36m',     # 青色
        'INFO': '\033[32m',      # 绿色
        'WARNING': '\033[33m',   # 黄色
        'ERROR': '\033[31m',     # 红色
        'CRITICAL': '\033[35m'   # 紫色
    }
    RESET = '\033[0m'
    
    def format(self, record):
        # 添加颜色
        level_color = self.COLORS.get(record.levelname, '')
        record.levelname = f"{level_color}{record.levelname}{self.RESET}"
        
        # 格式化时间
        record.asctime = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        
        return super().format(record)


class EnhancedLogger:
    """增强日志系统"""
    
    def __init__(self, 
                 name: str = "ticket_grabber",
                 log_dir: str = "logs",
                 max_file_size: int = 10 * 1024 * 1024,  # 10MB
                 backup_count: int = 7,
                 enable_performance: bool = True):
        """
        初始化增强日志系统
        
        Args:
            name: 日志器名称
            log_dir: 日志目录
            max_file_size: 单个日志文件最大大小（字节）
            backup_count: 保留的日志文件数量
            enable_performance: 是否启用性能监控
        """
        self.name = name
        self.log_dir = log_dir
        self.logger = logging.getLogger(name)
        self.performance = PerformanceLogger() if enable_performance else None
        
        # 创建日志目录
        os.makedirs(log_dir, exist_ok=True)
        
        # 设置日志级别
        self.logger.setLevel(logging.DEBUG)
        
        # 清除现有处理器
        self.logger.handlers.clear()
        
        # 设置控制台处理器
        self._setup_console_handler()
        
        # 设置文件处理器
        self._setup_file_handlers(max_file_size, backup_count)
        
        # 防止重复日志
        self.logger.propagate = False
        
        logging.info(f"增强日志系统初始化完成 - 日志目录: {log_dir}")
    
    def _setup_console_handler(self):
        """设置控制台处理器"""
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # 使用彩色格式化器
        console_formatter = ColoredFormatter(
            '%(asctime)s [%(levelname)s] %(module)s.%(funcName)s:%(lineno)d - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        
        self.logger.addHandler(console_handler)
    
    def _setup_file_handlers(self, max_file_size: int, backup_count: int):
        """设置文件处理器"""
        
        # 1. 主日志文件（所有级别）
        main_file = os.path.join(self.log_dir, f"{self.name}.log")
        main_handler = logging.handlers.RotatingFileHandler(
            main_file, maxBytes=max_file_size, backupCount=backup_count, encoding='utf-8'
        )
        main_handler.setLevel(logging.DEBUG)
        main_formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s.%(module)s.%(funcName)s:%(lineno)d - %(message)s'
        )
        main_handler.setFormatter(main_formatter)
        self.logger.addHandler(main_handler)
        
        # 2. 错误日志文件（ERROR及以上级别）
        error_file = os.path.join(self.log_dir, f"{self.name}_error.log")
        error_handler = logging.handlers.RotatingFileHandler(
            error_file, maxBytes=max_file_size, backupCount=backup_count, encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(main_formatter)
        self.logger.addHandler(error_handler)
        
        # 3. 性能日志文件（JSON格式）
        if self.performance:
            perf_file = os.path.join(self.log_dir, f"{self.name}_performance.jsonl")
            perf_handler = logging.handlers.RotatingFileHandler(
                perf_file, maxBytes=max_file_size, backupCount=backup_count, encoding='utf-8'
            )
            perf_handler.setLevel(logging.INFO)
            perf_handler.setFormatter(JSONFormatter())
            
            # 创建性能专用logger
            self.perf_logger = logging.getLogger(f"{self.name}.performance")
            self.perf_logger.setLevel(logging.INFO)
            self.perf_logger.addHandler(perf_handler)
            self.perf_logger.propagate = False
        
        # 4. 日期轮转日志（按日期归档）
        daily_file = os.path.join(self.log_dir, f"{self.name}_daily.log")
        daily_handler = logging.handlers.TimedRotatingFileHandler(
            daily_file, when='midnight', interval=1, backupCount=30, encoding='utf-8'
        )
        daily_handler.suffix = '%Y-%m-%d'
        daily_handler.setLevel(logging.INFO)
        daily_handler.setFormatter(main_formatter)
        self.logger.addHandler(daily_handler)
    
    def start_operation(self, operation_name: str) -> str:
        """开始记录操作性能"""
        if self.performance:
            operation_id = f"{operation_name}_{int(time.time() * 1000)}"
            self.performance.start_timer(operation_id)
            return operation_id
        return ""
    
    def end_operation(self, operation_id: str, extra_data: Optional[Dict] = None):
        """结束操作性能记录"""
        if self.performance and operation_id:
            duration = self.performance.end_timer(operation_id, extra_data)
            if duration and hasattr(self, 'perf_logger'):
                # 记录到性能日志
                perf_record = logging.LogRecord(
                    name=f"{self.name}.performance",
                    level=logging.INFO,
                    pathname="",
                    lineno=0,
                    msg="",
                    args=(),
                    exc_info=None
                )
                perf_record.extra_data = {
                    'operation': operation_id.split('_')[0],
                    'duration': duration,
                    'extra': extra_data or {}
                }
                self.perf_logger.handle(perf_record)
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计信息"""
        if self.performance:
            return self.performance.get_stats()
        return {}
    
    def log_structured(self, level: int, message: str, extra_data: Optional[Dict] = None):
        """记录结构化日志"""
        record = self.logger.makeRecord(
            self.logger.name, level, "", 0, message, (), None
        )
        if extra_data:
            record.extra_data = extra_data
        self.logger.handle(record)
    
    def debug(self, message: str, **kwargs):
        """调试日志"""
        self.logger.debug(message, extra=kwargs if kwargs else None)
    
    def info(self, message: str, **kwargs):
        """信息日志"""
        self.logger.info(message, extra=kwargs if kwargs else None)
    
    def warning(self, message: str, **kwargs):
        """警告日志"""
        self.logger.warning(message, extra=kwargs if kwargs else None)
    
    def error(self, message: str, **kwargs):
        """错误日志"""
        self.logger.error(message, extra=kwargs if kwargs else None)
    
    def critical(self, message: str, **kwargs):
        """严重错误日志"""
        self.logger.critical(message, extra=kwargs if kwargs else None)
    
    def platform_operation(self, platform: str, operation: str, success: bool, 
                          duration: float = None, order_count: int = None):
        """记录平台操作日志"""
        extra_data = {
            'platform': platform,
            'operation': operation,
            'success': success,
            'duration': duration,
            'order_count': order_count
        }
        
        level = logging.INFO if success else logging.WARNING
        message = f"{platform}平台{operation}{'成功' if success else '失败'}"
        
        if order_count is not None:
            message += f"，处理{order_count}条订单"
        if duration is not None:
            message += f"，耗时{duration:.2f}秒"
            
        self.log_structured(level, message, extra_data)
    
    def cleanup_old_logs(self, days_to_keep: int = 30):
        """清理旧日志文件"""
        try:
            import glob
            from pathlib import Path
            
            cutoff_time = time.time() - (days_to_keep * 24 * 3600)
            
            # 查找所有日志文件
            for log_file in glob.glob(os.path.join(self.log_dir, "*.log*")):
                if os.path.getmtime(log_file) < cutoff_time:
                    try:
                        os.remove(log_file)
                        self.info(f"已删除过期日志文件: {log_file}")
                    except Exception as e:
                        self.warning(f"删除日志文件失败: {log_file}, 错误: {e}")
                        
        except Exception as e:
            self.error(f"清理日志文件失败: {e}")


# 全局日志实例
_global_logger = None

def setup_global_logger(**kwargs) -> EnhancedLogger:
    """设置全局日志实例"""
    global _global_logger
    _global_logger = EnhancedLogger(**kwargs)
    return _global_logger

def get_logger() -> EnhancedLogger:
    """获取全局日志实例"""
    global _global_logger
    if _global_logger is None:
        _global_logger = EnhancedLogger()
    return _global_logger

# 便捷函数
def debug(message: str, **kwargs):
    get_logger().debug(message, **kwargs)

def info(message: str, **kwargs):
    get_logger().info(message, **kwargs)

def warning(message: str, **kwargs):
    get_logger().warning(message, **kwargs)

def error(message: str, **kwargs):
    get_logger().error(message, **kwargs)

def critical(message: str, **kwargs):
    get_logger().critical(message, **kwargs)

def start_operation(operation_name: str) -> str:
    return get_logger().start_operation(operation_name)

def end_operation(operation_id: str, **kwargs):
    get_logger().end_operation(operation_id, kwargs if kwargs else None)

def platform_operation(platform: str, operation: str, success: bool, **kwargs):
    get_logger().platform_operation(platform, operation, success, **kwargs)