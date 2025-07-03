# 智能抢单决策助手 - 主程序文件
# 项目初始化完成，准备开始开发

import json


class RuleEngine:
    """规则引擎类 - 负责加载和处理抢单决策规则"""

    def __init__(self, rules_filepath):
        """
        初始化规则引擎

        Args:
            rules_filepath (str): rules.json文件的路径
        """
        self.filepath = rules_filepath
        self.rules = []  # 存储加载后的所有规则
        self._load_rules()  # 加载和预处理规则

    def _load_rules(self):
        """
        内部方法：加载并预处理规则文件
        """
        try:
            # 尝试打开并读取JSON文件
            with open(self.filepath, 'r', encoding='utf-8') as file:
                rules_data = json.load(file)

            # 遍历每条规则进行预处理
            processed_rules = []
            for rule in rules_data:
                # 创建规则的副本以避免修改原始数据
                processed_rule = rule.copy()

                # 预处理：将hall_list转换为hall_set以提高查找性能
                if 'hall_logic' in processed_rule and 'hall_list' in processed_rule['hall_logic']:
                    hall_list = processed_rule['hall_logic']['hall_list']
                    processed_rule['hall_logic']['hall_set'] = set(hall_list)

                processed_rules.append(processed_rule)

            # 将预处理后的规则赋值给实例变量
            self.rules = processed_rules
            print(f"✅ 成功加载 {len(self.rules)} 条规则")

        except FileNotFoundError:
            print(f"❌ 错误：找不到规则文件 {self.filepath}")
            self.rules = []
        except json.JSONDecodeError as e:
            print(f"❌ 错误：规则文件JSON格式错误 - {e}")
            self.rules = []
        except Exception as e:
            print(f"❌ 错误：加载规则文件时发生未知错误 - {e}")
            self.rules = []

    def check_order(self, order):
        """
        检查订单是否符合规则条件

        Args:
            order (dict): 代表订单的字典

        Returns:
            待实现 - 后续会填充具体逻辑
        """
        pass


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

def test_rule_engine():
    """测试RuleEngine类的功能"""
    print("\n🔧 测试RuleEngine类...")

    # 创建RuleEngine实例
    engine = RuleEngine("rules.json")

    # 显示加载的规则信息
    print(f"📋 加载的规则数量: {len(engine.rules)}")

    # 显示每条规则的基本信息
    for i, rule in enumerate(engine.rules, 1):
        rule_name = rule.get('rule_name', '未命名规则')
        enabled = rule.get('enabled', False)
        status = "✅ 启用" if enabled else "❌ 禁用"
        print(f"   规则 {i}: {rule_name} - {status}")

        # 显示hall_set转换结果
        if 'hall_logic' in rule and 'hall_set' in rule['hall_logic']:
            hall_set = rule['hall_logic']['hall_set']
            print(f"      影厅类型集合: {hall_set}")


if __name__ == "__main__":
    print("智能抢单决策助手启动中...")

    # 测试依赖库导入
    if test_imports():
        # 测试RuleEngine类
        test_rule_engine()
