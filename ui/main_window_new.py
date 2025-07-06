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
    QListWidget, QPushButton, QLineEdit, QRadioButton, QCheckBox,
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
from config import RULES_FILE, API_REQUEST_INTERVAL, ALERT_TEXT_TEMPLATE, HAHA_PLATFORM_NAME, MAHUA_PLATFORM_NAME


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
            
            # 初始化TTS播放器
            tts_player = TTSPlayer()

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
                        
                        if result['success']:
                            successful_platforms.append(platform_name)
                            new_orders = result.get('new_orders', [])
                            total_new_orders += len(new_orders)
                            
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
                                        'order': match_result['order_details']
                                    }
                                    
                                    # 发送信号到主窗口
                                    self.new_opportunity.emit(opportunity_data)
                                    
                                    # 播放语音提醒
                                    alert_text = ALERT_TEXT_TEMPLATE.format(
                                        platform=platform_name,
                                        profit=match_result['total_profit']
                                    )
                                    tts_player.play_alert(alert_text)

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
        """初始化主窗口"""
        super().__init__()
        
        # 初始化数据库管理器
        self.db_manager = DatabaseManager()
        
        # 初始化规则引擎
        self.engine = RuleEngine(RULES_FILE, self.db_manager)
        
        # 当前编辑的规则
        self.current_rule = None
        self.current_strategy_type = None  # 'keywords' 或 'whitelist'
        
        # 设置窗口属性
        self.setWindowTitle("抢单提醒系统 - 多元化策略引擎")
        self.setGeometry(100, 100, 1400, 900)

        # 创建UI
        self.init_ui()

        # 连接信号与槽
        self.connect_signals()

        # 加载规则到编辑器
        self.load_rules_to_editor()

        # 启动后台工作线程
        self.init_worker_thread()

        # 记录应用程序启动
        logging.info("多元化策略引擎启动完成")

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

        # 启用此规则
        self.checkbox_enabled = QCheckBox("启用此规则")
        self.checkbox_enabled.setChecked(True)
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

        # 票数筛选
        ticket_widget = QWidget()
        ticket_layout = QHBoxLayout()

        self.checkbox_ticket_1 = QCheckBox("1张")
        self.checkbox_ticket_2 = QCheckBox("2张")
        self.checkbox_ticket_3 = QCheckBox("3张")
        self.checkbox_ticket_4_plus = QCheckBox("4张及以上")

        # 默认全选
        for checkbox in [self.checkbox_ticket_1, self.checkbox_ticket_2,
                        self.checkbox_ticket_3, self.checkbox_ticket_4_plus]:
            checkbox.setChecked(True)
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

        # 成本价
        self.edit_whitelist_cost = QLineEdit()
        self.edit_whitelist_cost.setPlaceholderText("例如：50.0")
        filter_layout.addRow("成本价:", self.edit_whitelist_cost)

        # 最低竞标价
        self.edit_whitelist_min_bid = QDoubleSpinBox()
        self.edit_whitelist_min_bid.setRange(0, 999)
        self.edit_whitelist_min_bid.setValue(0)
        self.edit_whitelist_min_bid.setSuffix(" 元")
        filter_layout.addRow("最低竞标价:", self.edit_whitelist_min_bid)

        # 最低利润
        self.edit_whitelist_min_profit = QLineEdit()
        self.edit_whitelist_min_profit.setPlaceholderText("例如：8.0")
        filter_layout.addRow("最低利润:", self.edit_whitelist_min_profit)

        filter_group.setLayout(filter_layout)
        form_layout.addRow("", filter_group)

        # 启用此规则
        self.checkbox_whitelist_enabled = QCheckBox("启用此规则")
        self.checkbox_whitelist_enabled.setChecked(True)
        form_layout.addRow("", self.checkbox_whitelist_enabled)

        card_widget.setLayout(form_layout)
        return card_widget

    def add_keyword_rule(self):
        """添加关键词策略"""
        try:
            # 设置当前策略类型
            self.current_strategy_type = 'keywords'
            self.current_rule = None

            # 隐藏引导标签，显示关键词策略卡片
            self.guide_label.hide()
            self.stacked_widget.show()
            self.stacked_widget.setCurrentWidget(self.keyword_card)

            # 清空表单
            self.clear_keyword_form()

            logging.info("开始创建新的关键词策略")
            self.statusBar().showMessage("正在创建新的关键词策略...")

        except Exception as e:
            logging.error(f"添加关键词策略失败: {e}")
            QMessageBox.warning(self, "错误", f"添加关键词策略失败: {e}")

    def add_whitelist_rule(self):
        """添加白名单策略"""
        try:
            # 设置当前策略类型
            self.current_strategy_type = 'whitelist'
            self.current_rule = None

            # 隐藏引导标签，显示白名单策略卡片
            self.guide_label.hide()
            self.stacked_widget.show()
            self.stacked_widget.setCurrentWidget(self.whitelist_card)

            # 清空表单
            self.clear_whitelist_form()

            logging.info("开始创建新的白名单策略")
            self.statusBar().showMessage("正在创建新的白名单策略...")

        except Exception as e:
            logging.error(f"添加白名单策略失败: {e}")
            QMessageBox.warning(self, "错误", f"添加白名单策略失败: {e}")

    def clear_keyword_form(self):
        """清空关键词策略表单"""
        self.edit_rule_name.clear()
        self.edit_city.clear()
        self.edit_cinema_keywords.clear()
        self.edit_hall_list.clear()
        self.edit_cost.clear()
        self.edit_min_profit.clear()
        self.radio_include.setChecked(True)
        self.checkbox_enabled.setChecked(True)

    def clear_whitelist_form(self):
        """清空白名单策略表单"""
        self.edit_whitelist_rule_name.clear()
        self.edit_whitelist_city.clear()
        self.edit_whitelist_cost.clear()
        self.edit_whitelist_min_profit.clear()
        self.edit_whitelist_min_bid.setValue(0)
        self.spin_min_price.setValue(0)
        self.spin_max_price.setValue(200)

        # 重置票数选择
        for checkbox in [self.checkbox_ticket_1, self.checkbox_ticket_2,
                        self.checkbox_ticket_3, self.checkbox_ticket_4_plus]:
            checkbox.setChecked(True)

        self.checkbox_whitelist_enabled.setChecked(True)
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
        """删除选中的规则"""
        try:
            current_item = self.rule_list.currentItem()
            if not current_item:
                QMessageBox.warning(self, "提示", "请先选择要删除的规则")
                return

            rule_name = current_item.text()

            # 确认删除
            reply = QMessageBox.question(
                self, "确认删除",
                f"确定要删除规则 '{rule_name}' 吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply != QMessageBox.StandardButton.Yes:
                return

            # 查找并删除规则
            rule_to_delete = None
            for rule in self.engine.rules:
                if rule.get('rule_name') == rule_name:
                    rule_to_delete = rule
                    break

            if rule_to_delete:
                # 如果是白名单策略，清空数据库中的影院数据
                match_conditions = rule_to_delete.get('match_conditions', {})
                if match_conditions.get('match_mode') == 'whitelist':
                    policy_id = rule_to_delete.get('rule_id')
                    if policy_id:
                        self.db_manager.clear_cinemas_for_policy(policy_id)

                # 从规则列表中删除
                self.engine.rules.remove(rule_to_delete)

                # 保存到文件并刷新UI
                self.save_rules_to_file()
                self.load_rules_to_editor()

                logging.info(f"规则 '{rule_name}' 已被删除")
                self.statusBar().showMessage(f"规则 '{rule_name}' 已删除")
            else:
                QMessageBox.warning(self, "错误", f"未找到规则 '{rule_name}'")

        except Exception as e:
            logging.error(f"删除规则失败: {e}")
            QMessageBox.warning(self, "错误", f"删除规则失败: {e}")

    def save_current_rule(self):
        """保存当前规则"""
        try:
            if self.current_strategy_type == 'keywords':
                self.save_keyword_rule()
            elif self.current_strategy_type == 'whitelist':
                self.save_whitelist_rule()
            else:
                QMessageBox.warning(self, "错误", "请先选择策略类型")
                return

            # 保存到文件并刷新UI
            self.save_rules_to_file()
            self.load_rules_to_editor()

            self.statusBar().showMessage("保存成功！")

        except Exception as e:
            logging.error(f"保存规则失败: {e}")
            QMessageBox.warning(self, "错误", f"保存规则失败: {e}")

    def save_keyword_rule(self):
        """保存关键词策略"""
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

        # 构建规则数据
        if self.current_rule:
            # 更新现有规则
            rule_id = self.current_rule.get('rule_id', str(uuid.uuid4()))
        else:
            # 创建新规则
            rule_id = str(uuid.uuid4())

        new_rule = {
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
            }
        }

        # 添加或更新规则
        if self.current_rule:
            # 更新现有规则
            for i, rule in enumerate(self.engine.rules):
                if rule.get('rule_id') == rule_id:
                    self.engine.rules[i] = new_rule
                    break
        else:
            # 添加新规则
            self.engine.rules.append(new_rule)

        logging.info(f"关键词策略 '{rule_name}' 保存成功")

    def save_whitelist_rule(self):
        """保存白名单策略"""
        # 数据获取与校验
        rule_name = self.edit_whitelist_rule_name.text().strip()
        city = self.edit_whitelist_city.text().strip()
        cost_text = self.edit_whitelist_cost.text().strip()
        min_profit_text = self.edit_whitelist_min_profit.text().strip()

        # 基本校验
        if not rule_name:
            raise ValueError("规则名称不能为空")

        # 检查是否已导入影院数据
        if not hasattr(self, 'current_policy_id'):
            raise ValueError("请先导入影院白名单")

        # 解析数值
        try:
            cost = float(cost_text) if cost_text else 0.0
            min_profit = float(min_profit_text) if min_profit_text else 0.0
        except ValueError:
            raise ValueError("成本价和最低利润必须是有效数字")

        # 构建规则数据
        if self.current_rule:
            rule_id = self.current_rule.get('rule_id', self.current_policy_id)
        else:
            rule_id = self.current_policy_id

        new_rule = {
            'rule_id': rule_id,
            'rule_name': rule_name,
            'enabled': self.checkbox_whitelist_enabled.isChecked(),
            'match_conditions': {
                'match_mode': 'whitelist',
                'city': city
            },
            'hall_logic': {
                'mode': 'ALL',
                'hall_list': [],
                'cost': cost
            },
            'profit_logic': {
                'min_profit_threshold': min_profit
            },
            'filter_logic': {
                'ticket_counts': self.get_selected_ticket_counts(),
                'price_range': {
                    'min': self.spin_min_price.value(),
                    'max': self.spin_max_price.value()
                },
                'min_bid_price': self.edit_whitelist_min_bid.value()
            }
        }

        # 添加或更新规则
        if self.current_rule:
            # 更新现有规则
            for i, rule in enumerate(self.engine.rules):
                if rule.get('rule_id') == rule_id:
                    self.engine.rules[i] = new_rule
                    break
        else:
            # 添加新规则
            self.engine.rules.append(new_rule)

        logging.info(f"白名单策略 '{rule_name}' 保存成功")

    def get_selected_ticket_counts(self):
        """获取选中的票数"""
        selected = []
        if self.checkbox_ticket_1.isChecked():
            selected.append(1)
        if self.checkbox_ticket_2.isChecked():
            selected.append(2)
        if self.checkbox_ticket_3.isChecked():
            selected.append(3)
        if self.checkbox_ticket_4_plus.isChecked():
            selected.extend([4, 5, 6, 7, 8, 9, 10])  # 4张及以上
        return selected

    def save_rules_to_file(self):
        """保存规则到文件"""
        try:
            # 准备保存的数据（不包含影院列表，但包含policy_id）
            rules_to_save = []
            for rule in self.engine.rules:
                rule_copy = rule.copy()
                # 移除运行时生成的字段
                if 'hall_logic' in rule_copy and 'hall_set' in rule_copy['hall_logic']:
                    del rule_copy['hall_logic']['hall_set']
                rules_to_save.append(rule_copy)

            # 保存到文件
            success = self.engine.save_rules(rules_to_save)
            if not success:
                raise Exception("保存规则文件失败")

        except Exception as e:
            logging.error(f"保存规则到文件失败: {e}")
            raise

    def load_rules_to_editor(self):
        """加载规则到编辑器"""
        try:
            # 清空规则列表
            self.rule_list.clear()

            # 添加规则到列表
            for rule in self.engine.rules:
                rule_name = rule.get('rule_name', '未命名规则')
                match_mode = rule.get('match_conditions', {}).get('match_mode', 'keywords')

                # 添加策略类型标识
                if match_mode == 'whitelist':
                    display_name = f"[白名单] {rule_name}"
                else:
                    display_name = f"[关键词] {rule_name}"

                self.rule_list.addItem(display_name)

            logging.info(f"已加载 {len(self.engine.rules)} 条规则到编辑器")

        except Exception as e:
            logging.error(f"加载规则到编辑器失败: {e}")

    def connect_signals(self):
        """连接信号与槽"""
        # 规则列表选择事件
        self.rule_list.itemClicked.connect(self.on_rule_selected)

        # 确保信号连接成功
        logging.info("规则列表点击事件已连接")

    def on_rule_selected(self, item):
        """规则选择事件处理"""
        try:
            # 添加调试信息
            logging.info(f"规则选择事件触发: {item.text()}")

            # 获取规则名称（去掉前缀）
            display_name = item.text()
            if display_name.startswith('[白名单] '):
                rule_name = display_name[6:]  # 去掉 "[白名单] "
            elif display_name.startswith('[关键词] '):
                rule_name = display_name[6:]  # 去掉 "[关键词] "
            else:
                rule_name = display_name

            logging.info(f"解析后的规则名称: {rule_name}")

            # 查找对应的规则
            selected_rule = None
            for rule in self.engine.rules:
                if rule.get('rule_name') == rule_name:
                    selected_rule = rule
                    break

            if not selected_rule:
                logging.warning(f"未找到规则: {rule_name}")
                return

            # 设置当前规则
            self.current_rule = selected_rule
            logging.info(f"当前规则已设置: {selected_rule.get('rule_id')}")

            # 根据策略类型显示对应的编辑卡片
            match_mode = selected_rule.get('match_conditions', {}).get('match_mode', 'keywords')
            logging.info(f"策略类型: {match_mode}")

            if match_mode == 'whitelist':
                logging.info("加载白名单策略")
                self.load_whitelist_rule(selected_rule)
            else:
                logging.info("加载关键词策略")
                self.load_keyword_rule(selected_rule)

        except Exception as e:
            logging.error(f"选择规则失败: {e}")
            import traceback
            traceback.print_exc()

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
        """加载白名单策略到表单"""
        self.current_strategy_type = 'whitelist'

        # 显示白名单策略卡片
        self.guide_label.hide()
        self.stacked_widget.show()
        self.stacked_widget.setCurrentWidget(self.whitelist_card)

        # 填充表单数据
        self.edit_whitelist_rule_name.setText(rule.get('rule_name', ''))

        match_conditions = rule.get('match_conditions', {})
        self.edit_whitelist_city.setText(match_conditions.get('city', ''))

        hall_logic = rule.get('hall_logic', {})
        self.edit_whitelist_cost.setText(str(hall_logic.get('cost', 0)))

        profit_logic = rule.get('profit_logic', {})
        self.edit_whitelist_min_profit.setText(str(profit_logic.get('min_profit_threshold', 0)))

        # 加载高级筛选规则
        filter_logic = rule.get('filter_logic', {})

        # 票数筛选
        ticket_counts = filter_logic.get('ticket_counts', [1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        self.checkbox_ticket_1.setChecked(1 in ticket_counts)
        self.checkbox_ticket_2.setChecked(2 in ticket_counts)
        self.checkbox_ticket_3.setChecked(3 in ticket_counts)
        self.checkbox_ticket_4_plus.setChecked(any(x >= 4 for x in ticket_counts))

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
        if successful_platforms:
            platforms_text = ", ".join(successful_platforms)
            status_text = f"轮询完成 - {platforms_text} - 新订单: {total_new_orders}"
        else:
            status_text = "轮询完成 - 所有平台都失败"

        self.statusBar().showMessage(status_text)

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
