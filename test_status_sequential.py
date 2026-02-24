#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
顺序测试工具 - 模拟 run.py 的状态检测逻辑
同一个 IP 的按钮按顺序发送，间隔500ms
"""
import socket
import time
import concurrent.futures

def test_single(ip, port, query, expected, timeout=2):
    """测试单个按钮"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)
        
        # 发送查询
        sock.sendto(query.encode('utf-8'), (ip, port))
        
        # 接收响应
        response, addr = sock.recvfrom(1024)
        response_str = response.decode('utf-8').strip()
        
        # 判断是否匹配
        is_on = expected.upper() in response_str.upper()
        result = 'ON' if is_on else 'OFF'
        
        sock.close()
        return True, query, response_str, result
        
    except socket.timeout:
        return False, query, '超时', 'OFF'
    except Exception as e:
        return False, query, str(e), 'ERROR'

def test_sequential(ip, port, num_buttons=8, delay=0.5):
    """顺序测试 - 同一个IP间隔发送"""
    print(f"\n{'#'*60}")
    print(f"# 顺序测试 {ip}:{port} (间隔 {delay*1000:.0f}ms)")
    print(f"{'#'*60}\n")
    
    results = []
    for i in range(1, num_buttons + 1):
        query = f'q{i}'
        expected = f'n{i}'
        
        print(f"[{i}/{num_buttons}] 查询: {query} -> ", end='', flush=True)
        
        success, q, response, result = test_single(ip, port, query, expected)
        results.append({
            'query': q,
            'response': response,
            'result': result,
            'success': success
        })
        
        print(f"收到: {response} -> 状态: {result}")
        
        # 间隔发送
        if i < num_buttons:
            time.sleep(delay)
    
    # 汇总
    print(f"\n{'#'*60}")
    print(f"# 测试结果汇总")
    print(f"{'#'*60}")
    success_count = sum(1 for r in results if r['success'])
    print(f"成功: {success_count}/{num_buttons}")
    
    for r in results:
        status = "✓" if r['success'] else "✗"
        print(f"{status} {r['query']} -> 收到:{r['response']} 状态:{r['result']}")
    
    return results

def test_multi_ip_sequential(ip_port_list, num_buttons=8, delay=0.5):
    """
    多IP顺序测试 - 模拟 run.py 的实际逻辑
    不同IP并发，同IP顺序
    """
    print(f"\n{'#'*60}")
    print(f"# 多IP顺序测试 (模拟 run.py 状态检测)")
    print(f"# 不同IP并发，同IP顺序间隔{delay*1000:.0f}ms")
    print(f"{'#'*60}\n")
    
    def test_one_ip(ip, port):
        results = []
        for i in range(1, num_buttons + 1):
            query = f'q{i}'
            expected = f'n{i}'
            success, q, response, result = test_single(ip, port, query, expected)
            results.append({
                'ip': ip,
                'query': q,
                'response': response,
                'result': result,
                'success': success
            })
            if i < num_buttons:
                time.sleep(delay)
        return results
    
    # 并发测试不同IP
    all_results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(ip_port_list)) as executor:
        future_to_ip = {}
        for ip, port in ip_port_list:
            future = executor.submit(test_one_ip, ip, port)
            future_to_ip[future] = ip
        
        for future in concurrent.futures.as_completed(future_to_ip):
            ip = future_to_ip[future]
            try:
                results = future.result()
                all_results.extend(results)
                print(f"[完成] IP {ip}: {sum(1 for r in results if r['success'])}/{num_buttons} 成功")
            except Exception as e:
                print(f"[错误] IP {ip}: {e}")
    
    # 汇总
    print(f"\n{'#'*60}")
    print(f"# 最终汇总")
    print(f"{'#'*60}")
    success_count = sum(1 for r in all_results if r['success'])
    total = len(all_results)
    print(f"总计: {success_count}/{total} 成功")
    
    return all_results

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='顺序测试工具')
    parser.add_argument('--ip', default='192.168.0.143', help='设备IP')
    parser.add_argument('--port', type=int, default=1053, help='设备端口')
    parser.add_argument('--count', type=int, default=8, help='按钮数量')
    parser.add_argument('--delay', type=float, default=0.5, help='间隔(秒)')
    
    args = parser.parse_args()
    
    # 顺序测试
    test_sequential(args.ip, args.port, args.count, args.delay)
