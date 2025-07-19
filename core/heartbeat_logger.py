#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
心跳机制专用日志记录器
提供独立的心跳日志文件和结构化日志记录功能
"""

import logging
import os
import time
import json
from logging.handlers import RotatingFileHandler
from typing import Dict, Any, Optional
from datetime import datetime


class HeartbeatLogger:
    """心跳机制专用日志记录器"""
    
    def __init__(self, log_dir: str = "logs"):
        """
        初始化心跳日志记录器
        
        Args:
            log_dir: 日志目录路径
        """
        self.log_dir = log_dir
        self.logger = None
        self._setup_logger()
    
    def _setup_logger(self):
        """设置独立的心跳日志记录器"""
        try:
            # 确保日志目录存在
            os.makedirs(self.log_dir, exist_ok=True)
            
            # 创建独立的logger实例
            self.logger = logging.getLogger('heartbeat')
            self.logger.setLevel(logging.DEBUG)
            
            # 清除已有的处理器，避免重复
            self.logger.handlers.clear()
            
            # 创建心跳日志文件路径
            log_file = os.path.join(self.log_dir, 'heartbeat.log')
            
            # 创建轮转文件处理器（最大10MB，保留5个备份文件）
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5,
                encoding='utf-8'
            )
            
            # 设置日志格式
            formatter = logging.Formatter(
                '%(asctime)s [%(levelname)s] %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(formatter)
            
            # 添加处理器
            self.logger.addHandler(file_handler)

            # 防止日志传播到根logger
            self.logger.propagate = False

            self.logger.info("心跳日志记录器初始化完成")

            # 强制刷新日志
            for handler in self.logger.handlers:
                handler.flush()
            
        except Exception as e:
            # 如果心跳日志初始化失败，使用主日志记录错误
            logging.error(f"心跳日志记录器初始化失败: {e}")
    
    def _mask_sensitive_data(self, data: str, mask_char: str = '*', keep_chars: int = 4) -> str:
        """
        脱敏敏感数据
        
        Args:
            data: 原始数据
            mask_char: 掩码字符
            keep_chars: 保留的字符数（前后各保留）
            
        Returns:
            脱敏后的数据
        """
        if not data or len(data) <= keep_chars * 2:
            return mask_char * len(data) if data else ""
        
        prefix = data[:keep_chars]
        suffix = data[-keep_chars:]
        middle_length = len(data) - keep_chars * 2
        
        return f"{prefix}{mask_char * middle_length}{suffix}"
    
    def log_heartbeat_request(self, heartbeat_type: str, machine_code: str, 
                            phone: str = None, token: str = None, 
                            request_data: Dict[str, Any] = None):
        """
        记录心跳请求信息
        
        Args:
            heartbeat_type: 心跳类型 ('scheduled', 'retry')
            machine_code: 机器码
            phone: 手机号
            token: 会话令牌
            request_data: 请求数据
        """
        try:
            # 脱敏处理
            masked_machine_code = self._mask_sensitive_data(machine_code) if machine_code else "N/A"
            masked_phone = self._mask_sensitive_data(phone) if phone else "N/A"
            masked_token = self._mask_sensitive_data(token, keep_chars=6) if token else "N/A"
            
            # 构建日志消息
            log_msg = f"HEARTBEAT_REQUEST: type={heartbeat_type}, machine_code={masked_machine_code}"
            
            if phone:
                log_msg += f", phone={masked_phone}"
            
            if token:
                log_msg += f", token={masked_token}"
            
            # 记录请求数据（脱敏）
            if request_data:
                safe_data = {}
                for key, value in request_data.items():
                    if key.lower() in ['token', 'machineCode', 'machine_code']:
                        safe_data[key] = self._mask_sensitive_data(str(value), keep_chars=6)
                    else:
                        safe_data[key] = value
                
                log_msg += f", request_data={json.dumps(safe_data, ensure_ascii=False)}"
            
            self.logger.info(log_msg)

            # 强制刷新日志
            for handler in self.logger.handlers:
                handler.flush()

        except Exception as e:
            self.logger.error(f"记录心跳请求日志失败: {e}")
            # 强制刷新日志
            for handler in self.logger.handlers:
                handler.flush()
    
    def log_heartbeat_response(self, status_code: int, response_data: Dict[str, Any] = None,
                             duration: float = None, success: bool = None, 
                             error_message: str = None):
        """
        记录心跳响应信息
        
        Args:
            status_code: HTTP状态码
            response_data: 响应数据
            duration: 请求耗时（秒）
            success: 认证结果
            error_message: 错误消息
        """
        try:
            # 构建日志消息
            log_msg = f"HEARTBEAT_RESPONSE: status={status_code}"
            
            if duration is not None:
                log_msg += f", duration={duration:.3f}s"
            
            if success is not None:
                result = "success" if success else "failure"
                log_msg += f", result={result}"
            
            if error_message:
                log_msg += f", error={error_message}"
            
            # 记录响应数据（脱敏）
            if response_data:
                safe_data = {}
                for key, value in response_data.items():
                    if key.lower() in ['token', 'session_token', 'access_token']:
                        safe_data[key] = self._mask_sensitive_data(str(value), keep_chars=6)
                    elif key.lower() in ['user_data', 'userdata'] and isinstance(value, dict):
                        # 脱敏用户数据
                        safe_user_data = {}
                        for user_key, user_value in value.items():
                            if user_key.lower() in ['phone', 'mobile', 'telephone']:
                                safe_user_data[user_key] = self._mask_sensitive_data(str(user_value))
                            else:
                                safe_user_data[user_key] = user_value
                        safe_data[key] = safe_user_data
                    else:
                        safe_data[key] = value
                
                log_msg += f", response_data={json.dumps(safe_data, ensure_ascii=False)}"
            
            # 根据结果选择日志级别
            if success is False or status_code >= 400:
                self.logger.error(log_msg)
            else:
                self.logger.info(log_msg)

            # 强制刷新日志
            for handler in self.logger.handlers:
                handler.flush()

        except Exception as e:
            self.logger.error(f"记录心跳响应日志失败: {e}")
            # 强制刷新日志
            for handler in self.logger.handlers:
                handler.flush()
    
    def log_heartbeat_retry(self, retry_count: int, max_retries: int, 
                          retry_interval: int, reason: str = None):
        """
        记录心跳重试信息
        
        Args:
            retry_count: 当前重试次数
            max_retries: 最大重试次数
            retry_interval: 重试间隔（秒）
            reason: 重试原因
        """
        try:
            log_msg = f"HEARTBEAT_RETRY: attempt={retry_count}/{max_retries}, interval={retry_interval}s"
            
            if reason:
                log_msg += f", reason={reason}"
            
            self.logger.warning(log_msg)
            
        except Exception as e:
            self.logger.error(f"记录心跳重试日志失败: {e}")
    
    def log_heartbeat_network_error(self, error_type: str, error_message: str, 
                                  attempt: int = None, duration: float = None):
        """
        记录心跳网络错误
        
        Args:
            error_type: 错误类型 ('timeout', 'connection', 'ssl', 'dns', 'other')
            error_message: 错误消息
            attempt: 尝试次数
            duration: 请求耗时
        """
        try:
            log_msg = f"HEARTBEAT_NETWORK_ERROR: type={error_type}, message={error_message}"
            
            if attempt is not None:
                log_msg += f", attempt={attempt}"
            
            if duration is not None:
                log_msg += f", duration={duration:.3f}s"
            
            self.logger.error(log_msg)
            
        except Exception as e:
            self.logger.error(f"记录心跳网络错误日志失败: {e}")
    
    def log_heartbeat_state_change(self, old_state: str, new_state: str, 
                                 trigger: str = None, details: str = None):
        """
        记录心跳状态变更
        
        Args:
            old_state: 旧状态
            new_state: 新状态
            trigger: 触发原因
            details: 详细信息
        """
        try:
            log_msg = f"HEARTBEAT_STATE_CHANGE: {old_state} -> {new_state}"
            
            if trigger:
                log_msg += f", trigger={trigger}"
            
            if details:
                log_msg += f", details={details}"
            
            self.logger.info(log_msg)
            
        except Exception as e:
            self.logger.error(f"记录心跳状态变更日志失败: {e}")
    
    def log_heartbeat_summary(self, total_attempts: int, success_count: int, 
                            failure_count: int, avg_duration: float = None):
        """
        记录心跳统计摘要
        
        Args:
            total_attempts: 总尝试次数
            success_count: 成功次数
            failure_count: 失败次数
            avg_duration: 平均耗时
        """
        try:
            success_rate = (success_count / total_attempts * 100) if total_attempts > 0 else 0
            
            log_msg = (f"HEARTBEAT_SUMMARY: total={total_attempts}, "
                      f"success={success_count}, failure={failure_count}, "
                      f"success_rate={success_rate:.1f}%")
            
            if avg_duration is not None:
                log_msg += f", avg_duration={avg_duration:.3f}s"
            
            self.logger.info(log_msg)
            
        except Exception as e:
            self.logger.error(f"记录心跳统计摘要日志失败: {e}")


# 全局心跳日志记录器实例
_heartbeat_logger = None

def get_heartbeat_logger() -> HeartbeatLogger:
    """获取全局心跳日志记录器实例"""
    global _heartbeat_logger
    if _heartbeat_logger is None:
        _heartbeat_logger = HeartbeatLogger()
    return _heartbeat_logger
