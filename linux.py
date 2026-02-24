#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Linux服务器实现，提供网页H5界面和UDP指令发送功能
"""

import os
import sys
import json
import configparser
import socket
import threading
import time
import logging
import hashlib
import random
import string
from flask import Flask, render_template, request, jsonify, send_from_directory

# 系统托盘图标支持（仅在Windows下启用，使用PySide6）
TRAY_SUPPORT = False
if sys.platform == 'win32':
    try:
        from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
        from PySide6.QtGui import QIcon, QAction
        from PySide6.QtCore import Qt, QThread, Signal
        TRAY_SUPPORT = True
        print("[系统] Windows系统，系统托盘功能已启用(PySide6)")
    except ImportError as e:
        print(f"[系统] 导入PySide6失败: {e}")
        TRAY_SUPPORT = False
        print("[系统] 警告: 未找到PySide6，系统托盘功能不可用")
else:
    print(f"[系统] {sys.platform}系统，系统托盘功能已禁用")

# 配置日志
def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('server.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

# 配置文件路径
CONFIG = "config.ini"
DATA_DIR = "data"
DEFAULT_RES = {'width': 1920, 'height': 1080}

# 改进的许可证文件保存逻辑
import os
import platform
import hashlib
import string
import random

# 缓存文件名，确保整个程序使用相同的文件名
cached_filename = None
cached_timestamp_filename = None

# 生成系统风格的文件名
def generate_system_style_filename(is_timestamp=False):
    """生成系统风格的文件名，确保整个程序使用相同的文件名"""
    global cached_filename, cached_timestamp_filename
    
    # 选择要使用的缓存变量
    cache_var = cached_timestamp_filename if is_timestamp else cached_filename
    if cache_var is None:
        # 基于机器ID生成文件名，确保一致性
        machine_id = get_machine_id()
        # 系统风格的文件名前缀
        prefixes = ['System', 'config', 'setup', 'service', 'update', 'driver']
        # 系统风格的文件扩展名
        extensions = ['.dll', '.sys', '.ini', '.dat', '.cfg']
        
        # 使用机器ID的哈希值选择前缀和扩展名，确保一致性
        hash_val = int(hashlib.md5((machine_id + ('_timestamp' if is_timestamp else '')).encode()).hexdigest(), 16)
        prefix = prefixes[hash_val % len(prefixes)]
        extension = extensions[hash_val % len(extensions)]
        
        # 生成基于机器ID的后缀，确保一致性
        suffix = hashlib.md5((machine_id + ('_suffix' if is_timestamp else '')).encode()).hexdigest()[:6]
        
        # 组合成文件名
        filename = f"{prefix}{suffix}{extension}"
        
        # 缓存文件名
        if is_timestamp:
            cached_timestamp_filename = filename
        else:
            cached_filename = filename
        
        return filename
    return cache_var

# 根据系统类型确定基础目录
def get_base_license_dir():
    """获取基础许可证目录"""
    system_type = platform.system()
    if system_type == 'Windows':
        # Windows系统：使用AppData目录
        appdata_dir = os.environ.get('APPDATA', os.path.join(os.path.expanduser('~'), 'AppData', 'Roaming'))
        return os.path.join(appdata_dir, 'Microsoft', 'Windows', 'Templates', 'System')
    else:
        # Linux系统：使用更常见的隐藏目录
        return os.path.join(os.path.expanduser('~'), '.config', 'local')

# 缓存机器ID，确保整个程序使用相同的机器ID
cached_machine_id = None

# 生成8位字母数字组合的机器ID
def get_machine_id():
    """生成8位字母数字组合的机器ID
    
    基于设备的硬件信息，确保更换设备后ID会变化，重做系统后ID保持不变
    """
    global cached_machine_id
    # 如果已经有缓存的机器ID，直接返回
    if cached_machine_id:
        return cached_machine_id
    
    try:
        # 获取系统信息作为基础
        system_info = []
        
        # 获取系统类型
        import platform
        system_type = platform.system()
        system_info.append(system_type)
        
        # 确保至少有一个稳定的标识符
        has_stable_info = False
        
        if system_type == 'Linux':
            # Linux系统，使用硬件信息
            # 1. 尝试读取 CPU 信息（更稳定的部分）
            try:
                with open('/proc/cpuinfo', 'r', encoding='utf-8') as f:
                    cpuinfo = f.read()
                    # 提取处理器型号和序列号
                    cpu_model = ''
                    cpu_serial = ''
                    for line in cpuinfo.split('\n'):
                        if line.startswith('model name'):
                            cpu_model = line
                        elif line.startswith('serial'):
                            cpu_serial = line
                    if cpu_model or cpu_serial:
                        system_info.append(cpu_model)
                        system_info.append(cpu_serial)
                        has_stable_info = True
            except Exception:
                pass
            
            # 2. 尝试读取硬盘信息（更稳定的标识符）
            try:
                import os
                if os.path.exists('/dev/disk/by-id'):
                    disk_ids = os.listdir('/dev/disk/by-id')[:5]  # 只取前5个
                    if disk_ids:
                        system_info.append(str(disk_ids))
                        has_stable_info = True
            except Exception:
                pass
            
            # 3. 尝试读取主板信息
            try:
                import subprocess
                result = subprocess.run(['dmidecode', '-t', 'baseboard'], 
                                     capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    # 提取主板型号和序列号
                    board_info = result.stdout[:1000]  # 只取前1000个字符
                    if board_info:
                        system_info.append(board_info)
                        has_stable_info = True
            except Exception:
                pass
            
            # 4. 尝试读取MAC地址
            try:
                import uuid
                mac = uuid.getnode()
                system_info.append(str(mac))
                has_stable_info = True
            except Exception:
                pass
        else:
            # Windows系统
            # 获取MAC地址
            try:
                import uuid
                mac = uuid.getnode()
                system_info.append(str(mac))
                has_stable_info = True
            except Exception:
                pass
            
            # 尝试获取CPU信息
            try:
                import subprocess
                result = subprocess.run(['wmic', 'cpu', 'get', 'name,serialnumber'], 
                                     capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    cpu_info = result.stdout.strip()
                    if cpu_info:
                        system_info.append(cpu_info)
                        has_stable_info = True
            except Exception:
                pass
            
            # 尝试获取硬盘信息
            try:
                import subprocess
                result = subprocess.run(['wmic', 'diskdrive', 'get', 'model,serialnumber'], 
                                     capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    disk_info = result.stdout.strip()
                    if disk_info:
                        system_info.append(disk_info)
                        has_stable_info = True
            except Exception:
                pass
        
        # 如果没有获取到任何稳定信息，使用系统类型和时间戳的哈希作为最后的保障
        # 这样即使在极端情况下，也能生成相对稳定的ID（至少在同一系统重启前是稳定的）
        if not has_stable_info:
            import time
            # 使用系统类型和启动时间的哈希
            boot_time = int(time.time() // 3600)  # 以小时为单位的时间戳，减少变化频率
            fallback_info = f"{system_type}|{boot_time}"
            system_info.append(fallback_info)
        
        # 组合系统信息
        info_str = "|".join(system_info)
        
        # 计算哈希值
        hash_obj = hashlib.sha256(info_str.encode('utf-8'))
        hash_hex = hash_obj.hexdigest()
        
        # 从哈希值中提取8位字母数字组合
        # 确保包含字母和数字
        chars = string.ascii_letters + string.digits
        machine_id = []
        
        # 遍历哈希值，选择合适的字符
        for i in range(8):
            if i == 0:
                # 第一位确保是字母
                idx = int(hash_hex[i*2:i*2+2], 16) % len(string.ascii_letters)
                machine_id.append(string.ascii_letters[idx])
            else:
                idx = int(hash_hex[i*2:i*2+2], 16) % len(chars)
                machine_id.append(chars[idx])
        
        # 确保至少有一个数字
        has_digit = any(c.isdigit() for c in machine_id)
        if not has_digit:
            # 如果没有数字，将最后一位替换为基于哈希的数字
            digit_idx = int(hash_hex[-2:], 16) % len(string.digits)
            machine_id[-1] = string.digits[digit_idx]
        
        final_id = ''.join(machine_id)
        # 缓存机器ID
        cached_machine_id = final_id
        logger.info(f"生成机器ID: {final_id}")
        return final_id
    except Exception as e:
        logger.error(f"生成机器ID失败: {e}")
        # 即使发生异常，也不要生成随机ID，而是基于系统类型和固定值生成一个稳定的ID
        import uuid
        import platform
        fallback_hash = hashlib.sha256(f"{platform.system()}|fallback|{uuid.getnode()}".encode('utf-8')).hexdigest()
        chars = string.ascii_letters + string.digits
        machine_id = []
        for i in range(8):
            if i == 0:
                idx = int(fallback_hash[i*2:i*2+2], 16) % len(string.ascii_letters)
                machine_id.append(string.ascii_letters[idx])
            else:
                idx = int(fallback_hash[i*2:i*2+2], 16) % len(chars)
                machine_id.append(chars[idx])
        # 确保至少有一个数字
        has_digit = any(c.isdigit() for c in machine_id)
        if not has_digit:
            digit_idx = int(fallback_hash[-2:], 16) % len(string.digits)
            machine_id[-1] = string.digits[digit_idx]
        final_id = ''.join(machine_id)
        # 缓存机器ID
        cached_machine_id = final_id
        logger.info(f"使用fallback生成机器ID: {final_id}")
        return final_id

# 生成难以发现的许可证目录和文件路径
def get_license_paths():
    """生成许可证文件和时间戳文件的路径，将两个文件放在不同位置增加破解难度"""
    global cached_machine_id
    try:
        # 使用缓存的机器ID，确保路径一致性
        if cached_machine_id is None:
            cached_machine_id = get_machine_id()
        machine_id = cached_machine_id
        
        # 生成系统风格的文件名，更隐蔽
        license_filename = generate_system_style_filename(is_timestamp=False)
        timestamp_filename = generate_system_style_filename(is_timestamp=True)
        
        # 1. 许可证文件放在程序根目录
        license_file = os.path.join(os.getcwd(), license_filename)
        # 移除文件路径日志，增加隐蔽性
        logger.info("许可证文件路径已生成")
        
        # 2. 时间戳文件放在隐蔽位置
        base_dir = get_base_license_dir()
        # 移除目录路径日志，增加隐蔽性
        logger.info("基础时间戳目录已获取")
        
        # 生成基于机器ID的目录名，增加隐蔽性
        dir_hash = hashlib.sha256((machine_id + '_dir_salt').encode()).hexdigest()[:16]
        
        # 简化目录结构，确保能够成功创建
        timestamp_dir = base_dir
        # 移除目录路径日志，增加隐蔽性
        logger.info("时间戳目录已生成")
        
        # 构建完整路径
        timestamp_file = os.path.join(timestamp_dir, timestamp_filename)
        # 移除文件路径日志，增加隐蔽性
        logger.info("时间戳文件路径已生成")
        
        return license_file, timestamp_file
    except Exception as e:
        logger.error(f"生成许可证路径失败: {e}")
        # 如果失败，使用备选方案
        if cached_machine_id is None:
            cached_machine_id = get_machine_id()
        machine_id = cached_machine_id
        
        # 1. 许可证文件放在程序根目录
        license_filename = generate_system_style_filename(is_timestamp=False)
        license_file = os.path.join(os.getcwd(), license_filename)
        
        # 2. 时间戳文件放在隐蔽的子目录
        hidden_dir = os.path.join(os.getcwd(), 'System32')  # 模仿系统目录名
        if not os.path.exists(hidden_dir):
            try:
                os.makedirs(hidden_dir, exist_ok=True)
                logger.info(f"创建隐蔽子目录: {hidden_dir}")
            except Exception as dir_error:
                logger.error(f"创建隐蔽子目录失败: {dir_error}")
                # 如果创建目录也失败，回退到当前目录
                hidden_dir = os.getcwd()
        
        timestamp_filename = generate_system_style_filename(is_timestamp=True)
        timestamp_file = os.path.join(hidden_dir, timestamp_filename)
        
        # 移除路径日志，增加隐蔽性
        logger.info("回退到备选路径 - 许可证")
        logger.info("回退到备选路径 - 时间戳")
        return license_file, timestamp_file

# 获取许可证文件路径
LICENSE_FILE, TIMESTAMP_FILE = get_license_paths()
# 确保目录存在
license_dir = os.path.dirname(LICENSE_FILE)
logger.info(f"确保目录存在: {license_dir}")
if not os.path.exists(license_dir):
    try:
        os.makedirs(license_dir, exist_ok=True)
        logger.info(f"目录创建成功: {license_dir}")
    except Exception as e:
        logger.error(f"创建目录失败: {e}")
        # 如果创建目录失败，在当前目录创建隐蔽子目录
        hidden_dir = os.path.join(os.getcwd(), 'System32')
        if not os.path.exists(hidden_dir):
            try:
                os.makedirs(hidden_dir, exist_ok=True)
                logger.info(f"创建隐蔽子目录: {hidden_dir}")
            except Exception as dir_error:
                logger.error(f"创建隐蔽子目录失败: {dir_error}")
                hidden_dir = os.getcwd()
        
        # 生成系统风格的文件名
        license_filename = generate_system_style_filename(is_timestamp=False)
        timestamp_filename = generate_system_style_filename(is_timestamp=True)
        
        LICENSE_FILE = os.path.join(hidden_dir, license_filename)
        TIMESTAMP_FILE = os.path.join(hidden_dir, timestamp_filename)
        logger.warning(f"回退到隐蔽目录: {LICENSE_FILE}")

# 生成注册码
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
        logger.error(f"生成注册码失败: {e}")
        return ""

# 验证注册码
def validate_license_key(machine_id, license_key):
    """验证注册码
    
    Args:
        machine_id: 机器ID
        license_key: 注册码
    
    Returns:
        tuple: (验证结果, 过期日期或错误信息)
    """
    try:
        # 移除连字符
        clean_key = license_key.replace('-', '')
        
        # 检查注册码长度
        if len(clean_key) != 16:
            return False, "注册码格式错误"
        
        # 尝试不同的过期日期（未来100年）
        import datetime
        today = datetime.date.today()
        
        # 首先尝试用户可能使用的日期格式
        # 测试最近的几个日期（今天、明天和后天）
        test_dates = [
            today.strftime("%Y-%m-%d"),
            (today + datetime.timedelta(days=1)).strftime("%Y-%m-%d"),
            (today + datetime.timedelta(days=2)).strftime("%Y-%m-%d"),
        ]
        
        # 测试这些日期
        for date_str in test_dates:
            expected_key = generate_license_key(machine_id, date_str)
            if expected_key.replace('-', '') == clean_key:
                # 检查是否过期
                check_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
                if check_date >= today:
                    return True, date_str
                else:
                    return False, "注册码已过期"
        
        # 测试长期授权的关键日期
        # 生成一系列可能的长期日期
        long_term_dates = []
        # 添加10年后的日期
        long_term_dates.append((today + datetime.timedelta(days=365*10)).strftime("%Y-%m-%d"))
        # 添加20年后的日期
        long_term_dates.append((today + datetime.timedelta(days=365*20)).strftime("%Y-%m-%d"))
        # 添加30年后的日期
        long_term_dates.append((today + datetime.timedelta(days=365*30)).strftime("%Y-%m-%d"))
        # 添加40年后的日期
        long_term_dates.append((today + datetime.timedelta(days=365*40)).strftime("%Y-%m-%d"))
        # 添加50年后的日期
        long_term_dates.append((today + datetime.timedelta(days=365*50)).strftime("%Y-%m-%d"))
        # 添加60年后的日期
        long_term_dates.append((today + datetime.timedelta(days=365*60)).strftime("%Y-%m-%d"))
        # 添加70年后的日期
        long_term_dates.append((today + datetime.timedelta(days=365*70)).strftime("%Y-%m-%d"))
        # 添加80年后的日期
        long_term_dates.append((today + datetime.timedelta(days=365*80)).strftime("%Y-%m-%d"))
        # 添加90年后的日期
        long_term_dates.append((today + datetime.timedelta(days=365*90)).strftime("%Y-%m-%d"))
        # 添加100年后的日期
        long_term_dates.append((today + datetime.timedelta(days=365*100)).strftime("%Y-%m-%d"))
        
        # 测试这些长期日期
        for date_str in long_term_dates:
            expected_key = generate_license_key(machine_id, date_str)
            if expected_key.replace('-', '') == clean_key:
                check_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
                if check_date >= today:
                    return True, date_str
                else:
                    return False, "注册码已过期"
        
        # 测试未来10年内的每一年的关键日期
        for year_offset in range(1, 11):
            current_year = today.year + year_offset
            # 测试每年的几个关键日期
            year_dates = [
                f"{current_year}-01-01",  # 元旦
                f"{current_year}-06-30",  # 半年
                f"{current_year}-12-31",  # 年底
            ]
            for date_str in year_dates:
                expected_key = generate_license_key(machine_id, date_str)
                if expected_key.replace('-', '') == clean_key:
                    check_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
                    if check_date >= today:
                        return True, date_str
                    else:
                        return False, "注册码已过期"
        
        # 测试未来3年内的每一天
        # 这样可以覆盖所有短期和中期授权的情况
        max_days = 365 * 3  # 未来3年
        for days_offset in range(3, max_days):
            check_date = today + datetime.timedelta(days=days_offset)
            date_str = check_date.strftime("%Y-%m-%d")
            expected_key = generate_license_key(machine_id, date_str)
            if expected_key.replace('-', '') == clean_key:
                if check_date >= today:
                    return True, date_str
                else:
                    return False, "注册码已过期"
        
        return False, "注册码无效"
    except Exception as e:
        logger.error(f"验证注册码失败: {e}")
        return False, "验证失败"

# 简单的加密和解密函数
def encrypt_data(data, key):
    """简单的加密函数，支持备选加密方法"""
    try:
        logger.info(f"开始加密数据，数据长度: {len(data)}")
        import base64
        
        # 尝试使用cryptography库
        try:
            from cryptography.fernet import Fernet
            logger.info("使用cryptography.fernet加密")
            
            # 使用key生成加密密钥
            key_hash = hashlib.sha256(key.encode()).digest()
            encoded_key = base64.urlsafe_b64encode(key_hash[:32])
            
            cipher_suite = Fernet(encoded_key)
            encrypted_data = cipher_suite.encrypt(data.encode())
            encoded_encrypted_data = base64.urlsafe_b64encode(encrypted_data).decode()
            
            logger.info("加密数据成功")
            return encoded_encrypted_data
        except ImportError as e:
            logger.warning(f"cryptography.fernet不可用，使用内置加密方法: {e}")
            # 使用内置的简单加密方法作为备选
            return simple_encrypt(data, key)
        except Exception as e:
            logger.warning(f"cryptography.fernet加密失败，使用内置加密方法: {e}")
            # 使用内置的简单加密方法作为备选
            return simple_encrypt(data, key)
    except Exception as e:
        logger.error(f"加密数据失败: {e}")
        import traceback
        logger.error(f"详细错误信息: {traceback.format_exc()}")
        return None

def simple_encrypt(data, key):
    """简单的内置加密方法"""
    try:
        logger.info("使用内置加密方法")
        import base64
        
        # 使用key生成加密密钥
        key_hash = hashlib.sha256(key.encode()).digest()
        
        # 简单的XOR加密
        encrypted = []
        for i, char in enumerate(data):
            key_char = key_hash[i % len(key_hash)]
            encrypted_char = chr(ord(char) ^ key_char)
            encrypted.append(encrypted_char)
        
        encrypted_str = ''.join(encrypted)
        encoded_encrypted_data = base64.urlsafe_b64encode(encrypted_str.encode()).decode()
        
        logger.info("内置加密方法成功")
        return encoded_encrypted_data
    except Exception as e:
        logger.error(f"内置加密方法失败: {e}")
        import traceback
        logger.error(f"详细错误信息: {traceback.format_exc()}")
        return None

def decrypt_data(encrypted_data, key):
    """简单的解密函数，支持备选解密方法"""
    try:
        logger.info(f"开始解密数据，数据长度: {len(encrypted_data)}")
        import base64
        
        # 尝试使用cryptography库解密
        try:
            from cryptography.fernet import Fernet
            logger.info("使用cryptography.fernet解密")
            
            # 使用key生成加密密钥
            key_hash = hashlib.sha256(key.encode()).digest()
            cipher_suite = Fernet(base64.urlsafe_b64encode(key_hash[:32]))
            
            # 解密数据
            decoded_data = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted_data = cipher_suite.decrypt(decoded_data)
            
            logger.info("解密数据成功")
            return decrypted_data.decode()
        except ImportError as e:
            logger.warning(f"cryptography.fernet不可用，使用内置解密方法: {e}")
            # 使用内置的简单解密方法作为备选
            return simple_decrypt(encrypted_data, key)
        except Exception as e:
            logger.warning(f"cryptography.fernet解密失败，使用内置解密方法: {e}")
            # 使用内置的简单解密方法作为备选
            return simple_decrypt(encrypted_data, key)
    except Exception as e:
        logger.error(f"解密数据失败: {e}")
        import traceback
        logger.error(f"详细错误信息: {traceback.format_exc()}")
        return None

def simple_decrypt(encrypted_data, key):
    """简单的内置解密方法"""
    try:
        logger.info("使用内置解密方法")
        import base64
        
        # 解码数据
        decoded_data = base64.urlsafe_b64decode(encrypted_data.encode())
        encrypted_str = decoded_data.decode()
        
        # 使用key生成加密密钥
        key_hash = hashlib.sha256(key.encode()).digest()
        
        # 简单的XOR解密
        decrypted = []
        for i, char in enumerate(encrypted_str):
            key_char = key_hash[i % len(key_hash)]
            decrypted_char = chr(ord(char) ^ key_char)
            decrypted.append(decrypted_char)
        
        decrypted_str = ''.join(decrypted)
        
        logger.info("内置解密方法成功")
        return decrypted_str
    except Exception as e:
        logger.error(f"内置解密方法失败: {e}")
        import traceback
        logger.error(f"详细错误信息: {traceback.format_exc()}")
        return None

# 保存时间戳信息
def save_timestamp_info(machine_id, timestamp):
    """保存时间戳信息到单独的文件"""
    try:
        # 移除文件路径日志，增加隐蔽性
        logger.info("保存时间戳信息")
        # 生成基于机器ID的加密密钥
        timestamp_key = f"{machine_id}_timestamp_key_2026"
        
        # 创建时间戳信息
        timestamp_info = {
            "timestamp": timestamp,
            "checksum": hashlib.sha256((machine_id + str(timestamp)).encode()).hexdigest()
        }
        
        # 转换为JSON字符串
        import json
        timestamp_json = json.dumps(timestamp_info, ensure_ascii=False)
        
        # 加密数据
        encrypted_data = encrypt_data(timestamp_json, timestamp_key)
        if not encrypted_data:
            logger.error("加密时间戳数据失败")
            return False
        
        # 确保目录存在
        timestamp_dir = os.path.dirname(TIMESTAMP_FILE)
        # 移除目录路径日志，增加隐蔽性
        logger.info("时间戳目录已获取")
        if not os.path.exists(timestamp_dir):
            try:
                # 移除目录路径日志，增加隐蔽性
                logger.info("创建时间戳目录")
                os.makedirs(timestamp_dir, exist_ok=True)
                # 移除目录路径日志，增加隐蔽性
                logger.info("创建时间戳目录成功")
            except Exception as dir_error:
                logger.error(f"创建时间戳目录失败: {dir_error}")
                import traceback
                logger.error(f"详细错误信息: {traceback.format_exc()}")
                return False
        else:
            # 移除目录路径日志，增加隐蔽性
            logger.info("时间戳目录已存在")
        
        # 检查目录是否可写
        if not os.access(timestamp_dir, os.W_OK):
            logger.error("时间戳目录不可写")
            return False
        
        # 保存加密数据
        # 移除文件路径日志，增加隐蔽性
        logger.info("保存时间戳文件")
        with open(TIMESTAMP_FILE, 'w', encoding='utf-8') as f:
            f.write(encrypted_data)
        # 移除文件路径日志，增加隐蔽性
        logger.info("保存时间戳文件成功")
        
        logger.info("保存时间戳信息成功")
        return True
    except Exception as e:
        logger.error(f"保存时间戳信息失败: {e}")
        import traceback
        logger.error(f"详细错误信息: {traceback.format_exc()}")
        return False

# 加载时间戳信息
def load_timestamp_info(machine_id):
    """从单独的文件加载时间戳信息"""
    try:
        if not os.path.exists(TIMESTAMP_FILE):
            return None
        
        # 读取加密数据
        with open(TIMESTAMP_FILE, 'r', encoding='utf-8') as f:
            encrypted_data = f.read().strip()
        
        if not encrypted_data:
            return None
        
        # 生成基于机器ID的加密密钥
        timestamp_key = f"{machine_id}_timestamp_key_2026"
        
        # 解密数据
        decrypted_data = decrypt_data(encrypted_data, timestamp_key)
        if not decrypted_data:
            return None
        
        # 解析JSON
        import json
        timestamp_info = json.loads(decrypted_data)
        
        # 验证校验和
        expected_checksum = hashlib.sha256((machine_id + str(timestamp_info['timestamp'])).encode()).hexdigest()
        if timestamp_info.get('checksum') != expected_checksum:
            return None
        
        return timestamp_info
    except Exception as e:
        logger.error(f"加载时间戳信息失败: {e}")
        return None

# 保存许可证信息
def save_license_info(machine_id, license_key, expire_date):
    """保存许可证信息（加密）"""
    try:
        # 生成基于机器ID的加密密钥
        encryption_key = f"{machine_id}_secure_key_2026"
        
        current_time = time.time()
        license_info = {
            "machine_id": machine_id,
            "license_key": license_key,
            "expire_date": expire_date,
            "activated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "timestamp": current_time,  # 保存激活时间戳
            "checksum": hashlib.sha256(f"{machine_id}{license_key}{expire_date}".encode()).hexdigest()  # 校验和
        }
        
        # 转换为JSON字符串
        import json
        license_json = json.dumps(license_info, ensure_ascii=False)
        
        # 加密数据
        encrypted_data = encrypt_data(license_json, encryption_key)
        if not encrypted_data:
            logger.error("加密许可证数据失败")
            return False
        
        # 确保目录存在
        license_dir = os.path.dirname(LICENSE_FILE)
        # 移除目录路径日志，增加隐蔽性
        logger.info("许可证目录已获取")
        if not os.path.exists(license_dir):
            try:
                # 移除目录路径日志，增加隐蔽性
                logger.info("创建许可证目录")
                os.makedirs(license_dir, exist_ok=True)
                # 移除目录路径日志，增加隐蔽性
                logger.info("创建许可证目录成功")
            except Exception as dir_error:
                logger.error(f"创建许可证目录失败: {dir_error}")
                return False
        else:
            # 移除目录路径日志，增加隐蔽性
            logger.info("许可证目录已存在")
        
        # 检查目录是否可写
        if not os.access(license_dir, os.W_OK):
            logger.error("许可证目录不可写")
            return False
        
        # 保存加密数据
        # 移除文件路径日志，增加隐蔽性
        logger.info("保存许可证文件")
        with open(LICENSE_FILE, 'w', encoding='utf-8') as f:
            f.write(encrypted_data)
        # 移除文件路径日志，增加隐蔽性
        logger.info("保存许可证文件成功")
        
        # 保存时间戳到单独的文件
        logger.info(f"保存时间戳信息")
        try:
            if not save_timestamp_info(machine_id, current_time):
                logger.warning("保存时间戳信息失败，尝试备选方案")
                # 时间戳保存失败不影响许可证保存
                # 尝试在当前目录保存时间戳
                try:
                    # 在当前目录创建一个简单的时间戳文件
                    simple_timestamp_file = os.path.join(os.getcwd(), f".{hashlib.md5((machine_id + '_timestamp').encode()).hexdigest()[:8]}.tmp")
                    with open(simple_timestamp_file, 'w', encoding='utf-8') as f:
                        f.write(str(current_time))
                    logger.info("备选时间戳保存成功")
                except Exception as e:
                    logger.warning(f"备选时间戳保存也失败: {e}")
                    # 继续执行，时间戳不是必须的
        except Exception as e:
            logger.warning(f"时间戳保存过程异常: {e}")
        
        # 无论时间戳是否保存成功，只要许可证文件保存成功就算成功
        return True
    except Exception as e:
        logger.error(f"保存许可证信息失败: {e}")
        import traceback
        logger.error(f"详细错误信息: {traceback.format_exc()}")
        return False

# 加载许可证信息
def load_license_info():
    """加载许可证信息（解密）"""
    try:
        if not os.path.exists(LICENSE_FILE):
            return None
        
        # 读取加密数据
        with open(LICENSE_FILE, 'r', encoding='utf-8') as f:
            encrypted_data = f.read().strip()
        
        if not encrypted_data:
            return None
        
        # 获取机器ID用于解密
        machine_id = get_machine_id()
        encryption_key = f"{machine_id}_secure_key_2026"
        
        # 解密数据
        decrypted_data = decrypt_data(encrypted_data, encryption_key)
        if not decrypted_data:
            return None
        
        # 解析JSON
        import json
        license_info = json.loads(decrypted_data)
        
        # 验证校验和
        expected_checksum = hashlib.sha256(f"{license_info['machine_id']}{license_info['license_key']}{license_info['expire_date']}".encode()).hexdigest()
        if license_info.get('checksum') != expected_checksum:
            return None
        
        return license_info
    except Exception as e:
        logger.error(f"加载许可证信息失败: {e}")
        return None

# 许可证状态缓存
_license_cache = None
_license_cache_time = 0
LICENSE_CACHE_INTERVAL = 30  # 许可证检查缓存30秒

# 检查许可证状态
def check_license_status():
    """检查许可证状态（增强的时间篡改检测，带缓存）
    
    Returns:
        tuple: (是否有效, 过期日期或错误信息)
    """
    global _license_cache, _license_cache_time
    
    # 检查缓存
    current_time = time.time()
    if _license_cache is not None and (current_time - _license_cache_time < LICENSE_CACHE_INTERVAL):
        return _license_cache
    
    try:
        # 检查许可证文件是否存在
        if not os.path.exists(LICENSE_FILE):
            _license_cache = (False, "未找到许可证")
            _license_cache_time = current_time
            return _license_cache
        
        license_info = load_license_info()
        if not license_info:
            _license_cache = (False, "未找到许可证")
            _license_cache_time = current_time
            return _license_cache
        
        machine_id = get_machine_id()
        if license_info.get("machine_id") != machine_id:
            _license_cache = (False, "许可证与当前机器不匹配")
            _license_cache_time = current_time
            return _license_cache
        
        # 检查时间篡改
        activation_time = license_info.get("timestamp", 0)
        
        # 1. 检查当前时间是否早于激活时间
        if current_time < activation_time - 3600:  # 允许1小时的误差
            _license_cache = (False, "检测到系统时间被调整，请恢复正确时间后重新注册")
            _license_cache_time = current_time
            return _license_cache
        
        # 2. 从单独的时间戳文件加载信息
        timestamp_info = load_timestamp_info(machine_id)
        if timestamp_info:
            last_timestamp = timestamp_info.get("timestamp", 0)
            # 检查当前时间是否早于上次时间戳
            if current_time < last_timestamp - 3600:  # 允许1小时的误差
                _license_cache = (False, "检测到系统时间被调整，请恢复正确时间后重新注册")
                _license_cache_time = current_time
                return _license_cache
        
        # 3. 检查许可证文件是否被篡改（通过校验和）
        expected_checksum = hashlib.sha256(f"{license_info['machine_id']}{license_info['license_key']}{license_info['expire_date']}".encode()).hexdigest()
        if license_info.get('checksum') != expected_checksum:
            _license_cache = (False, "许可证文件已被篡改，注册失效")
            _license_cache_time = current_time
            return _license_cache
        
        # 4. 检查是否过期
        import datetime
        expire_date_str = license_info.get("expire_date")
        if not expire_date_str:
            _license_cache = (False, "许可证信息不完整")
            _license_cache_time = current_time
            return _license_cache
        
        expire_date = datetime.datetime.strptime(expire_date_str, "%Y-%m-%d").date()
        today = datetime.date.today()
        
        if expire_date < today:
            _license_cache = (False, "许可证已过期")
            _license_cache_time = current_time
            return _license_cache
        
        # 每5分钟更新一次时间戳（避免频繁写文件）
        if timestamp_info:
            last_save_time = timestamp_info.get("timestamp", 0)
            if current_time - last_save_time > 300:  # 5分钟
                try:
                    save_timestamp_info(machine_id, current_time)
                    # 同时更新许可证文件的修改时间
                    if os.path.exists(LICENSE_FILE):
                        os.utime(LICENSE_FILE, (current_time, current_time))
                except Exception:
                    pass  # 时间戳更新失败不影响许可证状态
        
        _license_cache = (True, expire_date_str)
        _license_cache_time = current_time
        return _license_cache
    except Exception as e:
        logger.error(f"检查许可证状态失败: {e}")
        _license_cache = (False, "检查失败")
        _license_cache_time = current_time
        return _license_cache

app = Flask(__name__)
app.static_folder = 'static'

# 优化Flask配置，适合低配置服务器
app.config['TEMPLATES_AUTO_RELOAD'] = False  # 禁用模板自动重载
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 31536000  # 静态文件缓存1年
app.config['JSONIFY_MIMETYPE'] = 'application/json'
app.config['JSON_SORT_KEYS'] = False  # 禁用JSON排序，提高性能

# 禁用Flask的调试日志，减少IO操作
import werkzeug
werkzeug_log = logging.getLogger('werkzeug')
werkzeug_log.setLevel(logging.ERROR)

# 全局配置
config_data = {}

# 开关按钮状态存储
switch_states = {}

# 需要跳过的检测次数（按钮点击后设置为1，检测后减1，为0时正常更新）
pending_skip = {}

# 线程池配置
import concurrent.futures
# 设置线程池大小为64，支持64条并发指令
MAX_WORKERS = 64
thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS)

# 定时任务支持
import threading
import datetime

# 定时任务检查间隔（秒）
SCHEDULE_CHECK_INTERVAL = 10

# 状态检测配置
STATUS_CHECK_INTERVAL = 8  # 状态检测间隔（秒）
STATUS_CHECK_TIMEOUT = 2   # 状态检测超时（秒）

# 定时任务检查线程
def schedule_check_thread():
    """定时检查并执行定时任务"""
    while True:
        try:
            # 检查许可证状态
            valid, message = check_license_status()
            if not valid:
                # 未授权，跳过执行
                logger.info(f"[定时任务] 未授权，跳过执行: {message}")
                time.sleep(SCHEDULE_CHECK_INTERVAL)
                continue
            
            # 加载配置
            cfg = load_cfg()
            schedules = cfg.get('schedules', [])
            
            # 获取当前时间
            now = datetime.datetime.now()
            current_time = now.strftime('%H:%M')
            current_date = now.strftime('%m-%d')
            current_weekday = now.strftime('%A')
            
            # 星期映射
            weekday_map = {
                'Monday': '周一',
                'Tuesday': '周二',
                'Wednesday': '周三',
                'Thursday': '周四',
                'Friday': '周五',
                'Saturday': '周六',
                'Sunday': '周日'
            }
            current_week = weekday_map.get(current_weekday, '')
            
            # 检查每个定时任务
            for schedule in schedules:
                if not schedule.get('enable', True):
                    continue
                
                # 检查时间
                if schedule.get('time', '') != current_time:
                    continue
                
                # 检查日期
                date_match = False
                date = schedule.get('date', '')
                if not date:
                    date_match = True
                elif len(date) == 10:  # yyyy-MM-DD 格式（指定日期）
                    current_full_date = now.strftime('%Y-%m-%d')
                    if date == current_full_date:
                        date_match = True
                elif len(date) == 5:  # MM-DD 格式（每年）
                    if date == current_date:
                        date_match = True
                elif len(date) == 2:  # DD 格式（每月）
                    current_day = now.strftime('%d')
                    current_month = now.month
                    # 检查当前月份是否有该日期
                    try:
                        # 尝试创建一个日期对象来验证
                        test_date = datetime.date(now.year, current_month, int(date))
                        # 如果没有抛出异常，说明日期有效
                        if date == current_day:
                            date_match = True
                    except ValueError:
                        # 日期无效，跳过
                        date_match = False
                
                if not date_match:
                    continue
                
                # 检查星期
                week = schedule.get('week', '')
                if week:
                    # 检查是否是多个星期几（逗号分隔）
                    week_days = week.split(',')
                    if current_week not in week_days:
                        continue
                
                # 执行定时任务
                logger.info(f"[定时任务] 执行定时任务: {schedule.get('name', '')}")
                
                # 创建命令对象
                cmd_type = schedule.get('cmd_type', '指令表')
                cmd_id = schedule.get('cmd_id', '')
                
                if cmd_type == '指令表':
                    # 执行指令表指令
                    cmd = {
                        'type': 'udp',
                        'udp_command_id': cmd_id
                    }
                elif cmd_type == '组指令':
                    # 执行组指令
                    cmd = {
                        'type': 'udp_group',
                        'udp_group_id': cmd_id
                    }
                else:
                    logger.warning(f"[定时任务] 未知指令类型: {cmd_type}")
                    continue
                
                # 执行命令
                execute_command(cmd, cfg.get('udp_commands', []), cfg.get('udp_groups', []))
                
        except Exception as e:
            logger.error(f"[定时任务] 检查定时任务时出错: {e}")
        
        # 等待下一次检查
        time.sleep(SCHEDULE_CHECK_INTERVAL)

# 异步状态检测函数
def check_button_status_async(button, timeout=1):
    """异步检查单个按钮状态 - 使用随机端口，像测试工具一样"""
    try:
        button_id = button.get('id', '未知')
        status_ip = button.get('status_ip', '')
        status_port = button.get('status_port', 5005)
        status_query_cmd = button.get('status_query_cmd', '')
        status_response_cmd = button.get('status_response_cmd', '')
        encoding = button.get('status_encoding', '16进制')
        
        # 检查必要的参数
        if not status_ip or not status_query_cmd:
            logger.warning(f"[状态检测] 按钮 {button_id} 缺少IP或查询指令")
            return button_id, 'off'
        
        logger.info(f"[状态检测] 按钮 {button_id} 配置: IP={status_ip}:{status_port}, 查询='{status_query_cmd}', 期望='{status_response_cmd}', 编码={encoding}")
        
        # 创建 socket（使用随机端口，像测试工具一样）
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(timeout)
        except Exception as e:
            logger.error(f"[状态检测] 按钮 {button_id} 创建 socket 失败: {e}")
            return button_id, 'off'
        
        # 根据编码格式处理指令
        try:
            if encoding == '16进制' or status_query_cmd.startswith('0x'):
                cmd_hex = status_query_cmd.replace('0x', '').replace(' ', '')
                # 尝试作为十六进制解码，如果失败则使用字符串
                try:
                    cmd_bytes = bytes.fromhex(cmd_hex)
                except ValueError:
                    # 不是有效的十六进制，使用字符串编码
                    logger.debug(f"[状态检测] 按钮 {button_id} 指令'{status_query_cmd}'不是有效十六进制，使用字符串编码")
                    cmd_bytes = status_query_cmd.encode('utf-8')
            else:
                cmd_bytes = status_query_cmd.encode('utf-8')
        except Exception as e:
            logger.error(f"[状态检测] 按钮 {button_id} 指令编码失败: {e}")
            sock.close()
            return button_id, 'off'
        
        # 发送查询指令
        try:
            sock.sendto(cmd_bytes, (status_ip, status_port))
        except Exception:
            sock.close()
            return button_id, 'off'
        
        # 接收响应（1秒超时）
        try:
            response, addr = sock.recvfrom(1024)
            response_ip = addr[0]
            
            # 验证响应是否来自目标设备
            if response_ip != status_ip:
                sock.close()
                return button_id, 'off'
            
            # 解析响应
            try:
                response_str = response.decode('utf-8').strip()
            except:
                response_str = response.hex().upper()
            
            # 判断是否匹配期望响应
            # 只有匹配期望响应才是 ON，其他情况都是 OFF
            expected_clean = status_response_cmd.replace(' ', '')
            response_upper = response_str.upper()
            expected_upper = expected_clean.upper()
            is_on = expected_upper in response_upper
            result = 'on' if is_on else 'off'
            
            logger.info(f"[状态检测] 按钮 {button_id}: 查询='{status_query_cmd}' 收到='{response_str}'(大写:{response_upper}) 期望='{expected_clean}'(大写:{expected_upper}) 匹配={is_on} 状态={result}")
            
            sock.close()
            return button_id, result
                
        except socket.timeout:
            # 1秒内未收到响应，认为是关闭状态
            logger.debug(f"[状态检测] 按钮 {button_id} 超时，状态=off")
            sock.close()
            return button_id, 'off'
            
        except Exception as e:
            # 任何错误都认为是关闭状态
            logger.debug(f"[状态检测] 按钮 {button_id} 错误: {e}，状态=off")
            sock.close()
            return button_id, 'off'
            
    except Exception as e:
        logger.error(f"[状态检测] 按钮 {button.get('id', '未知')} 异常: {e}")
        return button.get('id', '未知'), 'off'

# 并发状态检测线程
def status_check_thread():
    """并发状态检测线程"""
    import concurrent.futures
    global switch_states
    
    # 缓存配置，避免每次都重新加载
    cached_cfg = None
    cfg_last_load_time = 0
    
    while True:
        loop_start_time = time.time()
        try:
            # 检查许可证状态（每30秒检查一次，避免频繁文件操作）
            valid, message = check_license_status()
            if not valid:
                logger.info(f"[状态检测] 未授权，跳过执行: {message}")
                time.sleep(STATUS_CHECK_INTERVAL)
                continue
            
            # 加载配置（缓存5秒）
            current_time = time.time()
            if cached_cfg is None or (current_time - cfg_last_load_time > 5):
                cached_cfg = load_cfg()
                cfg_last_load_time = current_time
            
            cfg = cached_cfg
            pages = cfg.get('pages', [])
            
            # 收集所有需要状态检测的按钮
            buttons_to_check = []
            for page in pages:
                for button in page.get('buttons', []):
                    if button.get('status_enable', False):
                        buttons_to_check.append(button)
            
            if buttons_to_check:
                logger.info(f"[状态检测] 开始检测 {len(buttons_to_check)} 个按钮")
                
                # 按 IP 分组按钮
                buttons_by_ip = {}
                for button in buttons_to_check:
                    ip = button.get('status_ip', '')
                    if ip:
                        if ip not in buttons_by_ip:
                            buttons_by_ip[ip] = []
                        buttons_by_ip[ip].append(button)
                
                new_states = {}
                
                # 对不同 IP 的按钮使用线程池并发检测
                def check_ip_buttons(ip, buttons):
                    """检测同一个 IP 下的所有按钮（顺序执行，间隔500ms）"""
                    ip_states = {}
                    for i, button in enumerate(buttons):
                        button_id = button.get('id', '未知')
                        # 同一个 IP 的按钮，间隔 500ms 发送
                        if i > 0:
                            time.sleep(0.5)
                        
                        try:
                            result_id, state = check_button_status_async(button, timeout=1)
                            ip_states[result_id] = state
                        except Exception as e:
                            logger.debug(f"[状态检测] 按钮 {button_id} 检测出错: {e}")
                            ip_states[button_id] = 'off'
                    return ip_states
                
                # 使用线程池并发处理不同 IP
                with concurrent.futures.ThreadPoolExecutor(max_workers=len(buttons_by_ip)) as executor:
                    future_to_ip = {}
                    for ip, buttons in buttons_by_ip.items():
                        future = executor.submit(check_ip_buttons, ip, buttons)
                        future_to_ip[future] = ip
                    
                    # 收集结果
                    for future in concurrent.futures.as_completed(future_to_ip):
                        ip = future_to_ip[future]
                        try:
                            ip_states = future.result()
                            new_states.update(ip_states)
                        except Exception as e:
                            logger.error(f"[状态检测] IP {ip} 检测出错: {e}")
                
                # 更新全局开关状态（跳过需要跳过的按钮）
                updated_count = 0
                skipped_count = 0
                for btn_id, state in new_states.items():
                    if btn_id in pending_skip and pending_skip[btn_id] > 0:
                        # 需要跳过这次检测结果
                        pending_skip[btn_id] -= 1
                        skipped_count += 1
                        logger.info(f"[状态检测] 按钮 {btn_id}: 检测结果 {state} 被跳过（还剩 {pending_skip[btn_id]} 次）")
                        if pending_skip[btn_id] == 0:
                            del pending_skip[btn_id]
                    else:
                        # 正常更新状态
                        switch_states[btn_id] = state
                        updated_count += 1
                        logger.info(f"[状态检测] 按钮 {btn_id}: {state}")
                
                logger.info(f"[状态检测] 完成，更新 {updated_count} 个，跳过 {skipped_count} 个，switch_states现在有{len(switch_states)}个按钮")
            else:
                logger.debug(f"[状态检测] 没有需要检测的按钮")
            
        except Exception as e:
            logger.error(f"[状态检测] 检查状态时出错: {e}")
            import traceback
            logger.error(f"[状态检测] 错误详情: {traceback.format_exc()}")
        
        # 计算实际睡眠时间，确保固定间隔
        elapsed = time.time() - loop_start_time
        sleep_time = max(0, STATUS_CHECK_INTERVAL - elapsed)
        logger.info(f"[状态检测] 本次检测耗时 {elapsed:.2f} 秒，休息 {sleep_time:.2f} 秒")
        if sleep_time > 0:
            time.sleep(sleep_time)

# 启动定时任务检查线程
def start_schedule_thread():
    """启动定时任务检查线程"""
    schedule_thread = threading.Thread(target=schedule_check_thread, daemon=True)
    schedule_thread.start()
    logger.info("[定时任务] 定时任务检查线程已启动")

def full_path(rel_path):
    """获取完整路径"""
    if not rel_path:
        return ''
    if os.path.isabs(rel_path):
        return rel_path
    # 如果路径已经带 data/ 前缀，不再加
    if rel_path.startswith(DATA_DIR + os.sep) or rel_path.startswith(DATA_DIR + '/'):
        return rel_path
    return os.path.join(DATA_DIR, rel_path)


def load_cfg(filename=CONFIG):
    """加载配置文件"""
    config = configparser.ConfigParser()
    config.read(filename, encoding="utf-8")

    # 读取分辨率
    try:
        width = int(config.get("resolution", "width"))
        height = int(config.get("resolution", "height"))
    except Exception:
        width, height = 1920, 1080  # 默认分辨率

    resolution = {
        "width": width,
        "height": height
    }
    
    # 读取全局状态图片设置（在按钮配置之前读取，供按钮使用）
    status_on_src = config.get('global', 'status_on_src', fallback='')
    status_off_src = config.get('global', 'status_off_src', fallback='')

    pages = []
    for section in config.sections():
        if section.lower().startswith("page"):
            try:
                page_num = int(section[4:])
            except:
                page_num = 1

            page_cfg = {
                "page": page_num,
                "buttons": [],
                "texts": [],
                "bg": config.get(section, "bg", fallback="")
            }

            # 找出所有控件前缀（如button1, webpage1, switch1, aircon1等）
            keys = config.options(section)
            btn_ids = set()
            text_ids = set()
            for key in keys:
                if "." in key:
                    prefix = key.split(".", 1)[0]
                    if prefix.startswith("button") or prefix.startswith("webpage") or prefix.startswith("switch") or prefix.startswith("aircon"):
                        btn_ids.add(prefix)
                    elif prefix.startswith("text"):
                        text_ids.add(prefix)

            for btn_id in sorted(btn_ids):
                # 读取按钮位置
                pos_str = config.get(section, f"{btn_id}.pos", fallback="0,0,0,0")
                try:
                    x, y, w, h = [int(v.strip()) for v in pos_str.split(",")]
                except:
                    x = y = w = h = 0

                # 读取图片
                img_str = config.get(section, f"{btn_id}.img", fallback=",")
                imgs = [p.strip() for p in img_str.split(",")]
                src = imgs[0] if len(imgs) > 0 else ""
                pressed_src = imgs[1] if len(imgs) > 1 else src

                # 读取跳转页
                try:
                    switch_page = int(config.get(section, f"{btn_id}.switch", fallback="0"))
                except:
                    switch_page = 0

                # 读取指令列表
                commands = []
                idx = 1
                while True:
                    key = f"{btn_id}.text{idx}"
                    if not config.has_option(section, key):
                        break
                    val = config.get(section, key)
                    if not val:  # 跳过空命令
                        idx += 1
                        continue
                    # 先获取命令类型
                    ctype_parts = val.strip().split(",")
                    if not ctype_parts:  # 跳过格式错误的命令
                        idx += 1
                        continue
                    ctype = ctype_parts[0].lower()

                    if ctype == "close_all_windows":
                        # 处理关闭所有窗口命令，只有命令类型
                        commands.append({
                            "type": ctype
                        })
                    elif ctype == "media_window":
                        # 解析媒体窗口命令参数
                        # 格式: media_window,media_path,x,y,width,height,play_mode,mutex_mode
                        media_parts = val.split(",", 7)
                        if len(media_parts) >= 6:
                            media_path = media_parts[1].strip()
                            try:
                                win_x = int(media_parts[2].strip())
                                win_y = int(media_parts[3].strip())
                                win_width = int(media_parts[4].strip())
                                win_height = int(media_parts[5].strip())
                                play_mode = media_parts[6].strip() if len(media_parts) >= 7 else "loop"
                                mutex_mode = media_parts[7].strip() if len(media_parts) >= 8 else "共存"

                                commands.append({
                                    "type": ctype,
                                    "media": media_path,
                                    "x": win_x,
                                    "y": win_y,
                                    "width": win_width,
                                    "height": win_height,
                                    "play_mode": play_mode,
                                    "mutex_mode": mutex_mode
                                })
                            except ValueError:
                                # 参数解析失败，跳过此命令
                                pass
                    elif ctype == "udp" and len(ctype_parts) >= 3:
                        # 处理指令表指令
                        # 格式: udp,command_id,command_name[,state] 或 udp,command_id,state
                        udp_command_id = ctype_parts[1].strip()
                        command_name = ""
                        state = "" 
                        # 检查是否有状态参数
                        if len(ctype_parts) >= 3:
                            # 检查最后一个参数是否是状态
                            last_part = ctype_parts[-1].strip()
                            if last_part in ["on", "off"]:
                                state = last_part
                                # 如果有命令名称，提取命令名称
                                if len(ctype_parts) >= 4:
                                    command_name = ",".join(ctype_parts[2:-1]).strip()
                            else:
                                # 没有状态参数，所有剩余部分都是命令名称
                                command_name = ",".join(ctype_parts[2:]).strip()
                        commands.append({
                            "type": ctype,
                            "udp_command_id": udp_command_id,
                            "name": command_name,
                            "state": state
                        })
                    elif ctype == "udp_group" and len(ctype_parts) >= 3:
                        # 处理组指令
                        # 格式: udp_group,group_id,group_name[,state] 或 udp_group,group_id,state
                        udp_group_id = ctype_parts[1].strip()
                        group_name = ""
                        state = "" 
                        # 检查是否有状态参数
                        if len(ctype_parts) >= 3:
                            # 检查最后一个参数是否是状态
                            last_part = ctype_parts[-1].strip()
                            if last_part in ["on", "off"]:
                                state = last_part
                                # 如果有组名称，提取组名称
                                if len(ctype_parts) >= 4:
                                    group_name = ",".join(ctype_parts[2:-1]).strip()
                            else:
                                # 没有状态参数，所有剩余部分都是组名称
                                group_name = ",".join(ctype_parts[2:]).strip()
                        commands.append({
                            "type": ctype,
                            "udp_group_id": udp_group_id,
                            "name": group_name,
                            "state": state
                        })
                    else:
                        # 解析传统命令（udp/tcp）
                        # 先按逗号分割，最多分割5次，得到6个部分
                        parts = val.split(",", 5)
                        if len(parts) >= 4:  # 至少需要4个部分：type,ip:port,fmt,msg[,delay][,mutex_mode]
                            ipport = parts[1].strip()
                            fmt = parts[2].strip().lower()
                            msg = parts[3].strip()

                            # 解析IP和端口
                            ip_port_parts = ipport.split(":")
                            if len(ip_port_parts) == 2:
                                ip = ip_port_parts[0].strip()
                                try:
                                    port = int(ip_port_parts[1].strip())
                                except (ValueError, TypeError):
                                    port = 0
                            else:
                                ip = ""
                                port = 0

                            # 解析延时参数，默认为0
                            delay = 0
                            if len(parts) > 4:  # 如果有第5个部分，说明有延时参数
                                try:
                                    delay = int(parts[4].strip())
                                except (ValueError, IndexError):
                                    delay = 0

                            commands.append({
                                "type": ctype,
                                "ip": ip,
                                "port": port,
                                "fmt": fmt,
                                "msg": msg,
                                "delay": delay
                            })
                    idx += 1

                # 读取状态显示设置
                status_enable = config.getboolean(section, f"{btn_id}.status_enable", fallback=False)

                try:
                    status_x = int(config.get(section, f"{btn_id}.status_x", fallback="0"))
                    status_y = int(config.get(section, f"{btn_id}.status_y", fallback="0"))
                    status_width = int(config.get(section, f"{btn_id}.status_width", fallback="32"))
                    status_height = int(config.get(section, f"{btn_id}.status_height", fallback="32"))
                    status_port = int(config.get(section, f"{btn_id}.status_port", fallback="5005"))
                except ValueError:
                    status_x = 0
                    status_y = 0
                    status_width = 32
                    status_height = 32
                    status_port = 5005

                status_ip = config.get(section, f"{btn_id}.status_ip", fallback="")
                status_query_cmd = config.get(section, f"{btn_id}.status_query_cmd", fallback="")
                status_response_cmd = config.get(section, f"{btn_id}.status_response_cmd", fallback="")
                status_encoding = config.get(section, f"{btn_id}.status_encoding", fallback="16进制")
                
                # 读取网页控件的url属性
                url = config.get(section, f"{btn_id}.url", fallback="")
                # 确保URL格式正确，添加http://或https://前缀
                if url and not (url.startswith("http://") or url.startswith("https://")):
                    url = "http://" + url
                
                # 读取开关按钮的on_src和off_src属性
                on_src = config.get(section, f"{btn_id}.on_src", fallback="")
                off_src = config.get(section, f"{btn_id}.off_src", fallback="")
                
                # 读取开关控件的IP端口配置（当不选择设备时使用）
                # 优先读取新格式 switch_ip 和 switch_port
                switch_ip = config.get(section, f"{btn_id}.switch_ip", fallback="")
                switch_port = config.getint(section, f"{btn_id}.switch_port", fallback=5000)
                # 兼容旧格式
                switch_on_ip = config.get(section, f"{btn_id}.on_ip", fallback="")
                switch_on_port = config.getint(section, f"{btn_id}.on_port", fallback=5000)
                switch_off_ip = config.get(section, f"{btn_id}.off_ip", fallback="")
                switch_off_port = config.getint(section, f"{btn_id}.off_port", fallback=5000)
                switch_on_cmd = config.get(section, f"{btn_id}.on_cmd", fallback="")
                switch_off_cmd = config.get(section, f"{btn_id}.off_cmd", fallback="")
                
                # 读取询问指令和响应指令（用于状态检测）
                query_cmd = config.get(section, f"{btn_id}.query_cmd", fallback="")
                response_cmd = config.get(section, f"{btn_id}.response_cmd", fallback="")
                
                # 读取编码格式（16进制或字符串）
                encoding = config.get(section, f"{btn_id}.encoding", fallback="16进制")
                
                # 处理开关控件的设备指令（兼容旧格式）
                device_use = config.getboolean(section, f"{btn_id}.device_use", fallback=False)
                device_id = config.get(section, f"{btn_id}.device_id", fallback="")
                device_cmd_index = config.get(section, f"{btn_id}.device_cmd_index", fallback="1")
                
                # 如果开关控件使用了设备，从设备指令表中提取指令
                if device_use and device_id and device_cmd_index:
                    # 查找设备配置
                    device_section = f"devices"
                    if config.has_section(device_section):
                        device_ip = config.get(device_section, f"{device_id}_ip", fallback="")
                        device_port = config.getint(device_section, f"{device_id}_port", fallback=5000)
                        device_mode = config.get(device_section, f"{device_id}_mode", fallback="UDP")
                        
                        if device_ip:
                            # 从设备指令表中提取对应索引的指令
                            cmd_index = int(device_cmd_index)
                            
                            # 获取开指令
                            on_cmd = config.get(device_section, f"{device_id}_cmd{cmd_index}_on", fallback="")
                            if on_cmd:
                                commands.append({
                                    "type": "udp",
                                    "ip": device_ip,
                                    "port": device_port,
                                    "fmt": "hex" if device_mode == "UDP" else "ascii",
                                    "msg": on_cmd,
                                    "delay": 0,
                                    "state": "on"
                                })
                            
                            # 获取关指令
                            off_cmd = config.get(device_section, f"{device_id}_cmd{cmd_index}_off", fallback="")
                            if off_cmd:
                                commands.append({
                                    "type": "udp",
                                    "ip": device_ip,
                                    "port": device_port,
                                    "fmt": "hex" if device_mode == "UDP" else "ascii",
                                    "msg": off_cmd,
                                    "delay": 0,
                                    "state": "off"
                                })
                            
                            # 获取查询指令和反馈指令用于状态检测
                            query_cmd = config.get(device_section, f"{device_id}_cmd{cmd_index}_check", fallback="")
                            response_cmd = config.get(device_section, f"{device_id}_cmd{cmd_index}_feedback", fallback="")
                            device_encoding = config.get(device_section, f"{device_id}_cmd{cmd_index}_encoding", fallback="16进制")
                            
                            # 如果配置了查询指令，添加到状态检测
                            if query_cmd and response_cmd:
                                # 覆盖状态检测配置
                                status_enable = True
                                status_ip = device_ip
                                status_port = device_port
                                status_query_cmd = query_cmd
                                status_response_cmd = response_cmd
                                status_encoding = device_encoding
                
                # 处理开关控件自己的IP端口配置（当不选择设备时）
                elif not device_use:
                    # 优先使用新格式 switch_ip 和 switch_port
                    current_switch_ip = switch_ip if switch_ip else switch_on_ip
                    current_switch_port = switch_port if switch_ip else switch_on_port
                    
                    # 使用开关控件自己的IP和端口配置
                    if current_switch_ip and switch_on_cmd:
                        # 创建开指令
                        commands.append({
                            "type": "udp",
                            "ip": current_switch_ip,
                            "port": current_switch_port,
                            "fmt": "hex",
                            "msg": switch_on_cmd,
                            "delay": 0,
                            "state": "on"
                        })
                    
                    # 关指令也使用同样的 IP 和端口
                    current_switch_off_ip = switch_ip if switch_ip else switch_off_ip
                    current_switch_off_port = switch_port if switch_ip else switch_off_port
                    
                    if current_switch_off_ip and switch_off_cmd:
                        # 创建关指令
                        commands.append({
                            "type": "udp",
                            "ip": current_switch_off_ip,
                            "port": current_switch_off_port,
                            "fmt": "hex",
                            "msg": switch_off_cmd,
                            "delay": 0,
                            "state": "off"
                        })
                    
                    # 如果配置了查询指令，添加到状态检测
                    # 优先使用专门的询问指令和响应指令，如果没有则使用开指令和关指令
                    if current_switch_ip and query_cmd and response_cmd:
                        status_enable = True
                        status_ip = current_switch_ip
                        status_port = current_switch_port
                        status_query_cmd = query_cmd
                        status_response_cmd = response_cmd
                    elif current_switch_ip and switch_on_cmd and switch_off_cmd:
                        # 兼容旧格式：使用开指令和关指令作为查询和响应
                        status_enable = True
                        status_ip = current_switch_ip
                        status_port = current_switch_port
                        status_query_cmd = switch_on_cmd
                        status_response_cmd = switch_off_cmd
                
                # 读取空调面板的特有属性
                mode = config.get(section, f"{btn_id}.mode", fallback="auto")
                temperature = int(config.get(section, f"{btn_id}.temperature", fallback="26"))
                fan_speed = config.get(section, f"{btn_id}.fan_speed", fallback="medium")
                power = config.get(section, f"{btn_id}.power", fallback="off")
                
                # 根据控件ID的前缀设置控件类型
                if btn_id.startswith("webpage"):
                    ctrl_type = "webpage"
                elif btn_id.startswith("switch"):
                    ctrl_type = "switch"
                elif btn_id.startswith("aircon"):
                    ctrl_type = "aircon"
                else:
                    ctrl_type = "button"

                btn_cfg = {
                    "id": btn_id,
                    "x": x,
                    "y": y,
                    "w": w,
                    "h": h,
                    "src": src,
                    "pressed_src": pressed_src,
                    "type": ctrl_type,
                    "switch_page": switch_page,
                    "url": url,
                    "on_src": on_src,
                    "off_src": off_src,
                    "commands": commands,
                    # 开关控件IP和端口设置
                    "switch_ip": switch_ip,
                    "switch_port": switch_port,
                    "encoding": encoding,
                    # 空调面板特有属性
                    "mode": mode,
                    "temperature": temperature,
                    "fan_speed": fan_speed,
                    "power": power,
                    # 状态显示设置
                    "status_enable": status_enable,
                    "status_x": status_x,
                    "status_y": status_y,
                    "status_width": status_width,
                    "status_height": status_height,
                    "status_ip": status_ip,
                    "status_port": status_port,
                    "status_encoding": status_encoding,
                    "status_query_cmd": status_query_cmd,
                    "status_response_cmd": status_response_cmd
                }
                
                # 只有非开关控件才需要状态图标设置（开关控件用自己的on_src/off_src显示状态）
                if ctrl_type != 'switch':
                    btn_cfg["status_on_src"] = status_on_src
                    btn_cfg["status_off_src"] = status_off_src
                page_cfg["buttons"].append(btn_cfg)

            # 加载文字项
            for text_id in sorted(text_ids):
                # 读取文字位置
                pos_str = config.get(section, f"{text_id}.pos", fallback="0,0,200,50")
                try:
                    x, y, w, h = [int(v.strip()) for v in pos_str.split(",")]
                except:
                    x, y, w, h = 0, 0, 200, 50

                text_cfg = {
                    "id": text_id,
                    "x": x,
                    "y": y,
                    "w": w,
                    "h": h,
                    "type": "text",
                    "text": config.get(section, f"{text_id}.text_content", fallback="文字"),
                    "font_family": config.get(section, f"{text_id}.font_family", fallback="Microsoft YaHei"),
                    "color": config.get(section, f"{text_id}.color", fallback="#000000"),
                    "align": config.get(section, f"{text_id}.align", fallback="left"),
                    "bold": config.getboolean(section, f"{text_id}.bold", fallback=False),
                    "italic": config.getboolean(section, f"{text_id}.italic", fallback=False)
                }
                page_cfg["texts"].append(text_cfg)

            pages.append(page_cfg)

    # 如果配置文件没有页面，返回一个默认空页
    if not pages:
        pages = [{"page": 1, "bg": "", "buttons": [], "texts": []}]

    # 读取网络设置
    network = {'web_port': '5000'}  # 默认网页端口为5000
    if 'network' in config:
        network = dict(config['network'])
        # 确保web_port存在
        if 'web_port' not in network:
            network['web_port'] = '5000'

    try:
        status_x = int(config.get('global', 'status_x', fallback='0'))
        status_y = int(config.get('global', 'status_y', fallback='0'))
        status_width = int(config.get('global', 'status_width', fallback='32'))
        status_height = int(config.get('global', 'status_height', fallback='32'))
    except ValueError:
        status_x = 0
        status_y = 0
        status_width = 32
        status_height = 32
    
    # 读取等待图片设置
    wait_image_src = config.get('global', 'wait_image_src', fallback='')
    
    try:
        wait_image_x = int(config.get('global', 'wait_image_x', fallback='960'))
        wait_image_y = int(config.get('global', 'wait_image_y', fallback='540'))
        wait_image_width = int(config.get('global', 'wait_image_width', fallback='200'))
        wait_image_height = int(config.get('global', 'wait_image_height', fallback='200'))
    except ValueError:
        wait_image_x = 960
        wait_image_y = 540
        wait_image_width = 200
        wait_image_height = 200

    # 读取UDP指令
    udp_commands = []
    if 'udp_commands' in config:
        cmd_ids = set()
        for key in config['udp_commands']:
            if '_payload' in key:
                cmd_id = key.replace('_payload', '')
                cmd_ids.add(cmd_id)

        for cmd_id in cmd_ids:
            # 优先使用保存的ID，否则使用解析出的ID
            saved_id = config['udp_commands'].get(f'{cmd_id}_id', cmd_id)
            cmd = {
                'id': saved_id,
                'name': config['udp_commands'].get(f'{cmd_id}_name', cmd_id),
                'payload': config['udp_commands'].get(f'{cmd_id}_payload', ''),
                'encoding': config['udp_commands'].get(f'{cmd_id}_encoding', 'ascii'),
                'ip': config['udp_commands'].get(f'{cmd_id}_ip', ''),
                'port': int(config['udp_commands'].get(f'{cmd_id}_port', '5000')),
                'mode': config['udp_commands'].get(f'{cmd_id}_mode', 'UDP')
            }
            udp_commands.append(cmd)

    # 读取UDP组
    udp_groups = []
    if 'udp_groups' in config:
        group_ids = set()
        for key in config['udp_groups']:
            if '_name' in key:
                group_id = key.replace('_name', '')
                group_ids.add(group_id)

        for group_id in group_ids:
            group = {
                'id': group_id,
                'name': config['udp_groups'].get(f'{group_id}_name', ''),
                'commands': []
            }
            # 读取组内的命令
            # 首先尝试新格式: group1_commands = command_id:delay,command_id:delay,...
            if f'{group_id}_commands' in config['udp_groups']:
                commands_str = config['udp_groups'][f'{group_id}_commands']
                commands_list = commands_str.split(',')
                for cmd_str in commands_list:
                    cmd_parts = cmd_str.split(':', 1)
                    if len(cmd_parts) >= 1:
                        cmd_id = cmd_parts[0].strip()
                        delay = int(cmd_parts[1].strip()) if len(cmd_parts) > 1 else 0
                        group['commands'].append({
                            'type': 'udp',
                            'id': cmd_id,
                            'delay': delay
                        })
            # 然后尝试旧格式: group1_cmd1 = udp,command_id
            cmd_keys = [k for k in config['udp_groups'] if k.startswith(f'{group_id}_cmd')]
            for cmd_key in sorted(cmd_keys):
                cmd_val = config['udp_groups'][cmd_key]
                # 解析命令，格式: udp,command_id 或 udp_group,group_id
                cmd_parts = cmd_val.split(',', 1)
                if len(cmd_parts) == 2:
                    cmd_type = cmd_parts[0].strip()
                    cmd_id = cmd_parts[1].strip()
                    group['commands'].append({
                        'type': cmd_type,
                        'id': cmd_id
                    })
            udp_groups.append(group)

    # 读取定时任务
    schedules = []
    if 'schedules' in config:
        sched_ids = set()
        for key in config['schedules']:
            if key.endswith('_name'):
                # 检查键是否是命令名称（如 time1_cmd_name），如果是则跳过
                if '_cmd_name' in key:
                    continue
                sched_id = key[:-5]  # 移除末尾的 '_name'
                sched_ids.add(sched_id)

        for sched_id in sched_ids:
            sched = {
                'id': sched_id,
                'name': config['schedules'].get(f'{sched_id}_name', ''),
                'date': config['schedules'].get(f'{sched_id}_date', ''),
                'week': config['schedules'].get(f'{sched_id}_week', ''),
                'time': config['schedules'].get(f'{sched_id}_time', '00:00'),
                'cmd_type': config['schedules'].get(f'{sched_id}_cmd_type', '指令表'),
                'cmd_id': config['schedules'].get(f'{sched_id}_cmd_id', ''),
                'enable': config.getboolean('schedules', f'{sched_id}_enable', fallback=True)
            }
            schedules.append(sched)

    # 读取UDP指令匹配规则
    udp_matches = []
    if 'udp_matches' in config:
        match_ids = set()
        for key in config['udp_matches']:
            if key.endswith('_match_cmd'):
                match_id = key[:-10]  # 移除末尾的 '_match_cmd'
                match_ids.add(match_id)
        
        for match_id in match_ids:
            match = {
                'id': match_id,
                'match_cmd': config['udp_matches'].get(f'{match_id}_match_cmd', ''),
                'mode': config['udp_matches'].get(f'{match_id}_mode', '字符串'),
                'cmd_type': config['udp_matches'].get(f'{match_id}_cmd_type', '指令表'),
                'exec_cmd_id': config['udp_matches'].get(f'{match_id}_exec_cmd_id', '')
            }
            udp_matches.append(match)

    # 统计配置信息
    total_buttons = sum(len(page.get('buttons', [])) for page in pages)
    total_texts = sum(len(page.get('texts', [])) for page in pages)
    total_schedules = len(schedules)
    total_udp_commands = len(udp_commands)
    total_udp_groups = len(udp_groups)
    total_udp_matches = len(udp_matches)
    
    logger.info(f"[配置加载] 完成: {len(pages)}个页面, {total_buttons}个按钮, {total_texts}个文字, "
                f"{total_udp_commands}条UDP指令, {total_udp_groups}个UDP组, {total_schedules}个定时任务, {total_udp_matches}个匹配规则")
    
    return {
        "resolution": resolution,
        "pages": pages,
        "network": network,
        "status_on_src": status_on_src,
        "status_off_src": status_off_src,
        "status_x": status_x,
        "status_y": status_y,
        "status_width": status_width,
        "status_height": status_height,
        "wait_image_src": wait_image_src,
        "wait_image_x": wait_image_x,
        "wait_image_y": wait_image_y,
        "wait_image_width": wait_image_width,
        "wait_image_height": wait_image_height,
        "udp_commands": udp_commands,
        "udp_groups": udp_groups,
        "schedules": schedules,
        "udp_matches": udp_matches
    }


def udp_listen_thread():
    """UDP监听线程，监听UDP指令并执行匹配的命令"""
    while True:
        sock = None
        try:
            # 检查许可证状态
            valid, message = check_license_status()
            if not valid:
                # 未授权，跳过执行
                logger.info(f"[UDP监听] 未授权，跳过执行: {message}")
                time.sleep(5)  # 等待5秒后重试
                continue
            
            # 加载配置
            cfg = load_cfg()
            udp_listen_port = int(cfg.get('network', {}).get('udp_listen_port', '5005'))
            udp_matches = cfg.get('udp_matches', [])
            udp_commands = cfg.get('udp_commands', [])
            udp_groups = cfg.get('udp_groups', [])
            
            logger.info(f"[UDP监听] 开始监听UDP端口: {udp_listen_port}")
            
            # 创建UDP套接字
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # 设置SO_REUSEADDR选项，允许端口被重用
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('', udp_listen_port))
            sock.settimeout(5)  # 设置超时，以便定期重新加载配置
            
            while True:
                try:
                    # 接收UDP数据包
                    data, addr = sock.recvfrom(1024)
                    # 尝试解码，处理可能的编码错误
                    try:
                        received_cmd = data.decode('ascii').strip()
                        # 移除可能的引号
                        received_cmd = received_cmd.strip('"').strip('\'')
                    except UnicodeDecodeError:
                        # 如果解码失败，尝试使用utf-8解码
                        try:
                            received_cmd = data.decode('utf-8').strip()
                            # 移除可能的引号
                            received_cmd = received_cmd.strip('"').strip('\'')
                        except UnicodeDecodeError:
                            # 如果仍然解码失败，记录错误并跳过
                            logger.error(f"[UDP监听] 解码UDP数据包失败")
                            continue
                    
                    logger.info(f"[UDP监听] 接收到UDP指令: {received_cmd} 来自 {addr}")
                    
                    # 检查是否匹配配置的指令
                    match_found = False
                    for match in udp_matches:
                        match_cmd = match.get('match_cmd', '').strip()
                        mode = match.get('mode', '字符串')
                        
                        # 根据模式进行匹配
                        matched = False
                        if mode == '字符串':
                            # 字符串模式匹配
                            if match_cmd and match_cmd == received_cmd:
                                matched = True
                        elif mode == '16进制':
                            # 16进制模式匹配
                            try:
                                # 直接将二进制数据转换为16进制字符串
                                hex_received = data.hex().upper()
                                clean_match = match_cmd.replace(' ', '').replace('\n', '').replace('\r', '').upper()
                                if clean_match and clean_match == hex_received:
                                    matched = True
                                    logger.info(f"[UDP监听] 使用二进制数据转换匹配成功: {hex_received}")
                            except Exception as e:
                                logger.error(f"[UDP监听] 16进制匹配出错: {e}")
                        
                        if matched:
                            logger.info(f"[UDP监听] 指令匹配成功: {match_cmd} (模式: {mode})")
                            
                            # 创建命令对象
                            cmd_type = match.get('cmd_type', '指令表')
                            exec_cmd_id = match.get('exec_cmd_id', '')
                            
                            if cmd_type == '指令表':
                                # 执行指令表指令
                                cmd = {
                                    'type': 'udp',
                                    'udp_command_id': exec_cmd_id
                                }
                            elif cmd_type == '组指令':
                                # 执行组指令
                                cmd = {
                                    'type': 'udp_group',
                                    'udp_group_id': exec_cmd_id
                                }
                            else:
                                logger.warning(f"[UDP监听] 未知指令类型: {cmd_type}")
                                continue
                            
                            # 执行命令
                            logger.info(f"[UDP监听] 执行命令: {cmd_type} - {exec_cmd_id}")
                            execute_command(cmd, udp_commands, udp_groups)
                            match_found = True
                            break
                    
                    if not match_found:
                        logger.info(f"[UDP监听] 未找到匹配的转发规则")
                    
                except socket.timeout:
                    # 超时，重新加载配置
                    break
                except Exception as e:
                    logger.error(f"[UDP监听] 处理UDP指令时出错: {e}")
            
        except Exception as e:
            logger.error(f"[UDP监听] 监听UDP端口时出错: {e}")
            time.sleep(5)  # 出错后等待5秒再重试
        finally:
            # 确保套接字被关闭
            if sock:
                try:
                    sock.close()
                except:
                    pass

# 启动UDP监听线程
def start_udp_listen_thread():
    """启动UDP监听线程"""
    udp_thread = threading.Thread(target=udp_listen_thread, daemon=True)
    udp_thread.start()
    logger.info("[UDP监听] UDP监听线程已启动")

# 启动状态检测线程
def start_status_check_thread():
    """启动状态检测线程"""
    status_thread = threading.Thread(target=status_check_thread, daemon=True)
    status_thread.start()
    logger.info("[状态检测] 状态检测线程已启动")

# 启动定时任务检查线程
start_schedule_thread()

# 启动UDP监听线程
start_udp_listen_thread()

# 启动状态检测线程
start_status_check_thread()


def send_wake_on_lan(mac_address):
    """发送网络唤醒魔术包"""
    try:
        # 验证MAC地址格式
        mac = mac_address.replace(':', '').replace('-', '').replace(' ', '').upper()
        if len(mac) != 12:
            print(f"[WOL] 无效的MAC地址: {mac_address}")
            return False
        
        # 创建魔术包: 6个0xFF字节，后跟16次MAC地址
        magic_packet = b'\xff' * 6 + bytes.fromhex(mac) * 16
        
        # 创建UDP套接字
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(2)
        
        # 发送到广播地址和端口9
        broadcast_ip = '255.255.255.255'
        port = 9
        print(f"[WOL] 发送网络唤醒包到广播地址 {broadcast_ip}:{port}")
        print(f"[WOL] MAC地址: {mac_address}")
        
        sock.sendto(magic_packet, (broadcast_ip, port))
        sock.close()
        print(f"[WOL] 网络唤醒包发送成功")
        return True
    except Exception as e:
        print(f"[WOL] 发送网络唤醒包失败: {e}")
        return False

def send_udp_command(ip, port, message, encoding='ascii'):
    """发送UDP指令"""
    try:
        # 检查参数有效性
        if not ip:
            print("[UDP] IP地址为空")
            return False
        if not port or port <= 0 or port > 65535:
            print(f"[UDP] 端口无效: {port}")
            return False
        if not message:
            print("[UDP] 消息为空")
            return False
        
        # 处理网络唤醒
        if encoding == 'wake_on_lan':
            return send_wake_on_lan(message)
        
        print(f"[UDP] 准备发送指令到 {ip}:{port}")
        print(f"[UDP] 消息: {message}")
        print(f"[UDP] 编码: {encoding}")
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(2)
        # 编码消息
        if encoding == 'hex' or encoding == '16进制':
            # 直接发送16进制字符串，不转换
            print(f"[UDP] 直接发送16进制字符串")
            message = message.encode('ascii')
        elif encoding == '字符串':
            # 直接发送字符串
            print(f"[UDP] 直接发送字符串")
            message = message.encode('ascii')
        else:
            # 使用指定编码发送
            print(f"[UDP] 使用编码 {encoding} 发送")
            message = message.encode(encoding)
        
        print(f"[UDP] 发送指令到 {ip}:{port}")
        sock.sendto(message, (ip, port))
        sock.close()
        print(f"[UDP] 指令发送成功: {ip}:{port}")
        return True
    except Exception as e:
        print(f"[UDP] 发送指令失败: {e}")
        return False


def send_tcp_command(ip, port, message, timeout=2):
    """发送TCP指令"""
    try:
        # 检查参数有效性
        if not ip:
            print("[TCP] IP地址为空")
            return False
        if not port or port <= 0 or port > 65535:
            print(f"[TCP] 端口无效: {port}")
            return False
        if not message:
            print("[TCP] 消息为空")
            return False
        
        print(f"[TCP] 准备发送指令到 {ip}:{port}")
        print(f"[TCP] 消息: {message}")
        print(f"[TCP] 超时设置: {timeout}秒")
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        
        # 连接服务器
        print(f"[TCP] 正在连接 {ip}:{port}...")
        try:
            sock.connect((ip, port))
        except ConnectionRefusedError:
            print(f"[TCP] 连接被拒绝: {ip}:{port}")
            sock.close()
            return False
        except Exception as e:
            print(f"[TCP] 连接失败: {e}")
            sock.close()
            return False
        
        # 发送消息
        print(f"[TCP] 发送指令到 {ip}:{port}")
        try:
            sock.sendall(message.encode('ascii'))
        except Exception as e:
            print(f"[TCP] 发送数据失败: {e}")
            sock.close()
            return False
        
        # 关闭连接
        sock.close()
        print(f"[TCP] 指令发送成功: {ip}:{port}")
        return True
    except Exception as e:
        print(f"[TCP] 发送指令失败: {e}")
        return False


def send_pjlink_command(ip, port, message, timeout=2):
    """发送PJLINK指令"""
    try:
        # 检查参数有效性
        if not ip:
            logger.info("[PJLINK] IP地址为空")
            return False
        
        # PJLINK默认端口是4352
        # 对于PJLINK模式，强制使用4352端口
        pjlink_port = 4352
        logger.info(f"[PJLINK] 使用标准端口: {pjlink_port}")
        
        if not message:
            logger.info("[PJLINK] 消息为空")
            return False
        
        logger.info(f"[PJLINK] 准备发送指令到 {ip}:{pjlink_port}")
        logger.info(f"[PJLINK] 消息: {message}")
        logger.info(f"[PJLINK] 超时设置: {timeout}秒")
        
        # PJLINK指令格式: %1POWR <command>
        msg_upper = message.upper()
        if msg_upper in ['ON', '1']:
            power_cmd = 'ON'
        elif msg_upper in ['OFF', '0']:
            power_cmd = 'OFF'
        else:
            logger.warning(f"[PJLINK] 无效的指令: {message}")
            return False
        
        # 构建PJLINK指令
        # 端口号作为密码
        password = str(port)
        # PJLINK标准指令格式
        pjlink_cmd = f'%1POWR {power_cmd}\r'
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        
        # 连接服务器
        logger.info(f"[PJLINK] 正在连接 {ip}:{pjlink_port}...")
        try:
            sock.connect((ip, pjlink_port))
        except ConnectionRefusedError:
            logger.warning(f"[PJLINK] 连接被拒绝: {ip}:{pjlink_port}")
            sock.close()
            return False
        except Exception as e:
            logger.warning(f"[PJLINK] 连接失败: {e}")
            sock.close()
            return False
        
        # 发送消息
        logger.info(f"[PJLINK] 发送指令到 {ip}:{pjlink_port}")
        logger.info(f"[PJLINK] 发送的指令: {pjlink_cmd}")
        try:
            sock.sendall(pjlink_cmd.encode('ascii'))
        except Exception as e:
            logger.warning(f"[PJLINK] 发送数据失败: {e}")
            sock.close()
            return False
        
        # 接收响应
        logger.info("[PJLINK] 等待响应...")
        try:
            response = sock.recv(1024)
            logger.info(f"[PJLINK] 收到响应: {response.decode('ascii')}")
        except Exception as e:
            logger.warning(f"[PJLINK] 接收响应失败: {e}")
            # 响应失败不影响指令发送结果
        
        # 关闭连接
        sock.close()
        logger.info(f"[PJLINK] 指令发送成功: {ip}:{pjlink_port}")
        return True
    except Exception as e:
        logger.warning(f"[PJLINK] 发送指令失败: {e}")
        return False


def execute_command(cmd, udp_commands, udp_groups):
    """执行命令"""
    print(f"[命令执行] 开始执行命令: {cmd['type']}")
    if cmd['type'] == 'udp':
        if 'udp_command_id' in cmd:
            print(f"[命令执行] 执行UDP指令表指令: {cmd['udp_command_id']}")
            # 从指令表中查找指令
            found = False
            for udp_cmd in udp_commands:
                if udp_cmd['id'] == cmd['udp_command_id']:
                    found = True
                    print(f"[命令执行] 找到指令: {udp_cmd['name']} (ID: {udp_cmd['id']})")
                    
                    # 根据模式执行相应的命令
                    mode = udp_cmd.get('mode', 'UDP')
                    print(f"[命令执行] 指令模式: {mode}")
                    
                    # 使用线程池执行，避免网络不通时卡死
                    # 使用默认参数解决闭包延迟绑定问题
                    def execute_in_thread(mode=mode, udp_cmd=udp_cmd):
                        if mode == 'UDP':
                            result = send_udp_command(
                                udp_cmd['ip'],
                                udp_cmd['port'],
                                udp_cmd['payload'],
                                udp_cmd['encoding']
                            )
                        elif mode == 'TCP':
                            result = send_tcp_command(
                                udp_cmd['ip'],
                                udp_cmd['port'],
                                udp_cmd['payload'],
                                timeout=2
                            )
                        elif mode == 'PJLINK':
                            result = send_pjlink_command(
                                udp_cmd['ip'],
                                udp_cmd['port'],
                                udp_cmd['payload'],
                                timeout=2
                            )
                        elif mode == '网络唤醒':
                            result = send_wake_on_lan(udp_cmd['payload'])
                        else:
                            logger.info(f"[命令执行] 未知模式: {mode}")
                            result = False
                        logger.info(f"[命令执行] 指令执行结果: {'成功' if result else '失败'}")
                    
                    # 使用线程池执行命令
                    thread_pool.submit(execute_in_thread)
                    return True  # 不等待线程完成，直接返回成功
            if not found:
                print(f"[命令执行] 未找到指令: {cmd['udp_command_id']}")
                return False
        elif 'ip' in cmd and 'port' in cmd and 'msg' in cmd:
            print(f"[命令执行] 执行直接UDP指令: {cmd['ip']}:{cmd['port']}")
            # 直接发送UDP指令
            encoding = 'ascii'
            if 'fmt' in cmd and cmd['fmt'] == 'hex':
                encoding = 'hex'
                print(f"[命令执行] 使用十六进制编码")
            else:
                print(f"[命令执行] 使用ASCII编码")
            result = send_udp_command(
                cmd['ip'],
                cmd['port'],
                cmd['msg'],
                encoding
            )
            print(f"[命令执行] 指令执行结果: {'成功' if result else '失败'}")
            return result
    elif cmd['type'] == 'udp_group':
        print(f"[命令执行] 执行UDP组指令: {cmd['udp_group_id']}")
        # 执行UDP组指令
        if 'udp_group_id' in cmd:
            found = False
            for group in udp_groups:
                if group['id'] == cmd['udp_group_id']:
                    found = True
                    print(f"[命令执行] 找到组: {group['name']} (ID: {group['id']})")
                    print(f"[命令执行] 组内命令数量: {len(group['commands'])}")
                    print(f"[命令执行] 组延时设置: {'有' if 'delay' in cmd else '无'}")
                    if 'delay' in cmd:
                        print(f"[命令执行] 延时时间: {cmd['delay']}ms")
                    
                    for i, group_cmd in enumerate(group['commands']):
                        print(f"[命令执行] ====== 执行组内命令 {i+1}/{len(group['commands'])} ======")
                        print(f"[命令执行] 命令类型: {group_cmd['type']}")
                        print(f"[命令执行] 命令ID: {group_cmd['id']}")
                        if 'delay' in group_cmd:
                            print(f"[命令执行] 命令延时: {group_cmd['delay']}ms")
                        # 递归执行组内的命令
                        if group_cmd['type'] == 'udp':
                            for udp_cmd in udp_commands:
                                if udp_cmd['id'] == group_cmd['id']:
                                    print(f"[命令执行] 找到组内UDP指令: {udp_cmd['name']} (ID: {udp_cmd['id']})")
                                    print(f"[命令执行] 指令IP: {udp_cmd['ip']}")
                                    print(f"[命令执行] 指令端口: {udp_cmd['port']}")
                                    print(f"[命令执行] 指令内容: {udp_cmd['payload']}")
                                    print(f"[命令执行] 编码方式: {udp_cmd['encoding']}")
                                    print(f"[命令执行] 指令模式: {udp_cmd.get('mode', 'UDP')}")
                                    print(f"[命令执行] 发送指令...")
                                    
                                    # 根据模式执行相应的命令
                                    mode = udp_cmd.get('mode', 'UDP')
                                    
                                    # 使用线程池执行，避免网络不通时卡死
                                    # 使用默认参数解决闭包延迟绑定问题
                                    def execute_in_thread(mode=mode, udp_cmd=udp_cmd):
                                        if mode == 'UDP':
                                            result = send_udp_command(
                                                udp_cmd['ip'],
                                                udp_cmd['port'],
                                                udp_cmd['payload'],
                                                udp_cmd['encoding']
                                            )
                                        elif mode == 'TCP':
                                            result = send_tcp_command(
                                                udp_cmd['ip'],
                                                udp_cmd['port'],
                                                udp_cmd['payload'],
                                                timeout=2
                                            )
                                        elif mode == 'PJLINK':
                                            result = send_pjlink_command(
                                                udp_cmd['ip'],
                                                udp_cmd['port'],
                                                udp_cmd['payload'],
                                                timeout=2
                                            )
                                        elif mode == '网络唤醒':
                                            result = send_wake_on_lan(udp_cmd['payload'])
                                        else:
                                            logger.info(f"[命令执行] 未知模式: {mode}")
                                            result = False
                                        logger.info(f"[命令执行] 组内指令执行结果: {'成功' if result else '失败'}")
                                    
                                    # 使用线程池执行命令
                                    thread_pool.submit(execute_in_thread)
                                    
                                    # 立即开始延时，不等待线程完成
                                    # 添加延时
                                    if 'delay' in group_cmd and group_cmd['delay'] > 0:
                                        delay = group_cmd['delay']
                                        print(f"[命令执行] ====== 添加延时: {delay}ms ======")
                                        time.sleep(delay / 1000)
                                        print(f"[命令执行] 延时结束")
                                    elif 'delay' in cmd:
                                        delay = cmd['delay']
                                        print(f"[命令执行] ====== 添加组级延时: {delay}ms ======")
                                        time.sleep(delay / 1000)
                                        print(f"[命令执行] 延时结束")
                        elif group_cmd['type'] == 'udp_group':
                            print(f"[命令执行] 执行嵌套组: {group_cmd['id']}")
                            # 处理嵌套组
                            for nested_group in udp_groups:
                                if nested_group['id'] == group_cmd['id']:
                                    print(f"[命令执行] 找到嵌套组: {nested_group['name']} (ID: {nested_group['id']})")
                                    print(f"[命令执行] 嵌套组内命令数量: {len(nested_group['commands'])}")
                                    for j, nested_cmd in enumerate(nested_group['commands']):
                                        print(f"[命令执行] 执行嵌套组内命令 {j+1}/{len(nested_group['commands'])}: {nested_cmd['type']}")
                                        if nested_cmd['type'] == 'udp':
                                            for udp_cmd in udp_commands:
                                                if udp_cmd['id'] == nested_cmd['id']:
                                                    print(f"[命令执行] 找到嵌套组内UDP指令: {udp_cmd['name']} (ID: {udp_cmd['id']})")
                                                    print(f"[命令执行] 指令IP: {udp_cmd['ip']}")
                                                    print(f"[命令执行] 指令端口: {udp_cmd['port']}")
                                                    print(f"[命令执行] 指令内容: {udp_cmd['payload']}")
                                                    print(f"[命令执行] 编码方式: {udp_cmd['encoding']}")
                                                    print(f"[命令执行] 发送指令...")
                                                    result = send_udp_command(
                                                        udp_cmd['ip'],
                                                        udp_cmd['port'],
                                                        udp_cmd['payload'],
                                                        udp_cmd['encoding']
                                                    )
                                                    print(f"[命令执行] 嵌套组内指令执行结果: {'成功' if result else '失败'}")
                                                    # 添加延时
                                                    if 'delay' in cmd:
                                                        delay = cmd['delay']
                                                        print(f"[命令执行] ====== 添加延时: {delay}ms ======")
                                                        time.sleep(delay / 1000)
                                                        print(f"[命令执行] 延时结束")
                    print(f"[命令执行] ====== 组指令执行完成 ======")
            if not found:
                print(f"[命令执行] 未找到组: {cmd['udp_group_id']}")
                return False
            print(f"[命令执行] 组指令执行完成")
            return True
    print(f"[命令执行] 未知命令类型: {cmd['type']}")
    return False


def save_cfg(data, filename=CONFIG):
    """保存配置文件"""
    config = configparser.ConfigParser(allow_no_value=True)
    config.optionxform = str  # 保持键的大小写

    # 保存分辨率
    width = data['resolution']['width']
    height = data['resolution']['height']
    config['resolution'] = {
        'width': str(width),
        'height': str(height)
    }

    # 保存网络设置
    if 'network' in data:
        config['network'] = data['network']

    # 保存全局状态图片设置
    config['global'] = {}
    config['global']['status_on_src'] = data.get('status_on_src', '')
    config['global']['status_off_src'] = data.get('status_off_src', '')
    config['global']['status_x'] = str(data.get('status_x', 0))
    config['global']['status_y'] = str(data.get('status_y', 0))
    config['global']['status_width'] = str(data.get('status_width', 32))
    config['global']['status_height'] = str(data.get('status_height', 32))
    
    # 保存等待图片设置
    config['global']['wait_image_src'] = data.get('wait_image_src', '')
    config['global']['wait_image_x'] = str(data.get('wait_image_x', 960))
    config['global']['wait_image_y'] = str(data.get('wait_image_y', 540))
    config['global']['wait_image_width'] = str(data.get('wait_image_width', 200))
    config['global']['wait_image_height'] = str(data.get('wait_image_height', 200))

    # 保存UDP指令
    if 'udp_commands' in data:
        config['udp_commands'] = {}
        for cmd in data['udp_commands']:
            cmd_id = cmd.get('id', '')
            config['udp_commands'][f'{cmd_id}_id'] = cmd_id
            config['udp_commands'][f'{cmd_id}_name'] = cmd.get('name', '')
            config['udp_commands'][f'{cmd_id}_payload'] = cmd.get('payload', '')
            config['udp_commands'][f'{cmd_id}_encoding'] = cmd.get('encoding', 'ascii')
            config['udp_commands'][f'{cmd_id}_ip'] = cmd.get('ip', '')
            config['udp_commands'][f'{cmd_id}_port'] = str(cmd.get('port', 5000))
            config['udp_commands'][f'{cmd_id}_mode'] = cmd.get('mode', 'UDP')

    # 保存UDP组
    if 'udp_groups' in data:
        config['udp_groups'] = {}
        for group in data['udp_groups']:
            group_id = group.get('id', '')
            config['udp_groups'][f'{group_id}_name'] = group.get('name', '')
            # 保存命令及其延时，格式: id:delay,id:delay
            commands_with_delay = []
            for cmd in group.get('commands', []):
                cmd_id = cmd.get('id', '')
                delay = cmd.get('delay', 0)
                commands_with_delay.append(f"{cmd_id}:{delay}")
            config['udp_groups'][f'{group_id}_commands'] = ','.join(commands_with_delay)

    for page in data['pages']:
        sec = f"page{page['page']}"
        config[sec] = {}
        # 只保存相对路径
        bg_path = page.get('bg', '')
        if bg_path:  # 只有在有背景路径时才处理
            if os.path.isabs(bg_path):
                # 如果路径是绝对路径，转换为相对于data目录的路径
                try:
                    rel_path = os.path.relpath(bg_path, 'data')
                    # 确保不会添加重复的data目录
                    if rel_path.startswith('data\\') or rel_path.startswith('data/'):
                        rel_path = rel_path[5:]  # 移除开头的 'data/' 或 'data\'
                    bg_path = rel_path
                except ValueError:
                    # 如果无法转换为相对路径（例如在不同驱动器上），则只保留文件名
                    bg_path = os.path.basename(bg_path)
            # 确保路径使用正斜杠
            bg_path = bg_path.replace('\\', '/')
        config[sec]['bg'] = bg_path

        for btn in page.get('buttons', []):
            prefix = btn['id']

            x = int(btn['x'])
            y = int(btn['y'])
            w = int(btn['w'])
            h = int(btn['h'])

            config[sec][f"{prefix}.pos"] = f"{x},{y},{w},{h}"
            config[sec][f"{prefix}.img"] = f"{btn.get('src', '')},{btn.get('pressed_src', '')}"
            config[sec][f"{prefix}.switch"] = str(btn.get('switch_page', 0))
            
            # 保存网页控件的url属性
            if btn.get('type') == 'webpage':
                config[sec][f"{prefix}.url"] = btn.get('url', '')
            # 保存开关按钮的on_src和off_src属性
            elif btn.get('type') == 'switch':
                config[sec][f"{prefix}.on_src"] = btn.get('on_src', '')
                config[sec][f"{prefix}.off_src"] = btn.get('off_src', '')
                # 保存开关控件的新格式 IP 和端口
                if 'switch_ip' in btn:
                    config[sec][f"{prefix}.switch_ip"] = btn.get('switch_ip', '')
                    config[sec][f"{prefix}.switch_port"] = str(btn.get('switch_port', 5000))
                # 保存开关控件的设备相关配置（兼容旧格式）
                if btn.get('device_use'):
                    config[sec][f"{prefix}.device_use"] = str(btn['device_use'])
                    config[sec][f"{prefix}.device_id"] = btn.get('device_id', '')
                    config[sec][f"{prefix}.device_cmd_index"] = str(btn.get('device_cmd_index', '1'))
                    config[sec][f"{prefix}.on_cmd"] = btn.get('on_cmd', '')
                    config[sec][f"{prefix}.off_cmd"] = btn.get('off_cmd', '')
                    config[sec][f"{prefix}.query_cmd"] = btn.get('query_cmd', '')
                    config[sec][f"{prefix}.response_cmd"] = btn.get('response_cmd', '')
            # 保存空调面板的特有属性
            elif btn.get('type') == 'aircon':
                config[sec][f"{prefix}.mode"] = btn.get('mode', 'auto')
                config[sec][f"{prefix}.temperature"] = str(btn.get('temperature', 26))
                config[sec][f"{prefix}.fan_speed"] = btn.get('fan_speed', 'medium')
                config[sec][f"{prefix}.power"] = btn.get('power', 'off')

            # 保存状态显示设置
            if btn.get('status_enable', False):
                config[sec][f"{prefix}.status_enable"] = str(btn['status_enable'])
                config[sec][f"{prefix}.status_ip"] = btn.get('status_ip', '')
                config[sec][f"{prefix}.status_port"] = str(btn.get('status_port', 5005))
                config[sec][f"{prefix}.status_query_cmd"] = btn.get('status_query_cmd', '')
                config[sec][f"{prefix}.status_response_cmd"] = btn.get('status_response_cmd', '')

            cmds = [c for c in btn.get('commands', []) if c['type'] != 'switch']
            for i, c in enumerate(cmds, 1):
                if c['type'] == 'media_window':
                    # 保存媒体窗口命令
                    media_path = c.get('media', '')
                    x = c.get('x', 200)
                    y = c.get('y', 200)
                    width = c.get('width', 800)
                    height = c.get('height', 600)
                    play_mode = c.get('play_mode', 'loop')
                    mutex_mode = c.get('mutex_mode', '共存')
                    config[sec][f"{prefix}.text{i}"] = f"{c['type']},{media_path},{x},{y},{width},{height},{play_mode},{mutex_mode}"
                elif c['type'] == 'close_all_windows':
                    # 保存关闭所有窗口命令
                    config[sec][f"{prefix}.text{i}"] = f"{c['type']}"
                elif c['type'] == 'udp' and 'udp_command_id' in c:
                    # 保存指令表指令，包含state属性
                    state = c.get('state', '')
                    if state:
                        config[sec][f"{prefix}.text{i}"] = f"{c['type']},{c['udp_command_id']},{state}"
                    else:
                        config[sec][f"{prefix}.text{i}"] = f"{c['type']},{c['udp_command_id']},{c.get('name', '')}"
                elif c['type'] == 'udp_group' and 'udp_group_id' in c:
                    # 保存组指令，包含state属性
                    state = c.get('state', '')
                    if state:
                        config[sec][f"{prefix}.text{i}"] = f"{c['type']},{c['udp_group_id']},{state}"
                    else:
                        config[sec][f"{prefix}.text{i}"] = f"{c['type']},{c['udp_group_id']},{c.get('name', '')}"
                else:
                    # 保存传统命令（udp/tcp）
                    ip = c.get('ip', '')
                    port = c.get('port', 0)
                    fmt = c.get('fmt', 'hex')
                    msg = c.get('msg', '')
                    delay = c.get('delay', 0)
                    ipport = f"{ip}:{port}"
                    config[sec][f"{prefix}.text{i}"] = f"{c['type']},{ipport},{fmt},{msg},{delay}"

    with open(filename, 'w', encoding='utf-8') as f:
        config.write(f)


# 视频背景支持的 JavaScript 代码
VIDEO_BACKGROUND_SCRIPT = '''
<script>
// 视频背景支持 - 由服务器自动注入
// 注意：此脚本只定义视频背景处理函数，不直接重写 loadPage
// loadPage 的重写统一在文字控件脚本中处理
(function() {
    // 保存当前视频路径，避免重复加载相同视频
    window.currentVideoPath = null;
    
    // 设置或更新视频背景 - 由主 loadPage 调用
    window.setupVideoBackground = function(bgPath) {
        if (!bgPath) return;
        
        const bgPathLower = bgPath.toLowerCase();
        // 检查是否是视频文件
        if (!bgPathLower.endsWith('.mp4') && !bgPathLower.endsWith('.webm') && !bgPathLower.endsWith('.ogg')) {
            // 不是视频，移除现有视频背景（但保留图片背景）
            const existingVideo = document.getElementById('video-background');
            if (existingVideo) {
                existingVideo.pause();
                existingVideo.remove();
                window.currentVideoPath = null;
                console.log('视频背景已移除，恢复图片背景');
            }
            return;
        }
        
        // 如果视频路径没有变化，不重新加载
        if (window.currentVideoPath === bgPath) {
            console.log('视频背景路径未变化，跳过重新加载');
            return;
        }
        
        console.log('设置视频背景:', bgPath);
        window.currentVideoPath = bgPath;
        
        let video = document.getElementById('video-background');
        
        // 如果视频元素已存在，只更新源
        if (video) {
            const cleanPath = bgPath.replace(/^data/, '');
            const newSrc = `/data/${cleanPath}`;
            // 只有在源变化时才更新
            if (video.src !== newSrc && video.src !== window.location.origin + newSrc) {
                video.src = newSrc;
                video.load();
                video.play().catch(e => console.error('视频播放失败:', e));
                console.log('视频源已更新:', newSrc);
            }
        } else {
            // 创建新的视频元素
            video = document.createElement('video');
            video.id = 'video-background';
            video.autoplay = true;
            video.loop = true;
            video.muted = true;
            video.playsInline = true;
            video.style.position = 'absolute';
            video.style.top = '0';
            video.style.left = '0';
            video.style.width = '100%';
            video.style.height = '100%';
            video.style.objectFit = 'fill';
            video.style.zIndex = '0';
            
            // 设置视频源
            const cleanPath = bgPath.replace(/^data/, '');
            video.src = `/data/${cleanPath}`;
            
            // 插入到背景 div 之前
            const container = document.getElementById('container');
            const background = document.getElementById('background');
            if (container && background) {
                container.insertBefore(video, background);
                // 隐藏原来的背景
                background.style.backgroundImage = 'none';
            }
            
            console.log('视频背景已创建:', video.src);
        }
    };
    
    // 移除视频背景
    window.removeVideoBackground = function() {
        const existingVideo = document.getElementById('video-background');
        if (existingVideo) {
            existingVideo.pause();
            existingVideo.remove();
            window.currentVideoPath = null;
            console.log('视频背景已移除');
        }
        // 恢复原来的背景显示
        const background = document.getElementById('background');
        if (background) {
            background.style.backgroundImage = '';
        }
    };
})();
</script>
'''

# 文字控件支持的 JavaScript 代码
TEXT_CONTROL_SCRIPT = '''
<script>
// 文字控件支持 - 由服务器自动注入
// 文字作为独立图层，使用 CSS transform 实现整体缩放变形
(function() {
    // 保存当前页面的文字数据
    window.currentTextsData = [];
    
    // 保存原始的 loadPage 函数引用
    let originalLoadPage = null;
    
    // 获取或创建文字图层容器
    function getTextsLayer() {
        let layer = document.getElementById('texts-layer');
        if (!layer) {
            layer = document.createElement('div');
            layer.id = 'texts-layer';
            // 使用原始分辨率作为画布大小
            const originalWidth = window.originalWidth || 1920;
            const originalHeight = window.originalHeight || 1080;
            layer.style.position = 'absolute';
            layer.style.top = '0';
            layer.style.left = '0';
            layer.style.width = originalWidth + 'px';
            layer.style.height = originalHeight + 'px';
            layer.style.pointerEvents = 'none';
            layer.style.zIndex = '15';
            layer.style.transformOrigin = 'top left';
            const container = document.getElementById('container');
            if (container) {
                container.appendChild(layer);
            }
        }
        return layer;
    }
    
    // 更新文字图层缩放
    function updateTextsLayerScale() {
        const layer = document.getElementById('texts-layer');
        if (!layer) return;
        
        const windowWidth = window.innerWidth;
        const windowHeight = window.innerHeight;
        const originalWidth = window.originalWidth || 1920;
        const originalHeight = window.originalHeight || 1080;
        
        // 计算缩放比例
        const scaleX = windowWidth / originalWidth;
        const scaleY = windowHeight / originalHeight;
        
        // 应用缩放变换 - 实现整体变形
        layer.style.transform = `scale(${scaleX}, ${scaleY})`;
        
        console.log('文字图层缩放:', scaleX, scaleY);
    }
    
    // 渲染文字到图层
    function renderTextsToLayer(texts) {
        const layer = getTextsLayer();
        
        // 清空现有文字
        layer.innerHTML = '';
        
        // 添加每个文字（使用原始坐标，不缩放）
        texts.forEach(text => {
            console.log('添加文字到图层:', text.id);
            
            const textElement = document.createElement('div');
            textElement.className = 'text-item';
            textElement.id = `text-${text.id}`;
            
            // 使用原始坐标和大小（图层会整体缩放）
            textElement.style.position = 'absolute';
            textElement.style.left = `${text.x}px`;
            textElement.style.top = `${text.y}px`;
            textElement.style.width = `${text.w}px`;
            textElement.style.height = `${text.h}px`;
            textElement.style.display = 'flex';
            textElement.style.alignItems = 'center';
            textElement.style.overflow = 'hidden';
            textElement.style.whiteSpace = 'nowrap';
            
            // 根据对齐方式设置
            if (text.align === 'center') {
                textElement.style.justifyContent = 'center';
            } else if (text.align === 'right') {
                textElement.style.justifyContent = 'flex-end';
            } else {
                textElement.style.justifyContent = 'flex-start';
            }
            
            // 创建文字内容
            const textContent = document.createElement('span');
            textContent.textContent = text.text || '文字';
            textContent.style.color = text.color || '#000000';
            textContent.style.fontFamily = text.font_family || 'Microsoft YaHei';
            textContent.style.fontWeight = text.bold ? 'bold' : 'normal';
            textContent.style.fontStyle = text.italic ? 'italic' : 'normal';
            // 字体大小使用原始大小（图层缩放会自动处理）
            const fontSize = Math.max(8, Math.floor(text.h * 0.7));
            textContent.style.fontSize = `${fontSize}px`;
            
            textElement.appendChild(textContent);
            layer.appendChild(textElement);
        });
        
        // 应用缩放
        updateTextsLayerScale();
    }
    
    // 加载页面文字
    function loadPageTexts(pageId) {
        return fetch(`/api/page/${pageId}`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // 处理文字控件
                    if (data.page.texts && data.page.texts.length > 0) {
                        window.currentTextsData = data.page.texts;
                        console.log('加载文字控件:', data.page.texts.length);
                        renderTextsToLayer(data.page.texts);
                    } else {
                        window.currentTextsData = [];
                        // 清空文字图层
                        const layer = document.getElementById('texts-layer');
                        if (layer) layer.innerHTML = '';
                    }
                    
                    // 处理视频背景（只在背景是视频时处理）
                    if (data.page.bg && window.setupVideoBackground) {
                        window.setupVideoBackground(data.page.bg);
                    }
                    // 注意：图片背景由 originalLoadPage 处理，这里不处理
                }
            })
            .catch(e => {
                console.error('文字控件加载失败:', e);
            });
    }
    
    // 重写 loadPage 函数
    function loadPageWithTexts(pageId) {
        // 调用原始的 loadPage（如果已保存）
        const originalPromise = originalLoadPage ? originalLoadPage(pageId) : Promise.resolve();
        
        return originalPromise.then(() => {
            // 加载文字
            return loadPageTexts(pageId);
        });
    }
    
    // 等待 loadPage 定义完成后再重写
    function initTextControl() {
        if (typeof window.loadPage === 'function') {
            // 保存原始函数
            originalLoadPage = window.loadPage;
            // 重写 loadPage
            window.loadPage = async function(pageId) {
                return loadPageWithTexts(pageId);
            };
            console.log('文字控件已初始化，loadPage 已重写');
        } else {
            // 如果 loadPage 还未定义，稍后重试
            setTimeout(initTextControl, 100);
        }
    }
    
    // 监听窗口大小变化，更新文字图层缩放
    window.addEventListener('resize', function() {
        console.log('窗口大小变化，更新文字图层缩放');
        updateTextsLayerScale();
    });
    
    // 开始初始化
    initTextControl();
})();
</script>
'''

# 路由
@app.route('/')
def index():
    """首页"""
    global config_data
    config_data = load_cfg()
    
    # 使用内存中的 HTML 模板（打包后也能正常工作）
    html_content = INDEX_HTML_TEMPLATE
    
    # 在 </body> 之前注入视频支持脚本和文字支持脚本
    html_content = html_content.replace('</body>', VIDEO_BACKGROUND_SCRIPT + TEXT_CONTROL_SCRIPT + '</body>')
    
    return html_content


# 配置文件加载时间
config_last_loaded = 0
CONFIG_RELOAD_INTERVAL = 10  # 10秒内不重复加载

# HTML模板（用于打包后直接使用，不依赖外部文件）
INDEX_HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>中控面板</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: Arial, sans-serif;
            overflow: hidden;
            background-color: #000;
        }
        
        #container {
            position: relative;
            width: 100vw;
            height: 100vh;
            overflow: hidden;
        }
        
        #background {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-size: 100% 100%;
            background-position: top left;
            background-repeat: no-repeat;
            z-index: 0;
        }
        
        /* 确保按钮也能正确缩放 */
        .button {
            position: absolute;
            cursor: pointer;
            z-index: 10;
            transform-origin: top left;
        }
        
        .button img {
            width: 100%;
            height: 100%;
        }
        
        .status-indicator {
            position: absolute;
            z-index: 20;
            transform-origin: top left;
        }
        
        .status-indicator img {
            width: 100%;
            height: 100%;
        }
        
        .wait-image {
            position: absolute;
            z-index: 1000;
            transform-origin: top left;
        }
        
        .wait-image img {
            width: 100%;
            height: 100%;
        }
        
        /* 文字图层样式 - 作为一个整体进行缩放变形 */
        #texts-layer {
            position: absolute;
            top: 0;
            left: 0;
            pointer-events: none;
            z-index: 15;
            transform-origin: top left;
        }
        
        /* 文字控件样式 */
        .text-item {
            position: absolute;
            display: flex;
            align-items: center;
            overflow: hidden;
            white-space: nowrap;
            pointer-events: none;
        }

    </style>
</head>
<body>
    <div id="container">
        <div id="background"></div>
        <div id="buttons-container"></div>
        <div id="texts-container"></div>
        <div id="wait-image" class="wait-image" style="display: none;">
            <img id="wait-image-img" src="" alt="等待中...">
        </div>
    </div>
    
    <!-- 注册窗口 -->
    <div id="license-dialog" style="display: none; position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: white; padding: 30px; border-radius: 10px; box-shadow: 0 0 20px rgba(0,0,0,0.5); z-index: 2000;">
        <h2 style="text-align: center; margin-bottom: 20px; color: #333;">软件注册</h2>
        <div style="margin-bottom: 20px;">
            <label style="display: block; margin-bottom: 5px; font-weight: bold;">机器ID:</label>
            <input type="text" id="machine-id" style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; font-size: 16px;" readonly>
        </div>
        <div style="margin-bottom: 20px;">
            <label style="display: block; margin-bottom: 5px; font-weight: bold;">注册码:</label>
            <input type="text" id="license-key" style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; font-size: 16px;" placeholder="请输入注册码">
        </div>
        <div style="text-align: center; margin-bottom: 20px;">
            <button id="validate-license" style="background: #4CAF50; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px;">注册</button>
            <button id="close-license" style="background: #f44336; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; margin-left: 10px;">关闭</button>
        </div>
        <div id="license-message" style="text-align: center; padding: 10px; border-radius: 5px; font-weight: bold;"></div>
    </div>
    
    <!-- 遮罩层 -->
    <div id="overlay" style="display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 1999;"></div>
    
    <script>
        let currentPage = 1;
        let config = null;
        
        // 全局变量
        let originalWidth = 1920; // 默认原始宽度
        let originalHeight = 1080; // 默认原始高度
        let waitImageConfig = {
            src: '',
            x: 960,
            y: 540,
            width: 200,
            height: 200
        };
        
        // 初始化
        async function init() {
            try {
                console.log('开始初始化...');
                // 获取原始配置的分辨率和等待图片设置
                try {
                    const configResponse = await fetch('/api/config');
                    if (configResponse.ok) {
                        const configData = await configResponse.json();
                        originalWidth = configData.resolution.width;
                        originalHeight = configData.resolution.height;
                        waitImageConfig = {
                            src: configData.wait_image_src || '',
                            x: configData.wait_image_x || 960,
                            y: configData.wait_image_y || 540,
                            width: configData.wait_image_width || 200,
                            height: configData.wait_image_height || 200
                        };
                        console.log('原始分辨率:', originalWidth, 'x', originalHeight);
                        console.log('等待图片设置:', waitImageConfig);
                        // 更新等待图片
                        updateWaitImage();
                    } else {
                        // 默认值
                        originalWidth = 1920;
                        originalHeight = 1080;
                        console.log('原始分辨率:', originalWidth, 'x', originalHeight);
                    }
                } catch (error) {
                    console.error('获取配置失败:', error);
                    // 使用默认值
                    originalWidth = 1920;
                    originalHeight = 1080;
                }
                
                // 检查许可证状态
                checkLicenseStatus();
                
                // 直接加载页面，不通过根路径获取配置
                loadPage(currentPage);
            } catch (error) {
                console.error('初始化失败:', error);
            }
        }
        
        // 更新等待图片
        function updateWaitImage() {
            const waitImage = document.getElementById('wait-image');
            const waitImageImg = document.getElementById('wait-image-img');
            
            if (waitImageConfig.src) {
                // 确保路径不包含重复的data/前缀
                const srcPath = waitImageConfig.src.replace(/^data/, '');
                waitImageImg.src = `/data/${srcPath}`;
                
                // 设置位置和大小
                const windowWidth = window.innerWidth;
                const windowHeight = window.innerHeight;
                const scaleX = windowWidth / originalWidth;
                const scaleY = windowHeight / originalHeight;
                
                const scaledX = waitImageConfig.x * scaleX;
                const scaledY = waitImageConfig.y * scaleY;
                const scaledW = waitImageConfig.width * scaleX;
                const scaledH = waitImageConfig.height * scaleY;
                
                waitImage.style.left = `${scaledX}px`;
                waitImage.style.top = `${scaledY}px`;
                waitImage.style.width = `${scaledW}px`;
                waitImage.style.height = `${scaledH}px`;
            }
        }
        
        // 显示等待图片
        function showWaitImage() {
            if (waitImageConfig.src) {
                const waitImage = document.getElementById('wait-image');
                waitImage.style.display = 'block';
                console.log('显示等待图片');
            }
        }
        
        // 隐藏等待图片
        function hideWaitImage() {
            const waitImage = document.getElementById('wait-image');
            waitImage.style.display = 'none';
            console.log('隐藏等待图片');
        }
        
        // 加载页面
        // 存储当前页面的按钮配置
        let currentButtonsConfig = [];
        
        async function loadPage(pageId) {
            try {
                console.log('加载页面:', pageId);
                const response = await fetch(`/api/page/${pageId}`);
                console.log('页面请求状态:', response.status);
                const data = await response.json();
                console.log('页面数据:', data);
                
                if (data.success) {
                    const page = data.page;
                    currentPage = pageId;
                    // 存储当前页面的按钮配置
                    currentButtonsConfig = page.buttons;
                    
                    // 更新背景
                    const background = document.getElementById('background');
                    if (page.bg) {
                        console.log('设置背景:', page.bg);
                        // 确保路径不包含重复的data/前缀
                        const bgPath = page.bg.replace(/^data/, '');
                        const fullBgPath = `/data/${bgPath}`;
                        console.log('完整背景路径:', fullBgPath);
                        background.style.backgroundImage = `url('${fullBgPath}')`;
                        // 测试背景图片是否存在
                        const img = new Image();
                        img.onload = function() {
                            console.log('背景图片加载成功');
                        };
                        img.onerror = function() {
                            console.error('背景图片加载失败:', fullBgPath);
                        };
                        img.src = fullBgPath;
                    } else {
                        console.log('无背景图片');
                        background.style.backgroundImage = 'none';
                    }
                    
                    // 清空按钮容器
                    const buttonsContainer = document.getElementById('buttons-container');
                    buttonsContainer.innerHTML = '';
                    
                    // 添加按钮
                    console.log('添加按钮:', page.buttons.length);
                    page.buttons.forEach(button => {
                        console.log('添加按钮:', button.id, '类型:', button.type || 'button');
                        // 计算缩放比例
                        const windowWidth = window.innerWidth;
                        const windowHeight = window.innerHeight;
                        const scaleX = windowWidth / originalWidth;
                        const scaleY = windowHeight / originalHeight;
                        console.log('缩放比例:', scaleX, scaleY);
                        
                        const buttonElement = document.createElement('div');
                        buttonElement.className = 'button';
                        // 添加按钮ID属性，用于后续查找
                        buttonElement.setAttribute('data-button-id', button.id);
                        // 根据缩放比例调整按钮位置和大小
                        const scaledX = button.x * scaleX;
                        const scaledY = button.y * scaleY;
                        const scaledW = button.w * scaleX;
                        const scaledH = button.h * scaleY;
                        console.log('按钮原始位置:', button.x, button.y, button.w, button.h);
                        console.log('按钮缩放后位置:', scaledX, scaledY, scaledW, scaledH);
                        buttonElement.style.left = `${scaledX}px`;
                        buttonElement.style.top = `${scaledY}px`;
                        buttonElement.style.width = `${scaledW}px`;
                        buttonElement.style.height = `${scaledH}px`;
                        buttonElement.style.overflow = 'hidden';
                        
                        // 根据按钮类型添加不同内容
                        if (button.type === 'webpage') {
                            // 处理网页控件
                            console.log('处理网页控件:', button.id, 'URL:', button.url);
                            
                            // 创建iframe
                            const iframe = document.createElement('iframe');
                            iframe.src = button.url || 'about:blank';
                            iframe.style.width = '100%';
                            iframe.style.height = '100%';
                            iframe.style.border = 'none';
                            iframe.style.backgroundColor = 'white';
                            iframe.style.overflow = 'hidden';
                            iframe.scrolling = 'no';
                            iframe.frameBorder = '0';
                            iframe.allow = 'fullscreen';
                            iframe.sandbox = 'allow-same-origin allow-scripts allow-forms allow-popups allow-pointer-lock allow-network';
                            iframe.setAttribute('sandbox', 'allow-same-origin allow-scripts allow-forms allow-popups allow-pointer-lock allow-network');
                            
                            // 添加自动缩放功能
                            iframe.onload = function() {
                                try {
                                    const iframeDocument = iframe.contentDocument || iframe.contentWindow.document;
                                    const iframeBody = iframeDocument.body;
                                    
                                    // 设置iframe内部样式，禁止滚动
                                    iframeDocument.documentElement.style.overflow = 'hidden';
                                    iframeBody.style.overflow = 'hidden';
                                    iframeBody.style.margin = '0';
                                    iframeBody.style.padding = '0';
                                    
                                    // 拦截所有链接点击事件，确保在本窗口打开
                                    const links = iframeBody.querySelectorAll('a');
                                    links.forEach(link => {
                                        link.addEventListener('click', function(e) {
                                            e.preventDefault();
                                            const href = this.getAttribute('href');
                                            if (href) {
                                                iframe.src = href;
                                            }
                                        });
                                    });
                                    
                                    // 尝试自动调整大小
                                    const resizeIframe = function() {
                                        try {
                                            const iframeWidth = iframe.contentWindow.innerWidth;
                                            const iframeHeight = iframe.contentWindow.innerHeight;
                                            const containerWidth = buttonElement.clientWidth;
                                            const containerHeight = buttonElement.clientHeight;
                                            
                                            // 计算缩放比例
                                            const scaleX = containerWidth / iframeWidth;
                                            const scaleY = containerHeight / iframeHeight;
                                            const scale = Math.min(scaleX, scaleY);
                                            
                                            // 应用缩放
                                            iframe.style.transformOrigin = 'top left';
                                            iframe.style.transform = `scale(${scale})`;
                                            iframe.style.width = `${iframeWidth}px`;
                                            iframe.style.height = `${iframeHeight}px`;
                                            iframe.style.marginLeft = `${(containerWidth - iframeWidth * scale) / 2}px`;
                                            iframe.style.marginTop = `${(containerHeight - iframeHeight * scale) / 2}px`;
                                        } catch (error) {
                                            console.error('调整iframe大小失败:', error);
                                        }
                                    };
                                    
                                    // 初始调整大小
                                    resizeIframe();
                                    
                                    // 监听窗口大小变化
                                    window.addEventListener('resize', resizeIframe);
                                    
                                    // 监听iframe内部大小变化
                                    const observer = new MutationObserver(resizeIframe);
                                    observer.observe(iframeBody, {
                                        attributes: true,
                                        childList: true,
                                        subtree: true
                                    });
                                } catch (error) {
                                    console.error('设置iframe属性失败:', error);
                                }
                            };
                            
                            // 添加到容器
                            buttonElement.appendChild(iframe);
                        } else if (button.type === 'switch') {
                            // 处理开关控件
                            console.log('处理开关控件:', button.id);
                            
                            // 添加开关图片
                            const img = document.createElement('img');
                            img.className = 'switch-image';
                            // 默认显示关状态图片
                            if (button.off_src) {
                                console.log('设置开关关状态图片:', button.off_src);
                                // 确保路径不包含重复的data/前缀
                                const srcPath = button.off_src.replace(/^data/, '');
                                img.src = `/data/${srcPath}`;
                            }
                            buttonElement.appendChild(img);
                            
                            // 开关控件不使用状态指示器，因为它自己就有on_src/off_src两张图片显示状态
                            
                            // 添加点击事件
                            buttonElement.addEventListener('click', () => handleButtonClick(button.id, pageId));
                        } else if (button.type === 'aircon') {
                            // 处理空调面板控件
                            console.log('处理空调面板控件:', button.id);
                            
                            // 创建空调面板的HTML结构
                            const airconContainer = document.createElement('div');
                            airconContainer.className = 'aircon-panel';
                            airconContainer.style.width = '100%';
                            airconContainer.style.height = '100%';
                            airconContainer.style.backgroundColor = '#ffffff';
                            airconContainer.style.borderRadius = '20px';
                            airconContainer.style.padding = '30px';
                            airconContainer.style.boxSizing = 'border-box';
                            airconContainer.style.display = 'flex';
                            airconContainer.style.flexDirection = 'column';
                            airconContainer.style.boxShadow = '0 4px 20px rgba(0, 0, 0, 0.1)';
                            airconContainer.style.position = 'relative';
                            
                            // 顶部电源按钮
                            const powerButton = document.createElement('button');
                            powerButton.className = 'aircon-power-button';
                            powerButton.style.width = '60px';
                            powerButton.style.height = '60px';
                            powerButton.style.borderRadius = '50%';
                            powerButton.style.border = 'none';
                            powerButton.style.backgroundColor = button.power === 'on' ? '#4CAF50' : '#E0E0E0';
                            powerButton.style.color = button.power === 'on' ? 'white' : '#757575';
                            powerButton.style.fontSize = '14px';
                            powerButton.style.fontWeight = 'bold';
                            powerButton.style.cursor = 'pointer';
                            powerButton.style.position = 'absolute';
                            powerButton.style.top = '20px';
                            powerButton.style.right = '20px';
                            powerButton.style.boxShadow = '0 2px 8px rgba(0, 0, 0, 0.15)';
                            powerButton.style.transition = 'all 0.3s ease';
                            powerButton.textContent = button.power === 'on' ? '开' : '关';
                            airconContainer.appendChild(powerButton);
                            
                            // 品牌标识
                            const brandLogo = document.createElement('div');
                            brandLogo.style.fontSize = '18px';
                            brandLogo.style.fontWeight = 'bold';
                            brandLogo.style.color = '#2196F3';
                            brandLogo.style.marginBottom = '20px';
                            brandLogo.style.textAlign = 'center';
                            brandLogo.textContent = '智能空调';
                            airconContainer.appendChild(brandLogo);
                            
                            // 温度显示
                            const tempDisplay = document.createElement('div');
                            tempDisplay.className = 'aircon-temp-display';
                            tempDisplay.style.fontSize = '64px';
                            tempDisplay.style.fontWeight = '300';
                            tempDisplay.style.textAlign = 'center';
                            tempDisplay.style.marginBottom = '30px';
                            tempDisplay.style.color = '#212121';
                            tempDisplay.style.textShadow = '0 2px 4px rgba(0, 0, 0, 0.1)';
                            tempDisplay.textContent = `${button.temperature}°C`;
                            airconContainer.appendChild(tempDisplay);
                            
                            // 模式显示
                            const modeDisplay = document.createElement('div');
                            modeDisplay.className = 'aircon-mode-display';
                            modeDisplay.style.fontSize = '18px';
                            modeDisplay.style.textAlign = 'center';
                            modeDisplay.style.marginBottom = '40px';
                            modeDisplay.style.color = '#757575';
                            const modeMap = {
                                'auto': '自动',
                                'cool': '制冷',
                                'heat': '制热',
                                'fan': '送风',
                                'dry': '除湿'
                            };
                            modeDisplay.textContent = modeMap[button.mode] || '自动';
                            airconContainer.appendChild(modeDisplay);
                            
                            // 温度控制按钮
                            const tempControl = document.createElement('div');
                            tempControl.className = 'aircon-temp-control';
                            tempControl.style.display = 'flex';
                            tempControl.style.justifyContent = 'center';
                            tempControl.style.marginBottom = '40px';
                            
                            const tempDownButton = document.createElement('button');
                            tempDownButton.className = 'aircon-temp-button';
                            tempDownButton.style.width = '70px';
                            tempDownButton.style.height = '70px';
                            tempDownButton.style.borderRadius = '50%';
                            tempDownButton.style.border = 'none';
                            tempDownButton.style.backgroundColor = '#F5F5F5';
                            tempDownButton.style.color = '#2196F3';
                            tempDownButton.style.fontSize = '32px';
                            tempDownButton.style.fontWeight = '300';
                            tempDownButton.style.cursor = 'pointer';
                            tempDownButton.style.marginRight = '30px';
                            tempDownButton.style.boxShadow = '0 2px 8px rgba(0, 0, 0, 0.1)';
                            tempDownButton.style.transition = 'all 0.3s ease';
                            tempDownButton.textContent = '−';
                            tempControl.appendChild(tempDownButton);
                            
                            const tempUpButton = document.createElement('button');
                            tempUpButton.className = 'aircon-temp-button';
                            tempUpButton.style.width = '70px';
                            tempUpButton.style.height = '70px';
                            tempUpButton.style.borderRadius = '50%';
                            tempUpButton.style.border = 'none';
                            tempUpButton.style.backgroundColor = '#F5F5F5';
                            tempUpButton.style.color = '#2196F3';
                            tempUpButton.style.fontSize = '32px';
                            tempUpButton.style.fontWeight = '300';
                            tempUpButton.style.cursor = 'pointer';
                            tempUpButton.style.boxShadow = '0 2px 8px rgba(0, 0, 0, 0.1)';
                            tempUpButton.style.transition = 'all 0.3s ease';
                            tempUpButton.textContent = '+';
                            tempControl.appendChild(tempUpButton);
                            
                            airconContainer.appendChild(tempControl);
                            
                            // 模式和风速控制
                            const modeFanControl = document.createElement('div');
                            modeFanControl.className = 'aircon-mode-fan-control';
                            modeFanControl.style.display = 'flex';
                            modeFanControl.style.justifyContent = 'space-around';
                            modeFanControl.style.marginBottom = '30px';
                            
                            // 模式控制
                            const modeControl = document.createElement('div');
                            modeControl.className = 'aircon-mode-control';
                            modeControl.style.display = 'flex';
                            modeControl.style.flexDirection = 'column';
                            modeControl.style.alignItems = 'center';
                            
                            const modeLabel = document.createElement('div');
                            modeLabel.style.fontSize = '14px';
                            modeLabel.style.marginBottom = '10px';
                            modeLabel.style.color = '#757575';
                            modeLabel.textContent = '模式';
                            modeControl.appendChild(modeLabel);
                            
                            const modeOptions = [
                                { value: 'auto', text: '自动' },
                                { value: 'cool', text: '制冷' },
                                { value: 'heat', text: '制热' },
                                { value: 'fan', text: '送风' },
                                { value: 'dry', text: '除湿' }
                            ];
                            
                            const modeButtons = document.createElement('div');
                            modeButtons.style.display = 'flex';
                            modeButtons.style.flexWrap = 'wrap';
                            modeButtons.style.justifyContent = 'center';
                            modeButtons.style.gap = '8px';
                            
                            modeOptions.forEach(option => {
                                const modeButton = document.createElement('button');
                                modeButton.className = 'aircon-mode-option';
                                modeButton.style.padding = '8px 16px';
                                modeButton.style.borderRadius = '20px';
                                modeButton.style.border = '1px solid #E0E0E0';
                                modeButton.style.backgroundColor = option.value === button.mode ? '#2196F3' : 'white';
                                modeButton.style.color = option.value === button.mode ? 'white' : '#757575';
                                modeButton.style.fontSize = '12px';
                                modeButton.style.cursor = 'pointer';
                                modeButton.style.transition = 'all 0.3s ease';
                                modeButton.textContent = option.text;
                                modeButton.value = option.value;
                                modeButtons.appendChild(modeButton);
                            });
                            
                            modeControl.appendChild(modeButtons);
                            modeFanControl.appendChild(modeControl);
                            
                            // 风速控制
                            const fanControl = document.createElement('div');
                            fanControl.className = 'aircon-fan-control';
                            fanControl.style.display = 'flex';
                            fanControl.style.flexDirection = 'column';
                            fanControl.style.alignItems = 'center';
                            
                            const fanLabel = document.createElement('div');
                            fanLabel.style.fontSize = '14px';
                            fanLabel.style.marginBottom = '10px';
                            fanLabel.style.color = '#757575';
                            fanLabel.textContent = '风速';
                            fanControl.appendChild(fanLabel);
                            
                            const fanOptions = [
                                { value: 'low', text: '低' },
                                { value: 'medium', text: '中' },
                                { value: 'high', text: '高' },
                                { value: 'auto', text: '自动' }
                            ];
                            
                            const fanButtons = document.createElement('div');
                            fanButtons.style.display = 'flex';
                            fanButtons.style.gap = '8px';
                            
                            fanOptions.forEach(option => {
                                const fanButton = document.createElement('button');
                                fanButton.className = 'aircon-fan-option';
                                fanButton.style.padding = '8px 16px';
                                fanButton.style.borderRadius = '20px';
                                fanButton.style.border = '1px solid #E0E0E0';
                                fanButton.style.backgroundColor = option.value === button.fan_speed ? '#4CAF50' : 'white';
                                fanButton.style.color = option.value === button.fan_speed ? 'white' : '#757575';
                                fanButton.style.fontSize = '12px';
                                fanButton.style.cursor = 'pointer';
                                fanButton.style.transition = 'all 0.3s ease';
                                fanButton.textContent = option.text;
                                fanButton.value = option.value;
                                fanButtons.appendChild(fanButton);
                            });
                            
                            fanControl.appendChild(fanButtons);
                            modeFanControl.appendChild(fanControl);
                            
                            airconContainer.appendChild(modeFanControl);
                            
                            // 底部状态信息
                            const statusInfo = document.createElement('div');
                            statusInfo.style.fontSize = '12px';
                            statusInfo.style.color = '#9E9E9E';
                            statusInfo.style.textAlign = 'center';
                            statusInfo.style.marginTop = 'auto';
                            statusInfo.textContent = '智能模式 | 节能运行';
                            airconContainer.appendChild(statusInfo);
                            
                            // 添加到容器
                            buttonElement.appendChild(airconContainer);
                            
                            // 添加事件监听器
                            powerButton.addEventListener('click', () => {
                                console.log('空调电源按钮点击');
                                // 这里可以添加电源控制逻辑
                            });
                            
                            tempDownButton.addEventListener('click', () => {
                                console.log('温度减按钮点击');
                                // 这里可以添加温度减逻辑
                            });
                            
                            tempUpButton.addEventListener('click', () => {
                                console.log('温度加按钮点击');
                                // 这里可以添加温度加逻辑
                            });
                            
                            // 模式按钮事件
                            const modeButtonElements = modeButtons.querySelectorAll('.aircon-mode-option');
                            modeButtonElements.forEach(button => {
                                button.addEventListener('click', () => {
                                    console.log('模式选择改变:', button.value);
                                    // 这里可以添加模式改变逻辑
                                });
                            });
                            
                            // 风速按钮事件
                            const fanButtonElements = fanButtons.querySelectorAll('.aircon-fan-option');
                            fanButtonElements.forEach(button => {
                                button.addEventListener('click', () => {
                                    console.log('风速选择改变:', button.value);
                                    // 这里可以添加风速改变逻辑
                                });
                            });
                        } else {
                            // 处理普通按钮
                            // 添加按钮图片
                            const img = document.createElement('img');
                            if (button.src) {
                                console.log('设置按钮图片:', button.src);
                                // 确保路径不包含重复的data/前缀
                                const srcPath = button.src.replace(/^data/, '');
                                img.src = `/data/${srcPath}`;
                            }
                            buttonElement.appendChild(img);
                            
                            // 添加状态指示器
                            if (button.status_enable) {
                                console.log('添加状态指示器');
                                const statusIndicator = document.createElement('div');
                                statusIndicator.className = 'status-indicator';
                                // 添加按钮ID属性，用于后续查找
                                statusIndicator.setAttribute('data-button-id', button.id);
                                // 根据缩放比例调整状态指示器位置和大小
                                const scaledStatusX = (button.x + button.status_x) * scaleX;
                                const scaledStatusY = (button.y + button.status_y) * scaleY;
                                const scaledStatusW = button.status_width * scaleX;
                                const scaledStatusH = button.status_height * scaleY;
                                console.log('状态指示器缩放后位置:', scaledStatusX, scaledStatusY, scaledStatusW, scaledStatusH);
                                statusIndicator.style.left = `${scaledStatusX}px`;
                                statusIndicator.style.top = `${scaledStatusY}px`;
                                statusIndicator.style.width = `${scaledStatusW}px`;
                                statusIndicator.style.height = `${scaledStatusH}px`;
                                
                                // 使用默认状态图片
                                const statusImg = document.createElement('img');
                                if (button.status_off_src) {
                                    // 确保路径不包含重复的data/前缀
                                    const statusPath = button.status_off_src.replace(/^data/, '');
                                    statusImg.src = `/data/${statusPath}`;
                                }
                                statusIndicator.appendChild(statusImg);
                                
                                buttonsContainer.appendChild(statusIndicator);
                            }
                            
                            // 添加点击事件
                            buttonElement.addEventListener('click', () => handleButtonClick(button.id, pageId));
                        }
                        
                        buttonsContainer.appendChild(buttonElement);
                    });
                } else {
                    console.error('加载页面失败:', data.message);
                }
            } catch (error) {
                console.error('加载页面失败:', error);
            }
        }
        
        // 处理按钮点击
        async function handleButtonClick(buttonId, pageId) {
            try {
                console.log('按钮点击:', buttonId, '页面:', pageId);
                
                // 显示等待图片
                showWaitImage();
                
                const response = await fetch('/api/button/click', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ button_id: buttonId, page_id: pageId })
                });
                
                const data = await response.json();
                console.log('按钮点击响应:', data);
                
                // 隐藏等待图片
                hideWaitImage();
                
                if (data.success && data.switch_page) {
                    // 页面跳转
                    loadPage(data.switch_page);
                } else if (data.success && data.switch_state !== undefined) {
                    // 更新开关状态图片和状态指示器
                    console.log('更新开关状态:', buttonId, '状态:', data.switch_state);
                    updateSwitchImage(buttonId, data.switch_state);
                    updateStatusIndicator(buttonId, data.switch_state);
                }
            } catch (error) {
                console.error('处理按钮点击失败:', error);
                // 隐藏等待图片
                hideWaitImage();
            }
        }
        
        // 更新开关图片
        function updateSwitchImage(buttonId, state) {
            try {
                // 查找开关控件的容器
                const buttonsContainer = document.getElementById('buttons-container');
                const buttonElements = buttonsContainer.querySelectorAll('.button');
                
                buttonElements.forEach(element => {
                    // 查找开关图片
                    const img = element.querySelector('.switch-image');
                    if (img) {
                        // 获取按钮数据（这里需要确保按钮容器有按钮ID信息）
                        // 由于我们没有直接存储按钮ID，我们需要通过其他方式找到对应的按钮
                        // 这里我们假设每个按钮容器都有一个data-button-id属性
                        const containerButtonId = element.getAttribute('data-button-id');
                        if (containerButtonId === buttonId) {
                            // 查找对应的按钮配置
                            const buttonConfig = findButtonConfig(buttonId);
                            if (buttonConfig) {
                                // 根据状态更新图片
                                const src = state === 'on' ? buttonConfig.on_src : buttonConfig.off_src;
                                if (src) {
                                    console.log('更新开关图片:', buttonId, '状态:', state, '图片:', src);
                                    // 确保路径不包含重复的data/前缀
                                    const srcPath = src.replace(/^data/, '');
                                    img.src = `/data/${srcPath}`;
                                }
                            }
                        }
                    }
                });
            } catch (error) {
                console.error('更新开关图片失败:', error);
            }
        }
        
        // 更新状态指示器
        function updateStatusIndicator(buttonId, state) {
            try {
                // 查找状态指示器
                const buttonsContainer = document.getElementById('buttons-container');
                const statusIndicators = buttonsContainer.querySelectorAll('.status-indicator');
                
                // 查找对应的按钮配置
                const buttonConfig = findButtonConfig(buttonId);
                if (!buttonConfig) return;
                
                // 更新状态指示器
                statusIndicators.forEach(indicator => {
                    // 查找与当前按钮ID匹配的状态指示器
                    const indicatorButtonId = indicator.getAttribute('data-button-id');
                    if (indicatorButtonId === buttonId) {
                        const statusImg = indicator.querySelector('img');
                        if (statusImg) {
                            // 根据状态更新图片
                            // 首先尝试使用按钮特定的状态图片
                            let statusSrc = '';
                            if (state === 'on') {
                                statusSrc = buttonConfig.status_on_src || '';
                            } else {
                                statusSrc = buttonConfig.status_off_src || '';
                            }
                            
                            if (statusSrc) {
                                console.log('更新状态指示器:', buttonId, '状态:', state, '图片:', statusSrc);
                                // 确保路径不包含重复的data/前缀
                                const statusPath = statusSrc.replace(/^data/, '');
                                statusImg.src = `/data/${statusPath}`;
                            }
                        }
                    }
                });
            } catch (error) {
                console.error('更新状态指示器失败:', error);
            }
        }
        
        // 查找按钮配置
        function findButtonConfig(buttonId) {
            // 从当前页面的按钮配置中查找
            for (const button of currentButtonsConfig) {
                if (button.id === buttonId) {
                    return button;
                }
            }
            return null;
        }
        
        // 处理页面缩放 - 只更新缩放，不重新加载数据
        function handleResize() {
            console.log('处理页面缩放');
            const container = document.getElementById('container');
            const windowWidth = window.innerWidth;
            const windowHeight = window.innerHeight;
            console.log('窗口大小:', windowWidth, 'x', windowHeight);
            
            // 设置容器大小为窗口大小
            container.style.width = `${windowWidth}px`;
            container.style.height = `${windowHeight}px`;
            
            // 计算缩放比例
            const scaleX = windowWidth / originalWidth;
            const scaleY = windowHeight / originalHeight;
            
            // 更新按钮位置和大小
            updateButtonsScale(scaleX, scaleY);
            
            // 更新等待图片位置和大小
            updateWaitImage();
            
            // 更新状态指示器位置
            updateStatusIndicatorsScale(scaleX, scaleY);
        }
        
        // 更新按钮缩放
        function updateButtonsScale(scaleX, scaleY) {
            const buttonsContainer = document.getElementById('buttons-container');
            if (!buttonsContainer) return;
            
            // 更新所有按钮
            const buttons = buttonsContainer.querySelectorAll('.button');
            buttons.forEach(button => {
                const buttonId = button.getAttribute('data-button-id');
                const buttonConfig = findButtonConfig(buttonId);
                if (buttonConfig) {
                    button.style.left = `${buttonConfig.x * scaleX}px`;
                    button.style.top = `${buttonConfig.y * scaleY}px`;
                    button.style.width = `${buttonConfig.w * scaleX}px`;
                    button.style.height = `${buttonConfig.h * scaleY}px`;
                }
            });
            
            console.log('按钮缩放更新完成');
        }
        
        // 更新状态指示器缩放
        function updateStatusIndicatorsScale(scaleX, scaleY) {
            const buttonsContainer = document.getElementById('buttons-container');
            if (!buttonsContainer) return;
            
            const indicators = buttonsContainer.querySelectorAll('.status-indicator');
            indicators.forEach(indicator => {
                const buttonId = indicator.getAttribute('data-button-id');
                const buttonConfig = findButtonConfig(buttonId);
                if (buttonConfig && buttonConfig.status_enable) {
                    indicator.style.left = `${(buttonConfig.x + buttonConfig.status_x) * scaleX}px`;
                    indicator.style.top = `${(buttonConfig.y + buttonConfig.status_y) * scaleY}px`;
                    indicator.style.width = `${buttonConfig.status_width * scaleX}px`;
                    indicator.style.height = `${buttonConfig.status_height * scaleY}px`;
                }
            });
            
            console.log('状态指示器缩放更新完成');
        }
        
        // 检查许可证状态
        async function checkLicenseStatus() {
            try {
                const response = await fetch('/api/license/status');
                if (response.ok) {
                    const data = await response.json();
                    console.log('许可证状态:', data);
                    if (!data.valid) {
                        console.log('许可证无效，显示注册窗口');
                        // 在未授权状态下，自动弹出注册窗口
                        openLicenseDialog();
                    }
                }
            } catch (error) {
                console.error('检查许可证状态失败:', error);
            }
        }
        
        // 打开注册窗口
        async function openLicenseDialog() {
            try {
                // 获取机器ID
                const response = await fetch('/api/license/machine-id');
                if (response.ok) {
                    const data = await response.json();
                    if (data.success) {
                        document.getElementById('machine-id').value = data.machine_id;
                        document.getElementById('license-key').value = '';
                        document.getElementById('license-message').textContent = '';
                        document.getElementById('license-dialog').style.display = 'block';
                        document.getElementById('overlay').style.display = 'block';
                    }
                }
            } catch (error) {
                console.error('获取机器ID失败:', error);
            }
        }
        
        // 关闭注册窗口
        function closeLicenseDialog() {
            document.getElementById('license-dialog').style.display = 'none';
            document.getElementById('overlay').style.display = 'none';
            // 20秒后再次弹出注册窗口
            setTimeout(() => {
                // 再次检查许可证状态，如果仍然未授权，则显示注册窗口
                checkLicenseStatus();
            }, 10000);
        }
        
        // 验证注册码
        async function validateLicense() {
            try {
                const licenseKey = document.getElementById('license-key').value;
                if (!licenseKey) {
                    document.getElementById('license-message').textContent = '请输入注册码';
                    document.getElementById('license-message').style.color = 'red';
                    return;
                }
                
                const response = await fetch('/api/license/validate', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ license_key: licenseKey })
                });
                
                if (response.ok) {
                    const data = await response.json();
                    if (data.success) {
                        document.getElementById('license-message').textContent = data.message;
                        document.getElementById('license-message').style.color = 'green';
                        // 3秒后关闭窗口
                        setTimeout(closeLicenseDialog, 3000);
                    } else {
                        document.getElementById('license-message').textContent = data.message;
                        document.getElementById('license-message').style.color = 'red';
                    }
                }
            } catch (error) {
                console.error('验证注册码失败:', error);
                document.getElementById('license-message').textContent = '验证失败，请重试';
                document.getElementById('license-message').style.color = 'red';
            }
        }
        
        // 定期更新按钮状态
        async function updateButtonStatus() {
            try {
                const response = await fetch('/api/button/status');
                if (response.ok) {
                    const data = await response.json();
                    if (data.success) {
                        const states = data.states;
                        // 更新开关状态和状态指示器
                        for (const buttonId in states) {
                            updateSwitchImage(buttonId, states[buttonId]);
                            updateStatusIndicator(buttonId, states[buttonId]);
                        }
                    }
                }
            } catch (error) {
                console.error('更新按钮状态失败:', error);
            }
        }
        
        // 初始化
        console.log('调用init()');
        init();
        
        // 每5秒更新一次按钮状态
        setInterval(updateButtonStatus, 5000);
        // 初始调用一次
        updateButtonStatus();
        
        // 监听窗口大小变化
        window.addEventListener('resize', handleResize);
        // 初始调用一次
        handleResize();
        
        // 键盘回车事件监听
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                // 打开注册窗口
                openLicenseDialog();
            }
        });
        
        // 绑定按钮事件
        document.addEventListener('DOMContentLoaded', function() {
            const validateBtn = document.getElementById('validate-license');
            const closeBtn = document.getElementById('close-license');
            
            if (validateBtn) {
                validateBtn.addEventListener('click', validateLicense);
            }
            
            if (closeBtn) {
                closeBtn.addEventListener('click', closeLicenseDialog);
            }
        });
    </script>
</body>
</html>'''

@app.route('/api/config')
def get_config():
    """获取配置信息"""
    global config_data
    global config_last_loaded
    current_time = time.time()
    
    # 检查是否需要重新加载配置
    if not config_data or (current_time - config_last_loaded > CONFIG_RELOAD_INTERVAL):
        config_data = load_cfg()
        config_last_loaded = current_time
        logger.info("配置文件已加载")
    return jsonify(config_data)

@app.route('/api/license/machine-id')
def get_machine_id_api():
    """获取机器ID"""
    try:
        machine_id = get_machine_id()
        return jsonify({'success': True, 'machine_id': machine_id})
    except Exception as e:
        logger.error(f"获取机器ID失败: {e}")
        return jsonify({'success': False, 'message': '获取机器ID失败'})

@app.route('/api/license/validate', methods=['POST'])
def validate_license_api():
    """验证注册码"""
    try:
        data = request.get_json()
        license_key = data.get('license_key', '')
        
        if not license_key:
            return jsonify({'success': False, 'message': '请输入注册码'})
        
        machine_id = get_machine_id()
        logger.info(f"验证注册码，机器ID: {machine_id}")
        valid, message = validate_license_key(machine_id, license_key)
        
        if valid:
            logger.info(f"注册码验证成功，过期日期: {message}")
            # 使用已经设置好的隐蔽路径
            global LICENSE_FILE, TIMESTAMP_FILE
            logger.info(f"使用隐蔽路径保存许可证: {LICENSE_FILE}")
            logger.info(f"使用隐蔽路径保存时间戳: {TIMESTAMP_FILE}")
            
            # 确保目录存在
            license_dir = os.path.dirname(LICENSE_FILE)
            if not os.path.exists(license_dir):
                try:
                    os.makedirs(license_dir, exist_ok=True)
                    logger.info(f"目录创建成功: {license_dir}")
                except Exception as e:
                    logger.error(f"创建目录失败: {e}")
                    return jsonify({'success': False, 'message': '创建许可证目录失败'})
            
            # 保存许可证信息
            save_success = save_license_info(machine_id, license_key, message)
            if save_success:
                logger.info(f"许可证信息保存成功，文件路径: {LICENSE_FILE}")
                # 立即检查许可证状态，验证保存是否成功
                status_valid, status_message = check_license_status()
                if status_valid:
                    logger.info(f"许可证状态检查成功: {status_message}")
                    return jsonify({'success': True, 'message': f'注册成功！过期日期: {message}'})
                else:
                    logger.error(f"许可证状态检查失败: {status_message}")
                    return jsonify({'success': False, 'message': f'注册成功但许可证状态检查失败: {status_message}'})
            else:
                logger.error(f"保存许可证信息失败")
                return jsonify({'success': False, 'message': '保存许可证信息失败'})
        else:
            logger.warning(f"注册码验证失败: {message}")
            return jsonify({'success': False, 'message': message})
    except Exception as e:
        logger.error(f"验证注册码失败: {e}")
        return jsonify({'success': False, 'message': f'验证失败: {str(e)}'})

@app.route('/api/license/status')
def get_license_status_api():
    """获取许可证状态"""
    try:
        valid, message = check_license_status()
        return jsonify({'success': True, 'valid': valid, 'message': message})
    except Exception as e:
        logger.error(f"获取许可证状态失败: {e}")
        return jsonify({'success': False, 'message': '获取状态失败'})


@app.route('/api/button/click', methods=['POST'])
def button_click():
    """处理按钮点击事件"""
    # 检查许可证状态
    valid, message = check_license_status()
    if not valid:
        logger.warning("未授权访问: 按钮点击")
        return jsonify({'success': False, 'message': '未授权，请先注册软件'})
    
    logger.info("收到按钮点击请求")
    data = request.get_json()
    button_id = data.get('button_id')
    page_id = data.get('page_id')
    logger.info(f"按钮ID: {button_id}, 页面ID: {page_id}")

    global config_data
    global config_last_loaded
    current_time = time.time()
    
    # 检查是否需要重新加载配置
    if not config_data or (current_time - config_last_loaded > CONFIG_RELOAD_INTERVAL):
        logger.info("加载配置数据")
        config_data = load_cfg()
        config_last_loaded = current_time

    # 查找按钮
    logger.info("查找按钮")
    button = None
    for page in config_data['pages']:
        if page['page'] == page_id:
            logger.info(f"找到页面: {page_id}")
            for btn in page['buttons']:
                if btn['id'] == button_id:
                    button = btn
                    logger.info(f"找到按钮: {button_id}")
                    break
            if button:
                break

    if not button:
        logger.warning(f"未找到按钮: {button_id}")
        return jsonify({'success': False, 'message': '按钮不存在'})

    # 执行按钮命令
    commands = button.get('commands', [])
    logger.info(f"执行按钮命令，命令数量: {len(commands)}")
    results = []
    
    # 对于开关按钮，根据状态执行相应的命令
    if button.get('type') == 'switch':
        # 获取当前状态，默认为off
        current_state = switch_states.get(button_id, 'off')
        # 切换状态
        new_state = 'on' if current_state == 'off' else 'off'
        switch_states[button_id] = new_state
        # 标记需要跳过一次检测（下一次检测结果不更新，等待再下一次）
        pending_skip[button_id] = 1
        logger.info(f"开关按钮 {button_id} 状态切换: {current_state} -> {new_state} (跳过一次检测)")
        
        # 执行对应状态的命令
        for i, cmd in enumerate(commands):
            # 只执行与当前状态匹配的命令
            if cmd.get('state') == new_state:
                logger.info(f"执行命令 {i+1}/{len(commands)}: {cmd['type']} (状态: {new_state})")
                result = execute_command(cmd, config_data['udp_commands'], config_data['udp_groups'])
                results.append(result)
                logger.info(f"命令执行结果: {'成功' if result else '失败'}")
    else:
        # 对于普通按钮，执行所有命令
        for i, cmd in enumerate(commands):
            logger.info(f"执行命令 {i+1}/{len(commands)}: {cmd['type']}")
            result = execute_command(cmd, config_data['udp_commands'], config_data['udp_groups'])
            results.append(result)
            logger.info(f"命令执行结果: {'成功' if result else '失败'}")

    # 检查是否有页面跳转
    switch_page = button.get('switch_page', 0)
    if switch_page > 0:
        logger.info(f"页面跳转: {switch_page}")
        # 对于开关按钮，返回新状态
        if button.get('type') == 'switch':
            return jsonify({'success': True, 'switch_page': switch_page, 'switch_state': switch_states.get(button_id, 'off')})
        else:
            return jsonify({'success': True, 'switch_page': switch_page})

    # 对于开关按钮，返回新状态
    if button.get('type') == 'switch':
        logger.info("处理完成，返回开关状态")
        return jsonify({'success': True, 'switch_state': switch_states.get(button_id, 'off')})

    logger.info("处理完成")
    return jsonify({'success': True})


@app.route('/api/page/<int:page_id>')
def get_page(page_id):
    """获取指定页面的配置"""
    global config_data
    if not config_data:
        config_data = load_cfg()

    for page in config_data['pages']:
        if page['page'] == page_id:
            return jsonify({'success': True, 'page': page})

    return jsonify({'success': False, 'message': '页面不存在'})


@app.route('/api/button/status')
def get_button_status():
    """获取按钮状态"""
    global switch_states
    logger.info(f"[状态API] 返回按钮状态: {len(switch_states)} 个按钮")
    return jsonify({'success': True, 'states': switch_states})


@app.route('/data/<path:filename>')
def serve_data(filename):
    """提供data目录下的文件"""
    # 获取data目录的绝对路径（支持打包后的exe）
    if getattr(sys, 'frozen', False):
        # 打包后的exe环境
        base_dir = os.path.dirname(sys.executable)
    else:
        # 开发环境
        base_dir = os.path.dirname(os.path.abspath(__file__))
    
    data_dir = os.path.join(base_dir, 'data')
    
    # 根据文件扩展名设置正确的 MIME 类型
    import mimetypes
    
    # 确保 MP4 视频文件的 MIME 类型正确
    if filename.lower().endswith('.mp4'):
        return send_from_directory(data_dir, filename, mimetype='video/mp4')
    elif filename.lower().endswith('.webm'):
        return send_from_directory(data_dir, filename, mimetype='video/webm')
    elif filename.lower().endswith('.ogg') or filename.lower().endswith('.ogv'):
        return send_from_directory(data_dir, filename, mimetype='video/ogg')
    else:
        return send_from_directory(data_dir, filename)


@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    """文件上传功能"""
    if request.method == 'POST':
        # 检查是否有文件被上传
        if 'config_file' in request.files:
            config_file = request.files['config_file']
            if config_file.filename == 'config.ini':
                # 保存配置文件
                config_file.save('config.ini')
                # 重新加载配置
                global config_data
                config_data = load_cfg()
                
        # 处理data目录文件上传
        for key, file in request.files.items():
            if key.startswith('data_file_') and file.filename:
                # 确保data目录存在
                if not os.path.exists('data'):
                    os.makedirs('data')
                # 保存文件到data目录
                # 处理可能包含路径的文件名
                file_path = os.path.join('data', file.filename)
                # 确保文件所在目录存在
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                file.save(file_path)
        
        return jsonify({'success': True, 'message': '文件上传成功'})
    
    # GET请求返回上传界面
    return '''
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>文件上传</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
            }
            h1 {
                text-align: center;
                color: #333;
            }
            .upload-form {
                background-color: #f5f5f5;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .form-group {
                margin-bottom: 20px;
            }
            label {
                display: block;
                margin-bottom: 8px;
                font-weight: bold;
                color: #555;
            }
            input[type="file"] {
                width: 100%;
                padding: 10px;
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: white;
            }
            button {
                background-color: #4CAF50;
                color: white;
                padding: 12px 20px;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                font-size: 16px;
            }
            button:hover {
                background-color: #45a049;
            }
            .message {
                margin-top: 20px;
                padding: 10px;
                border-radius: 4px;
                text-align: center;
            }
            .success {
                background-color: #d4edda;
                color: #155724;
                border: 1px solid #c3e6cb;
            }
            .error {
                background-color: #f8d7da;
                color: #721c24;
                border: 1px solid #f5c6cb;
            }
        </style>
    </head>
    <body>
        <h1>中控面板配置上传</h1>
        <div class="upload-form">
            <form method="post" enctype="multipart/form-data">
                <div class="form-group">
                    <label for="config_file">配置文件 (config.ini):</label>
                    <input type="file" id="config_file" name="config_file" accept=".ini">
                </div>
                <div class="form-group">
                    <label for="data_files">资源文件 (图片、视频等):</label>
                    <input type="file" id="data_files" name="data_files" multiple accept="image/*,video/*">
                </div>
                <button type="submit">上传文件</button>
            </form>
        </div>
        <div id="message" class="message" style="display: none;"></div>
        
        <script>
            // 监听表单提交
            document.querySelector('form').addEventListener('submit', function(e) {
                e.preventDefault();
                
                const formData = new FormData(this);
                const messageDiv = document.getElementById('message');
                
                fetch('/upload', {
                    method: 'POST',
                    body: formData
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        messageDiv.className = 'message success';
                        messageDiv.textContent = data.message;
                    } else {
                        messageDiv.className = 'message error';
                        messageDiv.textContent = data.message || '上传失败';
                    }
                    messageDiv.style.display = 'block';
                    
                    // 3秒后隐藏消息
                    setTimeout(() => {
                        messageDiv.style.display = 'none';
                    }, 3000);
                })
                .catch(error => {
                    messageDiv.className = 'message error';
                    messageDiv.textContent = '上传失败: ' + error.message;
                    messageDiv.style.display = 'block';
                });
            });
        </script>
    </body>
    </html>
    '''


# 重启Flask应用的函数
def restart_flask_app(port):
    """重启Flask应用"""
    global tray_icon_instance, qt_app
    print("[系统托盘] 正在重启服务器...")
    
    # 关闭托盘图标
    if tray_icon_instance:
        tray_icon_instance.hide()
        tray_icon_instance = None
    
    # 退出Qt应用
    if qt_app:
        qt_app.quit()
        qt_app = None
    
    # 使用os.execv重启当前进程
    python = sys.executable
    os.execl(python, python, *sys.argv)


# 全局变量存储托盘图标实例
tray_icon_instance = None
qt_app = None

# 创建系统托盘图标的函数（在主线程中调用）
def create_tray_icon():
    """创建系统托盘图标"""
    global tray_icon_instance, qt_app
    
    if not TRAY_SUPPORT:
        print("[系统托盘] 系统托盘功能不可用")
        return None
    
    try:
        # 创建Qt应用
        qt_app = QApplication.instance()
        if not qt_app:
            qt_app = QApplication(sys.argv)
        
        # 创建托盘图标
        tray_icon = QSystemTrayIcon()
        
        # 设置图标（使用默认图标或自定义图标）
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'icon.ico')
        if os.path.exists(icon_path):
            tray_icon.setIcon(QIcon(icon_path))
        else:
            # 使用系统默认图标
            from PySide6.QtWidgets import QStyle
            tray_icon.setIcon(qt_app.style().standardIcon(QStyle.SP_ComputerIcon))
        
        tray_icon.setToolTip("中控服务器运行中")
        
        # 创建右键菜单
        menu = QMenu()
        
        # 显示状态
        status_action = QAction("中控服务器运行中", tray_icon)
        status_action.setEnabled(False)
        menu.addAction(status_action)
        menu.addSeparator()
        
        # 打开网页
        def open_webpage():
            import webbrowser
            webbrowser.open("http://localhost:5000")
        
        open_action = QAction("打开控制面板", tray_icon)
        open_action.triggered.connect(open_webpage)
        menu.addAction(open_action)
        menu.addSeparator()
        
        # 重启服务
        def restart_server():
            print("[系统托盘] 重启服务器")
            restart_flask_app(5000)
        
        restart_action = QAction("重启服务", tray_icon)
        restart_action.triggered.connect(restart_server)
        menu.addAction(restart_action)
        
        # 退出
        def exit_server():
            print("[系统托盘] 退出服务器")
            tray_icon.hide()
            qt_app.quit()
            os._exit(0)
        
        exit_action = QAction("退出", tray_icon)
        exit_action.triggered.connect(exit_server)
        menu.addAction(exit_action)
        
        # 设置菜单
        tray_icon.setContextMenu(menu)
        
        # 显示托盘图标
        tray_icon.show()
        
        tray_icon_instance = tray_icon
        print("[系统托盘] 系统托盘图标已创建")
        return qt_app
        
    except Exception as e:
        print(f"[系统托盘] 创建失败: {e}")
        return None


if __name__ == '__main__':
    # 确保static目录存在
    if not os.path.exists('static'):
        os.makedirs('static')
    
    # 确保data目录存在
    if not os.path.exists('data'):
        os.makedirs('data')
    
    # 检查许可证状态
    print("检查许可证状态...")
    valid, message = check_license_status()
    if not valid:
        print(f"\n未注册或许可证已过期:")
        print(f"状态: {message}")
        print(f"机器ID: {get_machine_id()}")
        print("\n请在网页界面中按回车键打开注册窗口进行注册")
        print("服务将继续运行，但某些功能可能受限")
    else:
        print(f"\n许可证状态:")
        print(f"状态: 有效")
        print(f"过期日期: {message}")
        print(f"机器ID: {get_machine_id()}")
    
    # HTML模板已内置于 INDEX_HTML_TEMPLATE 变量中
    # 无需创建外部模板文件，打包后也能正常工作
    
    # 启动服务器
    # 加载配置，获取网页端口
    cfg = load_cfg()
    web_port = 5000  # 默认端口
    if 'network' in cfg and 'web_port' in cfg['network']:
        try:
            web_port = int(cfg['network']['web_port'])
        except (ValueError, TypeError):
            web_port = 5000
    
    # 启动系统托盘图标（如果支持）
    qt_app = None
    if TRAY_SUPPORT:
        try:
            print("[系统托盘] 启动系统托盘图标...")
            qt_app = create_tray_icon()
            if qt_app:
                print("[系统托盘] 系统托盘图标已启动")
            else:
                print("[系统托盘] 系统托盘图标启动失败")
        except Exception as e:
            print(f"[系统托盘] 启动失败: {e}")
    else:
        print("[系统托盘] 系统托盘功能不可用")
    
    # 尝试启动服务器（在新线程中启动Flask，主线程运行Qt事件循环）
    def run_flask():
        try:
            print(f"[服务器] 尝试启动，使用端口: {web_port}")
            app.run(host='0.0.0.0', port=web_port, debug=False, threaded=True)
        except PermissionError:
            print(f"[错误] 权限不足，无法绑定到端口 {web_port}")
            print("[提示] 1-1023端口需要root权限，建议使用1024以上的端口")
            # 尝试使用默认端口5000
            print("[服务器] 尝试使用默认端口5000启动...")
            app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
        except OSError as e:
            if "Address already in use" in str(e):
                print(f"[错误] 端口 {web_port} 已被占用")
                print("[提示] 请关闭占用该端口的进程，或修改配置文件中的web_port设置")
            else:
                print(f"[错误] 启动服务器时出错: {e}")
    
    # 如果托盘图标启动成功，在新线程中启动Flask，主线程运行Qt事件循环
    if qt_app:
        flask_thread = threading.Thread(target=run_flask, daemon=True)
        flask_thread.start()
        print("[系统托盘] 进入Qt事件循环，托盘图标已激活")
        qt_app.exec()
    else:
        # 没有托盘图标，直接启动Flask（阻塞模式）
        run_flask()
