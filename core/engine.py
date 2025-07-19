#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
【中央仓储架构】规则引擎模块 - 状态广播系统
负责加载和处理抢单决策规则，支持关键词策略和白名单策略两种模式
实现单向数据流和状态驱动的UI刷新机制
"""

import json
import logging
import uuid
from typing import Dict, List, Any, Optional, Set
from PyQt6.QtCore import QObject, pyqtSignal
from .database import DatabaseManager


class WhitelistPolicy:
    """白名单策略类 - 处理基于影院白名单的订单匹配"""

    def __init__(self, rule_data: Dict, cinema_set: Set[str]):
        """
        初始化白名单策略

        Args:
            rule_data (Dict): 规则数据
            cinema_set (Set[str]): 影院名称集合
        """
        self.rule_data = rule_data
        self.cinema_set = cinema_set
        self.filters = rule_data.get('filter_logic', {})

    def check(self, order: Dict) -> Optional[Dict]:
        """
        【v2.4 时空策略版】白名单策略的核心匹配逻辑

        Args:
            order (Dict): 订单数据

        Returns:
            Optional[Dict]: 匹配成功返回结果字典，失败返回None
        """
        # 第一关：影片检查
        match_conditions = self.rule_data.get('match_conditions', {})
        target_movie_keywords = match_conditions.get('target_movie_keywords', [])

        if target_movie_keywords:  # 如果设置了影片过滤
            order_movie_name = order.get('movie_name', '')
            if not order_movie_name:
                return None  # 没有影片名称信息，不匹配

            # 执行"OR"逻辑匹配：任何一个关键词被包含即可
            movie_matched = False
            order_movie_lower = order_movie_name.lower().strip()

            for keyword in target_movie_keywords:
                keyword_lower = keyword.lower().strip()
                if keyword_lower in order_movie_lower:
                    movie_matched = True
                    break

            if not movie_matched:
                return None  # 影片不匹配，不符合条件

        # 第二关：检查订单的影院名称是否在该策略的白名单集合中
        order_cinema_name = order.get('cinema_name', '').lower().strip()
        cinema_matched = False

        for whitelist_cinema in self.cinema_set:
            whitelist_cinema_lower = whitelist_cinema.lower().strip()
            if (whitelist_cinema_lower in order_cinema_name or
                order_cinema_name in whitelist_cinema_lower):
                cinema_matched = True
                break

        if not cinema_matched:
            return None  # 影院不在白名单中

        # 第三关：从该策略的高级筛选规则中获取用户设置
        ticket_counts = self.filters.get('ticket_counts', [1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        price_range = self.filters.get('price_range', {'min': 0, 'max': 999})
        min_bid_price = self.filters.get('min_bid_price', 0)

        # c. 逐一进行校验
        order_seat_count = order.get('seat_count', 1)
        order_original_price = order.get('original_price', 0)
        order_bidding_price = order.get('bidding_price', 0)

        # 检查票数
        if order_seat_count not in ticket_counts:
            return None

        # 检查原价范围
        if not (price_range['min'] <= order_original_price <= price_range['max']):
            return None

        # 检查最低竞标价
        if order_bidding_price < min_bid_price:
            return None

        # d. 所有条件都满足，计算利润并返回匹配结果
        hall_logic = self.rule_data.get('hall_logic', {})
        profit_logic = self.rule_data.get('profit_logic', {})

        hall_cost = hall_logic.get('cost', 0)
        single_ticket_profit = order_bidding_price - hall_cost
        total_profit = single_ticket_profit * order_seat_count
        min_profit_threshold = profit_logic.get('min_profit_threshold', 0)

        # 判断总利润是否达标
        if total_profit >= min_profit_threshold:
            return {
                'total_profit': total_profit,
                'seat_count': order_seat_count,
                'rule_name': self.rule_data.get('rule_name', '未命名规则'),
                'order_details': order.copy(),
                'strategy_type': 'whitelist'  # 标识策略类型
            }

        return None


class RuleEngine(QObject):
    """【中央仓储架构】规则引擎类 - 状态广播系统的核心

    作为应用程序的"真理来源"，负责：
    1. 从数据库加载和管理所有策略数据
    2. 在数据状态变更时向整个系统广播
    3. 提供统一的策略操作接口
    """

    # 【核心信号】策略数据更新时发射，驱动UI刷新
    policies_updated = pyqtSignal()

    def __init__(self, rules_filepath: str = None, db_manager: DatabaseManager = None):
        """
        初始化规则引擎

        Args:
            rules_filepath (str): 已废弃，保留用于兼容性
            db_manager (DatabaseManager): 数据库管理器实例
        """
        super().__init__()  # 初始化QObject

        self.filepath = rules_filepath  # 保留用于兼容性，实际不再使用
        self.rules = []  # 存储加载后的所有规则
        self.db_manager = db_manager or DatabaseManager()  # 数据库管理器
        self.whitelist_cache = {}  # 白名单策略的影院缓存 {policy_id: set}
        self._load_policies()  # 从数据库加载策略

    def _load_policies(self):
        """
        【中央仓储架构】从数据库加载并预处理策略数据
        """
        try:
            # 从数据库加载所有策略
            policies_data = self.db_manager.load_all_policies()

            # 遍历每条策略进行预处理
            processed_policies = []
            for policy in policies_data:
                # 创建策略的副本以避免修改原始数据
                processed_policy = policy.copy()

                # 预处理：将hall_list转换为hall_set以提高查找性能
                if 'hall_logic' in processed_policy and 'hall_list' in processed_policy['hall_logic']:
                    hall_list = processed_policy['hall_logic']['hall_list']
                    processed_policy['hall_logic']['hall_set'] = set(hall_list)

                # 如果是白名单策略，从数据库加载影院名单
                match_conditions = processed_policy.get('match_conditions', {})
                if match_conditions.get('match_mode') == 'whitelist':
                    policy_id = processed_policy.get('rule_id')
                    if policy_id:
                        cinema_set = self.db_manager.load_cinemas_for_policy(policy_id)
                        self.whitelist_cache[policy_id] = cinema_set
                        logging.info(f"为白名单策略 {policy_id} 加载了 {len(cinema_set)} 个影院")

                processed_policies.append(processed_policy)

            # 将预处理后的策略赋值给实例变量
            self.rules = processed_policies
            logging.info(f"从数据库成功加载 {len(self.rules)} 条策略")

            # 发射策略更新信号
            self.policies_updated.emit()

        except Exception as e:
            logging.error(f"错误：从数据库加载策略时发生错误 - {e}")
            self.rules = []

    def check_order(self, order, platform_name: str = None):
        """
        检查订单是否符合规则条件 - 增强版，包含调试记录功能

        Args:
            order (dict): 代表订单的字典
            platform_name (str): 平台名称，用于调试记录

        Returns:
            dict: 如果匹配成功且利润达标，返回包含利润和规则信息的字典
            None: 如果没有匹配的规则或利润不达标
        """
        result = self._check_order_core(order)
        
        # 如果匹配成功，保存调试记录
        if result and platform_name:
            self._save_match_debug_record(order, result, platform_name)
        
        return result

    def _check_order_core(self, order):
        """
        核心订单检查逻辑（原check_order方法）

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
            # 【安全机制】第一道关卡：检查策略是否被启用
            if not rule.get('enabled', False):
                continue  # 如果未启用，则立即跳过，检查下一个策略

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

            # 2. 影院匹配（支持关键词策略和白名单策略）
            match_mode = match_conditions.get('match_mode', 'keywords')

            if match_mode == 'whitelist':
                # 白名单策略：使用WhitelistPolicy类处理
                policy_id = rule.get('rule_id')
                if policy_id and policy_id in self.whitelist_cache:
                    whitelist_cinemas = self.whitelist_cache[policy_id]
                    whitelist_policy = WhitelistPolicy(rule, whitelist_cinemas)
                    result = whitelist_policy.check(order)
                    if result:
                        # 为白名单策略添加额外的调试信息
                        result['rule_id'] = rule.get('rule_id')
                        result['match_conditions'] = match_conditions
                        result['hall_logic'] = hall_logic
                        result['profit_logic'] = profit_logic
                        return result  # 白名单策略匹配成功，直接返回结果
                    else:
                        continue  # 白名单策略不匹配，跳到下一条规则
                else:
                    continue  # 白名单策略但没有加载到影院数据，跳过
            else:
                # 关键词策略：首先进行周几过滤检查
                filter_logic = rule.get('filter_logic', {})
                allowed_weekdays = filter_logic.get('allowed_weekdays', [])

                # 如果设置了周几过滤且不是全选（7天）
                if allowed_weekdays and len(allowed_weekdays) < 7:
                    # 获取订单的放映时间
                    show_timestamp = order.get('show_timestamp')
                    if not show_timestamp:
                        continue  # 没有放映时间信息，跳过此订单

                    try:
                        from datetime import datetime
                        # 解析时间字符串并获取周几（0=周一，6=周日）
                        show_datetime = datetime.strptime(show_timestamp, "%Y-%m-%d %H:%M:%S")
                        weekday = show_datetime.weekday()

                        if weekday not in allowed_weekdays:
                            continue  # 周几不匹配，跳到下一条规则
                    except ValueError as e:
                        logging.error(f"解析订单放映时间失败: {show_timestamp}, 错误: {e}")
                        continue  # 时间解析失败，跳过此订单

                # 检查所有关键词是否都出现在影院名称中
                cinema_keywords = match_conditions.get('cinema_keywords', [])
                if cinema_keywords:
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
                # 利润达标，返回匹配结果（包含详细调试信息）
                return {
                    'total_profit': total_profit,
                    'seat_count': order_seat_count,
                    'rule_name': rule.get('rule_name', '未命名规则'),
                    'rule_id': rule.get('rule_id'),
                    'order_details': order.copy(),  # 返回订单详情的副本
                    'strategy_type': 'keyword',  # 标识策略类型
                    # 【调试信息】详细匹配过程
                    'match_conditions': match_conditions,
                    'hall_logic': hall_logic,
                    'profit_logic': profit_logic,
                    'calculation_details': {
                        'hall_cost': hall_cost,
                        'single_ticket_profit': single_ticket_profit,
                        'min_profit_threshold': min_profit_threshold
                    }
                }

        # 如果循环正常结束，说明没有任何规则匹配成功
        return None

    def import_whitelist_cinemas(self, policy_id: str, cinema_names: Set[str]) -> bool:
        """
        导入白名单影院数据

        Args:
            policy_id (str): 策略ID
            cinema_names (Set[str]): 影院名称集合

        Returns:
            bool: 导入是否成功
        """
        try:
            # 先清空旧数据
            self.db_manager.clear_cinemas_for_policy(policy_id)

            # 添加新数据
            added_count = self.db_manager.add_cinemas_to_whitelist(policy_id, cinema_names)

            # 更新缓存
            self.whitelist_cache[policy_id] = cinema_names.copy()

            logging.info(f"成功导入白名单策略 {policy_id} 的 {added_count} 个影院")
            return True

        except Exception as e:
            logging.error(f"导入白名单影院失败: {e}")
            return False

    def get_whitelist_cinema_count(self, policy_id: str) -> int:
        """
        获取白名单策略的影院数量

        Args:
            policy_id (str): 策略ID

        Returns:
            int: 影院数量
        """
        if policy_id in self.whitelist_cache:
            return len(self.whitelist_cache[policy_id])
        return 0

    def reload_whitelist_for_policy(self, policy_id: str):
        """
        重新加载指定策略的白名单数据

        Args:
            policy_id (str): 策略ID
        """
        try:
            cinema_set = self.db_manager.load_cinemas_for_policy(policy_id)
            self.whitelist_cache[policy_id] = cinema_set
            logging.info(f"重新加载白名单策略 {policy_id} 的 {len(cinema_set)} 个影院")
        except Exception as e:
            logging.error(f"重新加载白名单策略失败: {e}")

    # ========================================
    # 【中央仓储架构】策略操作接口
    # ========================================

    def add_new_policy(self, policy: Dict[str, Any]) -> bool:
        """
        【核心方法】添加新策略

        Args:
            policy (Dict[str, Any]): 策略字典

        Returns:
            bool: 是否添加成功
        """
        try:
            # 确保策略有唯一ID
            if 'rule_id' not in policy:
                policy['rule_id'] = str(uuid.uuid4())

            # 设置排序值（添加到末尾）
            policy['policy_order'] = len(self.rules) + 1

            # 保存到数据库
            success = self.db_manager.save_policy(policy)
            if success:
                # 更新内存
                self.rules.append(policy)

                # 如果是白名单策略，初始化缓存
                match_conditions = policy.get('match_conditions', {})
                if match_conditions.get('match_mode') == 'whitelist':
                    policy_id = policy.get('rule_id')
                    if policy_id:
                        self.whitelist_cache[policy_id] = set()

                # 发射更新信号
                self.policies_updated.emit()
                logging.info(f"成功添加新策略: {policy.get('rule_name', '未命名')}")
                return True
            else:
                logging.error("添加策略失败：数据库保存失败")
                return False

        except Exception as e:
            logging.error(f"添加策略失败: {e}")
            return False

    def save_policy_changes(self, policy: Dict[str, Any]) -> bool:
        """
        【核心方法】保存策略修改

        Args:
            policy (Dict[str, Any]): 修改后的策略字典

        Returns:
            bool: 是否保存成功
        """
        try:
            # 保存到数据库
            success = self.db_manager.save_policy(policy)
            if success:
                # 【修复】更强健的内存更新逻辑 - 直接重新加载避免缓存不一致
                logging.info(f"策略保存成功，重新加载所有策略以确保数据一致性")
                self._load_policies()  # 重新从数据库加载所有策略，确保数据一致

                # 发射更新信号
                self.policies_updated.emit()
                logging.info(f"成功保存策略修改: {policy.get('rule_name', '未命名')}")
                return True
            else:
                logging.error("保存策略修改失败：数据库保存失败")
                return False

        except Exception as e:
            logging.error(f"保存策略修改失败: {e}")
            return False

    def delete_policy(self, policy_id: str, index: int) -> bool:
        """
        【核心方法】删除策略

        Args:
            policy_id (str): 策略ID
            index (int): 策略在列表中的索引

        Returns:
            bool: 是否删除成功
        """
        try:
            # 获取要删除的策略信息
            if 0 <= index < len(self.rules):
                policy_to_delete = self.rules[index]
            else:
                logging.error(f"删除策略失败：索引 {index} 超出范围")
                return False

            # 如果是白名单策略，清理关联数据
            match_conditions = policy_to_delete.get('match_conditions', {})
            if match_conditions.get('match_mode') == 'whitelist':
                deleted_count = self.db_manager.clear_cinemas_for_policy(policy_id)
                logging.info(f"清理了策略 {policy_id} 的 {deleted_count} 个关联影院")

                # 清理缓存
                self.whitelist_cache.pop(policy_id, None)

            # 从数据库删除策略
            success = self.db_manager.delete_policy(policy_id)
            if success:
                # 从内存中删除
                del self.rules[index]

                # 发射更新信号
                self.policies_updated.emit()
                logging.info(f"成功删除策略: {policy_to_delete.get('rule_name', '未命名')}")
                return True
            else:
                logging.error("删除策略失败：数据库删除失败")
                return False

        except Exception as e:
            logging.error(f"删除策略失败: {e}")
            return False

    def reload_policies(self) -> bool:
        """
        【辅助方法】重新加载所有策略

        Returns:
            bool: 是否重新加载成功
        """
        try:
            self._load_policies()
            logging.info("策略重新加载完成")
            return True
        except Exception as e:
            logging.error(f"重新加载策略失败: {e}")
            return False

    def _save_match_debug_record(self, order: Dict, match_result: Dict, platform_name: str):
        """
        保存匹配成功的调试记录到数据库
        
        Args:
            order (Dict): 原始订单数据
            match_result (Dict): 匹配结果
            platform_name (str): 平台名称
        """
        try:
            import uuid
            import time
            
            # 生成唯一记录ID
            record_id = f"{platform_name}_{int(time.time() * 1000)}_{str(uuid.uuid4())[:8]}"
            
            # 构建匹配详情
            match_details = {
                'matched_rule_name': match_result.get('rule_name'),
                'strategy_type': match_result.get('strategy_type'),
                'order_data_summary': {
                    'order_id': order.get('order_id'),
                    'city': order.get('city'),
                    'cinema_name': order.get('cinema_name'),
                    'hall_type': order.get('hall_type'),
                    'movie_name': order.get('movie_name'),
                    'bidding_price': order.get('bidding_price'),
                    'seat_count': order.get('seat_count'),
                    'original_price': order.get('original_price'),
                    'show_time': order.get('show_time')
                },
                'match_conditions_used': match_result.get('match_conditions', {}),
                'hall_logic_applied': match_result.get('hall_logic', {}),
                'profit_logic_settings': match_result.get('profit_logic', {}),
                'calculation_breakdown': match_result.get('calculation_details', {}),
                'final_result': {
                    'total_profit': match_result.get('total_profit'),
                    'seat_count': match_result.get('seat_count'),
                    'profit_per_ticket': match_result.get('total_profit', 0) / max(match_result.get('seat_count', 1), 1)
                }
            }
            
            # 利润计算详情
            profit_calculation = {
                'bidding_price': order.get('bidding_price', 0),
                'hall_cost': match_result.get('calculation_details', {}).get('hall_cost', 0),
                'single_ticket_profit': match_result.get('calculation_details', {}).get('single_ticket_profit', 0),
                'seat_count': match_result.get('seat_count', 1),
                'total_profit': match_result.get('total_profit', 0),
                'min_profit_threshold': match_result.get('calculation_details', {}).get('min_profit_threshold', 0),
                'profit_margin': match_result.get('total_profit', 0) - match_result.get('calculation_details', {}).get('min_profit_threshold', 0),
                'calculation_formula': f"({order.get('bidding_price', 0)} - {match_result.get('calculation_details', {}).get('hall_cost', 0)}) × {match_result.get('seat_count', 1)} = {match_result.get('total_profit', 0)}"
            }
            
            # 构建完整的匹配记录数据
            match_record_data = {
                'record_id': record_id,
                'order_id': order.get('order_id', ''),
                'rule_id': match_result.get('rule_id', ''),
                'rule_name': match_result.get('rule_name', ''),
                'rule_type': match_result.get('strategy_type', ''),
                'match_result': 'SUCCESS',
                'platform_name': platform_name,
                'order_data': order,
                'match_details': match_details,
                'profit_calculation': profit_calculation
            }
            
            # 保存到数据库
            success = self.db_manager.save_match_record(match_record_data)
            
            if success:
                logging.debug(f"✅ 保存匹配调试记录成功: {record_id}")
            else:
                logging.warning(f"❌ 保存匹配调试记录失败: {record_id}")
                
        except Exception as e:
            logging.error(f"保存匹配调试记录异常: {e}")
            import traceback
            logging.error(f"异常堆栈: {traceback.format_exc()}")

    def get_debug_statistics(self) -> Dict[str, Any]:
        """
        获取调试统计信息
        
        Returns:
            Dict[str, Any]: 调试统计数据
        """
        try:
            return self.db_manager.get_match_statistics()
        except Exception as e:
            logging.error(f"获取调试统计失败: {e}")
            return {}

    def query_match_records(self, **kwargs) -> List[Dict[str, Any]]:
        """
        查询匹配记录
        
        Args:
            **kwargs: 查询参数（limit, order_id, rule_id, platform_name等）
            
        Returns:
            List[Dict[str, Any]]: 匹配记录列表
        """
        try:
            return self.db_manager.get_match_records(**kwargs)
        except Exception as e:
            logging.error(f"查询匹配记录失败: {e}")
            return []
