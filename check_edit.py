import sys
import os

# 直接读取文件内容
with open('edit/edit.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 检查是否包含新添加的代码
if 'ip_edit' in content and 'port_spin' in content:
    print("✓ 文件已包含IP端口配置代码")
    
    # 查找位置
    pos = content.find('self.ip_edit = QLineEdit')
    if pos > 0:
        # 显示上下文
        start = max(0, pos - 200)
        end = min(len(content), pos + 200)
        context = content[start:end]
        print("\n代码上下文:")
        print(context)
else:
    print("✗ 文件未包含IP端口配置代码")
    print("正在搜索相关关键字...")
    keywords = ['ip_edit', 'port_spin', '网络配置', 'IP地址']
    for kw in keywords:
        if kw in content:
            print(f"  找到 '{kw}'")
        else:
            print(f"  未找到 '{kw}'")
