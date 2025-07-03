# 智能抢单决策助手 - 主程序文件
# 项目初始化完成，准备开始开发

import sys
import json
import asyncio
import aiohttp
import random
import time
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QTableWidget,
                             QTableWidgetItem, QVBoxLayout, QWidget, QDialog,
                             QListWidget, QPushButton, QSplitter, QFormLayout,
                             QLineEdit, QRadioButton, QCheckBox, QMenuBar,
                             QHBoxLayout, QButtonGroup, QLabel)
from PyQt6.QtCore import QThread, QObject, pyqtSignal, Qt
from PyQt6.QtGui import QColor, QAction


class RuleEditorWindow(QDialog):
    """规则编辑器窗口类 - 用于管理和编辑抢单规则"""

    def __init__(self):
        """初始化规则编辑器窗口"""
        super().__init__()

        # 设置窗口标题和大小
        self.setWindowTitle("规则编辑器")
        self.resize(800, 600)

        # 初始化UI
        self.init_ui()

    def init_ui(self):
        """初始化用户界面"""
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
        main_splitter.setSizes([240, 560])

        # 设置主布局
        main_layout = QVBoxLayout()
        main_layout.addWidget(main_splitter)
        self.setLayout(main_layout)

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
        self.btn_save_rules = QPushButton("保存所有规则")

        # 设置按钮样式
        for btn in [self.btn_add_rule, self.btn_delete_rule, self.btn_save_rules]:
            btn.setMinimumHeight(35)

        left_layout.addWidget(self.btn_add_rule)
        left_layout.addWidget(self.btn_delete_rule)
        left_layout.addWidget(self.btn_save_rules)

        # 连接按钮信号
        self.btn_add_rule.clicked.connect(self.add_new_rule)
        self.btn_delete_rule.clicked.connect(self.delete_rule)
        self.btn_save_rules.clicked.connect(self.save_all_rules)

        left_widget.setLayout(left_layout)
        return left_widget

    def create_right_panel(self):
        """创建右侧面板"""
        right_widget = QWidget()
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

        right_widget.setLayout(form_layout)
        return right_widget

    def add_new_rule(self):
        """添加新规则"""
        print("添加新规则")
        # TODO: 实现添加新规则逻辑

    def delete_rule(self):
        """删除规则"""
        print("删除规则")
        # TODO: 实现删除规则逻辑

    def save_all_rules(self):
        """保存所有规则"""
        print("保存所有规则")
        # TODO: 实现保存规则逻辑


class Worker(QObject):
    """后台工作线程类 - 负责异步处理订单监控和规则匹配"""

    # 定义自定义信号，用于向主窗口发送抢单机会数据
    new_opportunity = pyqtSignal(dict)

    def run(self):
        """后台任务主方法"""
        # 实例化规则引擎
        engine = RuleEngine('rules.json')

        async def main_loop():
            """主要的异步循环，模拟持续抓取订单"""
            print("🚀 后台监控线程启动...")

            # 模拟订单数据的基础模板
            cities = ['北京', '上海', '广州', '深圳', '杭州']
            cinema_templates = [
                '{}CBD万达影城',
                '{}万达影城',
                '{}大悦城影城',
                '{}购物中心影城'
            ]
            hall_types = ['IMAX厅', 'imax厅', '激光IMAX厅', '普通厅', '4DX厅', 'VIP厅']

            while True:
                try:
                    # 生成随机的模拟订单
                    city = random.choice(cities)
                    cinema_template = random.choice(cinema_templates)
                    cinema_name = cinema_template.format(city)
                    hall_type = random.choice(hall_types)
                    bidding_price = round(random.uniform(45.0, 80.0), 1)

                    # 创建模拟订单
                    order = {
                        'city': city,
                        'cinema_name': cinema_name,
                        'hall_type': hall_type,
                        'bidding_price': bidding_price,
                        'show_time': f"{random.randint(9, 22)}:{random.randint(0, 5)*10:02d}",
                        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }

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

                    # 控制抓取频率，模拟真实抓取间隔
                    await asyncio.sleep(1)

                except Exception as e:
                    print(f"❌ 后台处理出错: {e}")
                    await asyncio.sleep(2)

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

        # 创建菜单栏
        self.init_menu_bar()

        # 创建核心UI组件
        self.init_ui()

        # 启动后台工作线程
        self.init_worker_thread()

    def init_ui(self):
        """初始化用户界面"""
        # 创建状态栏
        self.statusBar().showMessage("系统准备就绪...")

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

        # 创建中心布局
        central_widget = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(self.table)
        central_widget.setLayout(layout)

        # 设置中心部件
        self.setCentralWidget(central_widget)

    def init_worker_thread(self):
        """初始化后台工作线程"""
        # 创建线程和工作对象
        self.thread = QThread()
        self.worker = Worker()

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

    def init_menu_bar(self):
        """初始化菜单栏"""
        # 创建菜单栏
        menubar = self.menuBar()

        # 创建"设置"菜单
        settings_menu = menubar.addMenu("设置")

        # 创建"配置规则..."动作
        rule_config_action = QAction("配置规则...", self)
        rule_config_action.setStatusTip("打开规则编辑器")
        rule_config_action.triggered.connect(self.open_rule_editor)

        # 添加动作到菜单
        settings_menu.addAction(rule_config_action)

    def open_rule_editor(self):
        """打开规则编辑器"""
        try:
            # 创建规则编辑器窗口实例
            rule_editor = RuleEditorWindow()

            # 以模态对话框形式显示
            rule_editor.exec()

        except Exception as e:
            print(f"❌ 打开规则编辑器时出错: {e}")


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
