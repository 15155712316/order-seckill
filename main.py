# 智能抢单决策助手 - 主程序文件
# 项目初始化完成，准备开始开发

import sys
import json
import asyncio
import aiohttp
import random
import time
import uuid
import collections
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QTableWidget,
                             QTableWidgetItem, QVBoxLayout, QWidget, QTabWidget,
                             QListWidget, QPushButton, QSplitter, QFormLayout,
                             QLineEdit, QRadioButton, QCheckBox,
                             QHBoxLayout, QButtonGroup, QLabel, QMessageBox)
from PyQt6.QtCore import QThread, QObject, pyqtSignal, Qt
from PyQt6.QtGui import QColor


class DataFetcher:
    """数据获取器类 - 负责从API获取订单数据并去重"""

    def __init__(self):
        """初始化数据获取器"""
        # 用于去重的双端队列，最多保存500个已见过的订单ID
        self.seen_order_ids = collections.deque(maxlen=500)

    async def fetch_latest_orders(self):
        """
        获取最新订单数据（模拟API调用）

        Returns:
            list: 经过去重的新订单列表
        """
        # 模拟API调用 - 创建包含重复和新订单的样本列表
        mock_api_response = [
            # 一些可能重复的订单
            {
                'order_id': 'order_001',
                'city': '北京',
                'cinema_name': '北京CBD万达影城',
                'hall_type': 'IMAX厅',
                'bidding_price': 65.0,
                'show_time': '14:30',
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            },
            {
                'order_id': 'order_002',
                'city': '上海',
                'cinema_name': '上海万达影城',
                'hall_type': '普通厅',
                'bidding_price': 45.0,
                'show_time': '16:00',
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            },
            {
                'order_id': 'order_003',
                'city': '北京',
                'cinema_name': '北京CBD万达影城',
                'hall_type': '激光IMAX厅',
                'bidding_price': 70.0,
                'show_time': '19:30',
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            },
            # 随机生成一些新订单
            {
                'order_id': f'order_{random.randint(1000, 9999)}',
                'city': random.choice(['北京', '上海', '广州', '深圳']),
                'cinema_name': f'{random.choice(["北京", "上海", "广州"])}CBD万达影城',
                'hall_type': random.choice(['IMAX厅', '激光IMAX厅', '普通厅', '4DX厅']),
                'bidding_price': round(random.uniform(40.0, 80.0), 1),
                'show_time': f"{random.randint(9, 22)}:{random.randint(0, 5)*10:02d}",
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            },
            {
                'order_id': f'order_{random.randint(1000, 9999)}',
                'city': random.choice(['北京', '上海', '广州', '深圳']),
                'cinema_name': f'{random.choice(["北京", "上海", "广州"])}万达影城',
                'hall_type': random.choice(['IMAX厅', '激光IMAX厅', '普通厅']),
                'bidding_price': round(random.uniform(40.0, 80.0), 1),
                'show_time': f"{random.randint(9, 22)}:{random.randint(0, 5)*10:02d}",
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        ]

        # 去重逻辑
        new_orders = []

        for order in mock_api_response:
            order_id = order.get('order_id')

            # 检查订单ID是否已经见过
            if order_id not in self.seen_order_ids:
                # 新订单：添加到结果列表并记录ID
                new_orders.append(order)
                self.seen_order_ids.append(order_id)

        # 模拟网络延迟
        await asyncio.sleep(0.1)

        return new_orders


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
            print("🚀 后台监控线程启动...")

            # 实例化数据获取器
            fetcher = DataFetcher()

            while True:
                try:
                    # 调用API获取最新订单（经过去重）
                    latest_orders = await fetcher.fetch_latest_orders()

                    # 遍历新订单并检查规则匹配
                    for order in latest_orders:
                        # 使用规则引擎检查订单
                        result = engine.check_order(order)

                        # 如果匹配成功，发射信号
                        if result is not None:
                            # 添加时间戳和场次信息到结果中
                            result['timestamp'] = order['timestamp']
                            result['show_time'] = order['show_time']

                            print(f"✅ 发现抢单机会: {result['rule_name']} - 利润{result['profit']:.1f}元")

                            # 发射信号到主窗口
                            self.new_opportunity.emit(result)

                    # 控制API调用频率
                    await asyncio.sleep(2)

                except Exception as e:
                    print(f"❌ 后台处理出错: {e}")
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
        self.engine = RuleEngine('rules.json')

        # 连接信号与槽
        self.connect_signals()

        # 加载规则到编辑器
        self.load_rules_to_editor()

        # 启动后台工作线程
        self.init_worker_thread()

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

            print("✅ 已清空表单，可以输入新规则")
            self.statusBar().showMessage("请填写新规则信息，然后点击'保存'")

        except Exception as e:
            print(f"❌ 添加新规则时出错: {e}")

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

            print(f"✅ 已删除规则: {rule_name}")
            self.statusBar().showMessage(f"规则 '{rule_name}' 已删除")

        except Exception as e:
            print(f"❌ 删除规则时出错: {e}")
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

                print(f"✅ 已更新规则: {rule_name}")

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
                print(f"✅ 已新增规则: {rule_name}")

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

        except Exception as e:
            print(f"❌ 保存规则时出错: {e}")
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
            with open('rules.json', 'w', encoding='utf-8') as f:
                json.dump(rules_to_save, f, ensure_ascii=False, indent=2)

            print("✅ 规则已保存到文件")

        except Exception as e:
            print(f"❌ 保存规则到文件时出错: {e}")
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

            print(f"✅ 已加载 {len(self.engine.rules)} 条规则到编辑器")

        except Exception as e:
            print(f"❌ 加载规则到编辑器时出错: {e}")

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
                print(f"❌ 未找到规则: {rule_name}")
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

            print(f"✅ 已显示规则详情: {rule_name}")

        except Exception as e:
            print(f"❌ 显示规则详情时出错: {e}")

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
            profit = opportunity_data.get('profit', 0)
            profit_item = QTableWidgetItem(f"{profit:.1f}元")
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
            self.statusBar().showMessage(f"发现 {total_opportunities} 个抢单机会，最新利润：{profit:.1f}元")

        except Exception as e:
            print(f"❌ 添加数据到表格时出错: {e}")

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



if __name__ == "__main__":
    # 创建PyQt6应用程序
    app = QApplication(sys.argv)

    # 创建主窗口
    window = MainWindow()

    # 显示窗口
    window.show()

    # 启动事件循环
    sys.exit(app.exec())
