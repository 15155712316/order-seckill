#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主窗口GUI模块 - 支持多元化策略引擎
包含关键词策略和白名单策略两种模式
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
    QListWidget, QListWidgetItem, QPushButton, QLineEdit, QRadioButton, QCheckBox,
    QButtonGroup, QLabel, QMessageBox, QStackedWidget, QFileDialog,
    QComboBox, QSpinBox, QDoubleSpinBox, QGroupBox
)
from PyQt6.QtCore import QObject, QThread, pyqtSignal, Qt
from PyQt6.QtGui import QColor

from core.engine import RuleEngine
from core.database import DatabaseManager
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
            """主循环：持续监控订单并匹配规则"""
            # 初始化平台适配器
            haha_adapter = HahaAdapter(HAHA_PLATFORM_NAME)
            mahua_adapter = MahuaAdapter(MAHUA_PLATFORM_NAME)

            while True:
                try:
                    # 发送状态更新
                    self.status_update.emit("正在获取订单数据...")

                    # 并发获取多个平台的数据
                    results = await asyncio.gather(
                        haha_adapter.fetch_and_process(),
                        mahua_adapter.fetch_and_process(),
                        return_exceptions=True
                    )

                    # 处理结果
                    successful_platforms = []
                    total_new_orders = 0

                    for i, result in enumerate(results):
                        platform_name = [HAHA_PLATFORM_NAME, MAHUA_PLATFORM_NAME][i]

                        if isinstance(result, Exception):
                            logging.error(f"{platform_name}平台获取数据失败: {result}")
                            continue

                        # 调试日志：打印平台返回的完整结果结构
                        logging.debug(f"🔍 {platform_name}平台返回结果: success={result.get('success')}, 字段={list(result.keys())}")

                        if result['success']:
                            successful_platforms.append(platform_name)
                            new_orders = result.get('orders', [])  # 修复：使用正确的字段名 'orders'
                            order_count = len(new_orders)
                            total_new_orders += order_count

                            # 调试日志：详细记录订单计数
                            logging.debug(f"📊 {platform_name}平台: 获取到 {order_count} 条新订单，累计 {total_new_orders} 条")
                            
                            # 对每个新订单进行规则匹配
                            for order in new_orders:
                                match_result = engine.check_order(order)
                                if match_result:
                                    # 发现抢单机会
                                    opportunity_data = {
                                        'platform': platform_name,
                                        'profit': match_result['total_profit'],
                                        'seat_count': match_result['seat_count'],
                                        'rule_name': match_result['rule_name'],
                                        'order': match_result['order_details'],
                                        'type': match_result.get('strategy_type', 'keyword')  # 添加策略类型
                                    }
                                    
                                    # 发送信号到主窗口
                                    self.new_opportunity.emit(opportunity_data)
                                    
                                    # 【移除Worker线程中的语音播报】
                                    # 语音播报现在在MainWindow的on_new_opportunity方法中处理
                                    # 这样可以确保语音播报在UI线程中执行，避免线程安全问题

                    # 发送轮询周期完成信号
                    self.cycle_finished.emit(successful_platforms, total_new_orders)

                    # 等待下一次轮询
                    await asyncio.sleep(API_REQUEST_INTERVAL)

                except Exception as e:
                    logging.error(f"主循环发生错误: {e}")
                    self.status_update.emit(f"发生错误: {e}")
                    await asyncio.sleep(5)  # 错误后短暂等待

        # 运行异步主循环
        asyncio.run(main_loop())


class MainWindow(QMainWindow):
    """主窗口类 - 多元化策略引擎界面"""

    def __init__(self):
        """【中央仓储架构】初始化主窗口 - 响应式UI"""
        super().__init__()

        # 初始化数据库管理器
        self.db_manager = DatabaseManager()

        # 【核心改进】初始化新的RuleEngine（状态广播系统）
        self.engine = RuleEngine(db_manager=self.db_manager)

        # 初始化语音播放器
        self.tts_player = TTSPlayer()

        # 当前编辑的规则
        self.current_rule = None
        self.current_strategy_type = None  # 'keywords' 或 'whitelist'

        # 设置窗口属性
        self.setWindowTitle("抢单提醒系统 - 中央仓储架构")
        self.setGeometry(100, 100, 1400, 900)

        # 创建UI
        self.init_ui()

        # 【核心改进】连接响应式信号与槽
        self.connect_signals()

        # 【修复】手动触发初始UI刷新
        # 因为引擎在初始化时发射的信号此时UI还未准备好接收
        self.refresh_policy_list_from_engine()
        logging.info("手动触发初始UI刷新完成")

        # 启动后台工作线程
        self.init_worker_thread()

        # 记录应用程序启动
        logging.info("中央仓储架构启动完成")

    def init_ui(self):
        """初始化用户界面"""
        # 创建中央窗口部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 创建Tab容器
        self.tab_widget = QTabWidget()
        central_widget_layout = QVBoxLayout()
        central_widget_layout.addWidget(self.tab_widget)
        central_widget.setLayout(central_widget_layout)

        # 创建各个Tab页
        self.create_monitoring_tab()
        self.create_editor_tab()

        # 创建状态栏
        self.statusBar().showMessage("系统已启动，等待数据...")

    def create_monitoring_tab(self):
        """创建第一个Tab页：抢单监控"""
        # 创建监控Tab容器
        self.monitoring_tab = QWidget()

        # 创建表格用于显示抢单机会
        self.opportunities_table = QTableWidget()
        self.opportunities_table.setColumnCount(7)
        self.opportunities_table.setHorizontalHeaderLabels([
            "平台", "利润", "票数", "规则名称", "城市", "影院", "影厅"
        ])

        # 设置表格属性
        self.opportunities_table.setAlternatingRowColors(True)
        self.opportunities_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        # 创建布局
        monitoring_layout = QVBoxLayout()
        monitoring_layout.addWidget(QLabel("抢单机会监控:"))
        monitoring_layout.addWidget(self.opportunities_table)
        self.monitoring_tab.setLayout(monitoring_layout)

        # 添加到Tab容器
        self.tab_widget.addTab(self.monitoring_tab, "抢单监控")

    def create_editor_tab(self):
        """创建第二个Tab页：策略编辑"""
        # 创建编辑Tab容器
        self.editor_tab = QWidget()

        # 创建主分割器（左右分割）
        main_splitter = QSplitter(Qt.Orientation.Horizontal)

        # 创建左右面板
        left_panel = self.create_left_panel()
        right_panel = self.create_right_panel()

        # 添加到分割器
        main_splitter.addWidget(left_panel)
        main_splitter.addWidget(right_panel)

        # 设置分割器比例
        main_splitter.setSizes([300, 700])

        # 创建编辑Tab布局
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
        self.btn_add_keyword_rule.clicked.connect(self.add_keyword_rule)
        self.btn_add_whitelist_rule.clicked.connect(self.add_whitelist_rule)
        self.btn_delete_rule.clicked.connect(self.delete_selected_rule)
        self.btn_save_rules.clicked.connect(self.save_current_rule)

        left_widget.setLayout(left_layout)
        return left_widget

    def create_right_panel(self):
        """创建右侧面板"""
        right_widget = QWidget()
        main_layout = QVBoxLayout()

        # 用户引导标签
        self.guide_label = QLabel("请从左侧选择规则进行编辑，或点击策略按钮创建新规则。")
        self.guide_label.setStyleSheet("color: gray; font-style: italic; padding: 20px; text-align: center;")
        self.guide_label.setWordWrap(True)
        main_layout.addWidget(self.guide_label)

        # 创建堆叠窗口部件
        self.stacked_widget = QStackedWidget()

        # 创建关键词策略编辑卡片
        self.keyword_card = self.create_keyword_strategy_card()
        self.stacked_widget.addWidget(self.keyword_card)

        # 创建白名单策略编辑卡片
        self.whitelist_card = self.create_whitelist_strategy_card()
        self.stacked_widget.addWidget(self.whitelist_card)

        main_layout.addWidget(self.stacked_widget)

        # 默认隐藏堆叠窗口部件
        self.stacked_widget.hide()

        right_widget.setLayout(main_layout)
        return right_widget

    def create_keyword_strategy_card(self):
        """创建关键词策略编辑卡片"""
        card_widget = QWidget()
        form_layout = QFormLayout()

        # 规则名称
        self.edit_rule_name = QLineEdit()
        form_layout.addRow("规则名称:", self.edit_rule_name)

        # 城市
        self.edit_city = QLineEdit()
        form_layout.addRow("城市:", self.edit_city)

        # 影院关键词
        self.edit_cinema_keywords = QLineEdit()
        self.edit_cinema_keywords.setPlaceholderText("多个关键词用逗号分隔，如：万达,CBD")
        form_layout.addRow("影院关键词:", self.edit_cinema_keywords)

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
        form_layout.addRow("影厅逻辑模式:", hall_mode_widget)

        # 影厅列表
        self.edit_hall_list = QLineEdit()
        self.edit_hall_list.setPlaceholderText("多个影厅用逗号分隔，如：IMAX,激光IMAX")
        form_layout.addRow("影厅列表:", self.edit_hall_list)

        # 成本价
        self.edit_cost = QLineEdit()
        self.edit_cost.setPlaceholderText("例如：50.0")
        form_layout.addRow("成本价:", self.edit_cost)

        # 最低利润
        self.edit_min_profit = QLineEdit()
        self.edit_min_profit.setPlaceholderText("例如：8.0")
        form_layout.addRow("最低利润:", self.edit_min_profit)

        # 【安全机制】启用此规则 - 默认不启用
        self.checkbox_enabled = QCheckBox("启用此策略")
        self.checkbox_enabled.setChecked(False)
        form_layout.addRow("", self.checkbox_enabled)

        card_widget.setLayout(form_layout)
        return card_widget

    def create_whitelist_strategy_card(self):
        """创建白名单策略编辑卡片"""
        card_widget = QWidget()
        form_layout = QFormLayout()

        # 规则名称
        self.edit_whitelist_rule_name = QLineEdit()
        form_layout.addRow("规则名称:", self.edit_whitelist_rule_name)

        # 城市（可选）
        self.edit_whitelist_city = QLineEdit()
        self.edit_whitelist_city.setPlaceholderText("留空表示不限制城市")
        form_layout.addRow("城市（可选）:", self.edit_whitelist_city)

        # 白名单管理组
        whitelist_group = QGroupBox("影院白名单")
        whitelist_layout = QVBoxLayout()

        # 导入Excel按钮
        self.btn_import_excel = QPushButton("导入Excel名单")
        self.btn_import_excel.clicked.connect(self.import_excel_whitelist)
        whitelist_layout.addWidget(self.btn_import_excel)

        # 影院数量显示
        self.label_cinema_count = QLabel("已从数据库加载 0 个影院")
        self.label_cinema_count.setStyleSheet("color: blue; font-weight: bold;")
        whitelist_layout.addWidget(self.label_cinema_count)

        whitelist_group.setLayout(whitelist_layout)
        form_layout.addRow("", whitelist_group)

        # 高级筛选规则组
        filter_group = QGroupBox("高级筛选规则")
        filter_layout = QFormLayout()

        # 【人性化升级】票数筛选模板
        ticket_widget = QWidget()
        ticket_layout = QHBoxLayout()

        self.checkbox_ticket_1 = QCheckBox("1张")
        self.checkbox_ticket_2 = QCheckBox("2张")
        self.checkbox_ticket_3 = QCheckBox("3张")
        self.checkbox_ticket_4 = QCheckBox("4张")
        self.checkbox_ticket_5_plus = QCheckBox("5张及以上")

        # 【安全机制】默认不启用任何票数筛选，用户需要主动选择
        self.ticket_checkboxes = [
            self.checkbox_ticket_1, self.checkbox_ticket_2,
            self.checkbox_ticket_3, self.checkbox_ticket_4,
            self.checkbox_ticket_5_plus
        ]

        for checkbox in self.ticket_checkboxes:
            checkbox.setChecked(False)  # 默认不启用
            ticket_layout.addWidget(checkbox)

        ticket_layout.addStretch()
        ticket_widget.setLayout(ticket_layout)
        filter_layout.addRow("票数筛选:", ticket_widget)

        # 原价范围
        price_widget = QWidget()
        price_layout = QHBoxLayout()

        self.spin_min_price = QDoubleSpinBox()
        self.spin_min_price.setRange(0, 999)
        self.spin_min_price.setValue(0)
        self.spin_min_price.setSuffix(" 元")

        price_layout.addWidget(QLabel("最低:"))
        price_layout.addWidget(self.spin_min_price)

        self.spin_max_price = QDoubleSpinBox()
        self.spin_max_price.setRange(0, 999)
        self.spin_max_price.setValue(200)
        self.spin_max_price.setSuffix(" 元")

        price_layout.addWidget(QLabel("最高:"))
        price_layout.addWidget(self.spin_max_price)
        price_layout.addStretch()

        price_widget.setLayout(price_layout)
        filter_layout.addRow("原价范围:", price_widget)

        # 【净化】移除成本价和最低利润字段，白名单策略不需要这些字段

        # 最低竞标价
        self.edit_whitelist_min_bid = QDoubleSpinBox()
        self.edit_whitelist_min_bid.setRange(0, 999)
        self.edit_whitelist_min_bid.setValue(0)
        self.edit_whitelist_min_bid.setSuffix(" 元")
        filter_layout.addRow("最低竞标价:", self.edit_whitelist_min_bid)

        filter_group.setLayout(filter_layout)
        form_layout.addRow("", filter_group)

        # 【安全机制】启用此规则 - 默认不启用
        self.checkbox_whitelist_enabled = QCheckBox("启用此策略")
        self.checkbox_whitelist_enabled.setChecked(False)
        form_layout.addRow("", self.checkbox_whitelist_enabled)

        card_widget.setLayout(form_layout)
        return card_widget

    def add_keyword_rule(self):
        """【中央仓储架构】添加关键词策略 - 简化版本"""
        try:
            # 【简化】现在只需创建包含新ID的策略字典，然后调用引擎方法
            import uuid

            new_policy = {
                'rule_id': str(uuid.uuid4()),
                'rule_name': '新关键词策略',
                'enabled': False,  # 【安全机制】默认不启用
                'match_conditions': {
                    'match_mode': 'keywords',
                    'city': '',
                    'cinema_keywords': []
                },
                'hall_logic': {
                    'mode': 'ALL',
                    'hall_list': [],
                    'cost': 30.0
                },
                'profit_logic': {
                    'min_profit_threshold': 10.0
                },
                'filter_logic': {
                    'ticket_counts': [],  # 【安全机制】默认不选择任何票数
                    'price_range': {'min': 0, 'max': 200},
                    'min_bid_price': 0
                }
            }

            # 【核心简化】调用引擎方法，引擎会自动发射信号刷新UI
            success = self.engine.add_new_policy(new_policy)

            if success:
                # 设置当前编辑状态
                self.current_strategy_type = 'keywords'
                self.current_rule = new_policy

                # 显示编辑界面
                self.guide_label.hide()
                self.stacked_widget.show()
                self.stacked_widget.setCurrentWidget(self.keyword_card)

                # 加载策略到表单
                self.load_keyword_rule(new_policy)

                logging.info("成功添加新的关键词策略")
                self.statusBar().showMessage("新关键词策略已创建")
            else:
                QMessageBox.critical(self, "错误", "添加关键词策略失败")

        except Exception as e:
            logging.error(f"添加关键词策略失败: {e}")
            QMessageBox.critical(self, "错误", f"添加关键词策略失败: {e}")

    def add_whitelist_rule(self):
        """【中央仓储架构】添加白名单策略 - 简化版本"""
        try:
            # 【简化】现在只需创建包含新ID的策略字典，然后调用引擎方法
            import uuid

            new_policy = {
                'rule_id': str(uuid.uuid4()),
                'rule_name': '新白名单策略',
                'enabled': False,  # 【安全机制】默认不启用
                'match_conditions': {
                    'match_mode': 'whitelist',
                    'city': ''
                },
                # 【净化】白名单策略不需要hall_logic和profit_logic
                'filter_logic': {
                    'ticket_counts': [],  # 【安全机制】默认不选择任何票数
                    'price_range': {'min': 0, 'max': 200},
                    'min_bid_price': 0
                }
            }

            # 【核心简化】调用引擎方法，引擎会自动发射信号刷新UI
            success = self.engine.add_new_policy(new_policy)

            if success:
                # 设置当前编辑状态
                self.current_strategy_type = 'whitelist'
                self.current_rule = new_policy
                self.current_policy_id = new_policy['rule_id']  # 白名单策略需要这个ID

                # 显示编辑界面
                self.guide_label.hide()
                self.stacked_widget.show()
                self.stacked_widget.setCurrentWidget(self.whitelist_card)

                # 加载策略到表单
                self.load_whitelist_rule(new_policy)

                logging.info("成功添加新的白名单策略")
                self.statusBar().showMessage("新白名单策略已创建，请导入影院名单")
            else:
                QMessageBox.critical(self, "错误", "添加白名单策略失败")

        except Exception as e:
            logging.error(f"添加白名单策略失败: {e}")
            QMessageBox.critical(self, "错误", f"添加白名单策略失败: {e}")

    def clear_keyword_form(self):
        """清空关键词策略表单"""
        self.edit_rule_name.clear()
        self.edit_city.clear()
        self.edit_cinema_keywords.clear()
        self.edit_hall_list.clear()
        self.edit_cost.clear()
        self.edit_min_profit.clear()
        self.radio_include.setChecked(True)
        self.checkbox_enabled.setChecked(False)  # 【安全机制】默认不启用

    def clear_whitelist_form(self):
        """【净化】清空白名单策略表单 - 移除成本和利润字段"""
        self.edit_whitelist_rule_name.clear()
        self.edit_whitelist_city.clear()
        # 【净化】移除成本价和最低利润的清空操作
        self.edit_whitelist_min_bid.setValue(0)
        self.spin_min_price.setValue(0)
        self.spin_max_price.setValue(200)

        # 【安全机制】重置票数选择 - 默认不启用
        for checkbox in self.ticket_checkboxes:
            checkbox.setChecked(False)

        self.checkbox_whitelist_enabled.setChecked(False)  # 【安全机制】默认不启用
        self.label_cinema_count.setText("已从数据库加载 0 个影院")

    def import_excel_whitelist(self):
        """导入Excel白名单 - v1.3 Bug修复版本"""
        try:
            # 打开文件选择对话框
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "选择Excel文件",
                "",
                "Excel文件 (*.xlsx *.xls);;CSV文件 (*.csv);;所有文件 (*)"
            )

            if not file_path:
                return

            # 使用新的健壮文件解析方法
            cinema_names = self.load_cinemas_from_file(file_path)

            if not cinema_names:
                # 错误信息已在load_cinemas_from_file中处理
                return

            # 生成临时策略ID（如果是新策略）
            if not self.current_rule:
                policy_id = str(uuid.uuid4())
            else:
                policy_id = self.current_rule.get('rule_id', str(uuid.uuid4()))

            # 导入到数据库
            success = self.engine.import_whitelist_cinemas(policy_id, cinema_names)

            if success:
                # 更新显示
                count = len(cinema_names)
                self.label_cinema_count.setText(f"已从数据库加载 {count} 个影院")

                # 保存策略ID以便后续保存
                self.current_policy_id = policy_id

                QMessageBox.information(self, "成功", f"成功导入 {count} 个影院到白名单")
                logging.info(f"成功导入 {count} 个影院到白名单策略 {policy_id}")
                self.statusBar().showMessage(f"成功导入 {count} 个影院")
            else:
                QMessageBox.warning(self, "错误", "导入影院数据失败")

        except Exception as e:
            logging.error(f"导入Excel白名单失败: {e}")
            QMessageBox.warning(self, "错误", f"导入失败: {e}")

    def load_cinemas_from_file(self, file_path: str) -> set:
        """
        【v1.3 Bug修复】从文件加载影院名单的健壮方法

        Args:
            file_path (str): 文件路径

        Returns:
            set: 影院名称集合，失败时返回空集合
        """
        try:
            # 根据文件扩展名选择读取方法
            if file_path.lower().endswith('.csv'):
                df = pd.read_csv(file_path, encoding='utf-8')
            else:
                # Excel文件
                df = pd.read_excel(file_path)

            logging.info(f"成功读取文件: {file_path}")
            logging.info(f"文件包含 {len(df)} 行数据，列名: {list(df.columns)}")

        except Exception as e:
            error_msg = f"读取文件失败: {e}"
            logging.error(error_msg)
            QMessageBox.warning(self, "错误", error_msg)
            return set()

        # 检查文件是否为空
        if df.empty:
            error_msg = "文件为空，没有数据"
            logging.error(error_msg)
            QMessageBox.warning(self, "错误", error_msg)
            return set()

        # 【核心修复】检查是否存在"影院名称"列
        target_column = "影院名称"
        if target_column not in df.columns:
            error_msg = f"关键列'{target_column}'未在文件中找到！"
            logging.error(error_msg)
            logging.error(f"文件中的列名: {list(df.columns)}")
            QMessageBox.warning(self, "错误", f"未找到'{target_column}'列\n\n文件中的列名: {list(df.columns)}\n\n请确保Excel文件包含名为'{target_column}'的列")
            return set()

        # 使用指定列名提取数据
        try:
            cinema_names_list = df[target_column].dropna().astype(str).tolist()
            logging.info(f"从'{target_column}'列提取到 {len(cinema_names_list)} 条原始数据")

        except Exception as e:
            error_msg = f"提取'{target_column}'列数据失败: {e}"
            logging.error(error_msg)
            QMessageBox.warning(self, "错误", error_msg)
            return set()

        # 清理和去重数据
        cinema_names = set()
        for name in cinema_names_list:
            cleaned_name = str(name).strip()
            if cleaned_name and cleaned_name != 'nan':  # 排除空值和NaN
                cinema_names.add(cleaned_name)

        if not cinema_names:
            error_msg = f"'{target_column}'列中未找到有效的影院名称"
            logging.error(error_msg)
            QMessageBox.warning(self, "错误", error_msg)
            return set()

        # 【验证日志】打印前5个成功提取的影院名称
        sample_names = list(cinema_names)[:5]
        logging.info(f"✅ 成功从文件中提取到 {len(cinema_names)} 个有效影院名称")
        logging.info(f"📋 前5个影院名称示例: {sample_names}")

        return cinema_names

    def delete_selected_rule(self):
        """
        【v1.3 最终修正版】删除选中的规则 - 使用行号索引直接删除，根治前缀匹配问题
        """
        try:
            # 1. 获取当前在QListWidget中被选中的行号索引
            current_row = self.rule_list.currentRow()

            # 2. 检查索引是否有效（用户是否真的选中了一项）
            if current_row == -1:
                self.statusBar().showMessage("请先在左侧列表中选择要删除的规则")
                return

            # 3. 从内存中获取规则对象，用于弹窗确认时显示名字
            if not (0 <= current_row < len(self.engine.rules)):
                logging.error(f"尝试删除一个无效的UI索引: {current_row}")
                self.statusBar().showMessage("删除失败：内部索引错误，请重启应用")
                return
            
            rule_to_delete = self.engine.rules[current_row]
            # 动态生成带前缀的显示名称，用于弹窗
            match_mode = rule_to_delete.get('match_conditions', {}).get('match_mode', 'keyword')
            prefix = "[白名单]" if match_mode == 'whitelist' else "[关键词]"
            rule_name_for_display = f"{prefix} {rule_to_delete.get('rule_name', '')}"

            # 4. 弹出二次确认对话框
            reply = QMessageBox.question(
                self, "确认删除",
                f"您确定要删除规则 '{rule_name_for_display}' 吗？\n此操作无法撤销。",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )

            # 5. 如果用户点击“No”，则不执行任何操作
            if reply != QMessageBox.StandardButton.Yes:
                return

            # 6. 【中央仓储架构】现在只需获取policy_id和index，然后调用引擎方法
            policy_id = rule_to_delete.get('rule_id')

            # 【必须删除所有手动操作self.rule_list的代码】
            success = self.engine.delete_policy(policy_id, current_row)

            if success:
                # 7. 清除当前编辑状态
                self.current_rule = None
                self.current_strategy_type = None

                # 8. 显示引导界面
                self.guide_label.show()
                self.stacked_widget.hide()

                # 9. 成功提示
                logging.info(f"策略 '{rule_name_for_display}' 删除成功")
                self.statusBar().showMessage(f"策略 '{rule_name_for_display}' 已删除")
            else:
                QMessageBox.critical(self, "删除失败", "删除策略时发生错误，请查看日志")

        except Exception as e:
            logging.error(f"删除规则时发生未知错误: {e}", exc_info=True)
            self.statusBar().showMessage("删除规则失败，请查看日志。")
    def save_current_rule(self):
        """【中央仓储架构】保存当前规则 - 简化版本"""
        try:
            if self.current_strategy_type == 'keywords':
                updated_policy = self.get_keyword_rule_data()
            elif self.current_strategy_type == 'whitelist':
                updated_policy = self.get_whitelist_rule_data()
            else:
                QMessageBox.warning(self, "错误", "请先选择策略类型")
                return

            # 【核心简化】现在只需调用引擎的save_policy_changes方法
            success = self.engine.save_policy_changes(updated_policy)

            if success:
                # 更新当前规则引用
                self.current_rule = updated_policy
                self.statusBar().showMessage("保存成功！")
                logging.info(f"策略 '{updated_policy.get('rule_name')}' 保存成功")
            else:
                QMessageBox.warning(self, "错误", "保存策略失败")

        except Exception as e:
            logging.error(f"保存规则失败: {e}")
            QMessageBox.warning(self, "错误", f"保存规则失败: {e}")

    def get_keyword_rule_data(self):
        """【中央仓储架构】获取关键词策略数据 - 纯数据获取方法"""
        # 数据获取与校验
        rule_name = self.edit_rule_name.text().strip()
        city = self.edit_city.text().strip()
        cinema_keywords_text = self.edit_cinema_keywords.text().strip()
        hall_list_text = self.edit_hall_list.text().strip()
        cost_text = self.edit_cost.text().strip()
        min_profit_text = self.edit_min_profit.text().strip()

        # 基本校验
        if not rule_name:
            raise ValueError("规则名称不能为空")

        if not cinema_keywords_text:
            raise ValueError("影院关键词不能为空")

        # 解析影院关键词
        cinema_keywords = [kw.strip() for kw in cinema_keywords_text.split(',') if kw.strip()]
        if not cinema_keywords:
            raise ValueError("请输入有效的影院关键词")

        # 解析影厅列表
        hall_list = []
        if hall_list_text:
            hall_list = [hall.strip() for hall in hall_list_text.split(',') if hall.strip()]

        # 解析数值
        try:
            cost = float(cost_text) if cost_text else 0.0
            min_profit = float(min_profit_text) if min_profit_text else 0.0
        except ValueError:
            raise ValueError("成本价和最低利润必须是有效数字")

        # 获取影厅逻辑模式
        if self.radio_all.isChecked():
            hall_mode = "ALL"
        elif self.radio_include.isChecked():
            hall_mode = "INCLUDE"
        else:
            hall_mode = "EXCLUDE"

        # 【人性化升级】获取票数选择 - 新的5个模板
        ticket_counts = []
        if hasattr(self, 'checkbox_ticket_1') and self.checkbox_ticket_1.isChecked():
            ticket_counts.append(1)
        if hasattr(self, 'checkbox_ticket_2') and self.checkbox_ticket_2.isChecked():
            ticket_counts.append(2)
        if hasattr(self, 'checkbox_ticket_3') and self.checkbox_ticket_3.isChecked():
            ticket_counts.append(3)
        if hasattr(self, 'checkbox_ticket_4') and self.checkbox_ticket_4.isChecked():
            ticket_counts.append(4)
        if hasattr(self, 'checkbox_ticket_5_plus') and self.checkbox_ticket_5_plus.isChecked():
            ticket_counts.extend(list(range(5, 21)))  # 5张及以上：5到20张

        # 构建策略数据
        rule_id = self.current_rule.get('rule_id') if self.current_rule else str(uuid.uuid4())

        policy_data = {
            'rule_id': rule_id,
            'rule_name': rule_name,
            'enabled': self.checkbox_enabled.isChecked(),
            'match_conditions': {
                'match_mode': 'keywords',
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
            },
            'filter_logic': {
                'ticket_counts': ticket_counts,
                'price_range': {
                    'min': getattr(self, 'spin_min_price', None).value() if hasattr(self, 'spin_min_price') else 0,
                    'max': getattr(self, 'spin_max_price', None).value() if hasattr(self, 'spin_max_price') else 200
                },
                'min_bid_price': getattr(self, 'edit_min_bid', None).value() if hasattr(self, 'edit_min_bid') else 0
            }
        }

        return policy_data

    def get_whitelist_rule_data(self):
        """【中央仓储架构】获取白名单策略数据 - 纯数据获取方法"""
        # 数据获取与校验
        rule_name = self.edit_whitelist_rule_name.text().strip()
        city = self.edit_whitelist_city.text().strip()

        # 基本校验
        if not rule_name:
            raise ValueError("规则名称不能为空")

        # 检查是否已导入影院数据
        if not hasattr(self, 'current_policy_id'):
            raise ValueError("请先导入影院白名单")

        # 构建策略数据
        rule_id = self.current_rule.get('rule_id') if self.current_rule else self.current_policy_id

        # 【净化】白名单策略数据结构 - 移除成本和利润字段
        policy_data = {
            'rule_id': rule_id,
            'rule_name': rule_name,
            'enabled': self.checkbox_whitelist_enabled.isChecked(),
            'match_conditions': {
                'match_mode': 'whitelist',
                'city': city
            },
            # 【净化】白名单策略不需要hall_logic和profit_logic
            'filter_logic': {
                'ticket_counts': self.get_selected_ticket_counts(),
                'price_range': {
                    'min': self.spin_min_price.value(),
                    'max': self.spin_max_price.value()
                },
                'min_bid_price': self.edit_whitelist_min_bid.value()
            }
        }

        return policy_data

    def get_selected_ticket_counts(self):
        """【人性化升级】获取选中的票数 - 新的5个模板"""
        selected = []
        if self.checkbox_ticket_1.isChecked():
            selected.append(1)
        if self.checkbox_ticket_2.isChecked():
            selected.append(2)
        if self.checkbox_ticket_3.isChecked():
            selected.append(3)
        if self.checkbox_ticket_4.isChecked():
            selected.append(4)
        if self.checkbox_ticket_5_plus.isChecked():
            selected.extend(list(range(5, 21)))  # 5张及以上：5到20张
        return selected

    # 【中央仓储架构】旧的save_rules_to_file方法已被删除
    # 现在数据直接保存到数据库，不再需要文件操作

    # 【中央仓储架构】旧的load_rules_to_editor方法已被删除
    # 现在UI刷新由refresh_policy_list_from_engine响应式方法处理

    def connect_signals(self):
        """【中央仓储架构】连接响应式信号与槽 - 状态驱动的UI刷新"""

        # 【核心连接】策略数据更新信号 → UI刷新槽
        # 使用Qt.ConnectionType.QueuedConnection确保信号在UI线程中处理
        from PyQt6.QtCore import Qt
        self.engine.policies_updated.connect(
            self.refresh_policy_list_from_engine,
            Qt.ConnectionType.QueuedConnection
        )

        # 规则列表选择事件
        self.rule_list.itemClicked.connect(self.on_rule_selected)
        self.rule_list.currentItemChanged.connect(self.on_rule_selection_changed)

        # 确保信号连接成功
        logging.info("响应式信号连接完成：策略更新 → UI刷新 (QueuedConnection)")
        logging.info("规则列表点击和选择变更事件已连接")

    def refresh_policy_list_from_engine(self):
        """
        【中央仓储架构】核心刷新槽 - UI列表更新的唯一入口

        此方法是UI列表更新的唯一入口，响应引擎的policies_updated信号
        实现单向数据流：Engine状态变更 → 信号发射 → UI刷新
        """
        try:
            logging.debug("开始响应式UI刷新...")

            # 1. 清空现有UI列表
            self.rule_list.clear()

            # 2. 遍历引擎中的所有策略，重建UI列表
            for i, policy in enumerate(self.engine.rules):
                rule_name = policy.get('rule_name', '未命名规则')

                # 根据策略类型添加前缀标识
                match_conditions = policy.get('match_conditions', {})
                match_mode = match_conditions.get('match_mode', 'keywords')

                if match_mode == 'whitelist':
                    type_prefix = "[白名单]"
                else:
                    type_prefix = "[关键词]"

                # 【安全机制】检查策略是否启用，添加状态前缀
                is_enabled = policy.get('enabled', False)
                if not is_enabled:
                    display_name = f"【已禁用】{type_prefix} {rule_name}"
                else:
                    display_name = f"{type_prefix} {rule_name}"

                # 3. 为每条策略创建新列表项并添加到UI
                item = QListWidgetItem(display_name)

                # 【视觉提示】为禁用的策略设置灰色文本
                if not is_enabled:
                    from PyQt6.QtCore import Qt
                    item.setForeground(Qt.GlobalColor.gray)

                self.rule_list.addItem(item)
                logging.debug(f"添加策略到UI: {i+1}. {display_name} (启用: {is_enabled})")

            # 4. 更新状态显示
            policy_count = len(self.engine.rules)
            logging.info(f"✅ 响应式UI刷新完成: {policy_count} 条策略已同步到UI")

            # 5. 如果没有策略，显示引导界面
            if policy_count == 0:
                self.guide_label.show()
                self.stacked_widget.hide()
                self.current_rule = None
                logging.debug("无策略，显示引导界面")

        except Exception as e:
            logging.error(f"响应式UI刷新失败: {e}", exc_info=True)
            # 即使出错也要确保UI处于一致状态
            self.rule_list.clear()
            self.guide_label.show()
            self.stacked_widget.hide()

    def on_rule_selected(self, item):
        """【v1.3 最终修正版】规则选择事件处理 - 使用索引确保正确切换"""
        if item is None:
            # 如果没有选中项，回到引导状态
            self.guide_label.show()
            self.stacked_widget.hide()
            self.current_rule = None
            return

        try:
            # 1. 获取当前选中的行号索引
            current_row = self.rule_list.row(item)
            
            if not (0 <= current_row < len(self.engine.rules)):
                logging.warning(f"选择的规则索引无效: {current_row}")
                return

            # 2. 【核心修复】直接使用索引从引擎获取策略对象
            policy = self.engine.rules[current_row]
            self.current_rule = policy # 设置当前正在编辑的规则
            
            match_mode = policy.get('match_conditions', {}).get('match_mode', 'keyword')
            logging.info(f"选中了第 {current_row} 行的规则，类型为: {match_mode}")

            # 3. 隐藏引导标签，显示编辑器
            self.guide_label.hide()
            self.stacked_widget.show()

            # 4. 根据策略类型，切换卡片并填充数据
            if match_mode == 'whitelist':
                self.stacked_widget.setCurrentWidget(self.whitelist_card)
                self.load_whitelist_rule(policy)
            else: # 默认为keyword
                self.stacked_widget.setCurrentWidget(self.keyword_card)
                self.load_keyword_rule(policy)

        except Exception as e:
            logging.error(f"显示规则详情时出错: {e}", exc_info=True)

    def on_rule_selection_changed(self, current_item, previous_item):
        """【UI同步修复】规则选择变更事件处理 - 确保UI状态同步"""
        try:
            # 记录选择变更的详细信息
            current_row = self.rule_list.currentRow() if current_item else -1
            previous_row = self.rule_list.row(previous_item) if previous_item else -1

            logging.debug(f"规则选择变更: {previous_row} -> {current_row}")

            # 验证当前选择的有效性
            if current_item is None:
                # 没有选中任何项，回到引导状态
                self.guide_label.show()
                self.stacked_widget.hide()
                self.current_rule = None
                logging.debug("清除规则选择，显示引导界面")
                return

            # 验证索引范围
            if not (0 <= current_row < len(self.engine.rules)):
                logging.warning(f"选择变更时索引无效: {current_row}, 规则总数: {len(self.engine.rules)}")
                # 清除无效选择
                self.rule_list.clearSelection()
                self.guide_label.show()
                self.stacked_widget.hide()
                self.current_rule = None
                return

            # 调用原有的规则选择处理逻辑
            self.on_rule_selected(current_item)

        except Exception as e:
            logging.error(f"处理规则选择变更时出错: {e}", exc_info=True)

    def load_keyword_rule(self, rule):
        """加载关键词策略到表单"""
        self.current_strategy_type = 'keywords'

        # 显示关键词策略卡片
        self.guide_label.hide()
        self.stacked_widget.show()
        self.stacked_widget.setCurrentWidget(self.keyword_card)

        # 填充表单数据
        self.edit_rule_name.setText(rule.get('rule_name', ''))

        match_conditions = rule.get('match_conditions', {})
        self.edit_city.setText(match_conditions.get('city', ''))

        cinema_keywords = match_conditions.get('cinema_keywords', [])
        self.edit_cinema_keywords.setText(', '.join(cinema_keywords))

        hall_logic = rule.get('hall_logic', {})
        hall_mode = hall_logic.get('mode', 'INCLUDE')

        if hall_mode == 'ALL':
            self.radio_all.setChecked(True)
        elif hall_mode == 'INCLUDE':
            self.radio_include.setChecked(True)
        else:
            self.radio_exclude.setChecked(True)

        hall_list = hall_logic.get('hall_list', [])
        self.edit_hall_list.setText(', '.join(hall_list))

        self.edit_cost.setText(str(hall_logic.get('cost', 0)))

        profit_logic = rule.get('profit_logic', {})
        self.edit_min_profit.setText(str(profit_logic.get('min_profit_threshold', 0)))

        self.checkbox_enabled.setChecked(rule.get('enabled', True))

    def load_whitelist_rule(self, rule):
        """【净化】加载白名单策略到表单 - 移除成本和利润字段处理"""
        self.current_strategy_type = 'whitelist'

        # 显示白名单策略卡片
        self.guide_label.hide()
        self.stacked_widget.show()
        self.stacked_widget.setCurrentWidget(self.whitelist_card)

        # 填充表单数据
        self.edit_whitelist_rule_name.setText(rule.get('rule_name', ''))

        match_conditions = rule.get('match_conditions', {})
        self.edit_whitelist_city.setText(match_conditions.get('city', ''))

        # 【净化】移除成本价和最低利润的加载，白名单策略不需要这些字段

        # 加载高级筛选规则
        filter_logic = rule.get('filter_logic', {})

        # 【人性化升级】票数筛选 - 新的5个模板加载逻辑
        ticket_counts = filter_logic.get('ticket_counts', [])
        self.checkbox_ticket_1.setChecked(1 in ticket_counts)
        self.checkbox_ticket_2.setChecked(2 in ticket_counts)
        self.checkbox_ticket_3.setChecked(3 in ticket_counts)
        self.checkbox_ticket_4.setChecked(4 in ticket_counts)
        self.checkbox_ticket_5_plus.setChecked(any(x >= 5 for x in ticket_counts))

        # 价格范围
        price_range = filter_logic.get('price_range', {'min': 0, 'max': 200})
        self.spin_min_price.setValue(price_range.get('min', 0))
        self.spin_max_price.setValue(price_range.get('max', 200))

        # 最低竞标价
        self.edit_whitelist_min_bid.setValue(filter_logic.get('min_bid_price', 0))

        self.checkbox_whitelist_enabled.setChecked(rule.get('enabled', True))

        # 加载影院数量
        policy_id = rule.get('rule_id')
        if policy_id:
            self.current_policy_id = policy_id
            cinema_count = self.engine.get_whitelist_cinema_count(policy_id)
            self.label_cinema_count.setText(f"已从数据库加载 {cinema_count} 个影院")

    def init_worker_thread(self):
        """初始化后台工作线程"""
        try:
            # 创建工作线程
            self.worker_thread = QThread()
            self.worker = Worker(self.engine)

            # 将Worker移动到线程中
            self.worker.moveToThread(self.worker_thread)

            # 连接信号
            self.worker_thread.started.connect(self.worker.run)
            self.worker.new_opportunity.connect(self.on_new_opportunity)
            self.worker.status_update.connect(self.on_status_update)
            self.worker.cycle_finished.connect(self.on_cycle_finished)

            # 启动线程
            self.worker_thread.start()

            logging.info("后台工作线程已启动")

        except Exception as e:
            logging.error(f"启动后台工作线程失败: {e}")

    def on_new_opportunity(self, opportunity_data):
        """处理新的抢单机会"""

        # 【第一步：建立语音处理的安全框架】
        try:
            # 日志记录，用于未来调试
            logging.info("MainWindow收到新机会，准备调用语音模块...")

            # 【第二步：实现差异化的播报文本生成】
            # 从opportunity_data字典中获取type字段的值
            opportunity_type = opportunity_data.get('type', opportunity_data.get('strategy_type', 'unknown'))

            if opportunity_type == 'whitelist':
                # 白名单策略的播报逻辑
                platform = opportunity_data.get('platform', '未知平台')
                alert_text = f"{platform}，白名单订单来了"

            elif opportunity_type == 'keyword' or opportunity_type == 'keywords':
                # 关键词策略的播报逻辑
                platform = opportunity_data.get('platform', '未知平台')
                profit = opportunity_data.get('profit', opportunity_data.get('total_profit'))

                # 检查profit字段是否存在且不为None
                if profit is not None:
                    try:
                        # 安全地将profit转换为保留两位小数的字符串
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

        # 【第四步：确保UI更新逻辑的执行】
        # 以下是原有的UI表格更新代码
        try:
            # 添加到表格
            row_position = self.opportunities_table.rowCount()
            self.opportunities_table.insertRow(row_position)

            # 填充数据
            order = opportunity_data['order']
            items = [
                opportunity_data['platform'],
                f"{opportunity_data['profit']:.2f}元",
                f"{opportunity_data['seat_count']}张",
                opportunity_data['rule_name'],
                order.get('city', ''),
                order.get('cinema_name', ''),
                order.get('hall_type', '')
            ]

            for col, item_text in enumerate(items):
                item = QTableWidgetItem(str(item_text))

                # 设置利润列的颜色
                if col == 1:  # 利润列
                    item.setForeground(QColor(255, 0, 0))  # 红色

                self.opportunities_table.setItem(row_position, col, item)

            # 自动滚动到最新行
            self.opportunities_table.scrollToBottom()

            # 调整列宽
            self.opportunities_table.resizeColumnsToContents()

            logging.info(f"发现抢单机会: {opportunity_data['platform']} - {opportunity_data['profit']:.2f}元")

        except Exception as e:
            logging.error(f"处理抢单机会失败: {e}")

    def on_status_update(self, status_text):
        """处理状态更新"""
        self.statusBar().showMessage(status_text)

    def on_cycle_finished(self, successful_platforms, total_new_orders):
        """处理轮询周期完成"""
        # 调试日志：记录状态更新的详细信息
        logging.debug(f"🔄 轮询周期完成 - 成功平台: {successful_platforms}, 新订单总数: {total_new_orders}")

        if successful_platforms:
            platforms_text = ", ".join(successful_platforms)
            status_text = f"轮询完成 - {platforms_text} - 新订单: {total_new_orders}"
        else:
            status_text = "轮询完成 - 所有平台都失败"

        self.statusBar().showMessage(status_text)

        # 调试日志：记录最终状态栏显示内容
        logging.debug(f"📱 状态栏更新: {status_text}")

    def closeEvent(self, event):
        """窗口关闭事件"""
        try:
            # 停止后台线程
            if hasattr(self, 'worker_thread') and self.worker_thread.isRunning():
                self.worker_thread.quit()
                self.worker_thread.wait(3000)  # 等待最多3秒

            # 关闭数据库连接
            if hasattr(self, 'db_manager'):
                self.db_manager.close()

            logging.info("应用程序正常退出")
            event.accept()

        except Exception as e:
            logging.error(f"关闭应用程序时发生错误: {e}")
            event.accept()


def main():
    """主函数"""
    # 创建应用程序
    app = QApplication(sys.argv)

    # 创建主窗口
    window = MainWindow()
    window.show()

    # 运行应用程序
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
