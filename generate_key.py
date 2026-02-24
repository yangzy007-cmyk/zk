#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成注册码（使用与服务端相同的算法）
"""

import hashlib
import string
import sys

def generate_license_key(machine_id, expire_date):
    """生成注册码
    
    Args:
        machine_id: 机器ID
        expire_date: 过期日期，格式为 "YYYY-MM-DD"
    
    Returns:
        注册码字符串
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

def main():
    """主函数"""
    if len(sys.argv) != 3:
        print("使用方法: python generate_key.py <机器ID> <过期日期>")
        print("示例: python generate_key.py npN0VN12 2026-02-20")
        return
    
    machine_id = sys.argv[1]
    expire_date = sys.argv[2]
    
    print(f"机器ID: {machine_id}")
    print(f"过期日期: {expire_date}")
    
    # 生成注册码
    license_key = generate_license_key(machine_id, expire_date)
    print(f"生成的注册码: {license_key}")

if __name__ == '__main__':
    main()
