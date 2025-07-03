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
            order (dict): 代表订单的字典，包含以下字段：
                - city: 城市名称
                - cinema_name: 影院名称
                - hall_type: 影厅类型
                - bidding_price: 竞价价格

        Returns:
            dict: 如果匹配成功且利润达标，返回包含利润和规则信息的字典
            None: 如果没有匹配的规则或利润不达标
        """
        # 遍历所有规则
        for rule in self.rules:
            # 前置检查：跳过被禁用的规则
            if not rule.get('enabled', True):
                continue

            # 数据准备与清洗：安全获取订单字段并转换为小写
            order_city = order.get('city', '').lower().strip()
            order_cinema_name = order.get('cinema_name', '').lower().strip()
            order_hall_type = order.get('hall_type', '').lower().strip()
            order_bidding_price = order.get('bidding_price', 0)

            # 获取规则条件
            match_conditions = rule.get('match_conditions', {})
            hall_logic = rule.get('hall_logic', {})
            profit_logic = rule.get('profit_logic', {})

            # 执行逐级匹配（"尽早失败"原则）

            # 1. 城市匹配
            rule_city = match_conditions.get('city', '').lower().strip()
            if rule_city and rule_city != order_city:
                continue  # 城市不匹配，跳到下一条规则

            # 2. 影院关键词匹配
            cinema_keywords = match_conditions.get('cinema_keywords', [])
            if cinema_keywords:
                # 检查所有关键词是否都出现在影院名称中
                keywords_matched = True
                for keyword in cinema_keywords:
                    keyword_lower = keyword.lower().strip()
                    if keyword_lower not in order_cinema_name:
                        keywords_matched = False
                        break

                if not keywords_matched:
                    continue  # 关键词不匹配，跳到下一条规则

            # 3. 影厅逻辑匹配
            hall_mode = hall_logic.get('mode', 'ALL').upper()
            hall_set = hall_logic.get('hall_set', set())

            if hall_mode == 'INCLUDE':
                # INCLUDE模式：订单的影厅类型必须在规则的hall_set中
                if order_hall_type not in {h.lower().strip() for h in hall_set}:
                    continue  # 影厅类型不在包含列表中，跳到下一条规则

            elif hall_mode == 'EXCLUDE':
                # EXCLUDE模式：订单的影厅类型不能在规则的hall_set中
                if order_hall_type in {h.lower().strip() for h in hall_set}:
                    continue  # 影厅类型在排除列表中，跳到下一条规则

            # ALL模式默认通过，无需检查

            # 4. 利润计算与决策
            # 如果执行到这里，说明所有匹配条件都满足
            hall_cost = hall_logic.get('cost', 0)
            profit = order_bidding_price - hall_cost
            min_profit_threshold = profit_logic.get('min_profit_threshold', 0)

            # 判断利润是否达标
            if profit >= min_profit_threshold:
                # 利润达标，返回匹配结果
                return {
                    'profit': profit,
                    'rule_name': rule.get('rule_name', '未命名规则'),
                    'rule_id': rule.get('rule_id', ''),
                    'hall_cost': hall_cost,
                    'min_profit_threshold': min_profit_threshold,
                    'order_details': order.copy()  # 返回订单详情的副本
                }

        # 如果循环正常结束，说明没有任何规则匹配成功
        return None


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


def test_check_order():
    """测试check_order方法的功能"""
    print("\n🧪 测试check_order方法...")

    # 创建RuleEngine实例
    engine = RuleEngine("rules.json")

    # 测试用例1：匹配成功的订单
    test_order_1 = {
        'city': '北京',
        'cinema_name': '万达影城CBD店',
        'hall_type': 'IMAX',
        'bidding_price': 60.0
    }

    print(f"\n📝 测试订单1: {test_order_1}")
    result_1 = engine.check_order(test_order_1)
    if result_1:
        print(f"✅ 匹配成功！")
        print(f"   规则名称: {result_1['rule_name']}")
        print(f"   计算利润: {result_1['profit']:.2f}元")
        print(f"   影厅成本: {result_1['hall_cost']:.2f}元")
        print(f"   最低利润要求: {result_1['min_profit_threshold']:.2f}元")
    else:
        print("❌ 未匹配到合适的规则")

    # 测试用例2：利润不达标的订单
    test_order_2 = {
        'city': '北京',
        'cinema_name': '万达影城CBD店',
        'hall_type': 'IMAX',
        'bidding_price': 55.0  # 利润只有5元，不达标
    }

    print(f"\n📝 测试订单2: {test_order_2}")
    result_2 = engine.check_order(test_order_2)
    if result_2:
        print(f"✅ 匹配成功！")
        print(f"   规则名称: {result_2['rule_name']}")
        print(f"   计算利润: {result_2['profit']:.2f}元")
    else:
        print("❌ 未匹配到合适的规则（可能是利润不达标）")

    # 测试用例3：城市不匹配的订单
    test_order_3 = {
        'city': '上海',
        'cinema_name': '万达影城CBD店',
        'hall_type': 'IMAX',
        'bidding_price': 60.0
    }

    print(f"\n📝 测试订单3: {test_order_3}")
    result_3 = engine.check_order(test_order_3)
    if result_3:
        print(f"✅ 匹配成功！")
        print(f"   规则名称: {result_3['rule_name']}")
        print(f"   计算利润: {result_3['profit']:.2f}元")
    else:
        print("❌ 未匹配到合适的规则（城市不匹配）")


if __name__ == "__main__":
    print("智能抢单决策助手启动中...")

    # 测试依赖库导入
    if test_imports():
        # 测试RuleEngine类
        test_rule_engine()

        # 测试check_order方法
        test_check_order()
