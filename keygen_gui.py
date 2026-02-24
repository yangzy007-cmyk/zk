#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
注册码生成器（算号器）- GUI版本

用于根据机器ID和过期日期生成注册码
"""

import sys
import hashlib
import string
from datetime import datetime
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QDateEdit, QMessageBox,
    QFormLayout, QGroupBox
)
from PySide6.QtCore import Qt, QDate

class KeygenApp(QMainWindow):
    """算号器GUI应用程序"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle('注册码生成器（算号器）')
        self.setGeometry(100, 100, 400, 300)
        self.setMinimumSize(350, 280)
        
        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建布局
        main_layout = QVBoxLayout(central_widget)
        
        # 创建输入组
        input_group = QGroupBox('输入信息')
        input_layout = QFormLayout()
        
        # 机器ID输入
        self.machine_id_label = QLabel('机器ID:')
        self.machine_id_edit = QLineEdit()
        self.machine_id_edit.setPlaceholderText('请输入8位字母数字组合')
        input_layout.addRow(self.machine_id_label, self.machine_id_edit)
        
        # 过期日期输入
        self.expire_date_label = QLabel('过期日期:')
        self.expire_date_edit = QDateEdit()
        self.expire_date_edit.setCalendarPopup(True)
        self.expire_date_edit.setDate(QDate.currentDate().addYears(1))  # 默认一年后过期
        input_layout.addRow(self.expire_date_label, self.expire_date_edit)
        
        input_group.setLayout(input_layout)
        main_layout.addWidget(input_group)
        
        # 创建生成按钮
        self.generate_button = QPushButton('生成注册码')
        self.generate_button.setStyleSheet('font-size: 14px; padding: 10px;')
        self.generate_button.clicked.connect(self.generate_license)
        main_layout.addWidget(self.generate_button)
        
        # 创建结果组
        self.result_group = QGroupBox('生成结果')
        result_layout = QFormLayout()
        
        # 注册码显示
        self.license_key_label = QLabel('注册码:')
        self.license_key_edit = QLineEdit()
        self.license_key_edit.setReadOnly(True)
        self.license_key_edit.setStyleSheet('background-color: #f0f0f0;')
        result_layout.addRow(self.license_key_label, self.license_key_edit)
        
        # 复制按钮
        self.copy_button = QPushButton('复制注册码')
        self.copy_button.clicked.connect(self.copy_license_key)
        result_layout.addRow(None, self.copy_button)
        
        self.result_group.setLayout(result_layout)
        main_layout.addWidget(self.result_group)
        
        # 添加状态栏
        self.statusBar().showMessage('就绪')
    
    def generate_license(self):
        """生成注册码"""
        # 获取输入
        machine_id = self.machine_id_edit.text().strip()
        expire_date = self.expire_date_edit.date().toString('yyyy-MM-dd')
        
        # 验证输入
        if not self.validate_machine_id(machine_id):
            QMessageBox.warning(self, '错误', '机器ID格式不正确，必须是8位字母数字组合')
            return
        
        # 生成注册码
        license_key = self.generate_license_key(machine_id, expire_date)
        
        if license_key:
            self.license_key_edit.setText(license_key)
            self.statusBar().showMessage('注册码生成成功')
            QMessageBox.information(self, '成功', '注册码生成成功！')
        else:
            QMessageBox.error(self, '错误', '生成注册码失败，请重试')
    
    def generate_license_key(self, machine_id, expire_date):
        """生成注册码
        
        Args:
            machine_id: 机器ID，8位字母数字组合
            expire_date: 过期日期，格式为 "YYYY-MM-DD"
        
        Returns:
            注册码字符串，格式为 XXXX-XXXX-XXXX-XXXX
        """
        try:
            # 组合机器ID和过期日期，添加盐值增加安全性
            salt = "zhongkongkong_secure_salt_2026"
            info_str = f"{salt}|{machine_id}|{expire_date}|{salt}"
            
            # 计算哈希值
            hash_obj = hashlib.sha256(info_str.encode('utf-8'))
            hash_hex = hash_obj.hexdigest()
            
            # 生成注册码（16位字母数字组合）
            chars = string.ascii_uppercase + string.digits
            license_key = []
            
            for i in range(16):
                idx = int(hash_hex[i*2:i*2+2], 16) % len(chars)
                license_key.append(chars[idx])
                
                # 每4位添加一个连字符
                if (i + 1) % 4 == 0 and i < 15:
                    license_key.append('-')
            
            return ''.join(license_key)
        except Exception as e:
            print(f"生成注册码失败: {e}")
            return ""
    
    def validate_machine_id(self, machine_id):
        """验证机器ID格式
        
        Args:
            machine_id: 机器ID
        
        Returns:
            bool: 机器ID格式是否正确
        """
        if len(machine_id) != 8:
            return False
        
        valid_chars = string.ascii_letters + string.digits
        for char in machine_id:
            if char not in valid_chars:
                return False
        
        return True
    
    def copy_license_key(self):
        """复制注册码到剪贴板"""
        license_key = self.license_key_edit.text()
        if license_key:
            clipboard = QApplication.clipboard()
            clipboard.setText(license_key)
            self.statusBar().showMessage('注册码已复制到剪贴板')
            QMessageBox.information(self, '成功', '注册码已复制到剪贴板！')
        else:
            QMessageBox.warning(self, '错误', '没有可复制的注册码')

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = KeygenApp()
    window.show()
    sys.exit(app.exec())
