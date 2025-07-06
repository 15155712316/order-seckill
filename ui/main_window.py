#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主窗口GUI模块 - 包含Worker类和MainWindow类
"""

import sys
import json
import uuid
import asyncio
import logging
from datetime import datetime
import pandas as pd

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QFormLayout,
    QWidget, QTableWidget, QTableWidgetItem, QTabWidget, QSplitter,
    QListWidget, QPushButton, QLineEdit, QRadioButton, QCheckBox,
    QButtonGroup, QLabel, QMessageBox, QStackedWidget, QFileDialog,
    QComboBox, QSpinBox, QDoubleSpinBox, QGroupBox
)
from PyQt6.QtCore import QObject, QThread, pyqtSignal, Qt
from PyQt6.QtGui import QColor

from core.engine import RuleEngine
from core.platforms.haha_adapter import HahaAdapter
from core.platforms.mahua_adapter import MahuaAdapter
from core.audio import TTSPlayer
from config import RULES_FILE, API_REQUEST_INTERVAL, HAHA_PLATFORM_NAME, MAHUA_PLATFORM_NAME


class Worker(QObject):
    """后台工作线程类 - 负责异步处理订单监控和规则匹配"""

    # 定义自定义信号，用于向主窗口发送抢单机会数据
    new_opportunity = pyqtSignal(dict)
    # 定义状态更新信号，用于向主窗口发送状态信息
    status_update = pyqtSignal(str)
    # 定义轮询周期完成信号，发送成功平台列表和新订单总数
    cycle_finished = pyqtSignal(list, int)

    def __init__(self, engine):
        """初始化Worker，接受规则引擎实例"""
        super().__init__()
        self.engine = engine

    def run(self):
        """后台任务主方法"""
        # 使用传入的规则引擎实例
        engine = self.engine

        async def main_loop():
            """主要的异步循环，从多个平台获取订单数据"""
            logging.info("后台监控线程启动")

            # 实例化多个平台适配器
            adapters = [
                HahaAdapter(HAHA_PLATFORM_NAME),
                MahuaAdapter(MAHUA_PLATFORM_NAME)
            ]

            while True:
                try:
                    # 发射状态更新信号 - 开始获取订单
                    self.status_update.emit("正在获取多平台订单...")

                    # 并发执行所有平台的任务
                    results = await asyncio.gather(
                        *[adapter.fetch_and_process() for adapter in adapters],
                        return_exceptions=True
                    )

                    # 处理结果
                    successful_platforms = []
                    total_new_orders = 0

                    for i, result in enumerate(results):
                        if isinstance(result, Exception):
                            logging.error(f"平台适配器执行出错: {result}")
                            continue

                        if isinstance(result, dict):
                            platform_name = result.get('name', '未知平台')
                            success = result.get('success', False)
                            orders = result.get('orders', [])

                            if success:
                                successful_platforms.append(platform_name)
                                total_new_orders += len(orders)
                                logging.info(f"{platform_name}平台获取成功，新增 {len(orders)} 条订单")

                                # 遍历当前平台的订单并检查规则匹配
                                for order in orders:
                                    # 使用规则引擎检查订单
                                    match_result = engine.check_order(order)

                                    # 如果匹配成功，发射信号
                                    if match_result is not None:
                                        # 创建包含平台信息的opportunity_data
                                        opportunity_data = {
                                            'platform': platform_name,  # 新增平台信息
                                            'timestamp': order.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                                            'show_time': order.get('show_time', '未知'),
                                            'total_profit': match_result['total_profit'],
                                            'seat_count': match_result['seat_count'],
                                            'rule_name': match_result['rule_name'],
                                            'order_details': match_result['order_details']
                                        }

                                        logging.info(f"发现抢单机会: {match_result['rule_name']} - 总利润{match_result['total_profit']:.1f}元 ({match_result['seat_count']}张票)")

                                        # 发射信号到主窗口
                                        self.new_opportunity.emit(opportunity_data)
                            else:
                                logging.warning(f"{platform_name}平台获取失败")
                        else:
                            # 兼容旧版本HahaAdapter返回格式（直接返回订单列表）
                            if isinstance(result, list):
                                platform_name = HAHA_PLATFORM_NAME
                                successful_platforms.append(platform_name)
                                total_new_orders += len(result)
                                logging.info(f"{platform_name}平台获取成功，新增 {len(result)} 条订单")

                                # 遍历当前平台的订单并检查规则匹配
                                for order in result:
                                    # 使用规则引擎检查订单
                                    match_result = engine.check_order(order)

                                    # 如果匹配成功，发射信号
                                    if match_result is not None:
                                        # 创建包含平台信息的opportunity_data
                                        opportunity_data = {
                                            'platform': platform_name,  # 新增平台信息
                                            'timestamp': order.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                                            'show_time': order.get('show_time', '未知'),
                                            'total_profit': match_result['total_profit'],
                                            'seat_count': match_result['seat_count'],
                                            'rule_name': match_result['rule_name'],
                                            'order_details': match_result['order_details']
                                        }

                                        logging.info(f"发现抢单机会: {match_result['rule_name']} - 总利润{match_result['total_profit']:.1f}元 ({match_result['seat_count']}张票)")

                                        # 发射信号到主窗口
                                        self.new_opportunity.emit(opportunity_data)

                    # 发射轮询周期完成信号
                    self.cycle_finished.emit(successful_platforms, total_new_orders)

                    # 控制API调用频率
                    await asyncio.sleep(API_REQUEST_INTERVAL)

                except Exception as e:
                    logging.error(f"后台处理出错: {e}")
                    self.status_update.emit(f"处理出错: {e}，{API_REQUEST_INTERVAL}秒后重试...")
                    await asyncio.sleep(API_REQUEST_INTERVAL)

        # 启动异步循环
        asyncio.run(main_loop())


class MainWindow(QMainWindow):
    """主窗口类 - 智能抢单决策助手的GUI界面"""

    def __init__(self):
        """初始化主窗口"""
        super().__init__()

        # 设置窗口标题
        self.setWindowTitle("智能抢单决策助手 v1.0")

        # 设置窗口初始大小
        self.resize(1200, 800)

        # 创建Tab容器
        self.tab_widget = QTabWidget()
        self.setCentralWidget(self.tab_widget)

        # 创建Tab页面
        self.create_monitoring_tab()
        self.create_editor_tab()

        # 【v1.3 最终Bug修复】初始化数据库管理器（支持白名单策略删除）
        from core.database import DatabaseManager
        self.db_manager = DatabaseManager()

        # 创建规则引擎实例（传入数据库管理器）
        self.engine = RuleEngine(RULES_FILE, self.db_manager)

        # 初始化语音播放器
        self.tts_player = TTSPlayer()

        # 连接信号与槽
        self.connect_signals()

        # 加载规则到编辑器
        self.load_rules_to_editor()

        # 启动后台工作线程
        self.init_worker_thread()

        # 记录应用程序启动
        logging.info("应用程序启动，主窗口已创建")

    def create_monitoring_tab(self):
        """创建第一个Tab页：抢单监控"""
        # 创建状态栏
        self.statusBar().showMessage("系统准备就绪...")

        # 创建监控Tab容器
        self.monitoring_tab = QWidget()

        # 创建表格
        self.table = QTableWidget()

        # 设置表格表头
        self.table.setColumnCount(8)
        headers = ['平台', '触发时间', '利润', '影院名称', '影厅', '场次', '竞标价', '匹配规则']
        self.table.setHorizontalHeaderLabels(headers)

        # 设置表格列宽
        self.table.setColumnWidth(0, 60)   # 平台
        self.table.setColumnWidth(1, 150)  # 触发时间
        self.table.setColumnWidth(2, 80)   # 利润
        self.table.setColumnWidth(3, 200)  # 影院名称
        self.table.setColumnWidth(4, 100)  # 影厅
        self.table.setColumnWidth(5, 120)  # 场次
        self.table.setColumnWidth(6, 80)   # 竞标价
        self.table.setColumnWidth(7, 180)  # 匹配规则

        # 创建布局并添加表格
        monitoring_layout = QVBoxLayout()
        monitoring_layout.addWidget(self.table)
        self.monitoring_tab.setLayout(monitoring_layout)

        # 添加到Tab容器
        self.tab_widget.addTab(self.monitoring_tab, "抢单监控")

    def create_editor_tab(self):
        """创建第二个Tab页：策略编辑"""
        # 创建编辑Tab容器
        self.editor_tab = QWidget()

        # 创建主分割器（左右分割）
        main_splitter = QSplitter(Qt.Orientation.Horizontal)

        # 创建左侧部分
        left_widget = self.create_left_panel()

        # 创建右侧部分
        right_widget = self.create_right_panel()

        # 添加到分割器
        main_splitter.addWidget(left_widget)
        main_splitter.addWidget(right_widget)

        # 设置分割器比例（左侧30%，右侧70%）
        main_splitter.setSizes([360, 840])

        # 设置编辑Tab布局
        editor_layout = QVBoxLayout()
        editor_layout.addWidget(main_splitter)
        self.editor_tab.setLayout(editor_layout)

        # 添加到Tab容器
        self.tab_widget.addTab(self.editor_tab, "策略编辑")

    def create_left_panel(self):
        """创建左侧面板"""
        left_widget = QWidget()
        left_layout = QVBoxLayout()

        # 规则列表
        self.rule_list = QListWidget()
        self.rule_list.setMinimumHeight(400)
        left_layout.addWidget(QLabel("规则列表:"))
        left_layout.addWidget(self.rule_list)

        # 按钮组
        self.btn_add_keyword_rule = QPushButton("+ 关键词策略")
        self.btn_add_whitelist_rule = QPushButton("+ 白名单策略")
        self.btn_delete_rule = QPushButton("删除规则")
        self.btn_save_rules = QPushButton("保存")

        # 设置按钮样式
        for btn in [self.btn_add_keyword_rule, self.btn_add_whitelist_rule,
                   self.btn_delete_rule, self.btn_save_rules]:
            btn.setMinimumHeight(35)

        # 添加策略类型按钮
        strategy_layout = QHBoxLayout()
        strategy_layout.addWidget(self.btn_add_keyword_rule)
        strategy_layout.addWidget(self.btn_add_whitelist_rule)
        left_layout.addLayout(strategy_layout)

        left_layout.addWidget(self.btn_delete_rule)
        left_layout.addWidget(self.btn_save_rules)

        # 连接按钮信号
        self.btn_add_keyword_rule.clicked.connect(self.add_new_rule)  # 暂时使用原有方法
        self.btn_add_whitelist_rule.clicked.connect(self.add_new_rule)  # 暂时使用原有方法
        self.btn_delete_rule.clicked.connect(self.delete_selected_rule)
        self.btn_save_rules.clicked.connect(self.save_current_rule)

        left_widget.setLayout(left_layout)
        return left_widget

    def create_right_panel(self):
        """【v1.3 Bug修复】创建右侧面板 - 支持多策略类型编辑"""
        right_widget = QWidget()
        main_layout = QVBoxLayout()

        # 用户引导标签
        self.guide_label = QLabel("请从左侧选择规则进行编辑，或点击'新增规则'。")
        self.guide_label.setStyleSheet("color: gray; font-style: italic; padding: 20px; text-align: center;")
        self.guide_label.setWordWrap(True)
        main_layout.addWidget(self.guide_label)

        # 创建编辑器堆叠窗口部件
        self.editor_stacked_widget = QStackedWidget()

        # 创建关键词策略编辑卡片（索引0）
        self.keyword_card = self.create_keyword_strategy_card()
        self.editor_stacked_widget.addWidget(self.keyword_card)

        # 创建白名单策略编辑卡片（索引1）
        self.whitelist_card = self.create_whitelist_strategy_card()
        self.editor_stacked_widget.addWidget(self.whitelist_card)

        main_layout.addWidget(self.editor_stacked_widget)

        # 默认隐藏堆叠窗口部件
        self.editor_stacked_widget.hide()

        right_widget.setLayout(main_layout)
        return right_widget

    def create_keyword_strategy_card(self):
        """创建关键词策略编辑卡片"""
        card_widget = QWidget()
        form_container_layout = QFormLayout()

        # 规则名称
        self.edit_rule_name = QLineEdit()
        form_container_layout.addRow("规则名称:", self.edit_rule_name)

        # 城市
        self.edit_city = QLineEdit()
        form_container_layout.addRow("城市:", self.edit_city)

        # 影院关键词
        self.edit_cinema_keywords = QLineEdit()
        self.edit_cinema_keywords.setPlaceholderText("多个关键词用逗号分隔，如：万达,CBD")
        form_container_layout.addRow("影院关键词:", self.edit_cinema_keywords)

        # 影厅逻辑模式
        hall_mode_widget = QWidget()
        hall_mode_layout = QHBoxLayout()

        self.radio_all = QRadioButton("所有")
        self.radio_include = QRadioButton("包含")
        self.radio_exclude = QRadioButton("不包含")

        # 创建按钮组确保单选
        self.hall_mode_group = QButtonGroup()
        self.hall_mode_group.addButton(self.radio_all, 0)
        self.hall_mode_group.addButton(self.radio_include, 1)
        self.hall_mode_group.addButton(self.radio_exclude, 2)

        # 默认选择"包含"
        self.radio_include.setChecked(True)

        hall_mode_layout.addWidget(self.radio_all)
        hall_mode_layout.addWidget(self.radio_include)
        hall_mode_layout.addWidget(self.radio_exclude)
        hall_mode_layout.addStretch()

        hall_mode_widget.setLayout(hall_mode_layout)
        form_container_layout.addRow("影厅逻辑模式:", hall_mode_widget)

        # 影厅列表
        self.edit_hall_list = QLineEdit()
        self.edit_hall_list.setPlaceholderText("多个影厅用逗号分隔，如：IMAX,激光IMAX")
        form_container_layout.addRow("影厅列表:", self.edit_hall_list)

        # 成本价
        self.edit_cost = QLineEdit()
        self.edit_cost.setPlaceholderText("例如：50.0")
        form_container_layout.addRow("成本价:", self.edit_cost)

        # 最低利润
        self.edit_min_profit = QLineEdit()
        self.edit_min_profit.setPlaceholderText("例如：8.0")
        form_container_layout.addRow("最低利润:", self.edit_min_profit)

        # 启用此规则
        self.checkbox_enabled = QCheckBox("启用此规则")
        self.checkbox_enabled.setChecked(True)
        form_container_layout.addRow("", self.checkbox_enabled)

        # 设置卡片布局
        card_widget.setLayout(form_container_layout)
        return card_widget

    def create_whitelist_strategy_card(self):
        """创建白名单策略编辑卡片"""
        card_widget = QWidget()
        form_container_layout = QFormLayout()

        # 白名单策略的表单字段
        self.edit_whitelist_rule_name = QLineEdit()
        form_container_layout.addRow("规则名称:", self.edit_whitelist_rule_name)

        self.edit_whitelist_city = QLineEdit()
        form_container_layout.addRow("城市（可选）:", self.edit_whitelist_city)

        # 白名单管理
        whitelist_label = QLabel("白名单管理：请使用新版UI导入Excel文件")
        whitelist_label.setStyleSheet("color: blue; font-weight: bold;")
        form_container_layout.addRow("", whitelist_label)

        # 启用此规则
        self.checkbox_whitelist_enabled = QCheckBox("启用此规则")
        self.checkbox_whitelist_enabled.setChecked(True)
        form_container_layout.addRow("", self.checkbox_whitelist_enabled)

        # 设置卡片布局
        card_widget.setLayout(form_container_layout)
        return card_widget

    def add_new_rule(self):
        """【v1.3 Bug修复】添加新规则 - 默认使用关键词策略"""
        try:
            # 隐藏引导标签，显示编辑器
            self.guide_label.hide()
            self.editor_stacked_widget.show()

            # 默认切换到关键词策略卡片（索引0）
            self.editor_stacked_widget.setCurrentIndex(0)

            # 清空关键词策略表单，准备输入新规则
            self.edit_rule_name.clear()
            self.edit_city.clear()
            self.edit_cinema_keywords.clear()
            self.edit_hall_list.clear()
            self.edit_cost.clear()
            self.edit_min_profit.clear()

            # 设置默认值
            self.radio_include.setChecked(True)
            self.checkbox_enabled.setChecked(True)

            # 清除列表选择，确保currentItem为None
            self.rule_list.clearSelection()
            self.rule_list.setCurrentItem(None)

            logging.debug("已清空表单，准备输入新规则")
            self.statusBar().showMessage("请填写新规则信息，然后点击'保存'")

        except Exception as e:
            logging.error(f"添加新规则时出错: {e}")

    def delete_selected_rule(self):
        """【v1.3 最终Bug修复】彻底重写删除逻辑 - 基于行号索引的精确删除"""
        try:
            # 1. 获取当前在QListWidget中被选中的行号索引
            current_row = self.rule_list.currentRow()

            # 2. 检查current_row是否有效（是否为-1）
            if current_row == -1:
                self.statusBar().showMessage("请先在左侧列表中选择要删除的规则")
                return

            # 验证索引范围，确保不会越界
            if not (0 <= current_row < len(self.engine.rules)):
                self.statusBar().showMessage("选择的规则索引无效，请重新选择")
                logging.error(f"删除规则时索引无效: {current_row}, 规则总数: {len(self.engine.rules)}")
                return

            # 3. 从self.engine.rules列表中，使用current_row作为索引，获取将要被删除的规则对象
            rule_to_delete = self.engine.rules[current_row]
            rule_name = rule_to_delete.get('rule_name', f"规则{current_row + 1}")

            # 获取规则类型，用于后续数据库清理
            match_conditions = rule_to_delete.get('match_conditions', {})
            match_mode = match_conditions.get('match_mode', 'keywords')

            # 4. 弹出QMessageBox进行二次确认，防止用户误删
            reply = QMessageBox.question(
                self,
                "确认删除",
                f"您确定要删除规则 '{rule_name}' 吗？此操作无法撤销。",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )

            # 如果用户取消删除，直接返回
            if reply != QMessageBox.StandardButton.Yes:
                return

            # 5. 直接使用del self.engine.rules[current_row]从内存中精确地删除该规则对象
            del self.engine.rules[current_row]

            # 6. 如果被删除的规则是白名单类型，则调用数据库管理器清理其在数据库中的关联影院
            if match_mode == 'whitelist':
                policy_id = rule_to_delete.get('rule_id')
                if policy_id:
                    deleted_count = self.db_manager.clear_cinemas_for_policy(policy_id)
                    logging.info(f"已从数据库中删除策略ID为 {policy_id} 的 {deleted_count} 个白名单影院")

            # 7. 调用self.engine.save_rules()将最新的规则列表持久化保存
            success = self.engine.save_rules(self.engine.rules)
            if not success:
                logging.error("保存规则到文件失败")
                self.statusBar().showMessage("删除成功但保存失败，请检查文件权限")
                return

            # 8. 【关键】调用self.load_rules_to_editor()方法，以"推倒重建"的方式，完整地刷新左侧的UI列表
            self.load_rules_to_editor()

            # 9. 将右侧的编辑区恢复到初始的引导界面状态
            self.guide_label.show()
            self.editor_stacked_widget.hide()

            # 成功提示
            logging.info(f"规则 '{rule_name}' 已被成功删除（原索引: {current_row}）")
            self.statusBar().showMessage(f"规则 '{rule_name}' 已删除")

        except Exception as e:
            logging.error(f"删除规则时出错: {e}", exc_info=True)
            self.statusBar().showMessage("删除规则失败，请查看日志")

    def save_current_rule(self):
        """应用并保存当前修改"""
        try:
            # a. 数据获取与校验
            rule_name = self.edit_rule_name.text().strip()
            city = self.edit_city.text().strip()
            cinema_keywords_text = self.edit_cinema_keywords.text().strip()
            hall_list_text = self.edit_hall_list.text().strip()
            cost_text = self.edit_cost.text().strip()
            min_profit_text = self.edit_min_profit.text().strip()

            # 严格的输入校验
            if not rule_name:
                QMessageBox.warning(self, "输入错误", "规则名称不能为空！")
                return

            # 验证数字字段
            try:
                cost = float(cost_text) if cost_text else 0.0
                min_profit = float(min_profit_text) if min_profit_text else 0.0
            except ValueError:
                QMessageBox.warning(self, "输入错误", "成本价和最低利润必须是有效的数字！")
                return

            # 处理关键词列表
            cinema_keywords = [kw.strip() for kw in cinema_keywords_text.split(',') if kw.strip()]

            # 处理影厅列表
            hall_list = [hall.strip() for hall in hall_list_text.split(',') if hall.strip()]

            # 获取影厅模式
            if self.radio_all.isChecked():
                hall_mode = 'ALL'
            elif self.radio_include.isChecked():
                hall_mode = 'INCLUDE'
            else:
                hall_mode = 'EXCLUDE'

            # b. 新增/更新逻辑判断
            current_item = self.rule_list.currentItem()

            if current_item:
                # 更新模式
                old_rule_name = current_item.text()

                # 如果规则名称发生变化，需要检查新名称是否已存在
                if rule_name != old_rule_name:
                    for rule in self.engine.rules:
                        if rule.get('rule_name') == rule_name:
                            QMessageBox.warning(self, "规则名称冲突", f"规则名称 '{rule_name}' 已存在，请使用其他名称！")
                            return

                # 找到并更新规则
                for i, rule in enumerate(self.engine.rules):
                    if rule.get('rule_name') == old_rule_name:
                        # 构建更新后的规则
                        updated_rule = {
                            'rule_id': rule.get('rule_id', str(uuid.uuid4())),
                            'rule_name': rule_name,
                            'enabled': self.checkbox_enabled.isChecked(),
                            'match_conditions': {
                                'city': city,
                                'cinema_keywords': cinema_keywords
                            },
                            'hall_logic': {
                                'mode': hall_mode,
                                'hall_list': hall_list,
                                'cost': cost
                            },
                            'profit_logic': {
                                'min_profit_threshold': min_profit
                            }
                        }
                        self.engine.rules[i] = updated_rule
                        break

                logging.debug(f"已更新规则: {rule_name}")

            else:
                # 新增模式
                # 执行规则名唯一性校验
                for rule in self.engine.rules:
                    if rule.get('rule_name') == rule_name:
                        QMessageBox.warning(self, "规则名称冲突", f"规则名称 '{rule_name}' 已存在，请使用其他名称！")
                        return

                # 创建新规则
                new_rule = {
                    'rule_id': str(uuid.uuid4()),
                    'rule_name': rule_name,
                    'enabled': self.checkbox_enabled.isChecked(),
                    'match_conditions': {
                        'city': city,
                        'cinema_keywords': cinema_keywords
                    },
                    'hall_logic': {
                        'mode': hall_mode,
                        'hall_list': hall_list,
                        'cost': cost
                    },
                    'profit_logic': {
                        'min_profit_threshold': min_profit
                    }
                }

                self.engine.rules.append(new_rule)
                logging.debug(f"已新增规则: {rule_name}")

            # 重新处理hall_set（为规则引擎预处理）
            for rule in self.engine.rules:
                if 'hall_logic' in rule and 'hall_list' in rule['hall_logic']:
                    hall_list = rule['hall_logic']['hall_list']
                    rule['hall_logic']['hall_set'] = set(hall_list)

            # c. 写入与刷新
            self.save_rules_to_file()
            self.load_rules_to_editor()

            # 在状态栏给出成功提示
            self.statusBar().showMessage("保存成功！")

            # 记录保存成功
            logging.info(f"规则 '{rule_name}' 已成功保存")

        except Exception as e:
            logging.error(f"保存规则时出错: {e}")
            QMessageBox.warning(self, "保存失败", f"保存规则时发生错误：{str(e)}")
            self.statusBar().showMessage("保存失败")

    def save_rules_to_file(self):
        """将规则保存到文件"""
        try:
            # 准备保存的数据（移除hall_set，因为它是运行时生成的）
            rules_to_save = []
            for rule in self.engine.rules:
                rule_copy = rule.copy()
                if 'hall_logic' in rule_copy and 'hall_set' in rule_copy['hall_logic']:
                    hall_logic_copy = rule_copy['hall_logic'].copy()
                    del hall_logic_copy['hall_set']
                    rule_copy['hall_logic'] = hall_logic_copy
                rules_to_save.append(rule_copy)

            # 写入文件
            with open(RULES_FILE, 'w', encoding='utf-8') as f:
                json.dump(rules_to_save, f, ensure_ascii=False, indent=2)

            logging.debug("规则已保存到文件")

        except Exception as e:
            logging.error(f"保存规则到文件时出错: {e}")
            raise

    def connect_signals(self):
        """连接信号与槽"""
        # 【v1.3 最终Bug修复】连接规则列表选择变化信号 - 使用新的方法名
        self.rule_list.currentItemChanged.connect(self.on_rule_selected)

        # 连接按钮信号（这些在create_left_panel中已经连接，这里重新确认）
        # 注意：现在使用的是新的按钮名称
        # self.btn_add_keyword_rule 和 self.btn_add_whitelist_rule 已在 create_left_panel 中连接

    def load_rules_to_editor(self):
        """加载规则到编辑器"""
        try:
            # 清空规则列表
            self.rule_list.clear()

            # 遍历规则，添加到列表中
            for rule in self.engine.rules:
                rule_name = rule.get('rule_name', '未命名规则')
                self.rule_list.addItem(rule_name)

            # 如果有规则，选择第一个
            if self.rule_list.count() > 0:
                self.rule_list.setCurrentRow(0)

            logging.debug(f"已加载 {len(self.engine.rules)} 条规则到编辑器")

        except Exception as e:
            logging.error(f"加载规则到编辑器时出错: {e}")

    def on_rule_selected(self, current_item, previous_item):
        """【v1.3 最终Bug修复】彻底重写规则选择逻辑 - 基于行号索引的精确切换"""
        # 如果没有选中项（例如删除后或清空选择），显示引导界面
        if current_item is None:
            self.guide_label.show()
            self.editor_stacked_widget.hide()
            return

        try:
            # 1. 获取当前被选中项的行号索引current_row
            current_row = self.rule_list.currentRow()

            # 2. 检查该索引是否有效
            if not (0 <= current_row < len(self.engine.rules)):
                logging.warning(f"选择的规则索引无效: {current_row}, 规则总数: {len(self.engine.rules)}")
                # 索引无效时，显示引导界面
                self.guide_label.show()
                self.editor_stacked_widget.hide()
                return

            # 3. 直接使用current_row作为索引，从self.engine.rules列表中获取正确的策略对象policy
            policy = self.engine.rules[current_row]

            # 4. 从这个policy对象中，读取其'match_mode'字段的值
            match_conditions = policy.get('match_conditions', {})
            match_mode = match_conditions.get('match_mode', 'keywords')

            # 5. 隐藏引导标签，显示编辑器
            self.guide_label.hide()
            self.editor_stacked_widget.show()

            # 6. 根据match_mode的值，使用setCurrentIndex()将右侧的编辑区切换到对应的"卡片"
            if match_mode == 'whitelist':
                # 白名单编辑卡片
                self.editor_stacked_widget.setCurrentIndex(1)
                logging.info(f"切换到白名单策略 '{policy.get('rule_name')}' 的编辑界面（卡片索引1）")
            elif match_mode == 'keywords' or match_mode == 'keyword':
                # 关键词编辑卡片
                self.editor_stacked_widget.setCurrentIndex(0)
                logging.info(f"切换到关键词策略 '{policy.get('rule_name')}' 的编辑界面（卡片索引0）")
            else:
                # 默认使用关键词策略卡片
                self.editor_stacked_widget.setCurrentIndex(0)
                logging.warning(f"未知的策略类型: {match_mode}，使用默认关键词卡片")

            # 7. 调用对应的fill_..._form(policy)方法，将policy对象中的数据填充到刚刚切换出来的、正确的UI界面上
            if match_mode == 'whitelist':
                self.fill_whitelist_form(policy)
            else:
                self.fill_keyword_form(policy)

            logging.debug(f"已成功切换到规则 '{policy.get('rule_name', '未命名')}' 的编辑界面")

        except Exception as e:
            logging.error(f"规则选择切换时出错: {e}", exc_info=True)
            # 出错时显示引导界面
            self.guide_label.show()
            self.editor_stacked_widget.hide()

    def fill_keyword_form(self, policy):
        """填充关键词策略表单"""
        try:
            # 规则名称
            self.edit_rule_name.setText(policy.get('rule_name', ''))

            # 匹配条件
            match_conditions = policy.get('match_conditions', {})
            self.edit_city.setText(match_conditions.get('city', ''))

            # 影院关键词（列表转字符串）
            keywords = match_conditions.get('cinema_keywords', [])
            self.edit_cinema_keywords.setText(','.join(keywords))

            # 影厅逻辑
            hall_logic = policy.get('hall_logic', {})
            mode = hall_logic.get('mode', 'INCLUDE').upper()

            # 设置单选按钮
            if mode == 'ALL':
                self.radio_all.setChecked(True)
            elif mode == 'INCLUDE':
                self.radio_include.setChecked(True)
            elif mode == 'EXCLUDE':
                self.radio_exclude.setChecked(True)

            # 影厅列表
            hall_list = hall_logic.get('hall_list', [])
            self.edit_hall_list.setText(','.join(hall_list))

            # 成本价
            cost = hall_logic.get('cost', 0)
            self.edit_cost.setText(str(cost))

            # 最低利润
            profit_logic = policy.get('profit_logic', {})
            min_profit = profit_logic.get('min_profit_threshold', 0)
            self.edit_min_profit.setText(str(min_profit))

            # 启用状态
            enabled = policy.get('enabled', True)
            self.checkbox_enabled.setChecked(enabled)

        except Exception as e:
            logging.error(f"填充关键词表单时出错: {e}")

    def fill_whitelist_form(self, policy):
        """填充白名单策略表单"""
        try:
            # 规则名称
            self.edit_whitelist_rule_name.setText(policy.get('rule_name', ''))

            # 匹配条件
            match_conditions = policy.get('match_conditions', {})
            self.edit_whitelist_city.setText(match_conditions.get('city', ''))

            # 启用状态
            enabled = policy.get('enabled', True)
            self.checkbox_whitelist_enabled.setChecked(enabled)

        except Exception as e:
            logging.error(f"填充白名单表单时出错: {e}")

    def init_worker_thread(self):
        """初始化后台工作线程"""
        # 创建线程和工作对象
        self.thread = QThread()
        self.worker = Worker(self.engine)

        # 将worker移动到新线程中
        self.worker.moveToThread(self.thread)

        # 连接信号与槽
        self.thread.started.connect(self.worker.run)
        self.worker.new_opportunity.connect(self.add_opportunity_to_table)
        self.worker.status_update.connect(self.statusBar().showMessage)
        self.worker.cycle_finished.connect(self.update_status_bar)

        # 启动线程
        self.thread.start()     

        # 更新状态栏
        self.statusBar().showMessage("后台监控已启动，等待抢单机会...")

    def add_opportunity_to_table(self, opportunity_data):
        """槽函数：接收抢单机会数据并添加到表格中"""

        # 【第一步：完整的语音处理模块】
        try:
            # 日志记录，方便未来调试
            logging.info("MainWindow收到新机会，准备调用语音模块...")

            # 声明空的alert_text字符串变量，用于存放最终要播报的文本
            alert_text = ""

            # 从传入的opportunity_data字典中获取type字段的值
            opportunity_type = opportunity_data.get('type', opportunity_data.get('strategy_type', 'unknown'))

            # 【第二步：实现差异化的文本生成逻辑】
            if opportunity_type == 'whitelist':
                # 白名单策略的播报逻辑
                platform = opportunity_data.get('platform', '未知平台')
                alert_text = f"{platform}，白名单订单来了"

            elif opportunity_type == 'keyword' or opportunity_type == 'keywords':
                # 关键词策略的播报逻辑
                platform = opportunity_data.get('platform', '未知平台')
                profit = opportunity_data.get('total_profit')

                # 对profit字段进行检查，确保它存在且不为None
                if profit is not None:
                    try:
                        # 安全地将profit转换为格式化的字符串（保留两位小数）
                        profit_str = f"{float(profit):.2f}"
                        alert_text = f"{profit_str}元利润，{platform}平台来单了"
                    except (ValueError, TypeError):
                        # 如果转换失败，使用"未知利润"作为后备
                        logging.warning(f"利润字段转换失败，原值: {profit}")
                        alert_text = f"未知利润，{platform}平台来单了"
                else:
                    # profit字段不存在，提供不包含利润的保底播报文本
                    alert_text = f"{platform}平台来单了"

            else:
                # 未知的策略类型，提供通用的播报文本
                platform = opportunity_data.get('platform', '未知平台')
                alert_text = f"{platform}平台有新订单"
                logging.warning(f"未知的策略类型: {opportunity_type}，使用通用播报文本")

            # 【第三步：执行语音播报】
            if alert_text:
                logging.info(f"最终生成的播报文本: {alert_text}")
                self.tts_player.play(alert_text)
            else:
                logging.warning("播报文本为空，跳过语音播报")

        except Exception as e:
            # 记录任何可能发生的未知异常
            logging.error(f"语音处理模块发生未知异常: {e}")

        # 【第四步：确认UI更新逻辑】
        # 以下是原有的UI表格更新代码
        try:
            # 提取平台和利润信息用于UI显示
            platform_name = opportunity_data.get('platform', '未知')
            total_profit = opportunity_data.get('total_profit', 0)

            # 在表格顶部插入新行
            self.table.insertRow(0)

            # 从opportunity_data字典中提取信息并填充到表格
            # 列顺序：['平台', '触发时间', '利润', '影院名称', '影厅', '场次', '竞标价', '匹配规则']

            # 平台
            platform_item = QTableWidgetItem(platform_name)
            self.table.setItem(0, 0, platform_item)

            # 触发时间
            timestamp_item = QTableWidgetItem(opportunity_data.get('timestamp', ''))
            self.table.setItem(0, 1, timestamp_item)

            # 利润（红色字体显示）
            seat_count = opportunity_data.get('seat_count', 1)
            profit_item = QTableWidgetItem(f"{total_profit:.1f}元 ({seat_count}张票)")
            profit_item.setForeground(QColor(255, 0, 0))  # 红色字体
            self.table.setItem(0, 2, profit_item)

            # 影院名称
            order_details = opportunity_data.get('order_details', {})
            cinema_item = QTableWidgetItem(order_details.get('cinema_name', ''))
            self.table.setItem(0, 3, cinema_item)

            # 影厅
            hall_item = QTableWidgetItem(order_details.get('hall_type', ''))
            self.table.setItem(0, 4, hall_item)

            # 场次
            show_time_item = QTableWidgetItem(opportunity_data.get('show_time', ''))
            self.table.setItem(0, 5, show_time_item)

            # 竞标价
            bidding_price = order_details.get('bidding_price', 0)
            price_item = QTableWidgetItem(f"{bidding_price:.1f}元")
            self.table.setItem(0, 6, price_item)

            # 匹配规则
            rule_item = QTableWidgetItem(opportunity_data.get('rule_name', ''))
            self.table.setItem(0, 7, rule_item)

            # 限制表格行数，避免数据过多
            if self.table.rowCount() > 100:
                self.table.removeRow(100)

            # 更新状态栏
            total_opportunities = self.table.rowCount()
            self.statusBar().showMessage(f"发现 {total_opportunities} 个抢单机会，最新利润：{total_profit:.1f}元")

            # 记录抢单机会
            logging.info(f"发现抢单机会: {opportunity_data['rule_name']} - 总利润 {opportunity_data['total_profit']:.2f}元 ({opportunity_data['seat_count']}张票)")

        except Exception as e:
            logging.error(f"添加数据到表格时出错: {e}")

    def update_status_bar(self, platform_names, new_order_count):
        """
        更新状态栏显示多平台状态

        Args:
            platform_names (list): 成功获取数据的平台名称列表
            new_order_count (int): 新订单总数
        """
        try:
            if platform_names:
                platforms_text = ', '.join(platform_names)
                status_text = f"({platforms_text}) 获取完成，新增 {new_order_count} 条订单。{API_REQUEST_INTERVAL}秒后开始下一次轮询..."
            else:
                status_text = f"所有平台获取失败，{API_REQUEST_INTERVAL}秒后重试..."

            self.statusBar().showMessage(status_text)

        except Exception as e:
            logging.error(f"更新状态栏时出错: {e}")

    def closeEvent(self, event):
        """重写关闭事件，实现优雅退出"""
        try:
            logging.info("正在关闭应用程序...")

            # 安全地退出后台线程
            if hasattr(self, 'thread') and self.thread.isRunning():
                logging.info("正在停止后台监控线程...")
                self.thread.quit()  # 请求线程退出

                # 等待线程完全退出，最多等待3秒
                if self.thread.wait(3000):  # 3000毫秒 = 3秒
                    logging.info("后台线程已安全退出")
                else:
                    logging.warning("后台线程退出超时，强制终止")
                    self.thread.terminate()
                    self.thread.wait(1000)  # 再等待1秒确保终止

            # 正式关闭窗口
            event.accept()
            logging.info("应用程序已关闭")

        except Exception as e:
            logging.error(f"关闭应用程序时出错: {e}")
            # 即使出错也要关闭窗口
            event.accept()
