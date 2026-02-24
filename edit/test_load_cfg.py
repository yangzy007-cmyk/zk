import sys
import configparser
import edit

if __name__ == "__main__":
    # 创建一个测试配置
    config = configparser.ConfigParser()
    config.optionxform = str  # 保持键的大小写
    
    # 添加设备配置
    config['devices'] = {
        '355c6fdb_name': '设备1',
        '355c6fdb_ip': '192.168.0.1',
        '355c6fdb_port': '5000',
        '355c6fdb_mode': 'UDP',
        '355c6fdb_cmd1_name': '1路指令',
        '355c6fdb_cmd1_on': '',
        '355c6fdb_cmd1_off': '',
        '355c6fdb_cmd1_check': '',
        '355c6fdb_cmd1_feedback': ''
    }
    
    # 保存到临时文件
    with open('test_config.ini', 'w', encoding='utf-8') as f:
        config.write(f)
    
    try:
        # 尝试加载配置
        print("Loading config...")
        loaded_cfg = edit.load_cfg('test_config.ini')
        
        # 打印设备列表
        print(f"\nLoaded devices: {len(loaded_cfg.get('devices', []))}")
        for i, device in enumerate(loaded_cfg.get('devices', [])):
            print(f"\nDevice {i+1}:")
            print(f"  ID: {device.get('id')}")
            print(f"  Name: {device.get('name')}")
            print(f"  IP: {device.get('ip')}")
            print(f"  Port: {device.get('port')}")
            print(f"  Mode: {device.get('mode')}")
            print(f"  Commands: {len(device.get('commands', []))}")
            for j, cmd in enumerate(device.get('commands', [])):
                print(f"    Command {j+1}:")
                print(f"      Name: {cmd.get('name')}")
                print(f"      On: {cmd.get('on')}")
                print(f"      Off: {cmd.get('off')}")
                print(f"      Check: {cmd.get('check')}")
                print(f"      Feedback: {cmd.get('feedback')}")
        
        print("\nLoad config successful!")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    
    # 清理临时文件
    import os
    if os.path.exists('test_config.ini'):
        os.remove('test_config.ini')
