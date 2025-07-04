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

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QFormLayout,
    QWidget, QTableWidget, QTableWidgetItem, QTabWidget, QSplitter,
    QListWidget, QPushButton, QLineEdit, QRadioButton, QCheckBox,
    QButtonGroup, QLabel, QMessageBox
)
from PyQt6.QtCore import QObject, QThread, pyqtSignal, Qt
from PyQt6.QtGui import QColor

from core.engine import RuleEngine
from core.platforms.haha_adapter import HahaAdapter
from config import RULES_FILE


class Worker(QObject):
    """后台工作线程类 - 负责异步处理订单监控和规则匹配"""

    # 定义自定义信号，用于向主窗口发送抢单机会数据
    new_opportunity = pyqtSignal(dict)

    def __init__(self, engine):
        """初始化Worker，接受规则引擎实例"""
        super().__init__()
        self.engine = engine

    def run(self):
        """后台任务主方法"""
        # 使用传入的规则引擎实例
        engine = self.engine

        async def main_loop():
            """主要的异步循环，从API获取订单数据"""
            logging.info("后台监控线程启动")

            # 实例化哈哈平台适配器
            adapter = HahaAdapter()

            while True:
                try:
                    # 调用适配器获取最新订单（经过去重）
                    latest_orders = await adapter.fetch_and_process()

                    # 遍历新订单并检查规则匹配
                    for order in latest_orders:
                        # 使用规则引擎检查订单
                        result = engine.check_order(order)

                        # 如果匹配成功，发射信号
                        if result is not None:
                            # 添加时间戳和场次信息到结果中
                            result['timestamp'] = order.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                            result['show_time'] = order.get('show_time', '未知')

                            logging.info(f"发现抢单机会: {result['rule_name']} - 总利润{result['total_profit']:.1f}元 ({result['seat_count']}张票)")

                            # 发射信号到主窗口
                            self.new_opportunity.emit(result)

                    # 控制API调用频率（延长到5秒便于观察测试）
                    await asyncio.sleep(5)

                except Exception as e:
                    logging.error(f"后台处理出错: {e}")
                    await asyncio.sleep(5)

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

        # 创建规则引擎实例
        self.engine = RuleEngine(RULES_FILE)

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
        self.table.setColumnCount(7)
        headers = ['触发时间', '利润', '影院名称', '影厅', '场次', '竞标价', '匹配规则']
        self.table.setHorizontalHeaderLabels(headers)

        # 设置表格列宽
        self.table.setColumnWidth(0, 150)  # 触发时间
        self.table.setColumnWidth(1, 80)   # 利润
        self.table.setColumnWidth(2, 200)  # 影院名称
        self.table.setColumnWidth(3, 100)  # 影厅
        self.table.setColumnWidth(4, 120)  # 场次
        self.table.setColumnWidth(5, 80)   # 竞标价
        self.table.setColumnWidth(6, 180)  # 匹配规则

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
        self.btn_add_rule = QPushButton("新增规则")
        self.btn_delete_rule = QPushButton("删除规则")
        self.btn_save_rules = QPushButton("保存")

        # 设置按钮样式
        for btn in [self.btn_add_rule, self.btn_delete_rule, self.btn_save_rules]:
            btn.setMinimumHeight(35)

        left_layout.addWidget(self.btn_add_rule)
        left_layout.addWidget(self.btn_delete_rule)
        left_layout.addWidget(self.btn_save_rules)

        # 连接按钮信号
        self.btn_add_rule.clicked.connect(self.add_new_rule)
        self.btn_delete_rule.clicked.connect(self.delete_selected_rule)
        self.btn_save_rules.clicked.connect(self.save_current_rule)

        left_widget.setLayout(left_layout)
        return left_widget

    def create_right_panel(self):
        """创建右侧面板"""
        right_widget = QWidget()
        form_layout = QFormLayout()

        # 用户引导标签
        self.guide_label = QLabel("请从左侧选择规则进行编辑，或点击'新增规则'。")
        self.guide_label.setStyleSheet("color: gray; font-style: italic; padding: 20px; text-align: center;")
        self.guide_label.setWordWrap(True)
        form_layout.addRow("", self.guide_label)

        # 创建表单控件容器
        self.form_container = QWidget()
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

        # 设置表单容器布局
        self.form_container.setLayout(form_container_layout)

        # 将表单容器添加到主布局
        form_layout.addRow("", self.form_container)

        # 初始状态：显示引导标签，隐藏表单容器
        self.guide_label.show()
        self.form_container.hide()

        right_widget.setLayout(form_layout)
        return right_widget

    def add_new_rule(self):
        """添加新规则"""
        try:
            # 隐藏引导标签，显示表单容器
            self.guide_label.hide()
            self.form_container.show()

            # 清空右侧表单，准备输入新规则
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
        """删除选中的规则"""
        try:
            current_item = self.rule_list.currentItem()
            if current_item is None:
                self.statusBar().showMessage("请先选择要删除的规则")
                return

            rule_name = current_item.text()

            # 弹出确认对话框
            reply = QMessageBox.question(
                self,
                "确认删除",
                f"您确定要删除规则 '{rule_name}' 吗？此操作无法撤销。",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )

            # 如果用户点击了No，直接返回
            if reply != QMessageBox.StandardButton.Yes:
                return

            # 从内存中删除规则
            self.engine.rules = [rule for rule in self.engine.rules
                               if rule.get('rule_name') != rule_name]

            # 保存到文件并刷新UI
            self.save_rules_to_file()
            self.load_rules_to_editor()

            logging.info(f"规则 '{rule_name}' 已被删除")
            self.statusBar().showMessage(f"规则 '{rule_name}' 已删除")

        except Exception as e:
            logging.error(f"删除规则时出错: {e}")
            self.statusBar().showMessage("删除规则失败")

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
        # 连接规则列表选择变化信号
        self.rule_list.currentItemChanged.connect(self.display_rule_details)

        # 连接按钮信号（这些在create_left_panel中已经连接，这里重新确认）
        self.btn_add_rule.clicked.connect(self.add_new_rule)
        self.btn_delete_rule.clicked.connect(self.delete_selected_rule)
        self.btn_save_rules.clicked.connect(self.save_current_rule)

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

    def display_rule_details(self, current_item):
        """显示规则详情"""
        if current_item is None:
            # 显示引导标签，隐藏表单容器
            self.guide_label.show()
            self.form_container.hide()
            return

        try:
            # 隐藏引导标签，显示表单容器
            self.guide_label.hide()
            self.form_container.show()

            rule_name = current_item.text()

            # 在规则列表中找到对应的规则
            selected_rule = None
            for rule in self.engine.rules:
                if rule.get('rule_name') == rule_name:
                    selected_rule = rule
                    break

            if selected_rule is None:
                logging.warning(f"未找到规则: {rule_name}")
                return

            # 填充表单数据
            self.edit_rule_name.setText(selected_rule.get('rule_name', ''))

            # 匹配条件
            match_conditions = selected_rule.get('match_conditions', {})
            self.edit_city.setText(match_conditions.get('city', ''))

            # 影院关键词（列表转字符串）
            keywords = match_conditions.get('cinema_keywords', [])
            self.edit_cinema_keywords.setText(','.join(keywords))

            # 影厅逻辑
            hall_logic = selected_rule.get('hall_logic', {})
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
            profit_logic = selected_rule.get('profit_logic', {})
            min_profit = profit_logic.get('min_profit_threshold', 0)
            self.edit_min_profit.setText(str(min_profit))

            # 启用状态
            enabled = selected_rule.get('enabled', True)
            self.checkbox_enabled.setChecked(enabled)

            logging.debug(f"已显示规则详情: {rule_name}")

        except Exception as e:
            logging.error(f"显示规则详情时出错: {e}")

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

        # 启动线程
        self.thread.start()

        # 更新状态栏
        self.statusBar().showMessage("后台监控已启动，等待抢单机会...")

    def add_opportunity_to_table(self, opportunity_data):
        """槽函数：接收抢单机会数据并添加到表格中"""
        try:
            # 在表格顶部插入新行
            self.table.insertRow(0)

            # 从opportunity_data字典中提取信息并填充到表格
            # 列顺序：['触发时间', '利润', '影院名称', '影厅', '场次', '竞标价', '匹配规则']

            # 触发时间
            timestamp_item = QTableWidgetItem(opportunity_data.get('timestamp', ''))
            self.table.setItem(0, 0, timestamp_item)

            # 利润（红色字体显示）
            total_profit = opportunity_data.get('total_profit', 0)
            seat_count = opportunity_data.get('seat_count', 1)
            profit_item = QTableWidgetItem(f"{total_profit:.1f}元 ({seat_count}张票)")
            profit_item.setForeground(QColor(255, 0, 0))  # 红色字体
            self.table.setItem(0, 1, profit_item)

            # 影院名称
            order_details = opportunity_data.get('order_details', {})
            cinema_item = QTableWidgetItem(order_details.get('cinema_name', ''))
            self.table.setItem(0, 2, cinema_item)

            # 影厅
            hall_item = QTableWidgetItem(order_details.get('hall_type', ''))
            self.table.setItem(0, 3, hall_item)

            # 场次
            show_time_item = QTableWidgetItem(opportunity_data.get('show_time', ''))
            self.table.setItem(0, 4, show_time_item)

            # 竞标价
            bidding_price = order_details.get('bidding_price', 0)
            price_item = QTableWidgetItem(f"{bidding_price:.1f}元")
            self.table.setItem(0, 5, price_item)

            # 匹配规则
            rule_item = QTableWidgetItem(opportunity_data.get('rule_name', ''))
            self.table.setItem(0, 6, rule_item)

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
