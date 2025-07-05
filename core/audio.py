#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
音频处理模块 - 负责语音生成和播放功能
"""

import os
import logging
import hashlib
import threading
from gtts import gTTS
from playsound import playsound
from config import TTS_CACHE_DIR


class TTSPlayer:
    """文本转语音播放器类 - 带缓存功能"""
    
    def __init__(self):
        """初始化TTS播放器"""
        self.cache_dir = TTS_CACHE_DIR
        self._ensure_cache_dir()
        logging.info(f"TTSPlayer初始化完成，缓存目录: {self.cache_dir}")
    
    def _ensure_cache_dir(self):
        """确保缓存目录存在"""
        try:
            if not os.path.exists(self.cache_dir):
                os.makedirs(self.cache_dir)
                logging.info(f"创建语音缓存目录: {self.cache_dir}")
        except Exception as e:
            logging.error(f"创建缓存目录失败: {e}")
    
    def _generate_filename(self, text: str) -> str:
        """
        根据文本内容生成唯一的文件名
        
        Args:
            text (str): 要转换的文本
            
        Returns:
            str: 生成的文件名（包含完整路径）
        """
        try:
            # 使用MD5生成唯一文件名
            text_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
            filename = f"{text_hash}.mp3"
            filepath = os.path.join(self.cache_dir, filename)
            return filepath
        except Exception as e:
            logging.error(f"生成文件名失败: {e}")
            return None
    
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
        播放音频文件（在后台线程中）
        
        Args:
            filepath (str): 音频文件路径
        """
        try:
            logging.info(f"正在播放语音: {filepath}")
            playsound(filepath, block=False)
            logging.info("语音播放完成")
            
        except Exception as e:
            logging.error(f"播放语音失败: {e}")
    
    def play(self, text_to_speak: str):
        """
        播放指定文本的语音（核心方法）
        
        Args:
            text_to_speak (str): 要播报的文字
        """
        try:
            if not text_to_speak or not text_to_speak.strip():
                logging.warning("播放文本为空，跳过语音播报")
                return
            
            # 生成文件路径
            filepath = self._generate_filename(text_to_speak)
            if not filepath:
                logging.error("生成文件路径失败，跳过语音播报")
                return
            
            # 检查缓存文件是否存在
            if os.path.exists(filepath):
                logging.info(f"使用缓存的语音文件: {filepath}")
                # 在后台线程中播放，避免阻塞主程序
                threading.Thread(
                    target=self._play_audio_file, 
                    args=(filepath,), 
                    daemon=True
                ).start()
            else:
                logging.info(f"缓存文件不存在，需要生成新的语音文件")
                
                # 生成新的语音文件
                if self._generate_tts_file(text_to_speak, filepath):
                    # 生成成功后播放
                    threading.Thread(
                        target=self._play_audio_file, 
                        args=(filepath,), 
                        daemon=True
                    ).start()
                else:
                    logging.error("语音文件生成失败，无法播放")
                    
        except Exception as e:
            logging.error(f"语音播放过程中发生错误: {e}")
            # 确保任何错误都不会影响主程序运行
    
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
        """获取缓存信息"""
        try:
            if not os.path.exists(self.cache_dir):
                return {"file_count": 0, "total_size": 0}
            
            file_count = 0
            total_size = 0
            
            for filename in os.listdir(self.cache_dir):
                if filename.endswith('.mp3'):
                    filepath = os.path.join(self.cache_dir, filename)
                    file_count += 1
                    total_size += os.path.getsize(filepath)
            
            return {
                "file_count": file_count,
                "total_size": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2)
            }
            
        except Exception as e:
            logging.error(f"获取缓存信息失败: {e}")
            return {"file_count": 0, "total_size": 0}
