# -*- coding: utf-8 -*-
import sys

# 读取原文件
with open('g:\python\zhonkgongkong\edit\edit.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 检查是否包含网络设置
if '网络设置' in content:
    print("文件已包含网络设置代码")
else:
    print("文件不包含网络设置代码")

# 检查文件编码
print(f"文件长度: {len(content)} 字符")
print(f"前100个字符: {content[:100]}")
