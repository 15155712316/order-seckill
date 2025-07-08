#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
守护者之盾 - 用户认证模块
提供机器码生成、在线认证、设备绑定等安全功能
"""

import hashlib
import subprocess
import logging
import aiohttp
import asyncio
import platform
import uuid
from typing import Tuple, Dict, Optional
import config

class AuthManager:
    """【守护者之盾】认证管理器"""
    
    def __init__(self):
        """初始化认证管理器"""
        self.server_url = config.API_BASE_URL  # 使用配置文件中的服务器地址
        self.network_config = config.NETWORK_CONFIG  # 网络配置
        self.machine_code = None
        self.session_token = None
        self.user_data = None

        logging.info(f"守护者之盾认证管理器初始化完成，服务器: {self.server_url}")
    
    def get_machine_code(self) -> str:
        """
        生成机器码 - V3.1权威修正版
        严格遵循经过验证的算法，确保生成结果的一致性。
        """
        if self.machine_code:
            return self.machine_code

        try:
            # 使用普通字典，最后统一排序，确保最终顺序一致
            hardware_info = {}

            # 1. 获取计算机名
            try:
                hardware_info["computer"] = platform.node()
            except Exception:
                pass

            # 2. 获取处理器信息
            try:
                hardware_info["processor"] = platform.processor()
            except Exception:
                pass

            # 3. 获取系统信息
            try:
                hardware_info["system"] = f"{platform.system()}-{platform.machine()}"
            except Exception:
                pass

            # 4. Windows平台特定信息
            if platform.system().lower() == 'windows':
                # 4.1 主板序列号
                try:
                    result = subprocess.run(
                        ['wmic', 'baseboard', 'get', 'serialnumber'],
                        capture_output=True, text=True, timeout=10,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                    if result.returncode == 0:
                        lines = result.stdout.strip().split('\n')
                        for line in lines:
                            if line.strip() and 'SerialNumber' not in line:
                                hardware_info["board"] = line.strip()
                                break
                except Exception:
                    pass

                # 4.2 CPU序列号
                try:
                    result = subprocess.run(
                        ['wmic', 'cpu', 'get', 'processorid'],
                        capture_output=True, text=True, timeout=10,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                    if result.returncode == 0:
                        lines = result.stdout.strip().split('\n')
                        for line in lines:
                            if line.strip() and 'ProcessorId' not in line:
                                hardware_info["cpu"] = line.strip()
                                break
                except Exception:
                    pass

                # 4.3 硬盘序列号
                try:
                    result = subprocess.run(
                        ['wmic', 'diskdrive', 'get', 'serialnumber'],
                        capture_output=True, text=True, timeout=10,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                    if result.returncode == 0:
                        lines = result.stdout.strip().split('\n')
                        for line in lines:
                            if line.strip() and 'SerialNumber' not in line:
                                hardware_info["disk"] = line.strip()
                                break
                except Exception:
                    pass

            # 5. MAC地址补充
            if len(hardware_info) < 2:
                try:
                    hardware_info["mac"] = hex(uuid.getnode())
                except Exception:
                    pass

            # 6. 按键名排序并组合所有硬件信息
            sorted_keys = sorted(hardware_info.keys())
            combined_parts = [f"{key}:{hardware_info[key]}" for key in sorted_keys]
            combined_info = "|".join(combined_parts)

            # 7. 生成最终机器码
            machine_code = hashlib.md5(combined_info.encode('utf-8')).hexdigest()[:16].upper()

            self.machine_code = machine_code
            logging.info(f"机器码生成成功: {machine_code[:8]}...")

            return machine_code

        except Exception:
            # 备用机制：如果主流程发生任何未知异常
            fallback_info = f"{platform.node()}-{platform.system()}-{platform.machine()}"
            fallback_code = hashlib.md5(fallback_info.encode('utf-8')).hexdigest()[:16].upper()
            self.machine_code = fallback_code
            logging.warning(f"使用备选机器码: {fallback_code[:8]}...")
            return fallback_code

    
    async def login(self, phone: str) -> Tuple[bool, str, Optional[Dict]]:
        """
        异步登录认证

        Args:
            phone (str): 手机号

        Returns:
            Tuple[bool, str, Optional[Dict]]: (成功状态, 消息, 用户数据)
        """
        machine_code = self.get_machine_code()

        # 准备登录数据
        login_data = {
            "phone": phone,
            "machineCode": machine_code,  # 使用驼峰命名
            "app_version": "3.1.0",
            "platform": "windows"
        }

        # 构建完整的登录URL
        login_url = f"{self.server_url}/login"

        # 重试逻辑
        retry_count = self.network_config.get('retry_count', 3)
        timeout = self.network_config.get('timeout', 30)
        verify_ssl = self.network_config.get('verify_ssl', False)

        for attempt in range(retry_count):
            try:
                logging.info(f"尝试登录 (第{attempt + 1}次): {phone}")

                # 创建SSL连接器
                connector = aiohttp.TCPConnector(ssl=verify_ssl)

                # 发送登录请求
                async with aiohttp.ClientSession(
                    connector=connector,
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as session:
                    async with session.post(
                        login_url,
                        json=login_data,
                        headers={
                            "Content-Type": "application/json",
                            "User-Agent": "SmartTicketGrabber/3.1.0"
                        }
                    ) as response:

                        if response.status == 200:
                            result = await response.json()

                            if result.get("success"):
                                # 登录成功
                                self.session_token = result.get("token")
                                self.user_data = result.get("user_data", {})

                                logging.info(f"用户登录成功: {phone}")
                                return True, "登录成功", self.user_data
                            else:
                                # 登录失败
                                error_message = result.get("message", "登录失败")
                                logging.warning(f"登录失败: {error_message}")
                                return False, error_message, None
                        else:
                            # HTTP错误
                            error_text = await response.text()
                            error_msg = f"服务器错误: HTTP {response.status}"
                            logging.error(f"登录请求失败: {error_msg} - {error_text}")

                            # 如果是最后一次重试，返回错误
                            if attempt == retry_count - 1:
                                return False, error_msg, None
                            else:
                                # 继续重试
                                logging.info(f"HTTP错误，准备重试...")
                                await asyncio.sleep(1)  # 重试前等待1秒
                                continue

            except aiohttp.ClientError as e:
                logging.error(f"网络连接失败 (第{attempt + 1}次): {e}")
                if attempt == retry_count - 1:
                    return False, "网络连接失败，请检查网络设置", None
                else:
                    logging.info(f"网络错误，准备重试...")
                    await asyncio.sleep(2)  # 重试前等待2秒
                    continue

            except asyncio.TimeoutError:
                logging.error(f"登录请求超时 (第{attempt + 1}次)")
                if attempt == retry_count - 1:
                    return False, "请求超时，请稍后重试", None
                else:
                    logging.info(f"请求超时，准备重试...")
                    await asyncio.sleep(2)  # 重试前等待2秒
                    continue

            except Exception as e:
                logging.error(f"登录过程异常 (第{attempt + 1}次): {e}")
                if attempt == retry_count - 1:
                    return False, f"登录异常: {str(e)}", None
                else:
                    logging.info(f"登录异常，准备重试...")
                    await asyncio.sleep(1)  # 重试前等待1秒
                    continue

        # 如果所有重试都失败了
        return False, "登录失败，已达到最大重试次数", None
    
    async def validate_session(self) -> Tuple[bool, str]:
        """
        验证会话有效性（心跳检测）

        Returns:
            Tuple[bool, str]: (验证结果, 消息)
        """
        if not self.session_token:
            return False, "未登录"

        machine_code = self.get_machine_code()

        # 准备验证数据
        validate_data = {
            "token": self.session_token,
            "machineCode": machine_code  # 使用驼峰命名
        }

        # 构建完整的验证URL
        validate_url = f"{self.server_url}/validate"

        # 网络配置
        timeout = self.network_config.get('timeout', 15)  # 心跳检测使用较短超时
        verify_ssl = self.network_config.get('verify_ssl', False)
        retry_count = min(self.network_config.get('retry_count', 3), 2)  # 心跳检测最多重试2次

        for attempt in range(retry_count):
            try:
                logging.debug(f"执行心跳验证 (第{attempt + 1}次)")

                # 创建SSL连接器
                connector = aiohttp.TCPConnector(ssl=verify_ssl)

                # 发送验证请求
                async with aiohttp.ClientSession(
                    connector=connector,
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as session:
                    async with session.post(
                        validate_url,
                        json=validate_data,
                        headers={
                            "Content-Type": "application/json",
                            "Authorization": f"Bearer {self.session_token}",
                            "User-Agent": "SmartTicketGrabber/3.1.0"
                        }
                    ) as response:

                        if response.status == 200:
                            result = await response.json()

                            if result.get("success"):
                                # 验证成功，更新用户数据
                                self.user_data = result.get("user_data", self.user_data)
                                logging.debug("会话验证成功")
                                return True, "会话有效"
                            else:
                                # 验证失败
                                error_message = result.get("message", "会话无效")
                                logging.warning(f"会话验证失败: {error_message}")
                                return False, error_message
                        else:
                            # HTTP错误
                            error_msg = f"服务器错误: HTTP {response.status}"
                            logging.error(f"会话验证请求失败: {error_msg}")

                            # 如果是最后一次重试，返回错误
                            if attempt == retry_count - 1:
                                return False, error_msg
                            else:
                                # 继续重试
                                logging.debug(f"HTTP错误，准备重试...")
                                await asyncio.sleep(1)
                                continue

            except aiohttp.ClientError as e:
                logging.error(f"心跳验证网络错误 (第{attempt + 1}次): {e}")
                if attempt == retry_count - 1:
                    return False, "网络连接失败"
                else:
                    await asyncio.sleep(1)
                    continue

            except asyncio.TimeoutError:
                logging.error(f"心跳验证超时 (第{attempt + 1}次)")
                if attempt == retry_count - 1:
                    return False, "验证请求超时"
                else:
                    await asyncio.sleep(1)
                    continue

            except Exception as e:
                logging.error(f"心跳验证异常 (第{attempt + 1}次): {e}")
                if attempt == retry_count - 1:
                    return False, f"验证异常: {str(e)}"
                else:
                    await asyncio.sleep(1)
                    continue

        # 如果所有重试都失败了
        return False, "心跳验证失败，已达到最大重试次数"
    
    def get_user_info(self) -> Optional[Dict]:
        """
        获取当前用户信息
        
        Returns:
            Optional[Dict]: 用户信息字典
        """
        return self.user_data
    
    def is_logged_in(self) -> bool:
        """
        检查是否已登录
        
        Returns:
            bool: 登录状态
        """
        return self.session_token is not None and self.user_data is not None
    
    def logout(self):
        """登出，清除会话信息"""
        self.session_token = None
        self.user_data = None
        logging.info("用户已登出")

# 错误消息映射表
ERROR_MESSAGE_MAP = {
    "Invalid phone number": "手机号格式不正确",
    "User not found": "用户不存在，请联系管理员",
    "Device not authorized": "系统检测到您的硬件发生了变更。为了您的账号安全，请联系管理员进行设备的重新授权。",
    "Account disabled": "账号已被禁用，请联系管理员",
    "Insufficient credits": "积分不足，请联系管理员充值",
    "Session expired": "会话已过期，请重新登录",
    "Invalid token": "登录状态无效，请重新登录",
    "Machine code mismatch": "设备验证失败，请联系管理员",
    "Server maintenance": "服务器维护中，请稍后重试",
    "Rate limit exceeded": "请求过于频繁，请稍后重试"
}

def get_user_friendly_message(server_message: str) -> str:
    """
    将服务器错误消息转换为用户友好的提示
    
    Args:
        server_message (str): 服务器返回的错误消息
        
    Returns:
        str: 用户友好的错误提示
    """
    return ERROR_MESSAGE_MAP.get(server_message, server_message)
