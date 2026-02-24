#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试设备状态检测
"""
import socket
import time

def test_device(ip, port, query_cmd, expected_response, encoding='字符串'):
    """测试单个设备"""
    print(f"\n{'='*60}")
    print(f"测试设备: {ip}:{port}")
    print(f"查询指令: {query_cmd} (编码: {encoding})")
    print(f"期望响应: {expected_response}")
    print(f"{'='*60}")
    
    try:
        # 创建 socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(3)
        
        # 根据编码处理指令
        if encoding == '16进制' or query_cmd.startswith('0x'):
            cmd_hex = query_cmd.replace('0x', '').replace(' ', '')
            cmd_bytes = bytes.fromhex(cmd_hex)
            print(f"发送(十六进制): {cmd_bytes.hex().upper()}")
        else:
            cmd_bytes = query_cmd.encode('utf-8')
            print(f"发送(字符串): {query_cmd}")
            print(f"发送(字节): {cmd_bytes}")
        
        # 发送查询
        sock.sendto(cmd_bytes, (ip, port))
        print(f"已发送到 {ip}:{port}")
        
        # 接收响应
        try:
            response, addr = sock.recvfrom(1024)
            print(f"\n收到响应来自 {addr}:")
            print(f"  原始字节: {response}")
            print(f"  十六进制: {response.hex().upper()}")
            
            try:
                response_str = response.decode('utf-8').strip()
                print(f"  字符串: '{response_str}'")
                print(f"  字符串(大写): '{response_str.upper()}'")
            except:
                response_str = response.hex().upper()
                print(f"  解码失败，使用十六进制: {response_str}")
            
            # 检查匹配
            expected_upper = expected_response.upper()
            response_upper = response_str.upper()
            
            print(f"\n匹配检查:")
            print(f"  期望(大写): '{expected_upper}'")
            print(f"  实际(大写): '{response_upper}'")
            print(f"  包含检查: {expected_upper in response_upper}")
            
            if expected_upper in response_upper:
                print(f"\n✓ 状态: ON (匹配成功)")
                return True
            else:
                print(f"\n✗ 状态: OFF (不匹配)")
                return False
                
        except socket.timeout:
            print(f"\n✗ 超时: 3秒内未收到响应")
            return False
            
    except Exception as e:
        print(f"\n✗ 错误: {e}")
        return False
    finally:
        sock.close()

if __name__ == '__main__':
    # 测试你的设备
    print("开始测试设备...")
    
    # 测试 192.168.0.143:1053
    result = test_device(
        ip='192.168.0.143',
        port=1053,
        query_cmd='q1',
        expected_response='n1',
        encoding='字符串'
    )
    
    print(f"\n{'='*60}")
    print(f"测试结果: {'成功' if result else '失败'}")
    print(f"{'='*60}")
