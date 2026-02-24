# -*- coding: utf-8 -*-
# 测试代码是否在文件中

with open('g:\python\zhonkgongkong\edit\edit.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 检查关键代码
if 'IP 地址:' in content and 'switch_ip_edit' in content:
    print("✓ 代码确实在文件中！")
    # 找到位置
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if 'IP 地址:' in line:
            print(f"  找到 'IP 地址:' 在第 {i+1} 行")
        if 'switch_ip_edit' in line:
            print(f"  找到 'switch_ip_edit' 在第 {i+1} 行: {line.strip()}")
else:
    print("✗ 代码不在文件中！")

print(f"\n文件总行数: {len(content.split(chr(10)))}")
