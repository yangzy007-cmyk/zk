#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试 PySide6 导入"""

import sys
print(f"Python: {sys.executable}")
print(f"Version: {sys.version}")
print()

try:
    from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
    print("✓ PySide6.QtWidgets 导入成功")
except ImportError as e:
    print(f"✗ PySide6.QtWidgets 导入失败: {e}")

try:
    from PySide6.QtGui import QIcon, QAction
    print("✓ PySide6.QtGui 导入成功")
except ImportError as e:
    print(f"✗ PySide6.QtGui 导入失败: {e}")

try:
    from PySide6.QtCore import Qt, QThread, Signal
    print("✓ PySide6.QtCore 导入成功")
except ImportError as e:
    print(f"✗ PySide6.QtCore 导入失败: {e}")

print()
print("测试完成")
