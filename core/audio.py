# core/audio.py
import logging
import threading
import pyttsx3

class TTSPlayer:
    """
    文本转语音播放器类 - V4.0.1 "最终修复" pyttsx3 核心
    在保持外部架构不变的前提下，将内部实现替换为完全离线的pyttsx3。
    """

    def __init__(self):
        """
        初始化TTS播放器。
        只初始化一个用于保证顺序播放的线程锁。
        """
        # 这个锁，是您现有代码中保证顺序播放的核心，我们必须保留它。
        self._play_lock = threading.Lock()
        logging.info("【V4.0.1】TTSPlayer初始化完成，已准备好使用pyttsx3离线引擎。")

    def _execute_tts_in_thread(self, text: str):
        """
        这是一个私有方法，它会在一个独立的线程中被执行。
        负责初始化引擎、播报语音、然后销毁引擎。
        """
        engine = None
        try:
            # 【核心】每次播报，都创建一个全新的、干净的引擎实例
            logging.info(f"【后台线程】为任务 '{text}' 创建新pyttsx3引擎...")
            engine = pyttsx3.init()

            # --- 在新引擎上应用所有语音配置 ---
            voices = engine.getProperty('voices')
            # 尝试寻找中文语音包
            chinese_voice = next((v.id for v in voices if 'chinese' in v.name.lower() or 'zh' in v.lang.lower()), None)
            if chinese_voice:
                engine.setProperty('voice', chinese_voice)

            engine.setProperty('rate', 180)  # 设置语速
            engine.setProperty('volume', 1.0) # 设置音量

            logging.info(f"【后台线程】引擎创建完毕，开始播报: '{text}'")
            engine.say(text)
            engine.runAndWait() # 这个阻塞操作，安全地在后台线程中执行

            logging.info(f"【后台线程】播报任务 '{text}' 完成。")

        except Exception as e:
            logging.error(f"【后台线程】pyttsx3播报时发生未知异常: {e}", exc_info=True)
        finally:
            # 确保引擎资源被释放
            if engine is not None:
                del engine

    def play(self, text_to_speak: str, **kwargs):
        """
        播放指定文本的语音。
        完全遵循您现有的、经过验证的“为每次播放创建新线程”的模式。
        """
        if not text_to_speak or not text_to_speak.strip():
            logging.warning("播放文本为空，跳过语音播报。")
            return

        # 使用您原有的、带锁的、在新线程中播放的模式
        def target_with_lock():
            with self._play_lock:
                self._execute_tts_in_thread(text_to_speak)

        play_thread = threading.Thread(target=target_with_lock, daemon=False)
        play_thread.start()
        logging.info(f"【UI线程】已为任务 '{text_to_speak}' 创建并启动了独立的播报线程。")

    def cleanup(self):
        pass

    def __del__(self):
        self.cleanup()