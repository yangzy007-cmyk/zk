#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
状态检测测试工具
可以模拟设备响应，也可以测试真实设备
"""
import socket
import threading
import time
import sys

# 模拟设备服务器
class MockDevice:
    def __init__(self, ip='0.0.0.0', port=1053):
        self.ip = ip
        self.port = port
        self.running = False
        self.sock = None
        self.states = {
            'q1': 'n1', 'q2': 'n2', 'q3': 'n3', 'q4': 'n4',
            'q5': 'n5', 'q6': 'n6', 'q7': 'n7', 'q8': 'n8'
        }
        
    def start(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.ip, self.port))
        self.running = True
        print(f"[模拟设备] 启动在 {self.ip}:{self.port}")
        print(f"[模拟设备] 支持的查询: {self.states}")
        
        while self.running:
            try:
                self.sock.settimeout(1)
                data, addr = self.sock.recvfrom(1024)
                query = data.decode('utf-8').strip()
                print(f"[模拟设备] 收到来自 {addr}: '{query}'")
                
                if query in self.states:
                    response = self.states[query]
                    self.sock.sendto(response.encode('utf-8'), addr)
                    print(f"[模拟设备] 回复: '{response}'")
                else:
                    print(f"[模拟设备] 未知查询: '{query}'")
            except socket.timeout:
                continue
            except Exception as e:
                print(f"[模拟设备] 错误: {e}")
                
    def stop(self):
        self.running = False
        if self.sock:
            self.sock.close()

# 测试状态检测
def test_status_check(ip, port, query_cmd, expected_response, timeout=2):
    """测试单个状态检测"""
    print(f"\n{'='*60}")
    print(f"测试: {ip}:{port}")
    print(f"查询: '{query_cmd}' -> 期望: '{expected_response}'")
    print(f"{'='*60}")
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)
        
        # 发送查询
        sock.sendto(query_cmd.encode('utf-8'), (ip, port))
        print(f"[发送] '{query_cmd}' -> {ip}:{port}")
        
        # 接收响应
        response, addr = sock.recvfrom(1024)
        response_str = response.decode('utf-8').strip()
        
        print(f"[接收] 来自 {addr}: '{response_str}'")
        print(f"[字节] {response}")
        print(f"[十六进制] {response.hex().upper()}")
        
        # 检查匹配
        if expected_response.upper() in response_str.upper():
            print(f"[结果] ✓ ON - 匹配成功")
            return True, response_str
        else:
            print(f"[结果] ✗ OFF - 不匹配")
            return False, response_str
            
    except socket.timeout:
        print(f"[结果] ✗ 超时 - {timeout}秒无响应")
        return False, None
    except Exception as e:
        print(f"[结果] ✗ 错误: {e}")
        return False, None
    finally:
        sock.close()

# 批量测试
def batch_test(ip, port, num_buttons=8):
    """批量测试多个按钮"""
    print(f"\n{'#'*60}")
    print(f"# 批量测试 {ip}:{port}")
    print(f"{'#'*60}")
    
    results = {}
    for i in range(1, num_buttons + 1):
        query = f'q{i}'
        expected = f'n{i}'
        success, response = test_status_check(ip, port, query, expected)
        results[query] = {
            'success': success,
            'response': response,
            'expected': expected
        }
        time.sleep(0.1)  # 间隔100ms
    
    # 汇总
    print(f"\n{'#'*60}")
    print(f"# 测试结果汇总")
    print(f"{'#'*60}")
    success_count = sum(1 for r in results.values() if r['success'])
    print(f"成功: {success_count}/{num_buttons}")
    
    for query, result in results.items():
        status = "✓" if result['success'] else "✗"
        print(f"{status} {query} -> 期望:{result['expected']} 实际:{result['response']}")
    
    return results

# 并发测试（模拟多个按钮同时检测）
def concurrent_test(ip, port, num_buttons=8):
    """并发测试 - 模拟状态检测线程的行为"""
    print(f"\n{'#'*60}")
    print(f"# 并发测试 {ip}:{port} (模拟实际状态检测)")
    print(f"{'#'*60}")
    
    import concurrent.futures
    
    def check_one(i):
        query = f'q{i}'
        expected = f'n{i}'
        success, response = test_status_check(ip, port, query, expected, timeout=2)
        return i, success, response
    
    # 并发执行
    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_buttons) as executor:
        futures = [executor.submit(check_one, i) for i in range(1, num_buttons + 1)]
        
        for future in concurrent.futures.as_completed(futures):
            i, success, response = future.result()
            results[i] = {'success': success, 'response': response}
    
    # 汇总
    print(f"\n{'#'*60}")
    print(f"# 并发测试结果")
    print(f"{'#'*60}")
    success_count = sum(1 for r in results.values() if r['success'])
    print(f"成功: {success_count}/{num_buttons}")
    
    return results

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='状态检测测试工具')
    parser.add_argument('--mode', choices=['test', 'mock', 'batch', 'concurrent'], 
                       default='test', help='测试模式')
    parser.add_argument('--ip', default='192.168.0.143', help='设备IP')
    parser.add_argument('--port', type=int, default=1053, help='设备端口')
    parser.add_argument('--query', default='q1', help='查询指令')
    parser.add_argument('--expected', default='n1', help='期望响应')
    parser.add_argument('--count', type=int, default=8, help='按钮数量')
    
    args = parser.parse_args()
    
    if args.mode == 'mock':
        # 启动模拟设备
        device = MockDevice(port=args.port)
        try:
            device.start()
        except KeyboardInterrupt:
            device.stop()
            print("\n[模拟设备] 已停止")
    
    elif args.mode == 'test':
        # 单次测试
        test_status_check(args.ip, args.port, args.query, args.expected)
    
    elif args.mode == 'batch':
        # 批量测试
        batch_test(args.ip, args.port, args.count)
    
    elif args.mode == 'concurrent':
        # 并发测试
        concurrent_test(args.ip, args.port, args.count)
