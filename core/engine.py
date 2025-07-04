#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
规则引擎模块 - 负责加载和处理抢单决策规则
"""

import json
import logging


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
            logging.info(f"成功加载 {len(self.rules)} 条规则")

        except FileNotFoundError:
            logging.error(f"错误：找不到规则文件 {self.filepath}")
            self.rules = []
        except json.JSONDecodeError as e:
            logging.error(f"错误：规则文件JSON格式错误 - {e}")
            self.rules = []
        except Exception as e:
            logging.error(f"错误：加载规则文件时发生未知错误 - {e}")
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
                - seat_count: 票数（新增字段）

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
            order_seat_count = order.get('seat_count', 1)  # 获取票数字段，默认为1

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
                # 使用更灵活的匹配逻辑，支持部分匹配
                hall_matched = False
                for hall_type in hall_set:
                    hall_type_lower = hall_type.lower().strip()
                    # 检查是否包含关键词（如"IMAX"包含在"IMAX厅"中）
                    if hall_type_lower in order_hall_type or order_hall_type in hall_type_lower:
                        hall_matched = True
                        break

                if not hall_matched:
                    continue  # 影厅类型不匹配，跳到下一条规则

            elif hall_mode == 'EXCLUDE':
                # EXCLUDE模式：订单的影厅类型不能在规则的hall_set中
                hall_matched = False
                for hall_type in hall_set:
                    hall_type_lower = hall_type.lower().strip()
                    # 检查是否包含关键词
                    if hall_type_lower in order_hall_type or order_hall_type in hall_type_lower:
                        hall_matched = True
                        break

                if hall_matched:
                    continue  # 影厅类型在排除列表中，跳到下一条规则

            # ALL模式默认通过，无需检查

            # 4. 利润计算与决策
            # 如果执行到这里，说明所有匹配条件都满足
            hall_cost = hall_logic.get('cost', 0)

            # 修正后的利润计算公式：考虑票数
            single_ticket_profit = order_bidding_price - hall_cost
            total_profit = single_ticket_profit * order_seat_count
            min_profit_threshold = profit_logic.get('min_profit_threshold', 0)

            # 判断总利润是否达标
            if total_profit >= min_profit_threshold:
                # 利润达标，返回匹配结果
                return {
                    'total_profit': total_profit,
                    'seat_count': order_seat_count,
                    'rule_name': rule.get('rule_name', '未命名规则'),
                    'order_details': order.copy()  # 返回订单详情的副本
                }

        # 如果循环正常结束，说明没有任何规则匹配成功
        return None
