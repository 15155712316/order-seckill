# 智能抢单决策助手 - 主程序文件
# 项目初始化完成，准备开始开发

# 测试导入所有依赖库
def test_imports():
    try:
        import PyQt6
        print("✅ PyQt6 导入成功")

        import aiohttp
        print("✅ aiohttp 导入成功")

        import playsound
        print("✅ playsound 导入成功")

        print("🎉 所有依赖库安装成功！")
        return True
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        return False

if __name__ == "__main__":
    print("智能抢单决策助手启动中...")
    test_imports()
