#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
音频处理模块 - 负责语音生成和播放功能
"""

import os
import logging
import hashlib
import threading
import time
import subprocess
import sys
from gtts import gTTS
from config import TTS_CACHE_DIR, WHITELIST_ALERT_TEXT


class TTSPlayer:
    """文本转语音播放器类 - 基于pygame的高性能音频播放"""

    def __init__(self):
        """初始化TTS播放器"""
        self.cache_dir = TTS_CACHE_DIR
        self._ensure_cache_dir()
        # 添加播放锁，防止并发播放冲突
        self._play_lock = threading.Lock()
        # pygame初始化状态跟踪
        self._pygame_initialized = False
        logging.info(f"TTSPlayer初始化完成，缓存目录: {self.cache_dir}")
        logging.info("音频播放器已切换为pygame引擎")
    
    def _ensure_cache_dir(self):
        """确保缓存目录存在"""
        try:
            if not os.path.exists(self.cache_dir):
                os.makedirs(self.cache_dir)
                logging.info(f"创建语音缓存目录: {self.cache_dir}")
        except Exception as e:
            logging.error(f"创建缓存目录失败: {e}")

    def _init_pygame(self):
        """延迟初始化pygame，提升启动性能"""
        if self._pygame_initialized:
            return True

        try:
            import pygame

            # 优化的pygame初始化参数
            pygame.mixer.pre_init(
                frequency=44100,    # 高质量采样率
                size=-16,          # 16位音频
                channels=2,        # 立体声
                buffer=1024        # 优化的缓冲区大小，平衡延迟和稳定性
            )
            pygame.mixer.init()

            self._pygame_initialized = True
            logging.debug("pygame音频引擎初始化成功")
            return True

        except ImportError:
            logging.error("pygame库不可用，请安装: pip install pygame")
            return False
        except Exception as e:
            logging.error(f"pygame初始化失败: {e}")
            return False
    
    def _generate_filename(self, text: str) -> str:
        """
        根据文本内容生成唯一的文件名（优化版本）

        Args:
            text (str): 要转换的文本

        Returns:
            str: 生成的文件名（包含完整路径）
        """
        try:
            # 【优化】对关键词策略的利润语音进行智能缓存
            optimized_text = self._optimize_profit_text(text)

            # 使用MD5生成唯一文件名
            text_hash = hashlib.md5(optimized_text.encode('utf-8')).hexdigest()
            filename = f"{text_hash}.mp3"
            filepath = os.path.join(self.cache_dir, filename)
            return filepath
        except Exception as e:
            logging.error(f"生成文件名失败: {e}")
            return None

    def _optimize_profit_text(self, text: str) -> str:
        """
        优化利润相关的语音文本，使用整数利润金额提高缓存命中率

        Args:
            text (str): 原始文本

        Returns:
            str: 优化后的文本（整数利润金额）
        """
        import re

        # 检查是否是利润相关的语音文本
        profit_pattern = r'(\d+\.?\d*)元利润，(.+)平台来单了'
        match = re.match(profit_pattern, text)

        if match:
            profit_str = match.group(1)
            platform = match.group(2)

            try:
                profit_value = float(profit_str)

                # 【新的缓存优化策略】将利润金额四舍五入为整数
                # 这样可以保持精确的利润信息，同时提高缓存复用率
                rounded_profit = round(profit_value)

                # 返回整数利润的文本模板
                return f"{rounded_profit}元利润，{platform}平台来单了"

            except (ValueError, TypeError):
                # 如果利润解析失败，返回原文本
                logging.warning(f"利润解析失败，原文本: {text}")
                pass

        # 非利润文本或解析失败，返回原文本
        return text
    
    def _generate_tts_file(self, text: str, filepath: str) -> bool:
        """
        生成TTS语音文件
        
        Args:
            text (str): 要转换的文本
            filepath (str): 保存文件的路径
            
        Returns:
            bool: 生成是否成功
        """
        try:
            logging.info(f"正在生成语音文件: {text}")
            
            # 使用gTTS生成语音
            tts = gTTS(text=text, lang='zh', slow=False)
            tts.save(filepath)
            
            logging.info(f"语音文件生成成功: {filepath}")
            return True
            
        except Exception as e:
            logging.error(f"生成语音文件失败: {e}")
            return False
    
    def _play_audio_file(self, filepath: str):
        """
        播放音频文件（多线程安全版本）

        Args:
            filepath (str): 音频文件路径
        """
        # 使用锁确保同时只有一个音频播放
        with self._play_lock:
            try:
                logging.info(f"正在播放语音: {filepath}")

                # 确保文件路径使用正确的编码
                safe_filepath = os.path.abspath(filepath)

                # 检查文件是否存在
                if not os.path.exists(safe_filepath):
                    logging.error(f"音频文件不存在: {safe_filepath}")
                    return

                # 使用多种播放方式，提高兼容性
                success = self._try_play_with_multiple_methods(safe_filepath)

                if success:
                    logging.info("语音播放完成")
                else:
                    logging.error("所有播放方法都失败")

            except Exception as e:
                logging.error(f"播放语音失败: {e}")
                logging.error(f"错误类型: {type(e).__name__}")

    def _try_play_with_multiple_methods(self, filepath: str) -> bool:
        """
        使用pygame作为主要播放器的音频播放方法

        Args:
            filepath (str): 音频文件路径

        Returns:
            bool: 是否播放成功
        """
        # 方法1：使用pygame（主要播放器）
        if not self._init_pygame():
            logging.error("pygame初始化失败，尝试备选方法")
        else:
            try:
                import pygame

                # 使用安全路径
                safe_filepath = self._get_safe_filepath(filepath)

                logging.debug(f"使用pygame播放: {safe_filepath}")

                # 加载并播放音频
                pygame.mixer.music.load(safe_filepath)
                pygame.mixer.music.play()

                # 等待播放完成，使用pygame的高效等待方法
                while pygame.mixer.music.get_busy():
                    pygame.time.wait(100)

                logging.debug("pygame播放成功")
                return True

            except Exception as e:
                logging.warning(f"pygame播放失败: {e}，尝试备选方法")

        # 方法2：备选方案 - winsound（Windows专用）
        if sys.platform.startswith('win'):
            try:
                import winsound

                # 使用安全路径
                safe_filepath = self._get_safe_filepath(filepath)

                logging.debug(f"使用winsound备选播放: {safe_filepath}")
                winsound.PlaySound(safe_filepath, winsound.SND_FILENAME | winsound.SND_NODEFAULT)
                logging.debug("winsound备选播放成功")
                return True
            except ImportError:
                logging.debug("winsound库不可用")
            except Exception as e:
                logging.warning(f"winsound备选播放失败: {e}")

        # 方法3：最后备选 - Windows Media Player静默模式
        if sys.platform.startswith('win'):
            try:
                safe_filepath = self._get_safe_filepath(filepath)

                logging.debug(f"使用Windows Media Player最后备选: {safe_filepath}")
                subprocess.run([
                    'powershell', '-WindowStyle', 'Hidden', '-c',
                    f'(New-Object Media.SoundPlayer "{safe_filepath}").PlaySync()'
                ], check=True, capture_output=True, timeout=10, creationflags=subprocess.CREATE_NO_WINDOW)
                logging.debug("Windows Media Player最后备选成功")
                return True
            except Exception as e:
                logging.warning(f"Windows Media Player最后备选失败: {e}")

        logging.error("所有音频播放方法都失败")
        return False

    def _get_safe_filepath(self, filepath: str) -> str:
        """
        获取安全的文件路径，解决中文路径编码问题

        Args:
            filepath (str): 原始文件路径

        Returns:
            str: 安全的文件路径
        """
        try:
            # 获取绝对路径
            abs_path = os.path.abspath(filepath)

            # 在Windows系统上，尝试获取短路径名（8.3格式）来避免中文编码问题
            if sys.platform.startswith('win'):
                try:
                    import ctypes
                    from ctypes import wintypes

                    # 获取短路径名
                    GetShortPathNameW = ctypes.windll.kernel32.GetShortPathNameW
                    GetShortPathNameW.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
                    GetShortPathNameW.restype = wintypes.DWORD

                    # 分配缓冲区
                    buffer_size = 260  # MAX_PATH
                    buffer = ctypes.create_unicode_buffer(buffer_size)

                    # 调用API获取短路径
                    result = GetShortPathNameW(abs_path, buffer, buffer_size)

                    if result > 0:
                        short_path = buffer.value
                        logging.debug(f"转换路径: {abs_path} → {short_path}")
                        return short_path
                    else:
                        logging.debug(f"无法获取短路径，使用原路径: {abs_path}")
                        return abs_path

                except Exception as e:
                    logging.debug(f"获取短路径失败: {e}，使用原路径")
                    return abs_path
            else:
                # 非Windows系统，直接返回绝对路径
                return abs_path

        except Exception as e:
            logging.warning(f"路径处理失败: {e}，使用原路径")
            return filepath

    def play(self, text_to_speak: str, strategy_type: str = None, platform: str = None):
        """
        播放指定文本的语音（优化缓存版本）

        Args:
            text_to_speak (str): 要播报的文字
            strategy_type (str): 策略类型 ('whitelist', 'keyword', None)
            platform (str): 平台名称 ('麻花', '哈哈', None)
        """
        try:
            if not text_to_speak or not text_to_speak.strip():
                logging.warning("播放文本为空，跳过语音播报")
                return

            # 【优化】根据策略类型选择不同的缓存策略
            if strategy_type == 'whitelist' and platform:
                # 白名单策略：使用平台级别的固定缓存
                filepath = self._get_whitelist_cache_file(platform)
                expected_text = f"{platform}，白名单订单来了"
            else:
                # 关键词策略或其他：使用基于内容的MD5缓存
                filepath = self._generate_filename(text_to_speak)
                expected_text = text_to_speak

            if not filepath:
                logging.error("生成文件路径失败，跳过语音播报")
                return

            # 检查缓存文件是否存在
            if os.path.exists(filepath):
                logging.info(f"使用缓存的语音文件: {filepath}")
                self._play_cached_file(filepath)
            else:
                logging.info(f"缓存文件不存在，需要生成新的语音文件: {expected_text}")
                self._generate_and_play(expected_text, filepath)

        except Exception as e:
            logging.error(f"语音播放过程中发生错误: {e}")
            # 确保任何错误都不会影响主程序运行

    def _get_whitelist_cache_file(self, platform: str) -> str:
        """
        获取白名单策略的固定缓存文件路径

        Args:
            platform (str): 平台名称

        Returns:
            str: 缓存文件路径
        """
        # 为每个平台创建固定的缓存文件名
        safe_platform = platform.replace('/', '_').replace('\\', '_')  # 处理特殊字符
        filename = f"whitelist_{safe_platform}.mp3"
        return os.path.join(self.cache_dir, filename)

    def _play_cached_file(self, filepath: str):
        """播放缓存文件"""
        play_thread = threading.Thread(
            target=self._play_audio_file,
            args=(filepath,),
            daemon=False
        )
        play_thread.start()

    def _generate_and_play(self, text: str, filepath: str):
        """生成语音文件并播放"""
        if self._generate_tts_file(text, filepath):
            self._play_cached_file(filepath)
        else:
            logging.error("语音文件生成失败，无法播放")

    def play_alert(self, alert_type='default'):
        """
        【v1.3 最终版】播放特定类型的提醒音频

        Args:
            alert_type (str): 提醒类型，'default' 或 'whitelist'
        """
        try:
            if alert_type == 'whitelist':
                # 白名单策略专用提醒
                fixed_filename = "whitelist_alert.mp3"
                filepath = os.path.join(self.cache_dir, fixed_filename)

                # 检查固定文件是否存在
                if os.path.exists(filepath):
                    logging.info(f"使用缓存的白名单提醒音频: {filepath}")
                    # 在后台线程中播放
                    threading.Thread(
                        target=self._play_audio_file,
                        args=(filepath,),
                        daemon=True
                    ).start()
                else:
                    logging.info(f"白名单提醒音频不存在，正在生成: {WHITELIST_ALERT_TEXT}")

                    # 生成白名单专用提醒音频
                    if self._generate_tts_file(WHITELIST_ALERT_TEXT, filepath):
                        # 生成成功后播放
                        threading.Thread(
                            target=self._play_audio_file,
                            args=(filepath,),
                            daemon=True
                        ).start()
                    else:
                        logging.error("白名单提醒音频生成失败")
            else:
                # 默认提醒（保持原有逻辑兼容性）
                logging.warning("play_alert调用了默认类型，建议使用具体的alert_type")

        except Exception as e:
            logging.error(f"播放提醒音频时发生错误: {e}")
    
    def clear_cache(self):
        """清空语音缓存"""
        try:
            if os.path.exists(self.cache_dir):
                for filename in os.listdir(self.cache_dir):
                    if filename.endswith('.mp3'):
                        filepath = os.path.join(self.cache_dir, filename)
                        os.remove(filepath)
                        logging.info(f"删除缓存文件: {filepath}")
                logging.info("语音缓存清空完成")
            else:
                logging.info("缓存目录不存在，无需清空")
                
        except Exception as e:
            logging.error(f"清空语音缓存失败: {e}")
    
    def get_cache_info(self):
        """获取详细的缓存信息（优化版本）"""
        try:
            if not os.path.exists(self.cache_dir):
                return {
                    "total_files": 0,
                    "total_size": 0,
                    "total_size_mb": 0,
                    "whitelist_files": 0,
                    "keyword_files": 0,
                    "cache_dir": self.cache_dir
                }

            total_files = 0
            total_size = 0
            whitelist_files = 0
            keyword_files = 0

            for filename in os.listdir(self.cache_dir):
                if filename.endswith('.mp3'):
                    filepath = os.path.join(self.cache_dir, filename)
                    total_files += 1
                    total_size += os.path.getsize(filepath)

                    # 分类统计
                    if filename.startswith('whitelist_'):
                        whitelist_files += 1
                    else:
                        keyword_files += 1

            return {
                "total_files": total_files,
                "total_size": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "whitelist_files": whitelist_files,
                "keyword_files": keyword_files,
                "cache_efficiency": f"{whitelist_files + keyword_files}/{total_files}",
                "cache_dir": self.cache_dir
            }

        except Exception as e:
            logging.error(f"获取缓存信息失败: {e}")
            return {
                "total_files": 0,
                "total_size": 0,
                "total_size_mb": 0,
                "whitelist_files": 0,
                "keyword_files": 0,
                "cache_dir": self.cache_dir
            }

    def cleanup(self):
        """清理pygame资源"""
        try:
            if self._pygame_initialized:
                import pygame
                pygame.mixer.quit()
                self._pygame_initialized = False
                logging.debug("pygame资源已清理")
        except Exception as e:
            logging.warning(f"pygame资源清理失败: {e}")

    def __del__(self):
        """析构函数，确保资源清理"""
        self.cleanup()
