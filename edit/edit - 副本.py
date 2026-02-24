import sys, os, copy
import configparser

from PySide6.QtCore import *
from PySide6.QtWidgets import *
from PySide6.QtMultimedia import *
from PySide6.QtMultimediaWidgets import QGraphicsVideoItem
from PySide6.QtGui import *

# 获取文件所在目录的绝对路径
if getattr(sys, 'frozen', False):
    # 如果是打包后的程序
    SCRIPT_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    # 如果是未打包的脚本
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(SCRIPT_DIR, "config.ini")
DATA_DIR = os.path.join(SCRIPT_DIR, "data")

# 确保data目录存在
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)
DEFAULT_RES = {'width': 1920, 'height': 1080}


def full_path(rel_path):
    if not rel_path:
        return ''
    if os.path.isabs(rel_path):
        return rel_path
    # 如果路径已经带 data\ 前缀，不再加
    if rel_path.startswith(os.path.basename(DATA_DIR) + os.sep) or rel_path.startswith(os.path.basename(DATA_DIR) + '/'):
        return os.path.join(os.path.dirname(DATA_DIR), rel_path)
    return os.path.join(DATA_DIR, rel_path)


def load_cfg(filename=CONFIG):
    config = configparser.ConfigParser()
    config.optionxform = str  # 保持键的大小写
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
                "bg": config.get(section, "bg", fallback="")
            }

            # 找出所有控件前缀（如button1, webpage1, switch1, aircon1等）
            keys = config.options(section)
            btn_ids = set()
            for key in keys:
                if "." in key:
                    prefix = key.split(".", 1)[0]
                    if prefix.startswith("button") or prefix.startswith("webpage") or prefix.startswith("switch") or prefix.startswith("aircon"):
                        btn_ids.add(prefix)

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
                        # 格式: udp,command_id[,state]
                        udp_command_id = ctype_parts[1].strip()
                        state = ""
                        # 检查是否有state参数
                        if len(ctype_parts) >= 3:
                            # 检查最后一个参数是否是state
                            last_part = ctype_parts[-1].strip()
                            if last_part in ["on", "off"]:
                                state = last_part
                            else:
                                # 兼容旧格式，尝试从命令名称中提取状态
                                if len(ctype_parts) >= 4:
                                    parts = ",".join(ctype_parts[2:]).strip().split(",")
                                    if parts and parts[-1] in ["on", "off"]:
                                        state = parts[-1]
                        # 使用命令ID作为名称，在实际使用时会从完整配置中获取
                        command_name = udp_command_id
                        commands.append({
                            "type": ctype,
                            "udp_command_id": udp_command_id,
                            "name": command_name,
                            "state": state
                        })
                    elif ctype == "udp_group" and len(ctype_parts) >= 3:
                        # 处理组指令
                        # 格式: udp_group,group_id[,state]
                        udp_group_id = ctype_parts[1].strip()
                        state = ""
                        # 检查是否有state参数
                        if len(ctype_parts) >= 3:
                            # 检查最后一个参数是否是state
                            last_part = ctype_parts[-1].strip()
                            if last_part in ["on", "off"]:
                                state = last_part
                            else:
                                # 兼容旧格式，尝试从命令名称中提取状态
                                if len(ctype_parts) >= 4:
                                    parts = ",".join(ctype_parts[2:]).strip().split(",")
                                    if parts and parts[-1] in ["on", "off"]:
                                        state = parts[-1]
                        # 使用组ID作为名称，在实际使用时会从完整配置中获取
                        group_name = udp_group_id
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
                
                # 读取网页控件的url属性
                url = config.get(section, f"{btn_id}.url", fallback="")
                
                # 读取开关按钮的on_src和off_src属性
                on_src = config.get(section, f"{btn_id}.on_src", fallback="")
                off_src = config.get(section, f"{btn_id}.off_src", fallback="")
                
                # 读取开关按钮的设备指令设置
                device_use = config.getboolean(section, f"{btn_id}.device_use", fallback=False)
                device_id = config.get(section, f"{btn_id}.device_id", fallback="")
                try:
                    device_cmd_index = int(config.get(section, f"{btn_id}.device_cmd_index", fallback="0"))
                except ValueError:
                    device_cmd_index = 0
                
                # 读取开关按钮的指令设置
                on_cmd = config.get(section, f"{btn_id}.on_cmd", fallback="")
                off_cmd = config.get(section, f"{btn_id}.off_cmd", fallback="")
                query_cmd = config.get(section, f"{btn_id}.query_cmd", fallback="")
                response_cmd = config.get(section, f"{btn_id}.response_cmd", fallback="")
                
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
                    "device_use": device_use,
                    "device_id": device_id,
                    "device_cmd_index": device_cmd_index,
                    "on_cmd": on_cmd,
                    "off_cmd": off_cmd,
                    "query_cmd": query_cmd,
                    "response_cmd": response_cmd,
                    "commands": commands,
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
                    "status_query_cmd": status_query_cmd,
                    "status_response_cmd": status_response_cmd
                }
                page_cfg["buttons"].append(btn_cfg)

            pages.append(page_cfg)

    # 如果配置文件没有页面，返回一个默认空页
    if not pages:
        pages = [{"page": 1, "bg": "", "buttons": []}]

    # 读取网络设置
    network = {}
    if 'network' in config:
        network = dict(config['network'])

    # 读取全局状态图片设置
    status_on_src = config.get('global', 'status_on_src', fallback='')
    status_off_src = config.get('global', 'status_off_src', fallback='')
    
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
                'encoding': config['udp_commands'].get(f'{cmd_id}_encoding', '16进制'),
                'mode': config['udp_commands'].get(f'{cmd_id}_mode', 'UDP'),
                'ip': config['udp_commands'].get(f'{cmd_id}_ip', ''),
                'port': int(config['udp_commands'].get(f'{cmd_id}_port', '5000'))
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
            commands_str = config['udp_groups'].get(f'{group_id}_commands', '')
            for cmd_info in commands_str.split(','):
                if cmd_info:
                    # 解析命令ID和延时，格式: id:delay
                    if ':' in cmd_info:
                        cmd_id, delay_str = cmd_info.split(':', 1)
                        try:
                            delay = int(delay_str.strip())
                        except ValueError:
                            delay = 0
                    else:
                        cmd_id = cmd_info
                        delay = 0
                    group['commands'].append({'id': cmd_id.strip(), 'delay': delay})
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

    # 读取设备配置
    devices = []
    if 'devices' in config:
        device_ids = set()
        for key in config['devices']:
            # 只识别设备的_name键，不识别指令的_name键
            if key.endswith('_name') and not '_cmd' in key:
                device_id = key[:-5]  # 移除末尾的 '_name'
                device_ids.add(device_id)
        
        for device_id in device_ids:
            device = {
                'id': device_id,
                'name': config['devices'].get(f'{device_id}_name', ''),
                'ip': config['devices'].get(f'{device_id}_ip', ''),
                'port': int(config['devices'].get(f'{device_id}_port', 5000)),
                'mode': config['devices'].get(f'{device_id}_mode', 'UDP'),
                'commands': []
            }
            
            # 读取设备指令
            cmd_idx = 1
            while True:
                cmd_name = config['devices'].get(f'{device_id}_cmd{cmd_idx}_name', '')
                if not cmd_name:
                    break
                
                cmd = {
                    'name': cmd_name,
                    'on': config['devices'].get(f'{device_id}_cmd{cmd_idx}_on', ''),
                    'off': config['devices'].get(f'{device_id}_cmd{cmd_idx}_off', ''),
                    'check': config['devices'].get(f'{device_id}_cmd{cmd_idx}_check', ''),
                    'feedback': config['devices'].get(f'{device_id}_cmd{cmd_idx}_feedback', ''),
                    'encoding': config['devices'].get(f'{device_id}_cmd{cmd_idx}_encoding', '16进制')
                }
                device['commands'].append(cmd)
                cmd_idx += 1
            
            devices.append(device)

    return {
        "resolution": resolution,
        "pages": pages,
        "network": network,
        "udp_commands": udp_commands,
        "udp_groups": udp_groups,
        "schedules": schedules,
        "udp_matches": udp_matches,
        "devices": devices,
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
        "wait_image_height": wait_image_height
    }


def save_cfg(data, filename=CONFIG):
    # 创建支持中文的配置解析器
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
            config['udp_commands'][f'{cmd_id}_encoding'] = cmd.get('encoding', '16进制')
            config['udp_commands'][f'{cmd_id}_mode'] = cmd.get('mode', 'UDP')
            config['udp_commands'][f'{cmd_id}_ip'] = cmd.get('ip', '')
            config['udp_commands'][f'{cmd_id}_port'] = str(cmd.get('port', 5000))

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

    # 保存定时任务
    if 'schedules' in data:
        config['schedules'] = {}
        for sched in data['schedules']:
            sched_id = sched.get('id', '')
            config['schedules'][f'{sched_id}_name'] = sched.get('name', '')
            config['schedules'][f'{sched_id}_date'] = sched.get('date', '')
            config['schedules'][f'{sched_id}_week'] = sched.get('week', '')
            config['schedules'][f'{sched_id}_time'] = sched.get('time', '00:00')
            config['schedules'][f'{sched_id}_cmd_type'] = sched.get('cmd_type', '指令表')
            config['schedules'][f'{sched_id}_cmd_id'] = sched.get('cmd_id', '')
            config['schedules'][f'{sched_id}_enable'] = str(sched.get('enable', True))

    # 保存UDP指令匹配规则
    if 'udp_matches' in data:
        config['udp_matches'] = {}
        for i, match in enumerate(data['udp_matches'], 1):
            match_id = match.get('id', f'match{i}')
            config['udp_matches'][f'{match_id}_match_cmd'] = match.get('match_cmd', '')
            config['udp_matches'][f'{match_id}_mode'] = match.get('mode', '字符串')
            config['udp_matches'][f'{match_id}_cmd_type'] = match.get('cmd_type', '指令表')
            config['udp_matches'][f'{match_id}_exec_cmd_id'] = match.get('exec_cmd_id', '')

    # 保存设备配置
    if 'devices' in data:
        config['devices'] = {}
        for device in data['devices']:
            device_id = device.get('id', '')
            config['devices'][f'{device_id}_name'] = device.get('name', '')
            config['devices'][f'{device_id}_ip'] = device.get('ip', '')
            config['devices'][f'{device_id}_port'] = str(device.get('port', 5000))
            config['devices'][f'{device_id}_mode'] = device.get('mode', 'UDP')
            
            # 保存设备指令
            for i, cmd in enumerate(device.get('commands', []), 1):
                config['devices'][f'{device_id}_cmd{i}_name'] = cmd.get('name', '')
                config['devices'][f'{device_id}_cmd{i}_on'] = cmd.get('on', '')
                config['devices'][f'{device_id}_cmd{i}_off'] = cmd.get('off', '')
                config['devices'][f'{device_id}_cmd{i}_check'] = cmd.get('check', '')
                config['devices'][f'{device_id}_cmd{i}_feedback'] = cmd.get('feedback', '')
                config['devices'][f'{device_id}_cmd{i}_encoding'] = cmd.get('encoding', '16进制')

    for page in data['pages']:
        sec = f"page{page['page']}"
        config[sec] = {}
        # 只保存相对路径
        bg_path = page.get('bg', '')
        if bg_path:  # 只有在有背景路径时才处理
            if os.path.isabs(bg_path):
                # 如果路径是绝对路径，转换为相对于data目录的路径
                try:
                    rel_path = os.path.relpath(bg_path, DATA_DIR)
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
                
                # 保存开关按钮的设备指令设置
                config[sec][f"{prefix}.device_use"] = str(btn.get('device_use', False))
                config[sec][f"{prefix}.device_id"] = btn.get('device_id', '')
                config[sec][f"{prefix}.device_cmd_index"] = str(btn.get('device_cmd_index', 0))
                
                # 保存开关按钮的指令设置
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
                    # 保存指令表指令，包含state属性，只保存命令ID和状态
                    state = c.get('state', '')
                    if state:
                        config[sec][f"{prefix}.text{i}"] = f"{c['type']},{c['udp_command_id']},{state}"
                    else:
                        config[sec][f"{prefix}.text{i}"] = f"{c['type']},{c['udp_command_id']}"
                elif c['type'] == 'udp_group' and 'udp_group_id' in c:
                    # 保存组指令，包含state属性，只保存命令ID和状态
                    state = c.get('state', '')
                    if state:
                        config[sec][f"{prefix}.text{i}"] = f"{c['type']},{c['udp_group_id']},{state}"
                    else:
                        config[sec][f"{prefix}.text{i}"] = f"{c['type']},{c['udp_group_id']}"
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


# ----------- 多条指令编辑 ----------
class MultiCmdWidget(QWidget):
    def __init__(self, commands):
        super().__init__()
        self.commands = commands or []
        self.lay = QVBoxLayout(self)
        self.table = QTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels(["命令类型", "IP", "端口", "指令/媒体路径", "格式", "延时(ms)", "窗口参数", "播放模式", "互斥模式"])
        self.lay.addWidget(self.table)
        self.lay.setContentsMargins(0, 0, 0, 0)

        btn_lay = QHBoxLayout()
        add_btn = QPushButton("添加")
        add_btn.clicked.connect(lambda: self.add_row())
        del_btn = QPushButton("删除")
        del_btn.clicked.connect(self.del_row)
        browse_btn = QPushButton("浏览媒体")
        browse_btn.clicked.connect(self.browse_media)
        btn_lay.addWidget(add_btn)
        btn_lay.addWidget(del_btn)
        btn_lay.addWidget(browse_btn)
        self.lay.addLayout(btn_lay)

        self.load_commands()

    def load_commands(self):
        self.table.setRowCount(0)
        for cmd in self.commands:
            if cmd['type'] == 'media_window':
                # 处理媒体窗口命令
                media_path = cmd.get('media', '')
                x = cmd.get('x', 200)
                y = cmd.get('y', 200)
                width = cmd.get('width', 800)
                height = cmd.get('height', 600)
                play_mode = cmd.get('play_mode', 'loop')
                mutex_mode = cmd.get('mutex_mode', '共存')
                window_params = f"{x},{y},{width},{height}"
                self.add_row(cmd['type'], '', 0, media_path, '', 0, window_params, play_mode, mutex_mode)
            elif cmd['type'] == 'close_all_windows':
                # 处理关闭所有窗口命令
                self.add_row(cmd['type'], '', 0, '', '', 0, '0,0,0,0', 'loop', '共存')
            else:
                # 处理传统命令（udp/tcp）
                self.add_row(cmd['type'], cmd.get('ip', ''), cmd.get('port', 0), 
                           cmd.get('msg', ''), cmd.get('fmt', 'hex'), 
                           cmd.get('delay', 0))

    def add_row(self, typ="udp", ip="192.168.0.15", port=5005, msg="A5", fmt="hex", delay=0, window_params="200,200,800,600", play_mode="loop", mutex_mode="共存"):
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        # 命令类型下拉框
        type_box = QComboBox()
        type_box.setStyleSheet("""
            QComboBox {
                background: #444;
                color: #eee;
                border: 1px solid #666;
                padding: 3px;
                min-width: 100px;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                width: 0;
                height: 0;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 4px solid #eee;
            }
        """)
        # 添加显示文本，内部仍然使用原始命令类型
        display_items = ["udp", "tcp", "开窗播放", "关闭所有窗口"]
        value_items = ["udp", "tcp", "media_window", "close_all_windows"]
        
        # 添加显示项
        for item in display_items:
            type_box.addItem(item)
        
        # 设置当前项
        try:
            # 找到对应的值索引
            index = value_items.index(typ)
            type_box.setCurrentIndex(index)
        except ValueError:
            # 如果找不到，默认为udp
            type_box.setCurrentIndex(0)
        
        # 连接信号，使用值而不是显示文本
        type_box.currentIndexChanged.connect(lambda index, row=row: self.on_command_type_changed(value_items[index], row))
        self.table.setCellWidget(row, 0, type_box)
        
        # IP 输入框
        ip_item = QTableWidgetItem(ip)
        self.table.setItem(row, 1, ip_item)
        
        # 端口输入框
        port_item = QTableWidgetItem(str(port))
        self.table.setItem(row, 2, port_item)
        
        # 指令/媒体路径输入框
        msg_item = QTableWidgetItem(msg)
        self.table.setItem(row, 3, msg_item)
        
        # 格式下拉框
        fmt_box = QComboBox()
        fmt_box.setStyleSheet("""
            QComboBox {
                background: #444;
                color: #eee;
                border: 1px solid #666;
                padding: 3px;
                min-width: 60px;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                width: 0;
                height: 0;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 4px solid #eee;
            }
        """)
        fmt_box.addItems(["hex", "text"])
        fmt_box.setCurrentText(fmt)
        self.table.setCellWidget(row, 4, fmt_box)
        
        # 延时输入框
        delay_item = QTableWidgetItem(str(delay))
        delay_item.setTextAlignment(Qt.AlignCenter)
        self.table.setItem(row, 5, delay_item)
        
        # 窗口参数输入框 (x,y,width,height)
        window_item = QTableWidgetItem(window_params)
        self.table.setItem(row, 6, window_item)
        
        # 播放模式下拉框
        play_mode_box = QComboBox()
        play_mode_box.setStyleSheet("""
            QComboBox {
                background: #444;
                color: #eee;
                border: 1px solid #666;
                padding: 3px;
                min-width: 100px;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                width: 0;
                height: 0;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 4px solid #eee;
            }
        """)
        play_mode_box.addItems(["loop", "once"])
        play_mode_box.setCurrentText(play_mode)
        self.table.setCellWidget(row, 7, play_mode_box)
        
        # 互斥模式下拉框
        mutex_mode_box = QComboBox()
        mutex_mode_box.setStyleSheet("""
            QComboBox {
                background: #444;
                color: #eee;
                border: 1px solid #666;
                padding: 3px;
                min-width: 100px;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                width: 0;
                height: 0;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 4px solid #eee;
            }
        """)
        mutex_mode_box.addItems(["共存", "独享"])
        mutex_mode_box.setCurrentText(mutex_mode)
        self.table.setCellWidget(row, 8, mutex_mode_box)
        
        # 初始化命令类型相关设置
        self.on_command_type_changed(typ, row)
        
        # 调整行高以适应内容
        self.table.resizeRowToContents(row)

    def del_row(self):
        rows = set(item.row() for item in self.table.selectedItems())
        for row in sorted(rows, reverse=True):
            self.table.removeRow(row)

    def browse_media(self):
        """浏览媒体文件并填充到选中的行"""
        selected_items = self.table.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "提示", "请先选择一行来设置媒体文件")
            return
        
        row = selected_items[0].row()
        type_box = self.table.cellWidget(row, 0)
        if not type_box:
            QMessageBox.information(self, "提示", "请先将命令类型设置为开窗播放")
            return
        
        # 获取当前索引对应的命令类型值
        current_index = type_box.currentIndex()
        value_items = ["udp", "tcp", "media_window", "close_all_windows"]
        if current_index < 0 or current_index >= len(value_items) or value_items[current_index] != "media_window":
            QMessageBox.information(self, "提示", "请先将命令类型设置为开窗播放")
            return
        
        path, _ = QFileDialog.getOpenFileName(
            self, 
            "选择媒体文件", 
            DATA_DIR, 
            "媒体文件 (*.mp4 *.avi *.mov *.mkv *.flv *.wmv *.jpg *.jpeg *.png *.bmp *.gif)"
        )
        if path:
            # 转换为相对路径
            if os.path.isabs(path):
                try:
                    rel_path = os.path.relpath(path, DATA_DIR)
                    if rel_path.startswith('..'):
                        # 如果文件不在data目录下，只使用文件名
                        rel_path = os.path.basename(path)
                except ValueError:
                    # 如果无法转换为相对路径，只使用文件名
                    rel_path = os.path.basename(path)
            else:
                rel_path = path
            
            # 填充媒体路径
            msg_item = self.table.item(row, 3)
            if msg_item:
                msg_item.setText(rel_path)

    def on_command_type_changed(self, text, row):
        """当命令类型改变时的处理"""
        # 对于media_window命令
        if text == "media_window":
            # 设置默认窗口参数
            window_item = self.table.item(row, 6)
            if window_item and not window_item.text():
                window_item.setText("200,200,800,600")
            # 设置默认播放模式
            play_mode_box = self.table.cellWidget(row, 7)
            if not play_mode_box:
                # 如果播放模式下拉框不存在，创建一个
                play_mode_box = QComboBox()
                play_mode_box.setStyleSheet("""
                    QComboBox {
                        background: #444;
                        color: #eee;
                        border: 1px solid #666;
                        padding: 3px;
                        min-width: 100px;
                    }
                    QComboBox::drop-down {
                        border: none;
                        width: 20px;
                    }
                    QComboBox::down-arrow {
                        image: none;
                        width: 0;
                        height: 0;
                        border-left: 4px solid transparent;
                        border-right: 4px solid transparent;
                        border-top: 4px solid #eee;
                    }
                """)
                play_mode_box.addItems(["loop", "once"])
                play_mode_box.setCurrentText("loop")
                self.table.setCellWidget(row, 7, play_mode_box)
        elif text == "close_all_windows":
            # 对于关闭所有窗口命令，不需要特殊的下拉框
            pass
        else:
            # 对于其他命令，确保格式下拉框存在
            fmt_box = self.table.cellWidget(row, 4)
            if not fmt_box:
                fmt_box = QComboBox()
                fmt_box.setStyleSheet("""
                    QComboBox {
                        background: #444;
                        color: #eee;
                        border: 1px solid #666;
                        padding: 3px;
                        min-width: 60px;
                    }
                    QComboBox::drop-down {
                        border: none;
                        width: 20px;
                    }
                    QComboBox::down-arrow {
                        image: none;
                        width: 0;
                        height: 0;
                        border-left: 4px solid transparent;
                        border-right: 4px solid transparent;
                        border-top: 4px solid #eee;
                    }
                """)
                fmt_box.addItems(["hex", "text"])
                fmt_box.setCurrentText("hex")
                self.table.setCellWidget(row, 4, fmt_box)

    def get_commands(self):
        cmds = []
        for r in range(self.table.rowCount()):
            type_box = self.table.cellWidget(r, 0)
            if not type_box:
                typ = "udp"
            else:
                # 通过索引获取实际命令类型值
                current_index = type_box.currentIndex()
                display_items = ["udp", "tcp", "开窗播放", "关闭所有窗口"]
                value_items = ["udp", "tcp", "media_window", "close_all_windows"]
                if 0 <= current_index < len(value_items):
                    typ = value_items[current_index]
                else:
                    typ = "udp"
            
            # 获取互斥模式
            mutex_mode_box = self.table.cellWidget(r, 8)
            mutex_mode = mutex_mode_box.currentText() if mutex_mode_box else "共存"
            
            if typ == "media_window":
                # 处理媒体窗口命令
                media_path = self.table.item(r, 3).text() if self.table.item(r, 3) else ""
                window_params = self.table.item(r, 6).text() if self.table.item(r, 6) else "200,200,800,600"
                
                # 解析窗口参数
                try:
                    params = window_params.split(',')
                    if len(params) >= 4:
                        x = int(params[0].strip())
                        y = int(params[1].strip())
                        width = int(params[2].strip())
                        height = int(params[3].strip())
                    else:
                        x, y, width, height = 200, 200, 800, 600
                except:
                    x, y, width, height = 200, 200, 800, 600
                
                # 从下拉框获取播放模式
                play_mode_box = self.table.cellWidget(r, 7)
                play_mode = play_mode_box.currentText() if play_mode_box else "loop"
                # 验证播放模式
                if play_mode not in ['loop', 'once']:
                    play_mode = 'loop'
                
                cmds.append({
                    "type": typ,
                    "media": media_path,
                    "x": x,
                    "y": y,
                    "width": width,
                    "height": height,
                    "play_mode": play_mode,
                    "mutex_mode": mutex_mode
                })
            elif typ == "close_all_windows":
                # 处理关闭所有窗口命令
                cmds.append({
                    "type": typ
                })
            else:
                # 处理传统命令（udp/tcp）
                ip = self.table.item(r, 1).text() if self.table.item(r, 1) else ""
                try:
                    port = int(self.table.item(r, 2).text()) if self.table.item(r, 2) else 0
                except Exception:
                    port = 0
                msg = self.table.item(r, 3).text() if self.table.item(r, 3) else ""
                fmt_box = self.table.cellWidget(r, 4)
                fmt = fmt_box.currentText() if fmt_box else "hex"
                delay = int(self.table.item(r, 5).text() or '0')
                cmds.append({
                    "type": typ,
                    "ip": ip,
                    "port": port,
                    "msg": msg,
                    "fmt": fmt,
                    "delay": delay
                })
        return cmds


class WebPagePropsDlg(QDialog):
    def __init__(self, cfg, logic_w, logic_h):
        super().__init__()
        self.cfg = copy.deepcopy(cfg)
        self.logic_w = logic_w
        self.logic_h = logic_h
        self.setWindowTitle("网页属性")

        lay = QFormLayout(self)

        # 解析ID和名称
        btn_id = self.cfg['id']
        if '_' in btn_id:
            # 如果ID中包含下划线，则分割ID和名称
            id_parts = btn_id.split('_', 1)
            btn_id = id_parts[0]
            default_name = id_parts[1] if len(id_parts) > 1 else f"网页{btn_id}"
        else:
            default_name = self.cfg.get('name', f"网页{btn_id}")
        
        # ID 和名称行
        id_lay = QHBoxLayout()
        id_lay.addWidget(QLabel("ID"))
        self.id_edit = QLineEdit(btn_id)
        # 添加输入验证器，只允许字母和数字
        self.id_edit.setValidator(QRegularExpressionValidator(QRegularExpression(r'[a-zA-Z0-9_]+')))
        id_lay.addWidget(self.id_edit)
        
        name_lay = QHBoxLayout()
        name_lay.addWidget(QLabel("名称"))
        self.name_edit = QLineEdit(default_name)
        name_lay.addWidget(self.name_edit)
        
        id_name_lay = QHBoxLayout()
        id_name_lay.addLayout(id_lay, 1)
        id_name_lay.addLayout(name_lay, 2)
        lay.addRow("ID和名称", id_name_lay)

        # 位置和大小
        w = QSpinBox()
        w.setRange(1, self.logic_w)
        w.setValue(int(self.cfg['w']))
        h = QSpinBox()
        h.setRange(1, self.logic_h)
        h.setValue(int(self.cfg['h']))
        x = QSpinBox()
        x.setRange(0, self.logic_w)
        x.setValue(int(self.cfg['x']))
        y = QSpinBox()
        y.setRange(0, self.logic_h)
        y.setValue(int(self.cfg['y']))
        lay.addRow("宽度 (像素)", w)
        lay.addRow("高度 (像素)", h)
        lay.addRow("X (像素)", x)
        lay.addRow("Y (像素)", y)
        self.w_spin, self.h_spin = w, h
        self.x_spin, self.y_spin = x, y

        # 网页地址
        self.url_edit = QLineEdit(self.cfg.get('url', ''))
        lay.addRow("网页地址", self.url_edit)

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def accept(self):
        # 获取ID和名称
        btn_id = self.id_edit.text().strip()
        if not btn_id:
            QMessageBox.warning(self, "错误", "ID不能为空")
            return
            
        btn_name = self.name_edit.text().strip() or f"网页{btn_id}"
        
        # 确保ID只包含基础部分（去掉可能存在的名称部分）
        if '_' in btn_id:
            btn_id = btn_id.split('_')[0]
            
        self.cfg_out = {
            'id': f"{btn_id}",  # 只保存基础ID，不包含名称
            'name': btn_name,   # 单独保存名称
            'w': self.w_spin.value(),
            'h': self.h_spin.value(),
            'x': self.x_spin.value(),
            'y': self.y_spin.value(),
            'url': self.url_edit.text(),
            'src': self.cfg.get('src', ''),
            'pressed_src': self.cfg.get('pressed_src', ''),
            'type': 'webpage',
            'commands': self.cfg.get('commands', [])
        }
        super().accept()


class SwitchPropsDlg(QDialog):
    def __init__(self, cfg, logic_w, logic_h):
        super().__init__()
        self.cfg = copy.deepcopy(cfg)
        self.logic_w = logic_w
        self.logic_h = logic_h
        self.setWindowTitle("开关属性")

        lay = QFormLayout(self)

        # 设备勾选项
        device_group = QGroupBox("设备选择")
        device_layout = QVBoxLayout()
        
        # 创建设备指令复选框
        self.device_checkbox = QCheckBox("使用设备指令")
        device_layout.addWidget(self.device_checkbox)
        
        # 创建设备下拉框
        device_layout.addWidget(QLabel("选择设备:"))
        self.device_combo = QComboBox()
        self.device_combo.setEnabled(False)
        device_layout.addWidget(self.device_combo)
        
        # 创建指令下拉框
        device_layout.addWidget(QLabel("选择指令:"))
        self.cmd_combo = QComboBox()
        self.cmd_combo.setEnabled(False)
        device_layout.addWidget(self.cmd_combo)
        
        device_group.setLayout(device_layout)
        lay.addRow(device_group)
        
        # 创建设备选择变化的处理函数
        def on_device_changed(index):
            """设备选择变化处理"""
            if index >= 0:
                device_id = self.device_combo.itemData(index)
                print(f"设备选择变化: index={index}, device_id={device_id}")
                # 清空指令下拉框
                self.cmd_combo.clear()
                # 加载配置
                cfg = load_cfg()
                devices = cfg.get('devices', [])
                # 查找选中的设备
                for device in devices:
                    if device.get('id') == device_id:
                        commands = device.get('commands', [])
                        # 添加指令到下拉框
                        for i, cmd in enumerate(commands):
                            cmd_name = cmd.get('name', f"指令{i+1}")
                            self.cmd_combo.addItem(cmd_name, i)
                        break
                # 确保指令下拉框被启用
                self.cmd_combo.setEnabled(True)
                # 设置之前保存的指令选择
                device_cmd_index = self.cfg.get('device_cmd_index', 0)
                # 确保 device_cmd_index 是整数类型
                try:
                    device_cmd_index = int(device_cmd_index)
                except (ValueError, TypeError):
                    device_cmd_index = 0
                
                # 使用索引设置指令选择
                if 0 <= device_cmd_index < self.cmd_combo.count():
                    self.cmd_combo.setCurrentIndex(device_cmd_index)
                print(f"指令列表加载完成: 选择索引={self.cmd_combo.currentIndex()}, 文本={self.cmd_combo.currentText()}")
        
        # 创建设备指令复选框处理函数
        def handle_device_check(checked):
            print(f"设备指令复选框状态变化: {checked}")
            # 直接设置下拉框启用状态
            self.device_combo.setEnabled(checked)
            self.cmd_combo.setEnabled(checked)
            
            # 如果未勾选，不加载设备列表
            if not checked:
                return
            
            # 加载设备列表
            print("加载设备列表")
            # 清空现有列表
            self.device_combo.clear()
            self.cmd_combo.clear()
            # 加载配置
            cfg = load_cfg()
            devices = cfg.get('devices', [])
            # 添加设备到下拉框
            for device in devices:
                device_id = device.get('id', '')
                device_name = device.get('name', '未命名设备')
                self.device_combo.addItem(device_name, device_id)
            # 确保下拉框确实被启用
            self.device_combo.setEnabled(True)
            self.cmd_combo.setEnabled(True)
            
            # 设置之前保存的设备选择
            device_id = self.cfg.get('device_id', '')
            print(f"尝试加载设备ID: {device_id}")
            
            if device_id:
                # 查找匹配的设备
                for i in range(self.device_combo.count()):
                    if self.device_combo.itemData(i) == device_id:
                        self.device_combo.setCurrentIndex(i)
                        print(f"成功找到设备: 索引{i}, 名称={self.device_combo.itemText(i)}")
                        # 手动触发设备选择变化，加载指令列表
                        on_device_changed(i)
                        break
        
        # 连接设备选择变化信号
        self.device_combo.currentIndexChanged.connect(on_device_changed)
        
        # 连接信号到处理函数
        self.device_checkbox.toggled.connect(handle_device_check)
        
        # 解析ID和名称
        btn_id = self.cfg['id']
        if '_' in btn_id:
            # 如果ID中包含下划线，则分割ID和名称
            id_parts = btn_id.split('_', 1)
            btn_id = id_parts[0]
            default_name = id_parts[1] if len(id_parts) > 1 else f"开关{btn_id}"
        else:
            default_name = self.cfg.get('name', f"开关{btn_id}")
        
        # ID 和名称行
        id_lay = QHBoxLayout()
        id_lay.addWidget(QLabel("ID"))
        self.id_edit = QLineEdit(btn_id)
        # 添加输入验证器，只允许字母和数字
        self.id_edit.setValidator(QRegularExpressionValidator(QRegularExpression(r'[a-zA-Z0-9_]+')))
        id_lay.addWidget(self.id_edit)
        
        name_lay = QHBoxLayout()
        name_lay.addWidget(QLabel("名称"))
        self.name_edit = QLineEdit(default_name)
        name_lay.addWidget(self.name_edit)
        
        id_name_lay = QHBoxLayout()
        id_name_lay.addLayout(id_lay, 1)
        id_name_lay.addLayout(name_lay, 2)
        lay.addRow("ID和名称", id_name_lay)

        # 开状态图片
        self.on_src_edit = QLineEdit(self.cfg.get('on_src', ''))
        browse_on = QPushButton("浏览")
        browse_on.clicked.connect(lambda: self.browse(self.on_src_edit))
        hl_on = QHBoxLayout()
        hl_on.addWidget(self.on_src_edit)
        hl_on.addWidget(browse_on)
        lay.addRow("开状态图片", hl_on)

        # 关状态图片
        self.off_src_edit = QLineEdit(self.cfg.get('off_src', ''))
        browse_off = QPushButton("浏览")
        browse_off.clicked.connect(lambda: self.browse(self.off_src_edit))
        hl_off = QHBoxLayout()
        hl_off.addWidget(self.off_src_edit)
        hl_off.addWidget(browse_off)
        lay.addRow("关状态图片", hl_off)

        # 位置和大小
        w = QSpinBox()
        w.setRange(1, self.logic_w)
        w.setValue(int(self.cfg['w']))
        h = QSpinBox()
        h.setRange(1, self.logic_h)
        h.setValue(int(self.cfg['h']))
        x = QSpinBox()
        x.setRange(0, self.logic_w)
        x.setValue(int(self.cfg['x']))
        y = QSpinBox()
        y.setRange(0, self.logic_h)
        y.setValue(int(self.cfg['y']))
        lay.addRow("宽度 (像素)", w)
        lay.addRow("高度 (像素)", h)
        lay.addRow("X (像素)", x)
        lay.addRow("Y (像素)", y)
        self.w_spin, self.h_spin = w, h
        self.x_spin, self.y_spin = x, y

        # 开状态指令配置
        on_cmd_group = QGroupBox("开状态指令配置")
        on_cmd_layout = QVBoxLayout()
        
        # 选择指令类型
        on_type_layout = QHBoxLayout()
        on_type_label = QLabel("指令类型:")
        self.on_cmd_type_combo = QComboBox()
        self.on_cmd_type_combo.addItems(["指令表", "组指令"])
        self.on_cmd_type_combo.currentIndexChanged.connect(self.on_on_cmd_type_changed)
        on_type_layout.addWidget(on_type_label)
        on_type_layout.addWidget(self.on_cmd_type_combo)
        on_cmd_layout.addLayout(on_type_layout)
        
        # 指令选择按钮
        on_btn_layout = QHBoxLayout()
        on_btn_layout.addWidget(QLabel("选择指令:"))
        self.on_cmd_select_btn = QPushButton("点击选择")
        self.on_cmd_select_btn.clicked.connect(self.select_on_command)
        on_btn_layout.addWidget(self.on_cmd_select_btn)
        
        # 显示选中的指令
        self.on_selected_cmd_label = QLabel("未选择指令")
        self.on_selected_cmd_label.setStyleSheet("color: #666")
        on_btn_layout.addWidget(self.on_selected_cmd_label)
        on_btn_layout.addStretch()
        on_cmd_layout.addLayout(on_btn_layout)
        on_cmd_group.setLayout(on_cmd_layout)
        lay.addRow(on_cmd_group)

        # 关状态指令配置
        off_cmd_group = QGroupBox("关状态指令配置")
        off_cmd_layout = QVBoxLayout()
        
        # 选择指令类型
        off_type_layout = QHBoxLayout()
        off_type_label = QLabel("指令类型:")
        self.off_cmd_type_combo = QComboBox()
        self.off_cmd_type_combo.addItems(["指令表", "组指令"])
        self.off_cmd_type_combo.currentIndexChanged.connect(self.on_off_cmd_type_changed)
        off_type_layout.addWidget(off_type_label)
        off_type_layout.addWidget(self.off_cmd_type_combo)
        off_cmd_layout.addLayout(off_type_layout)
        
        # 指令选择按钮
        off_btn_layout = QHBoxLayout()
        off_btn_layout.addWidget(QLabel("选择指令:"))
        self.off_cmd_select_btn = QPushButton("点击选择")
        self.off_cmd_select_btn.clicked.connect(self.select_off_command)
        off_btn_layout.addWidget(self.off_cmd_select_btn)
        
        # 显示选中的指令
        self.off_selected_cmd_label = QLabel("未选择指令")
        self.off_selected_cmd_label.setStyleSheet("color: #666")
        off_btn_layout.addWidget(self.off_selected_cmd_label)
        off_btn_layout.addStretch()
        off_cmd_layout.addLayout(off_btn_layout)
        off_cmd_group.setLayout(off_cmd_layout)
        lay.addRow(off_cmd_group)

        # 状态显示设置
        status_group = QGroupBox("状态显示设置")
        status_layout = QVBoxLayout()
        
        # 状态显示开关
        status_enable_layout = QHBoxLayout()
        status_enable_check = QCheckBox("启用状态显示")
        status_enable_layout.addWidget(status_enable_check)
        status_layout.addLayout(status_enable_layout)
        
        # UDP询问指令设置
        udp_query_layout = QGridLayout()
        udp_query_layout.addWidget(QLabel("IP地址:"), 0, 0)
        status_ip_edit = QLineEdit(self.cfg.get('status_ip', ''))
        udp_query_layout.addWidget(status_ip_edit, 0, 1)
        
        udp_query_layout.addWidget(QLabel("端口:"), 0, 2)
        status_port_spin = QSpinBox()
        status_port_spin.setRange(1, 65535)
        status_port_spin.setValue(self.cfg.get('status_port', 5005))
        udp_query_layout.addWidget(status_port_spin, 0, 3)
        
        udp_query_layout.addWidget(QLabel("询问指令:"), 1, 0)
        status_query_edit = QLineEdit(self.cfg.get('status_query_cmd', ''))
        udp_query_layout.addWidget(status_query_edit, 1, 1, 1, 3)
        
        udp_query_layout.addWidget(QLabel("响应指令:"), 2, 0)
        status_response_edit = QLineEdit(self.cfg.get('status_response_cmd', ''))
        udp_query_layout.addWidget(status_response_edit, 2, 1, 1, 3)
        status_layout.addLayout(udp_query_layout)
        
        status_group.setLayout(status_layout)
        lay.addRow(status_group)
        
        # 保存状态设置控件引用
        self.status_enable_check = status_enable_check
        self.status_ip_edit = status_ip_edit
        self.status_port_spin = status_port_spin
        self.status_query_edit = status_query_edit
        self.status_response_edit = status_response_edit

        # 加载已保存的状态设置
        self.status_enable_check.setChecked(self.cfg.get('status_enable', False))

        # 初始化设备指令复选框状态并加载设备列表
        device_use = self.cfg.get('device_use', False)
        self.device_checkbox.setChecked(device_use)
        # 立即调用处理函数，确保初始状态正确
        handle_device_check(device_use)
        
        # 加载已保存的指令信息
        self.on_selected_cmd_id = None
        self.on_selected_cmd_name = ""
        self.off_selected_cmd_id = None
        self.off_selected_cmd_name = ""
        self._load_saved_commands()

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def browse(self, line_edit):
        path, _ = QFileDialog.getOpenFileName(self, "选择图片", DATA_DIR, "图片 (*.png *.jpg *.jpeg *.bmp *.gif)")
        if path:
            filename = os.path.basename(path)
            line_edit.setText(filename)

    def select_on_command(self):
        """选择开状态指令（带搜索功能）"""
        # 获取配置
        cfg = load_cfg()
        
        # 根据选择的类型获取指令列表
        if self.on_cmd_type_combo.currentText() == "指令表":
            commands = cfg.get('udp_commands', [])
        else:
            commands = cfg.get('udp_groups', [])
        
        # 创建带搜索功能的选择对话框
        dlg = QDialog(self)
        dlg.setWindowTitle("选择开状态指令")
        dlg.resize(400, 300)
        
        layout = QVBoxLayout(dlg)
        
        # 搜索框
        search_layout = QHBoxLayout()
        search_label = QLabel("搜索:")
        search_edit = QLineEdit()
        search_edit.setPlaceholderText("输入指令名称搜索...")
        search_layout.addWidget(search_label)
        search_layout.addWidget(search_edit)
        layout.addLayout(search_layout)
        
        # 指令列表
        list_widget = QListWidget()
        layout.addWidget(list_widget)
        
        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        ok_btn = QPushButton("确定")
        cancel_btn = QPushButton("取消")
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
        # 加载指令列表
        def load_cmd_list():
            list_widget.clear()
            for cmd in commands:
                item = QListWidgetItem(cmd.get('name', cmd.get('id', '')))
                item.setData(Qt.UserRole, cmd.get('id', ''))
                list_widget.addItem(item)
        
        load_cmd_list()
        
        # 搜索功能
        def update_list():
            search_text = search_edit.text().lower()
            
            for i in range(list_widget.count()):
                item = list_widget.item(i)
                item_text = item.text().lower()
                
                # 按空格分割搜索关键字
                keywords = [kw.strip() for kw in search_text.split() if kw.strip()]
                
                if not keywords:
                    # 搜索框为空，显示所有指令
                    item.setHidden(False)
                else:
                    # 检查指令是否包含所有关键字（大小写不敏感）
                    if all(keyword in item_text for keyword in keywords):
                        item.setHidden(False)
                    else:
                        item.setHidden(True)
        
        search_edit.textChanged.connect(update_list)
        
        # 连接信号
        selected_item = None
        
        def on_ok():
            nonlocal selected_item
            items = list_widget.selectedItems()
            if items:
                selected_item = items[0]
                dlg.accept()
            else:
                QMessageBox.warning(dlg, "提示", "请选择一个指令")
        
        ok_btn.clicked.connect(on_ok)
        cancel_btn.clicked.connect(dlg.reject)
        
        # 双击选择
        def on_item_double_clicked(item):
            nonlocal selected_item
            selected_item = item
            dlg.accept()
        
        list_widget.itemDoubleClicked.connect(on_item_double_clicked)
        
        # 执行对话框
        if dlg.exec() == QDialog.Accepted and selected_item:
            self.on_selected_cmd_id = selected_item.data(Qt.UserRole)
            self.on_selected_cmd_name = selected_item.text()
            self.on_selected_cmd_label.setText(f"已选择: {self.on_selected_cmd_name}")
            self.on_selected_cmd_label.setStyleSheet("color: #000")

    def select_off_command(self):
        """选择关状态指令（带搜索功能）"""
        # 获取配置
        cfg = load_cfg()
        
        # 根据选择的类型获取指令列表
        if self.off_cmd_type_combo.currentText() == "指令表":
            commands = cfg.get('udp_commands', [])
        else:
            commands = cfg.get('udp_groups', [])
        
        # 创建带搜索功能的选择对话框
        dlg = QDialog(self)
        dlg.setWindowTitle("选择关状态指令")
        dlg.resize(400, 300)
        
        layout = QVBoxLayout(dlg)
        
        # 搜索框
        search_layout = QHBoxLayout()
        search_label = QLabel("搜索:")
        search_edit = QLineEdit()
        search_edit.setPlaceholderText("输入指令名称搜索...")
        search_layout.addWidget(search_label)
        search_layout.addWidget(search_edit)
        layout.addLayout(search_layout)
        
        # 指令列表
        list_widget = QListWidget()
        layout.addWidget(list_widget)
        
        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        ok_btn = QPushButton("确定")
        cancel_btn = QPushButton("取消")
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
        # 加载指令列表
        def load_cmd_list():
            list_widget.clear()
            for cmd in commands:
                item = QListWidgetItem(cmd.get('name', cmd.get('id', '')))
                item.setData(Qt.UserRole, cmd.get('id', ''))
                list_widget.addItem(item)
        
        load_cmd_list()
        
        # 搜索功能
        def update_list():
            search_text = search_edit.text().lower()
            
            for i in range(list_widget.count()):
                item = list_widget.item(i)
                item_text = item.text().lower()
                
                # 按空格分割搜索关键字
                keywords = [kw.strip() for kw in search_text.split() if kw.strip()]
                
                if not keywords:
                    # 搜索框为空，显示所有指令
                    item.setHidden(False)
                else:
                    # 检查指令是否包含所有关键字（大小写不敏感）
                    if all(keyword in item_text for keyword in keywords):
                        item.setHidden(False)
                    else:
                        item.setHidden(True)
        
        search_edit.textChanged.connect(update_list)
        
        # 连接信号
        selected_item = None
        
        def on_ok():
            nonlocal selected_item
            items = list_widget.selectedItems()
            if items:
                selected_item = items[0]
                dlg.accept()
            else:
                QMessageBox.warning(dlg, "提示", "请选择一个指令")
        
        ok_btn.clicked.connect(on_ok)
        cancel_btn.clicked.connect(dlg.reject)
        
        # 双击选择
        def on_item_double_clicked(item):
            nonlocal selected_item
            selected_item = item
            dlg.accept()
        
        list_widget.itemDoubleClicked.connect(on_item_double_clicked)
        
        # 执行对话框
        if dlg.exec() == QDialog.Accepted and selected_item:
            self.off_selected_cmd_id = selected_item.data(Qt.UserRole)
            self.off_selected_cmd_name = selected_item.text()
            self.off_selected_cmd_label.setText(f"已选择: {self.off_selected_cmd_name}")
            self.off_selected_cmd_label.setStyleSheet("color: #000")

    def on_on_cmd_type_changed(self):
        """开状态指令类型改变时的处理"""
        # 重置选中状态
        self.on_selected_cmd_id = None
        self.on_selected_cmd_name = ""
        self.on_selected_cmd_label.setText("未选择指令")
        self.on_selected_cmd_label.setStyleSheet("color: #666")

    def on_off_cmd_type_changed(self):
        """关状态指令类型改变时的处理"""
        # 重置选中状态
        self.off_selected_cmd_id = None
        self.off_selected_cmd_name = ""
        self.off_selected_cmd_label.setText("未选择指令")
        self.off_selected_cmd_label.setStyleSheet("color: #666")

    def _load_saved_commands(self):
        """加载已保存的指令信息"""
        # 获取命令配置
        commands = self.cfg.get('commands', [])
        
        # 加载完整配置，用于获取指令名称
        full_cfg = load_cfg()
        udp_commands = full_cfg.get('udp_commands', [])
        udp_groups = full_cfg.get('udp_groups', [])
        
        for cmd in commands:
            if cmd.get('type') == 'udp' and 'udp_command_id' in cmd and cmd.get('state') == 'on':
                # 开状态指令表指令
                self.on_cmd_type_combo.setCurrentText("指令表")
                self.on_selected_cmd_id = cmd.get('udp_command_id')
                # 从指令表中获取命令名称
                self.on_selected_cmd_name = self.on_selected_cmd_id
                for udp_cmd in udp_commands:
                    if udp_cmd.get('id') == self.on_selected_cmd_id:
                        self.on_selected_cmd_name = udp_cmd.get('name', self.on_selected_cmd_id)
                        break
                self.on_selected_cmd_label.setText(f"已选择: {self.on_selected_cmd_name}")
                self.on_selected_cmd_label.setStyleSheet("color: #000")
            elif cmd.get('type') == 'udp_group' and 'udp_group_id' in cmd and cmd.get('state') == 'on':
                # 开状态组指令
                self.on_cmd_type_combo.setCurrentText("组指令")
                self.on_selected_cmd_id = cmd.get('udp_group_id')
                # 从组指令中获取命令名称
                self.on_selected_cmd_name = self.on_selected_cmd_id
                for group in udp_groups:
                    if group.get('id') == self.on_selected_cmd_id:
                        self.on_selected_cmd_name = group.get('name', self.on_selected_cmd_id)
                        break
                self.on_selected_cmd_label.setText(f"已选择: {self.on_selected_cmd_name}")
                self.on_selected_cmd_label.setStyleSheet("color: #000")
            elif cmd.get('type') == 'udp' and 'udp_command_id' in cmd and cmd.get('state') == 'off':
                # 关状态指令表指令
                self.off_cmd_type_combo.setCurrentText("指令表")
                self.off_selected_cmd_id = cmd.get('udp_command_id')
                # 从指令表中获取命令名称
                self.off_selected_cmd_name = self.off_selected_cmd_id
                for udp_cmd in udp_commands:
                    if udp_cmd.get('id') == self.off_selected_cmd_id:
                        self.off_selected_cmd_name = udp_cmd.get('name', self.off_selected_cmd_id)
                        break
                self.off_selected_cmd_label.setText(f"已选择: {self.off_selected_cmd_name}")
                self.off_selected_cmd_label.setStyleSheet("color: #000")
            elif cmd.get('type') == 'udp_group' and 'udp_group_id' in cmd and cmd.get('state') == 'off':
                # 关状态组指令
                self.off_cmd_type_combo.setCurrentText("组指令")
                self.off_selected_cmd_id = cmd.get('udp_group_id')
                # 从组指令中获取命令名称
                self.off_selected_cmd_name = self.off_selected_cmd_id
                for group in udp_groups:
                    if group.get('id') == self.off_selected_cmd_id:
                        self.off_selected_cmd_name = group.get('name', self.off_selected_cmd_id)
                        break
                self.off_selected_cmd_label.setText(f"已选择: {self.off_selected_cmd_name}")
                self.off_selected_cmd_label.setStyleSheet("color: #000")

    def accept(self):
        commands = []
        
        # 添加开状态指令
        if self.on_selected_cmd_id:
            if self.on_cmd_type_combo.currentText() == "指令表":
                # 添加指令表指令
                commands.append({
                    "type": "udp",
                    "udp_command_id": self.on_selected_cmd_id,
                    "name": self.on_selected_cmd_name,
                    "state": "on"
                })
            else:
                # 添加组指令
                commands.append({
                    "type": "udp_group",
                    "udp_group_id": self.on_selected_cmd_id,
                    "name": self.on_selected_cmd_name,
                    "state": "on"
                })

        # 添加关状态指令
        if self.off_selected_cmd_id:
            if self.off_cmd_type_combo.currentText() == "指令表":
                # 添加指令表指令
                commands.append({
                    "type": "udp",
                    "udp_command_id": self.off_selected_cmd_id,
                    "name": self.off_selected_cmd_name,
                    "state": "off"
                })
            else:
                # 添加组指令
                commands.append({
                    "type": "udp_group",
                    "udp_group_id": self.off_selected_cmd_id,
                    "name": self.off_selected_cmd_name,
                    "state": "off"
                })

        # 获取ID和名称
        btn_id = self.id_edit.text().strip()
        if not btn_id:
            QMessageBox.warning(self, "错误", "ID不能为空")
            return
            
        btn_name = self.name_edit.text().strip() or f"开关{btn_id}"
        
        # 确保ID只包含基础部分（去掉可能存在的名称部分）
        if '_' in btn_id:
            btn_id = btn_id.split('_')[0]
            
        # 获取设备指令设置
        device_use = self.device_checkbox.isChecked()
        device_id = ""
        device_cmd_index = 0
        
        if device_use:
            device_index = self.device_combo.currentIndex()
            if device_index >= 0:
                device_id = self.device_combo.itemData(device_index)
            
            cmd_index = self.cmd_combo.currentIndex()
            if cmd_index >= 0:
                device_cmd_index = cmd_index
        
        self.cfg_out = {
            'id': f"{btn_id}",  # 只保存基础ID，不包含名称
            'name': btn_name,   # 单独保存名称
            'on_src': self.on_src_edit.text(),
            'off_src': self.off_src_edit.text(),
            'w': self.w_spin.value(),
            'h': self.h_spin.value(),
            'x': self.x_spin.value(),
            'y': self.y_spin.value(),
            'type': 'switch',
            'commands': commands,
            # 设备指令设置
            'device_use': device_use,
            'device_id': device_id,
            'device_cmd_index': device_cmd_index,
            # 状态显示设置
            'status_enable': self.status_enable_check.isChecked(),
            'status_ip': self.status_ip_edit.text(),
            'status_port': self.status_port_spin.value(),
            'status_query_cmd': self.status_query_edit.text(),
            'status_response_cmd': self.status_response_edit.text()
        }
        super().accept()
    
    def on_device_checkbox_changed(self, checked):
        """设备指令复选框状态变化处理"""
        # toggled 信号传递的是布尔值：checked 为 True 表示勾选，False 表示未勾选
        enabled = checked
        
        # 强制设置下拉框启用状态
        self.device_combo.setEnabled(enabled)
        self.cmd_combo.setEnabled(enabled)
        
        # 确保下拉框确实被启用
        print(f"设备指令复选框状态: {checked}, 下拉框启用状态: {enabled}")
        print(f"设备下拉框实际状态: {self.device_combo.isEnabled()}")
        print(f"指令下拉框实际状态: {self.cmd_combo.isEnabled()}")
        
        # 如果重新勾选，重新加载设备列表
        if enabled:
            print("重新加载设备列表")
            # 再次强制启用下拉框，确保状态正确
            self.device_combo.setEnabled(True)
            self.cmd_combo.setEnabled(True)
            # 加载设备列表
            self._load_devices()
    
    def _load_devices(self):
        """加载设备列表"""
        # 清空现有列表
        self.device_combo.clear()
        self.cmd_combo.clear()

        # 确保下拉框是启用的
        self.device_combo.setEnabled(True)
        self.cmd_combo.setEnabled(True)

        # 加载配置
        cfg = load_cfg()
        devices = cfg.get('devices', [])

        # 添加设备到下拉框
        device_id_to_name = {}
        for device in devices:
            device_id = device.get('id', '')
            device_name = device.get('name', '未命名设备')
            self.device_combo.addItem(device_name, device_id)
            device_id_to_name[device_id] = device_name

        # 设置当前设备
        device_id = self.cfg.get('device_id', '')
        if device_id:
            for i in range(self.device_combo.count()):
                if self.device_combo.itemData(i) == device_id:
                    self.device_combo.setCurrentIndex(i)
                    # 加载设备指令
                    self._load_device_commands(device_id)
                    break
    
    def _load_device_commands(self, device_id):
        """加载设备指令"""
        # 清空现有列表
        self.cmd_combo.clear()

        # 加载配置
        cfg = load_cfg()
        devices = cfg.get('devices', [])

        # 查找选中的设备
        for device in devices:
            if device.get('id') == device_id:
                commands = device.get('commands', [])
                # 添加指令到下拉框
                for i, cmd in enumerate(commands):
                    cmd_name = cmd.get('name', f"指令{i+1}")
                    self.cmd_combo.addItem(cmd_name, i)
                break

        # 设置当前指令
        cmd_index = self.cfg.get('device_cmd_index', 0)
        if 0 <= cmd_index < self.cmd_combo.count():
            self.cmd_combo.setCurrentIndex(cmd_index)
    
    def on_device_changed(self, index):
        """设备选择变化处理"""
        if index >= 0:
            device_id = self.device_combo.itemData(index)
            self._load_device_commands(device_id)


class AirconPropsDlg(QDialog):
    def __init__(self, cfg, logic_w, logic_h):
        super().__init__()
        self.cfg = copy.deepcopy(cfg)
        self.logic_w = logic_w
        self.logic_h = logic_h
        self.setWindowTitle("空调面板属性")

        lay = QFormLayout(self)

        # 解析ID和名称
        btn_id = self.cfg['id']
        if '_' in btn_id:
            # 如果ID中包含下划线，则分割ID和名称
            id_parts = btn_id.split('_', 1)
            btn_id = id_parts[0]
            default_name = id_parts[1] if len(id_parts) > 1 else f"空调面板{btn_id}"
        else:
            default_name = self.cfg.get('name', f"空调面板{btn_id}")
        
        # ID 和名称行
        id_lay = QHBoxLayout()
        id_lay.addWidget(QLabel("ID"))
        self.id_edit = QLineEdit(btn_id)
        # 添加输入验证器，只允许字母和数字
        self.id_edit.setValidator(QRegularExpressionValidator(QRegularExpression(r'[a-zA-Z0-9_]+')))
        id_lay.addWidget(self.id_edit)
        
        name_lay = QHBoxLayout()
        name_lay.addWidget(QLabel("名称"))
        self.name_edit = QLineEdit(default_name)
        name_lay.addWidget(self.name_edit)
        
        id_name_lay = QHBoxLayout()
        id_name_lay.addLayout(id_lay, 1)
        id_name_lay.addLayout(name_lay, 2)
        lay.addRow("ID和名称", id_name_lay)

        # 位置和大小
        w = QSpinBox()
        w.setRange(1, self.logic_w)
        w.setValue(int(self.cfg['w']))
        h = QSpinBox()
        h.setRange(1, self.logic_h)
        h.setValue(int(self.cfg['h']))
        x = QSpinBox()
        x.setRange(0, self.logic_w)
        x.setValue(int(self.cfg['x']))
        y = QSpinBox()
        y.setRange(0, self.logic_h)
        y.setValue(int(self.cfg['y']))
        lay.addRow("宽度 (像素)", w)
        lay.addRow("高度 (像素)", h)
        lay.addRow("X (像素)", x)
        lay.addRow("Y (像素)", y)
        self.w_spin, self.h_spin = w, h
        self.x_spin, self.y_spin = x, y

        # 空调面板特有属性
        aircon_group = QGroupBox("空调面板属性")
        aircon_layout = QVBoxLayout()
        
        # 模式设置
        mode_layout = QHBoxLayout()
        mode_label = QLabel("模式:")
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["自动", "制冷", "制热", "送风", "除湿"])
        mode_map = {"auto": 0, "cool": 1, "heat": 2, "fan": 3, "dry": 4}
        self.mode_combo.setCurrentIndex(mode_map.get(self.cfg.get('mode', 'auto'), 0))
        mode_layout.addWidget(mode_label)
        mode_layout.addWidget(self.mode_combo)
        aircon_layout.addLayout(mode_layout)
        
        # 温度设置
        temp_layout = QHBoxLayout()
        temp_label = QLabel("温度:")
        self.temp_spin = QSpinBox()
        self.temp_spin.setRange(16, 30)
        self.temp_spin.setValue(self.cfg.get('temperature', 26))
        temp_layout.addWidget(temp_label)
        temp_layout.addWidget(self.temp_spin)
        aircon_layout.addLayout(temp_layout)
        
        # 风速设置
        fan_layout = QHBoxLayout()
        fan_label = QLabel("风速:")
        self.fan_combo = QComboBox()
        self.fan_combo.addItems(["低", "中", "高", "自动"])
        fan_map = {"low": 0, "medium": 1, "high": 2, "auto": 3}
        self.fan_combo.setCurrentIndex(fan_map.get(self.cfg.get('fan_speed', 'medium'), 1))
        fan_layout.addWidget(fan_label)
        fan_layout.addWidget(self.fan_combo)
        aircon_layout.addLayout(fan_layout)
        
        # 电源状态设置
        power_layout = QHBoxLayout()
        power_label = QLabel("电源:")
        self.power_combo = QComboBox()
        self.power_combo.addItems(["关", "开"])
        power_map = {"off": 0, "on": 1}
        self.power_combo.setCurrentIndex(power_map.get(self.cfg.get('power', 'off'), 0))
        power_layout.addWidget(power_label)
        power_layout.addWidget(self.power_combo)
        aircon_layout.addLayout(power_layout)
        
        aircon_group.setLayout(aircon_layout)
        lay.addRow(aircon_group)

        # 状态显示设置
        status_group = QGroupBox("状态显示设置")
        status_layout = QVBoxLayout()
        
        # 状态显示开关
        status_enable_layout = QHBoxLayout()
        status_enable_check = QCheckBox("启用状态显示")
        status_enable_layout.addWidget(status_enable_check)
        status_layout.addLayout(status_enable_layout)
        
        # UDP询问指令设置
        udp_query_layout = QGridLayout()
        udp_query_layout.addWidget(QLabel("IP地址:"), 0, 0)
        status_ip_edit = QLineEdit(self.cfg.get('status_ip', ''))
        udp_query_layout.addWidget(status_ip_edit, 0, 1)
        
        udp_query_layout.addWidget(QLabel("端口:"), 0, 2)
        status_port_spin = QSpinBox()
        status_port_spin.setRange(1, 65535)
        status_port_spin.setValue(self.cfg.get('status_port', 5005))
        udp_query_layout.addWidget(status_port_spin, 0, 3)
        
        udp_query_layout.addWidget(QLabel("询问指令:"), 1, 0)
        status_query_edit = QLineEdit(self.cfg.get('status_query_cmd', ''))
        udp_query_layout.addWidget(status_query_edit, 1, 1, 1, 3)
        
        udp_query_layout.addWidget(QLabel("响应指令:"), 2, 0)
        status_response_edit = QLineEdit(self.cfg.get('status_response_cmd', ''))
        udp_query_layout.addWidget(status_response_edit, 2, 1, 1, 3)
        status_layout.addLayout(udp_query_layout)
        
        status_group.setLayout(status_layout)
        lay.addRow(status_group)
        
        # 保存状态设置控件引用
        self.status_enable_check = status_enable_check
        self.status_ip_edit = status_ip_edit
        self.status_port_spin = status_port_spin
        self.status_query_edit = status_query_edit
        self.status_response_edit = status_response_edit

        # 加载已保存的状态设置
        self.status_enable_check.setChecked(self.cfg.get('status_enable', False))

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def accept(self):
        commands = []
        
        # 获取ID和名称
        btn_id = self.id_edit.text().strip()
        if not btn_id:
            QMessageBox.warning(self, "错误", "ID不能为空")
            return
            
        btn_name = self.name_edit.text().strip() or f"空调面板{btn_id}"
        
        # 确保ID只包含基础部分（去掉可能存在的名称部分）
        if '_' in btn_id:
            btn_id = btn_id.split('_')[0]
            
        # 转换模式、风速和电源状态为内部值
        mode_map = {0: "auto", 1: "cool", 2: "heat", 3: "fan", 4: "dry"}
        mode = mode_map[self.mode_combo.currentIndex()]
        
        fan_map = {0: "low", 1: "medium", 2: "high", 3: "auto"}
        fan_speed = fan_map[self.fan_combo.currentIndex()]
        
        power_map = {0: "off", 1: "on"}
        power = power_map[self.power_combo.currentIndex()]
            
        self.cfg_out = {
            'id': f"{btn_id}",  # 只保存基础ID，不包含名称
            'name': btn_name,   # 单独保存名称
            'w': self.w_spin.value(),
            'h': self.h_spin.value(),
            'x': self.x_spin.value(),
            'y': self.y_spin.value(),
            'type': 'aircon',
            'commands': commands,
            # 空调面板特有属性
            'mode': mode,
            'temperature': self.temp_spin.value(),
            'fan_speed': fan_speed,
            'power': power,
            # 状态显示设置
            'status_enable': self.status_enable_check.isChecked(),
            'status_ip': self.status_ip_edit.text(),
            'status_port': self.status_port_spin.value(),
            'status_query_cmd': self.status_query_edit.text(),
            'status_response_cmd': self.status_response_edit.text()
        }
        super().accept()


class SwitchPropsDlg(QDialog):
    def __init__(self, cfg, logic_w, logic_h):
        super().__init__()
        self.cfg = copy.deepcopy(cfg)
        self.logic_w = logic_w
        self.logic_h = logic_h
        self.setWindowTitle("开关属性")

        lay = QFormLayout(self)

        # 解析ID和名称
        btn_id = self.cfg['id']
        if '_' in btn_id:
            # 如果ID中包含下划线，则分割ID和名称
            id_parts = btn_id.split('_', 1)
            btn_id = id_parts[0]
            default_name = id_parts[1] if len(id_parts) > 1 else f"开关{btn_id}"
        else:
            default_name = self.cfg.get('name', f"开关{btn_id}")
        
        # ID 和名称行
        id_lay = QHBoxLayout()
        id_lay.addWidget(QLabel("ID"))
        self.id_edit = QLineEdit(btn_id)
        # 添加输入验证器，只允许字母和数字
        self.id_edit.setValidator(QRegularExpressionValidator(QRegularExpression(r'[a-zA-Z0-9_]+')))
        id_lay.addWidget(self.id_edit)
        
        name_lay = QHBoxLayout()
        name_lay.addWidget(QLabel("名称"))
        self.name_edit = QLineEdit(default_name)
        name_lay.addWidget(self.name_edit)
        
        id_name_lay = QHBoxLayout()
        id_name_lay.addLayout(id_lay, 1)
        id_name_lay.addLayout(name_lay, 2)
        lay.addRow("ID和名称", id_name_lay)

        # 位置和大小
        w = QSpinBox()
        w.setRange(1, self.logic_w)
        w.setValue(int(self.cfg['w']))
        h = QSpinBox()
        h.setRange(1, self.logic_h)
        h.setValue(int(self.cfg['h']))
        x = QSpinBox()
        x.setRange(0, self.logic_w)
        x.setValue(int(self.cfg['x']))
        y = QSpinBox()
        y.setRange(0, self.logic_h)
        y.setValue(int(self.cfg['y']))
        lay.addRow("宽度 (像素)", w)
        lay.addRow("高度 (像素)", h)
        lay.addRow("X (像素)", x)
        lay.addRow("Y (像素)", y)
        self.w_spin, self.h_spin = w, h
        self.x_spin, self.y_spin = x, y

        # 开关图片设置
        self.on_src_edit = QLineEdit(self.cfg.get('on_src', ''))
        browse_on = QPushButton("浏览")
        browse_on.clicked.connect(lambda: self.browse(self.on_src_edit))
        hl_on = QHBoxLayout()
        hl_on.addWidget(self.on_src_edit)
        hl_on.addWidget(browse_on)
        lay.addRow("开状态图片", hl_on)

        self.off_src_edit = QLineEdit(self.cfg.get('off_src', ''))
        browse_off = QPushButton("浏览")
        browse_off.clicked.connect(lambda: self.browse(self.off_src_edit))
        hl_off = QHBoxLayout()
        hl_off.addWidget(self.off_src_edit)
        hl_off.addWidget(browse_off)
        lay.addRow("关状态图片", hl_off)

        # 设备勾选项
        device_group = QGroupBox("设备设置")
        device_layout = QVBoxLayout()
        
        # 设备勾选
        self.device_check = QCheckBox("使用设备指令")
        device_layout.addWidget(self.device_check)
        
        # 设备选择
        device_select_layout = QHBoxLayout()
        device_select_layout.addWidget(QLabel("设备:"))
        self.device_combo = QComboBox()
        device_select_layout.addWidget(self.device_combo)
        device_layout.addLayout(device_select_layout)
        
        # 指令选择
        cmd_select_layout = QHBoxLayout()
        cmd_select_layout.addWidget(QLabel("指令:"))
        self.cmd_combo = QComboBox()
        cmd_select_layout.addWidget(self.cmd_combo)
        device_layout.addLayout(cmd_select_layout)
        
        device_group.setLayout(device_layout)
        lay.addRow(device_group)

        # 指令配置
        cmd_group = QGroupBox("指令配置")
        cmd_layout = QVBoxLayout()
        
        # 开状态指令
        on_cmd_layout = QHBoxLayout()
        on_cmd_layout.addWidget(QLabel("开指令:"))
        self.on_cmd_edit = QLineEdit()
        on_cmd_layout.addWidget(self.on_cmd_edit)
        cmd_layout.addLayout(on_cmd_layout)
        
        # 关状态指令
        off_cmd_layout = QHBoxLayout()
        off_cmd_layout.addWidget(QLabel("关指令:"))
        self.off_cmd_edit = QLineEdit()
        off_cmd_layout.addWidget(self.off_cmd_edit)
        cmd_layout.addLayout(off_cmd_layout)
        
        # 询问指令（状态检测）
        query_cmd_layout = QHBoxLayout()
        query_cmd_layout.addWidget(QLabel("询问指令:"))
        self.query_cmd_edit = QLineEdit()
        query_cmd_layout.addWidget(self.query_cmd_edit)
        cmd_layout.addLayout(query_cmd_layout)
        
        # 响应指令（状态检测）
        response_cmd_layout = QHBoxLayout()
        response_cmd_layout.addWidget(QLabel("响应指令:"))
        self.response_cmd_edit = QLineEdit()
        response_cmd_layout.addWidget(self.response_cmd_edit)
        cmd_layout.addLayout(response_cmd_layout)
        
        cmd_group.setLayout(cmd_layout)
        lay.addRow(cmd_group)

        # 加载设备列表
        self.load_devices()
        
        # 连接信号
        self.device_check.stateChanged.connect(self.on_device_check_changed)
        self.device_combo.currentIndexChanged.connect(self.on_device_changed)
        
        # 加载已保存的设置
        self._load_saved_settings()

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def browse(self, line_edit):
        path, _ = QFileDialog.getOpenFileName(self, "选择图片", DATA_DIR, "图片 (*.png *.jpg *.jpeg *.bmp *.gif)")
        if path:
            filename = os.path.basename(path)
            line_edit.setText(filename)

    def load_devices(self):
        """加载设备列表"""
        cfg = load_cfg()
        devices = cfg.get('devices', [])
        
        # 清空现有项
        self.device_combo.clear()
        self.device_combo.addItem("请选择设备")
        
        # 添加设备
        for device in devices:
            self.device_combo.addItem(device.get('name', '未命名设备'), device)

    def on_device_check_changed(self, state):
        """设备勾选状态改变"""
        enabled = state == Qt.Checked
        self.device_combo.setEnabled(enabled)
        self.cmd_combo.setEnabled(enabled)
        
        # 当勾选设备时，禁用手动指令输入
        self.on_cmd_edit.setEnabled(not enabled)
        self.off_cmd_edit.setEnabled(not enabled)
        self.query_cmd_edit.setEnabled(not enabled)
        self.response_cmd_edit.setEnabled(not enabled)
        
        if enabled:
            # 当勾选设备时，重新加载设备列表
            self.load_devices()
            
            # 加载已保存的设备和指令选择
            device_id = self.cfg.get('device_id', '')
            cmd_index = self.cfg.get('device_cmd_index', 0)
            
            # 查找并设置设备
            for i in range(self.device_combo.count()):
                device = self.device_combo.itemData(i)
                if device and device.get('id') == device_id:
                    self.device_combo.setCurrentIndex(i)
                    break
            
            # 更新指令列表
            self.on_device_changed(self.device_combo.currentIndex())

    def on_device_changed(self, index):
        """设备选择改变"""
        if index <= 0:
            self.cmd_combo.clear()
            self.cmd_combo.addItem("请选择指令")
            return
        
        # 获取选中的设备
        device = self.device_combo.itemData(index)
        if not device:
            return
        
        # 清空现有指令
        self.cmd_combo.clear()
        self.cmd_combo.addItem("请选择指令")
        
        # 添加设备指令
        commands = device.get('commands', [])
        for i, cmd in enumerate(commands):
            self.cmd_combo.addItem(cmd.get('name', f"指令{i+1}"), cmd)

    def _load_saved_settings(self):
        """加载已保存的设置"""
        # 加载设备设置
        device_use = self.cfg.get('device_use', False)
        self.device_check.setChecked(device_use)
        
        # 加载设备和指令选择
        device_id = self.cfg.get('device_id', '')
        cmd_index = self.cfg.get('device_cmd_index', 0)
        
        # 查找并设置设备
        for i in range(self.device_combo.count()):
            device = self.device_combo.itemData(i)
            if device and device.get('id') == device_id:
                self.device_combo.setCurrentIndex(i)
                break
        
        # 触发设备改变事件
        self.on_device_changed(self.device_combo.currentIndex())
        
        # 查找并设置指令
        if cmd_index > 0 and cmd_index < self.cmd_combo.count():
            self.cmd_combo.setCurrentIndex(cmd_index)
        
        # 加载指令设置
        on_cmd = self.cfg.get('on_cmd', '')
        off_cmd = self.cfg.get('off_cmd', '')
        query_cmd = self.cfg.get('query_cmd', '')
        response_cmd = self.cfg.get('response_cmd', '')
        
        self.on_cmd_edit.setText(on_cmd)
        self.off_cmd_edit.setText(off_cmd)
        self.query_cmd_edit.setText(query_cmd)
        self.response_cmd_edit.setText(response_cmd)
        
        # 加载图片设置
        self.on_src_edit.setText(self.cfg.get('on_src', ''))
        self.off_src_edit.setText(self.cfg.get('off_src', ''))
        
        # 触发设备勾选状态改变事件
        self.on_device_check_changed(Qt.Checked if device_use else Qt.Unchecked)

    def accept(self):
        # 获取ID和名称
        btn_id = self.id_edit.text().strip()
        if not btn_id:
            QMessageBox.warning(self, "错误", "ID不能为空")
            return
            
        btn_name = self.name_edit.text().strip() or f"开关{btn_id}"
        
        # 确保ID只包含基础部分（去掉可能存在的名称部分）
        if '_' in btn_id:
            btn_id = btn_id.split('_')[0]
        
        # 设备设置
        device_use = self.device_check.isChecked()
        device_id = ""
        device_cmd_index = 0
        
        if device_use:
            # 获取选中的设备
            device_index = self.device_combo.currentIndex()
            if device_index > 0:
                device = self.device_combo.itemData(device_index)
                if device:
                    device_id = device.get('id', '')
            
            # 获取选中的指令
            cmd_index = self.cmd_combo.currentIndex()
            if cmd_index > 0:
                device_cmd_index = cmd_index
        
        # 指令设置
        on_cmd = self.on_cmd_edit.text()
        off_cmd = self.off_cmd_edit.text()
        query_cmd = self.query_cmd_edit.text()
        response_cmd = self.response_cmd_edit.text()
        
        # 如果使用设备指令，从设备中获取指令
        if device_use:
            device_index = self.device_combo.currentIndex()
            cmd_index = self.cmd_combo.currentIndex()
            
            if device_index > 0 and cmd_index > 0:
                device = self.device_combo.itemData(device_index)
                cmd = self.cmd_combo.itemData(cmd_index)
                
                if device and cmd:
                    on_cmd = cmd.get('on', '')
                    off_cmd = cmd.get('off', '')
                    query_cmd = cmd.get('check', '')
                    response_cmd = cmd.get('feedback', '')
        
        self.cfg_out = {
            'id': f"{btn_id}",  # 只保存基础ID，不包含名称
            'name': btn_name,   # 单独保存名称
            'w': self.w_spin.value(),
            'h': self.h_spin.value(),
            'x': self.x_spin.value(),
            'y': self.y_spin.value(),
            'type': 'switch',
            'on_src': self.on_src_edit.text(),
            'off_src': self.off_src_edit.text(),
            'device_use': device_use,
            'device_id': device_id,
            'device_cmd_index': device_cmd_index,
            'on_cmd': on_cmd,
            'off_cmd': off_cmd,
            'query_cmd': query_cmd,
            'response_cmd': response_cmd,
            # 不需要状态显示设置，因为开关的实时状态就可以反应实际状态
            'status_enable': False
        }
        super().accept()


class ButtonPropsDlg(QDialog):
    def __init__(self, cfg, logic_w, logic_h):
        super().__init__()
        self.cfg = copy.deepcopy(cfg)
        self.logic_w = logic_w
        self.logic_h = logic_h
        self.setWindowTitle("按钮属性")

        lay = QFormLayout(self)

        # 解析ID和名称
        btn_id = self.cfg['id']
        if '_' in btn_id:
            # 如果ID中包含下划线，则分割ID和名称
            id_parts = btn_id.split('_', 1)
            btn_id = id_parts[0]
            default_name = id_parts[1] if len(id_parts) > 1 else f"按钮{btn_id}"
        else:
            default_name = self.cfg.get('name', f"按钮{btn_id}")
        
        # ID 和名称行
        id_lay = QHBoxLayout()
        id_lay.addWidget(QLabel("ID"))
        self.id_edit = QLineEdit(btn_id)
        # 添加输入验证器，只允许字母和数字
        self.id_edit.setValidator(QRegularExpressionValidator(QRegularExpression(r'[a-zA-Z0-9_]+')))
        id_lay.addWidget(self.id_edit)
        
        name_lay = QHBoxLayout()
        name_lay.addWidget(QLabel("名称"))
        self.name_edit = QLineEdit(default_name)
        name_lay.addWidget(self.name_edit)
        
        id_name_lay = QHBoxLayout()
        id_name_lay.addLayout(id_lay, 1)
        id_name_lay.addLayout(name_lay, 2)
        lay.addRow("ID和名称", id_name_lay)

        self.src_edit = QLineEdit(self.cfg['src'])
        browse = QPushButton("浏览")
        browse.clicked.connect(lambda: self.browse(self.src_edit))
        hl = QHBoxLayout()
        hl.addWidget(self.src_edit)
        hl.addWidget(browse)
        lay.addRow("图片", hl)

        self.psrc_edit = QLineEdit(self.cfg['pressed_src'])
        browse2 = QPushButton("浏览")
        browse2.clicked.connect(lambda: self.browse(self.psrc_edit))
        hl2 = QHBoxLayout()
        hl2.addWidget(self.psrc_edit)
        hl2.addWidget(browse2)
        lay.addRow("按下图片", hl2)

        w = QSpinBox()
        w.setRange(1, self.logic_w)
        w.setValue(int(self.cfg['w']))
        h = QSpinBox()
        h.setRange(1, self.logic_h)
        h.setValue(int(self.cfg['h']))
        x = QSpinBox()
        x.setRange(0, self.logic_w)
        x.setValue(int(self.cfg['x']))
        y = QSpinBox()
        y.setRange(0, self.logic_h)
        y.setValue(int(self.cfg['y']))
        lay.addRow("宽度 (像素)", w)
        lay.addRow("高度 (像素)", h)
        lay.addRow("X (像素)", x)
        lay.addRow("Y (像素)", y)
        self.w_spin, self.h_spin = w, h
        self.x_spin, self.y_spin = x, y

        self.page_spin = QSpinBox()
        self.page_spin.setMinimum(0)
        self.page_spin.setMaximum(9999)
        self.page_spin.setValue(self.cfg.get('switch_page', 0))
        lay.addRow("跳转目标页码 (0为无跳转)", self.page_spin)

        # 发送指令配置
        cmd_group = QGroupBox("发送指令配置")
        cmd_layout = QVBoxLayout()
        
        # 选择指令类型
        type_layout = QHBoxLayout()
        type_label = QLabel("指令类型:")
        self.cmd_type_combo = QComboBox()
        self.cmd_type_combo.addItems(["指令表", "组指令"])
        self.cmd_type_combo.currentIndexChanged.connect(self.on_cmd_type_changed)
        type_layout.addWidget(type_label)
        type_layout.addWidget(self.cmd_type_combo)
        cmd_layout.addLayout(type_layout)
        
        # 指令选择按钮
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(QLabel("选择指令:"))
        self.cmd_select_btn = QPushButton("点击选择")
        self.cmd_select_btn.clicked.connect(self.select_command)
        btn_layout.addWidget(self.cmd_select_btn)
        
        # 显示选中的指令
        self.selected_cmd_label = QLabel("未选择指令")
        self.selected_cmd_label.setStyleSheet("color: #666")
        btn_layout.addWidget(self.selected_cmd_label)
        btn_layout.addStretch()
        cmd_layout.addLayout(btn_layout)
        
        # 加载已保存的指令信息
        self.selected_cmd_id = None
        self.selected_cmd_name = ""
        self._load_saved_command()
        
        cmd_group.setLayout(cmd_layout)
        lay.addRow(cmd_group)

        # 状态显示设置
        status_group = QGroupBox("状态显示设置")
        status_layout = QVBoxLayout()
        
        # 状态显示开关
        status_enable_layout = QHBoxLayout()
        status_enable_check = QCheckBox("启用状态显示")
        status_enable_layout.addWidget(status_enable_check)
        status_layout.addLayout(status_enable_layout)
        
        # UDP询问指令设置
        udp_query_layout = QGridLayout()
        udp_query_layout.addWidget(QLabel("IP地址:"), 0, 0)
        status_ip_edit = QLineEdit(self.cfg.get('status_ip', ''))
        udp_query_layout.addWidget(status_ip_edit, 0, 1)
        
        udp_query_layout.addWidget(QLabel("端口:"), 0, 2)
        status_port_spin = QSpinBox()
        status_port_spin.setRange(1, 65535)
        status_port_spin.setValue(self.cfg.get('status_port', 5005))
        udp_query_layout.addWidget(status_port_spin, 0, 3)
        
        udp_query_layout.addWidget(QLabel("询问指令:"), 1, 0)
        status_query_edit = QLineEdit(self.cfg.get('status_query_cmd', ''))
        udp_query_layout.addWidget(status_query_edit, 1, 1, 1, 3)
        
        udp_query_layout.addWidget(QLabel("响应指令:"), 2, 0)
        status_response_edit = QLineEdit(self.cfg.get('status_response_cmd', ''))
        udp_query_layout.addWidget(status_response_edit, 2, 1, 1, 3)
        status_layout.addLayout(udp_query_layout)
        
        status_group.setLayout(status_layout)
        lay.addRow(status_group)
        
        # 保存状态设置控件引用
        self.status_enable_check = status_enable_check
        self.status_ip_edit = status_ip_edit
        self.status_port_spin = status_port_spin
        self.status_query_edit = status_query_edit
        self.status_response_edit = status_response_edit
        
        # 加载已保存的状态设置
        self.status_enable_check.setChecked(self.cfg.get('status_enable', False))

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def browse(self, line_edit):
        path, _ = QFileDialog.getOpenFileName(self, "选择图片", DATA_DIR, "图片 (*.png *.jpg *.jpeg *.bmp *.gif)")
        if path:
            filename = os.path.basename(path)
            line_edit.setText(filename)

    def select_command(self):
        """选择指令（带搜索功能）"""
        # 获取配置
        cfg = load_cfg()
        
        # 根据选择的类型获取指令列表
        if self.cmd_type_combo.currentText() == "指令表":
            commands = cfg.get('udp_commands', [])
        else:
            commands = cfg.get('udp_groups', [])
        
        # 创建带搜索功能的选择对话框
        dlg = QDialog(self)
        dlg.setWindowTitle("选择指令")
        dlg.resize(400, 300)
        
        layout = QVBoxLayout(dlg)
        
        # 搜索框
        search_layout = QHBoxLayout()
        search_label = QLabel("搜索:")
        search_edit = QLineEdit()
        search_edit.setPlaceholderText("输入指令名称搜索...")
        search_layout.addWidget(search_label)
        search_layout.addWidget(search_edit)
        layout.addLayout(search_layout)
        
        # 指令列表
        list_widget = QListWidget()
        layout.addWidget(list_widget)
        
        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        ok_btn = QPushButton("确定")
        cancel_btn = QPushButton("取消")
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
        # 加载指令列表
        def load_cmd_list():
            list_widget.clear()
            for cmd in commands:
                item = QListWidgetItem(cmd.get('name', cmd.get('id', '')))
                item.setData(Qt.UserRole, cmd.get('id', ''))
                list_widget.addItem(item)
        
        load_cmd_list()
        
        # 搜索功能
        def update_list():
            search_text = search_edit.text().lower()
            
            for i in range(list_widget.count()):
                item = list_widget.item(i)
                item_text = item.text().lower()
                
                # 按空格分割搜索关键字
                keywords = [kw.strip() for kw in search_text.split() if kw.strip()]
                
                if not keywords:
                    # 搜索框为空，显示所有指令
                    item.setHidden(False)
                else:
                    # 检查指令是否包含所有关键字（大小写不敏感）
                    if all(keyword in item_text for keyword in keywords):
                        item.setHidden(False)
                    else:
                        item.setHidden(True)
        
        search_edit.textChanged.connect(update_list)
        
        # 连接信号
        selected_item = None
        
        def on_ok():
            nonlocal selected_item
            items = list_widget.selectedItems()
            if items:
                selected_item = items[0]
                dlg.accept()
            else:
                QMessageBox.warning(dlg, "提示", "请选择一个指令")
        
        ok_btn.clicked.connect(on_ok)
        cancel_btn.clicked.connect(dlg.reject)
        
        # 双击选择
        def on_item_double_clicked(item):
            nonlocal selected_item
            selected_item = item
            dlg.accept()
        
        list_widget.itemDoubleClicked.connect(on_item_double_clicked)
        
        # 执行对话框
        if dlg.exec() == QDialog.Accepted and selected_item:
            self.selected_cmd_id = selected_item.data(Qt.UserRole)
            self.selected_cmd_name = selected_item.text()
            self.selected_cmd_label.setText(f"已选择: {self.selected_cmd_name}")
            self.selected_cmd_label.setStyleSheet("color: #000")
    
    def _load_saved_command(self):
        """加载已保存的指令信息"""
        # 获取命令配置
        commands = self.cfg.get('commands', [])
        
        for cmd in commands:
            if cmd.get('type') == 'udp' and 'udp_command_id' in cmd:
                # 指令表指令
                self.cmd_type_combo.setCurrentText("指令表")
                self.selected_cmd_id = cmd.get('udp_command_id')
                self.selected_cmd_name = cmd.get('name', '')
                self.selected_cmd_label.setText(f"已选择: {self.selected_cmd_name}")
                self.selected_cmd_label.setStyleSheet("color: #000")
                break
            elif cmd.get('type') == 'udp_group' and 'udp_group_id' in cmd:
                # 组指令
                self.cmd_type_combo.setCurrentText("组指令")
                self.selected_cmd_id = cmd.get('udp_group_id')
                self.selected_cmd_name = cmd.get('name', '')
                self.selected_cmd_label.setText(f"已选择: {self.selected_cmd_name}")
                self.selected_cmd_label.setStyleSheet("color: #000")
                break
    
    def on_cmd_type_changed(self):
        """指令类型改变时的处理"""
        # 重置选中状态
        self.selected_cmd_id = None
        self.selected_cmd_name = ""
        self.selected_cmd_label.setText("未选择指令")
        self.selected_cmd_label.setStyleSheet("color: #666")
    
    def accept(self):
        switch_page = self.page_spin.value()
        commands = []
        
        # 添加跳转指令
        if switch_page != 0:
            commands.append({"type": "switch", "target": switch_page})
        
        # 添加选择的指令
        if self.selected_cmd_id:
            if self.cmd_type_combo.currentText() == "指令表":
                # 添加指令表指令
                commands.append({
                    "type": "udp",
                    "udp_command_id": self.selected_cmd_id,
                    "name": self.selected_cmd_name
                })
            else:
                # 添加组指令
                commands.append({
                    "type": "udp_group",
                    "udp_group_id": self.selected_cmd_id,
                    "name": self.selected_cmd_name
                })

        # 获取ID和名称
        btn_id = self.id_edit.text().strip()
        if not btn_id:
            QMessageBox.warning(self, "错误", "ID不能为空")
            return
            
        btn_name = self.name_edit.text().strip() or f"按钮{btn_id}"
        
        # 确保ID只包含基础部分（去掉可能存在的名称部分）
        if '_' in btn_id:
            btn_id = btn_id.split('_')[0]
            
        self.cfg_out = {
            'id': f"{btn_id}",  # 只保存基础ID，不包含名称
            'name': btn_name,   # 单独保存名称
            'src': self.src_edit.text(),
            'pressed_src': self.psrc_edit.text(),
            'w': self.w_spin.value(),
            'h': self.h_spin.value(),
            'x': self.x_spin.value(),
            'y': self.y_spin.value(),
            'switch_page': switch_page,
            'commands': commands,
            # 状态显示设置
            'status_enable': self.status_enable_check.isChecked(),
            'status_ip': self.status_ip_edit.text(),
            'status_port': self.status_port_spin.value(),
            'status_query_cmd': self.status_query_edit.text(),
            'status_response_cmd': self.status_response_edit.text()
        }
        super().accept()


class ButtonItem(QGraphicsPixmapItem):
    def __init__(self, cfg, logic_w, logic_h, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        # 确保有ID
        if not self.cfg.get('id'):
            # 生成10位字母数字组合的唯一ID
            import random
            import string
            
            def generate_id(length=10):
                characters = string.ascii_letters + string.digits
                return ''.join(random.choice(characters) for _ in range(length))
            
            # 确保ID唯一
            existing_ids = set()
            if hasattr(self, 'scene') and hasattr(self.scene(), 'page_cfg'):
                existing_ids = {btn.get('id', '') for btn in self.scene().page_cfg.get('buttons', [])}
            
            unique_id = None
            while not unique_id or unique_id in existing_ids:
                unique_id = generate_id(10)
            
            self.cfg['id'] = unique_id
        
        # 处理名称
        if 'name' not in self.cfg:
            # 尝试从ID中提取数字作为名称
            import re
            match = re.search(r'\d+', self.cfg['id'])
            num = match.group() if match else ''
            self.cfg['name'] = f"按钮{num}"
        
        self.logic_w = logic_w
        self.logic_h = logic_h
        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        
        # 状态显示相关属性
        self.status_item = None
        self.status_on = False
        
        self.update_pixmap()
        self.update_geometry()
        self.update_status_display()

    def update_pixmap(self):
        # 对于开关按钮，根据状态显示不同的图片
        if self.cfg.get('type') == 'switch':
            if self.status_on:
                src = self.cfg.get('on_src', '')
            else:
                src = self.cfg.get('off_src', '')
        elif self.cfg.get('type') == 'aircon':
            # 对于空调面板，创建一个默认的空调面板UI
            # 创建一个白色背景的QPixmap
            pixmap = QPixmap(self.cfg['w'], self.cfg['h'])
            pixmap.fill(Qt.white)
            
            # 创建QPainter绘制空调面板UI
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # 绘制边框
            painter.setPen(QPen(QColor(200, 200, 200), 2))
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(0, 0, self.cfg['w'], self.cfg['h'], 10, 10)
            
            # 绘制标题
            painter.setPen(QPen(QColor(33, 150, 243), 1))
            font = QFont()
            font.setBold(True)
            font.setPointSize(14)
            painter.setFont(font)
            painter.drawText(20, 30, "空调面板")
            
            # 绘制温度
            font.setPointSize(24)
            font.setBold(False)
            painter.setFont(font)
            painter.setPen(QPen(Qt.black, 1))
            painter.drawText(20, 70, f"温度: {self.cfg.get('temperature', 26)}°C")
            
            # 绘制模式
            painter.drawText(20, 100, f"模式: {self.cfg.get('mode', 'auto')}")
            
            # 绘制风速
            painter.drawText(20, 130, f"风速: {self.cfg.get('fan_speed', 'medium')}")
            
            # 绘制电源状态
            painter.drawText(20, 160, f"电源: {self.cfg.get('power', 'off')}")
            
            # 绘制提示信息
            font.setPointSize(10)
            painter.setPen(QPen(QColor(150, 150, 150), 1))
            painter.drawText(20, self.cfg['h'] - 20, "双击打开属性面板进行详细设置")
            
            painter.end()
            
            self.setPixmap(pixmap)
            return
        else:
            src = self.cfg['src']
        self.setPixmap(QPixmap(full_path(src)) if os.path.isfile(full_path(src)) else QPixmap(64, 64))

    def update_geometry(self):
        x = self.cfg['x']
        y = self.cfg['y']
        w = self.cfg['w']
        h = self.cfg['h']
        self.setPos(x, y)
        pixmap = self.pixmap()
        if pixmap.width() > 0 and pixmap.height() > 0:
            # Scale the pixmap to exactly match the target size
            scaled_pixmap = pixmap.scaled(w, h, 
                                       Qt.IgnoreAspectRatio, 
                                       Qt.SmoothTransformation)
            self.setPixmap(scaled_pixmap)
        # 不再重置缩放比例，让按钮能跟随View的缩放变换
        
        # 更新状态显示位置
        self.update_status_display()
    
    def update_status_display(self):
        """更新状态显示"""
        # 检查是否启用了状态显示
        if not self.cfg.get('status_enable', False):
            # 如果状态显示已禁用，移除状态显示项
            if self.status_item:
                scene = self.scene()
                if scene:
                    scene.removeItem(self.status_item)
                self.status_item = None
            return
        
        # 获取全局状态显示相关配置
        global_cfg = load_cfg()
        status_on_src = global_cfg.get('status_on_src', '')
        status_off_src = global_cfg.get('status_off_src', '')
        status_x = global_cfg.get('status_x', 0)
        status_y = global_cfg.get('status_y', 0)
        status_width = global_cfg.get('status_width', 32)
        status_height = global_cfg.get('status_height', 32)
        
        # 选择要显示的图片
        if self.status_on and status_on_src:
            status_src = status_on_src
        elif status_off_src:
            status_src = status_off_src
        else:
            # 如果没有图片，不显示状态
            if self.status_item:
                scene = self.scene()
                if scene:
                    scene.removeItem(self.status_item)
                self.status_item = None
            return
        
        # 创建或更新状态显示项
        if not self.status_item:
            from PySide6.QtWidgets import QGraphicsPixmapItem
            self.status_item = QGraphicsPixmapItem()
            self.status_item.setZValue(100)  # 确保状态显示在按钮上方
            scene = self.scene()
            if scene:
                scene.addItem(self.status_item)
        
        # 更新状态显示项的图片
        pixmap = QPixmap(full_path(status_src)) if os.path.isfile(full_path(status_src)) else QPixmap(status_width, status_height)
        if pixmap.width() > 0 and pixmap.height() > 0:
            scaled_pixmap = pixmap.scaled(status_width, status_height, 
                                       Qt.IgnoreAspectRatio, 
                                       Qt.SmoothTransformation)
            self.status_item.setPixmap(scaled_pixmap)
        
        # 更新状态显示项的位置
        button_x = self.cfg.get('x', 0)
        button_y = self.cfg.get('y', 0)
        self.status_item.setPos(button_x + status_x, button_y + status_y)
    
    def set_status(self, status_on):
        """设置状态并更新显示"""
        if self.status_on != status_on:
            self.status_on = status_on
            self.update_status_display()
            # 对于开关按钮，状态改变时更新图片
            if self.cfg.get('type') == 'switch':
                self.update_pixmap()
            
    def shape(self):
        # Return a shape that matches the full bounding rectangle
        # to make the entire area clickable, including transparent parts
        path = QPainterPath()
        path.addRect(self.boundingRect())
        return path
        
    def contains(self, point):
        # Always return True for any point within the bounding rectangle
        # This makes the entire button area clickable, including transparent parts
        return self.boundingRect().contains(point)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange:
            # 限制移动范围
            x = max(0, min(self.logic_w - self.boundingRect().width(), value.x()))
            y = max(0, min(self.logic_h - self.boundingRect().height(), value.y()))
            
            # 定义吸附阈值（像素）
            SNAP_THRESHOLD = 10
            
            # 获取场景中的其他按钮（排除自己）
            scene = self.scene()
            if not scene:  # 如果按钮还没有添加到场景中，直接返回
                return QPointF(x, y)
                
            other_buttons = [item for item in scene.items() 
                           if isinstance(item, ButtonItem) and item != self]
            
            # 检查与场景边界的吸附
            if x < SNAP_THRESHOLD:
                x = 0
            elif self.logic_w - (x + self.boundingRect().width()) < SNAP_THRESHOLD:
                x = self.logic_w - self.boundingRect().width()
                
            if y < SNAP_THRESHOLD:
                y = 0
            elif self.logic_h - (y + self.boundingRect().height()) < SNAP_THRESHOLD:
                y = self.logic_h - self.boundingRect().height()
            
            # 只检查与其他按钮的上边和左边对齐
            for btn in other_buttons:
                btn_rect = btn.mapRectToScene(btn.boundingRect())
                
                # 检查上边对齐（只与目标按钮的上边对齐）
                if abs(btn_rect.top() - y) < SNAP_THRESHOLD:
                    y = btn_rect.top()
                
                # 检查左边对齐（只与目标按钮的左边对齐）
                if abs(btn_rect.left() - x) < SNAP_THRESHOLD:
                    x = btn_rect.left()
            
            # 确保位置在有效范围内
            x = max(0, min(self.logic_w - self.boundingRect().width(), x))
            y = max(0, min(self.logic_h - self.boundingRect().height(), y))
            
            # 更新cfg中的像素位置
            self.cfg['x'] = int(round(x))
            self.cfg['y'] = int(round(y))
            
            # 如果当前场景中有边框，跟随移动
            if scene and getattr(scene, 'current_frame', None):
                if scene.current_frame.button_item == self:
                    scene.current_frame.update_rect()
            
            return QPointF(x, y)
        return super().itemChange(change, value)

    def contextMenuEvent(self, event):
        menu = QMenu()
        menu.addAction("属性").triggered.connect(self.edit_props)
        menu.addAction("复制").triggered.connect(self.duplicate)
        menu.addAction("删除").triggered.connect(self.delete)
        menu.exec(event.screenPos())

    def edit_props(self):
        # 根据控件类型选择不同的属性对话框
        if self.cfg.get('type') == 'webpage':
            dlg = WebPagePropsDlg(self.cfg, self.logic_w, self.logic_h)
        elif self.cfg.get('type') == 'switch':
            dlg = SwitchPropsDlg(self.cfg, self.logic_w, self.logic_h)
        elif self.cfg.get('type') == 'aircon':
            dlg = AirconPropsDlg(self.cfg, self.logic_w, self.logic_h)
        else:
            dlg = ButtonPropsDlg(self.cfg, self.logic_w, self.logic_h)
        
        if dlg.exec():
            self.cfg.update(dlg.cfg_out)
            self.update_pixmap()
            self.update_geometry()
            # 更新状态显示
            self.update_status_display()
            # 同步虚线框大小
            scene = self.scene()
            if scene and getattr(scene, 'current_frame', None):
                if scene.current_frame.button_item == self:
                    scene.current_frame.update_rect()
            self.scene().update()
            # 标记窗口为已修改
            if hasattr(self.scene(), 'parent') and hasattr(self.scene().parent(), 'setWindowModified'):
                self.scene().parent().setWindowModified(True)

    def duplicate(self):
        # Create a deep copy of the button configuration
        new_cfg = copy.deepcopy(self.cfg)
        
        # Generate a unique ID for the new button
        existing_ids = {btn['id'] for btn in self.scene().page_cfg.get('buttons', [])}
        
        # Extract base name (e.g., 'button' from 'button2')
        base_name = ''.join(filter(str.isalpha, new_cfg['id']))
        if not base_name:
            base_name = 'button'
            
        # Find the next available number
        idx = 1
        while True:
            new_id = f"{base_name}{idx}"
            if new_id not in existing_ids:
                break
            idx += 1
        
        # Update the new button's configuration
        new_cfg['id'] = new_id
        
        # Calculate new position with offset, but keep within bounds
        offset = 20
        new_x = min(self.cfg['x'] + offset, self.logic_w - self.cfg['w'] - 10)
        new_y = min(self.cfg['y'] + offset, self.logic_h - self.cfg['h'] - 10)
        
        # If we hit the right/bottom edge, try to move to the next row/column
        if new_x == self.cfg['x']:
            new_x = max(10, self.cfg['x'] - (self.logic_w - self.cfg['w'] - 10))
            new_y = min(self.cfg['y'] + self.cfg['h'] + offset, self.logic_h - self.cfg['h'] - 10)
        
        new_cfg['x'] = int(new_x)
        new_cfg['y'] = int(new_y)
        
        # Add the new button to the scene
        scene = self.scene()
        scene.page_cfg.setdefault('buttons', []).append(new_cfg)
        
        # Create and select the new button
        new_button = scene.add_button(new_cfg)
        if scene.current_frame:
            scene.removeItem(scene.current_frame)
        scene.current_frame = ButtonFrameItem(new_button)
        scene.addItem(scene.current_frame)

    def delete(self):
        scene = self.scene()
        if scene:
            # 删除虚线边框（如果当前选中的是这个按钮）
            if getattr(scene, 'current_frame', None) and scene.current_frame.button_item == self:
                scene.removeItem(scene.current_frame)
                scene.current_frame = None
            scene.removeItem(self)
            scene.page_cfg['buttons'].remove(self.cfg)


# >>> 修改开始：新增虚线边框类，用于显示按钮虚线框并支持拖拽调整大小和显示数字
class ButtonFrameItem(QGraphicsRectItem):
    HANDLE_SIZE = 8

    def __init__(self, button_item: ButtonItem):
        super().__init__()
        self.button_item = button_item  # 关联的按钮项
        self.setZValue(1000)  # 保证在按钮上层
        self.setFlag(QGraphicsItem.ItemIsSelectable, False)
        self.setFlag(QGraphicsItem.ItemIsMovable, False)
        self.setAcceptHoverEvents(True)
        self.setAcceptedMouseButtons(Qt.LeftButton)

        # 虚线画笔
        pen = QPen(Qt.white)
        pen.setStyle(Qt.DashLine)
        pen.setWidth(2)
        self.setPen(pen)

        # 记录拖拽状态
        self.dragging = False
        self.drag_start_pos = QPointF()
        self.drag_mode = None  # 'right', 'bottom', 'corner'等
        self.orig_rect = QRectF()

        self.update_rect()

    def update_rect(self):
        # 根据button_item的x,y,w,h设置虚线框大小和位置
        x = self.button_item.cfg['x']
        y = self.button_item.cfg['y']
        w = self.button_item.cfg['w']
        h = self.button_item.cfg['h']
        self.setRect(0, 0, w, h)
        self.setPos(x, y)
        self.update()

    def paint(self, painter: QPainter, option, widget=None):
        super().paint(painter, option, widget)
        # 绘制左上角灰底白字数字
        id_str = self.button_item.cfg['id']
        import re
        m = re.search(r'\d+', id_str)
        num_str = m.group() if m else ''
        if num_str:
            font = painter.font()
            font.setBold(True)
            font.setPointSizeF(font.pointSizeF() * 3)
            painter.setFont(font)
            fm = QFontMetrics(font)
            text_w = fm.horizontalAdvance(num_str)  # horizontalAdvance替代width，兼容新版Qt
            text_h = fm.height()

            rect = QRectF(self.rect())
            # 灰色半透明背景
            bg_rect = QRectF(rect.left(), rect.top(), text_w + 8, text_h + 4)
            painter.fillRect(bg_rect, QColor(100, 100, 100, 180))
            # 白字
            painter.setPen(Qt.white)
            painter.drawText(bg_rect.adjusted(4, 2, 0, 0), Qt.AlignLeft | Qt.AlignTop, num_str)

        # 绘制右下角拖拽句柄
        r = self.rect()
        handle_rect = QRectF(r.right() - self.HANDLE_SIZE, r.bottom() - self.HANDLE_SIZE,
                             self.HANDLE_SIZE, self.HANDLE_SIZE)
        painter.fillRect(handle_rect, Qt.white)

    def hoverMoveEvent(self, event: QGraphicsSceneHoverEvent):
        # 判断鼠标是否在右边缘，底边缘，右下角拖拽区域，改变鼠标形状提示
        pos = event.pos()
        r = self.rect()
        margin = 5

        on_right_edge = abs(pos.x() - r.right()) <= margin and r.top() <= pos.y() <= r.bottom()
        on_bottom_edge = abs(pos.y() - r.bottom()) <= margin and r.left() <= pos.x() <= r.right()
        on_corner = on_right_edge and on_bottom_edge

        if on_corner:
            self.setCursor(Qt.SizeFDiagCursor)
            self.drag_mode = 'corner'
        elif on_right_edge:
            self.setCursor(Qt.SizeHorCursor)
            self.drag_mode = 'right'
        elif on_bottom_edge:
            self.setCursor(Qt.SizeVerCursor)
            self.drag_mode = 'bottom'
        else:
            self.setCursor(Qt.ArrowCursor)
            self.drag_mode = None

        super().hoverMoveEvent(event)

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent):
        if self.drag_mode:
            self.dragging = True
            self.drag_start_pos = event.scenePos()
            self.orig_rect = QRectF(self.button_item.cfg['x'], 
                                  self.button_item.cfg['y'],
                                  self.button_item.cfg['w'],
                                  self.button_item.cfg['h'])
            event.accept()
        else:
            # Forward the event to the button item for dragging
            event.ignore()
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent):
        if not self.dragging:
            # Update cursor based on position
            pos = event.pos()
            r = self.rect()
            margin = 5
            
            on_right_edge = abs(pos.x() - r.right()) <= margin and r.top() <= pos.y() <= r.bottom()
            on_bottom_edge = abs(pos.y() - r.bottom()) <= margin and r.left() <= pos.x() <= r.right()
            on_corner = on_right_edge and on_bottom_edge

            if on_corner:
                self.setCursor(Qt.SizeFDiagCursor)
                self.drag_mode = 'corner'
            elif on_right_edge:
                self.setCursor(Qt.SizeHorCursor)
                self.drag_mode = 'right'
            elif on_bottom_edge:
                self.setCursor(Qt.SizeVerCursor)
                self.drag_mode = 'bottom'
            return

        # 计算移动距离
        delta = event.scenePos() - self.drag_start_pos
        
        # 保存原始位置，确保位置不会改变
        original_pos = QPointF(self.orig_rect.x(), self.orig_rect.y())
        new_rect = QRectF(self.orig_rect)
        
        # 定义吸附阈值（像素）
        SNAP_THRESHOLD = 10
        
        # 获取场景中的其他按钮（排除当前按钮）
        scene = self.scene()
        other_buttons = [item for item in scene.items() 
                       if isinstance(item, ButtonItem) and item != self.button_item]
        
        # 根据拖拽模式调整大小
        if self.drag_mode == 'right':
            new_w = max(10, self.orig_rect.width() + delta.x())
            # 确保调整后不会超出右边界
            max_w = self.button_item.logic_w - original_pos.x()
            new_rect.setWidth(min(new_w, max_w))
            
            # 检查与其他按钮的右边缘对齐（大小吸附）
            for btn in other_buttons:
                btn_rect = btn.mapRectToScene(btn.boundingRect())
                # 只检查大小对齐，不检查位置
                if abs(btn_rect.width() - new_rect.width()) < SNAP_THRESHOLD:
                    new_rect.setWidth(btn_rect.width())
                    break
                    
        elif self.drag_mode == 'bottom':
            new_h = max(10, self.orig_rect.height() + delta.y())
            # 确保调整后不会超出下边界
            max_h = self.button_item.logic_h - original_pos.y()
            new_rect.setHeight(min(new_h, max_h))
            
            # 检查与其他按钮的底边缘对齐（大小吸附）
            for btn in other_buttons:
                btn_rect = btn.mapRectToScene(btn.boundingRect())
                # 只检查大小对齐，不检查位置
                if abs(btn_rect.height() - new_rect.height()) < SNAP_THRESHOLD:
                    new_rect.setHeight(btn_rect.height())
                    break
                    
        elif self.drag_mode == 'corner':
            new_w = max(10, self.orig_rect.width() + delta.x())
            new_h = max(10, self.orig_rect.height() + delta.y())
            # 确保调整后不会超出右边界和下边界
            max_w = self.button_item.logic_w - original_pos.x()
            max_h = self.button_item.logic_h - original_pos.y()
            new_rect.setSize(QSizeF(min(new_w, max_w), min(new_h, max_h)))
            
            # 检查与其他按钮的大小对齐（只吸附大小，不吸附位置）
            for btn in other_buttons:
                btn_rect = btn.mapRectToScene(btn.boundingRect())
                # 检查宽度
                if abs(btn_rect.width() - new_rect.width()) < SNAP_THRESHOLD:
                    new_rect.setWidth(btn_rect.width())
                # 检查高度
                if abs(btn_rect.height() - new_rect.height()) < SNAP_THRESHOLD:
                    new_rect.setHeight(btn_rect.height())
        
        # 确保宽度和高度不小于最小值
        new_rect.setWidth(max(10, new_rect.width()))
        new_rect.setHeight(max(10, new_rect.height()))
        
        # 保持原始位置不变
        new_rect.moveTopLeft(original_pos)

        # 更新按钮大小和位置
        self.button_item.cfg['w'] = int(new_rect.width())
        self.button_item.cfg['h'] = int(new_rect.height())
        self.button_item.cfg['x'] = int(original_pos.x())
        self.button_item.cfg['y'] = int(original_pos.y())
        self.button_item.update_geometry()
        
        # 更新框架位置和大小
        self.setRect(0, 0, new_rect.width(), new_rect.height())
        self.setPos(original_pos)
        self.update()

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent):
        if self.dragging:
            self.dragging = False
            self.drag_mode = None
            event.accept()
        else:
            # Let the button handle the release event
            event.ignore()
            super().mouseReleaseEvent(event)


# <<< 修改结束


class Scene(QGraphicsScene):
    def __init__(self, page_cfg, logic_w, logic_h):
        super().__init__(0, 0, logic_w, logic_h)
        self.page_cfg = page_cfg
        self.logic_w = logic_w
        self.logic_h = logic_h

        # 背景相关初始化
        self.bg_video = None
        self.audio_out = None
        self.video_item = None
        self.bg_image = None
        
        # 设置背景
        self.setup_background()
        self.load_bg()

        self.current_frame = None  # 当前选中按钮的虚线框
        self.load_buttons()
        
    def setup_background(self):
        """初始化背景相关的组件"""
        bg = self.page_cfg.get('bg', '')
        if not bg:
            return
            
        bg_path = full_path(bg)
        if not os.path.isfile(bg_path):
            return
            
        # 检查文件类型
        if bg_path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
            # 图片背景
            self.bg_image = QGraphicsPixmapItem()
            self.bg_image.setZValue(-1)  # 确保背景在最底层
            self.addItem(self.bg_image)
        else:
            # 视频背景
            self.bg_video = QMediaPlayer()
            self.audio_out = QAudioOutput()
            self.bg_video.setAudioOutput(self.audio_out)
            self.audio_out.setMuted(True)
            if hasattr(self.bg_video, 'setLoops'):
                self.bg_video.setLoops(QMediaPlayer.Infinite)
            elif hasattr(self.bg_video, 'setLoopCount'):
                self.bg_video.setLoopCount(QMediaPlayer.Infinite)
                
            self.video_item = QGraphicsVideoItem()
            self.video_item.setSize(QSizeF(self.logic_w, self.logic_h))
            self.addItem(self.video_item)
            self.bg_video.setVideoOutput(self.video_item)

    def load_bg(self):
        """加载背景（图片或视频）"""
        bg = self.page_cfg.get('bg', '')
        if not bg:
            return
            
        bg_path = full_path(bg)
        if not os.path.isfile(bg_path):
            return
            
        # 处理图片背景
        if self.bg_image is not None:
            pixmap = QPixmap(bg_path)
            if not pixmap.isNull():
                # 缩放图片以完全填满整个场景，不保持宽高比
                scaled_pixmap = pixmap.scaled(
                    self.logic_w,
                    self.logic_h,
                    Qt.AspectRatioMode.IgnoreAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                
                # 直接填充整个场景
                x = 0
                y = 0
                
                self.bg_image.setPixmap(scaled_pixmap)
                self.bg_image.setPos(x, y)
        # 处理视频背景
        elif self.bg_video is not None and self.video_item is not None:
            self.bg_video.setSource(QUrl.fromLocalFile(bg_path))
            self.video_item.setSize(QSizeF(self.logic_w, self.logic_h))
            self.video_item.setPos(0, 0)
            self.bg_video.play()
            self.video_item.setVisible(True)

    def load_buttons(self):
        # Sort buttons by their numeric ID (e.g., button1, button2, button10)
        def get_button_number(btn):
            # Extract numeric part from button ID (e.g., 1 from 'button1')
            import re
            match = re.search(r'\d+', btn['id'])
            return int(match.group()) if match else 0
            
        # Sort buttons by their numeric ID
        buttons = sorted(self.page_cfg.get('buttons', []), key=get_button_number)
        
        # Add buttons in sorted order
        for btn_cfg in buttons:
            self.add_button(btn_cfg)

    def add_button(self, cfg):
        item = ButtonItem(cfg, self.logic_w, self.logic_h)
        self.addItem(item)
        item.setFlag(QGraphicsItem.ItemIsSelectable, True)
        item.setAcceptedMouseButtons(Qt.LeftButton)

        # 绑定点击事件，显示对应的虚线框
        def mouse_press_event(event, item=item):
            self.on_button_clicked(item, event)
            # 让按钮本身也处理默认逻辑（拖动等）
            super(ButtonItem, item).mousePressEvent(event)

        item.mousePressEvent = mouse_press_event
        return item

    def on_button_clicked(self, button_item, event):
        # 移除之前边框
        if self.current_frame:
            self.removeItem(self.current_frame)
            self.current_frame = None
        # 添加新边框
        self.current_frame = ButtonFrameItem(button_item)
        self.addItem(self.current_frame)
        self.current_frame.setSelected(True)


class View(QGraphicsView):
    def __init__(self, logic_w, logic_h, parent=None):
        super().__init__(parent)
        self.logic_w = logic_w
        self.logic_h = logic_h
        self.setRenderHint(QPainter.Antialiasing)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setBackgroundBrush(Qt.black)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setScene(Scene({"bg": "", "buttons": []}, logic_w, logic_h))
        self.setFocusPolicy(Qt.StrongFocus)  # 允许接收键盘事件
        
        # 初始化移动相关变量
        self.move_timer = QTimer(self)
        self.move_timer.setSingleShot(True)  # 单次触发，用于延迟启动连续移动
        self.move_timer.timeout.connect(self.start_continuous_move)
        
        self.continuous_move_timer = QTimer(self)
        self.continuous_move_timer.timeout.connect(self.move_selected_button)
        
        self.move_direction = None
        self.key_press_time = 0  # 记录按键按下的时间
        
    def start_continuous_move(self):
        """开始连续移动"""
        if not self.continuous_move_timer.isActive():
            self.continuous_move_timer.start(30)  # 30ms更新一次
    
    def keyPressEvent(self, event):
        """处理键盘按下事件"""
        key = event.key()
        
        # 如果按下了方向键
        if key in (Qt.Key_Left, Qt.Key_Right, Qt.Key_Up, Qt.Key_Down):
            event.accept()
            current_time = QDateTime.currentMSecsSinceEpoch()
            
            # 如果是新按键或方向改变
            if self.move_direction != key:
                self.move_direction = key
                self.key_press_time = current_time
                # 立即移动一次
                self.move_selected_button()
                # 启动延迟定时器
                self.move_timer.start(500)  # 500ms后开始连续移动
            # 如果正在连续移动中，但按键被重复触发
            elif not self.continuous_move_timer.isActive():
                self.move_selected_button()
        else:
            super().keyPressEvent(event)
    
    def keyReleaseEvent(self, event):
        """处理键盘释放事件，停止移动"""
        key = event.key()
        if key in (Qt.Key_Left, Qt.Key_Right, Qt.Key_Up, Qt.Key_Down):
            if key == self.move_direction:
                self.move_timer.stop()
                self.continuous_move_timer.stop()
                self.move_direction = None
            event.accept()
        else:
            super().keyReleaseEvent(event)
    
    def move_selected_button(self):
        """移动选中的按钮"""
        if not self.move_direction:
            return
            
        # 固定移动步长1像素
        dx, dy = 0, 0
        if self.move_direction == Qt.Key_Left:
            dx = -1
        elif self.move_direction == Qt.Key_Right:
            dx = 1
        elif self.move_direction == Qt.Key_Up:
            dy = -1
        elif self.move_direction == Qt.Key_Down:
            dy = 1
        
        # 获取场景和当前选中的按钮
        scene = self.scene()
        if not scene or not hasattr(scene, 'current_frame') or not scene.current_frame:
            return
            
        button_item = scene.current_frame.button_item
        if not button_item:
            return
        
        # 临时禁用磁性对齐
        button_item.setFlag(QGraphicsItem.ItemSendsGeometryChanges, False)
        
        try:
            # 计算新位置
            new_x = max(0, min(button_item.pos().x() + dx, 
                             button_item.logic_w - button_item.boundingRect().width()))
            new_y = max(0, min(button_item.pos().y() + dy,
                             button_item.logic_h - button_item.boundingRect().height()))
            
            # 更新按钮位置
            button_item.setPos(new_x, new_y)
            # 更新按钮配置
            button_item.cfg['x'] = int(round(new_x))
            button_item.cfg['y'] = int(round(new_y))
            # 更新选择框
            scene.current_frame.update_rect()
        finally:
            # 恢复磁性对齐
            button_item.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)

    def resizeEvent(self, event):
        view_size = self.viewport().size()
        scale_x = view_size.width() / self.logic_w
        scale_y = view_size.height() / self.logic_h
        self.resetTransform()
        self.scale(scale_x, scale_y)  # 这样拉伸到全屏，比例不保留
        self.setSceneRect(QRectF(0, 0, self.logic_w, self.logic_h))
        self.centerOn(self.logic_w / 2, self.logic_h / 2)
        super().resizeEvent(event)

    def set_page(self, page_cfg, logic_w, logic_h):
        old_scene = self.scene()
        if old_scene:
            # 安全地停止视频（如果存在）
            if hasattr(old_scene, 'bg_video') and old_scene.bg_video is not None:
                old_scene.bg_video.stop()
            old_scene.deleteLater()
            
        self.logic_w = logic_w
        self.logic_h = logic_h
        self.setScene(Scene(page_cfg, logic_w, logic_h))
        self.resizeEvent(QResizeEvent(self.viewport().size(), self.viewport().size()))





class PageManagerDlg(QDialog):
    def __init__(self, cfg):
        super().__init__()
        self.cfg = cfg
        self.setWindowTitle("页面管理")
        lay = QVBoxLayout(self)

        self.list = QListWidget()
        self.refresh()
        lay.addWidget(self.list)

        res_lay = QFormLayout()
        self.w_spin = QSpinBox()
        self.w_spin.setRange(640, 7680)
        self.w_spin.setValue(self.cfg['resolution']['width'])
        self.h_spin = QSpinBox()
        self.h_spin.setRange(480, 4320)
        self.h_spin.setValue(self.cfg['resolution']['height'])
        res_lay.addRow("逻辑宽", self.w_spin)
        res_lay.addRow("逻辑高", self.h_spin)
        lay.addLayout(res_lay)

        btn_lay = QHBoxLayout()
        add_btn = QPushButton("添加页面")
        add_btn.clicked.connect(self.add_page)
        del_btn = QPushButton("删除页面")
        del_btn.clicked.connect(self.remove_page)
        bg_btn = QPushButton("背景")
        bg_btn.clicked.connect(self.set_bg)
        btn_lay.addWidget(add_btn)
        btn_lay.addWidget(del_btn)
        btn_lay.addWidget(bg_btn)
        lay.addLayout(btn_lay)

        # 添加按钮框
        self.bb = QDialogButtonBox(
            QDialogButtonBox.Apply | 
            QDialogButtonBox.Ok | 
            QDialogButtonBox.Cancel
        )
        self.bb.button(QDialogButtonBox.Apply).setText("应用")
        self.bb.button(QDialogButtonBox.Ok).setText("确定")
        self.bb.button(QDialogButtonBox.Cancel).setText("取消")
        
        # 连接信号
        self.bb.accepted.connect(self.accept)
        self.bb.rejected.connect(self.reject)
        self.bb.clicked.connect(self.on_button_clicked)
        
        # 添加到布局
        lay.addWidget(self.bb)
        
        # 保存原始配置，用于取消时恢复
        self.original_cfg = copy.deepcopy(cfg)

    def refresh(self):
        """Refresh the page list display"""
        self.list.clear()
        for page in sorted(self.cfg['pages'], key=lambda x: x['page']):
            bg = page.get('bg', '')
            if bg:
                # 只显示文件名，不显示路径
                bg_name = os.path.basename(bg)
                # 如果文件在data目录下，只显示文件名
                if bg.startswith('data/'):
                    bg_name = os.path.basename(bg[5:])
                self.list.addItem(f"页面 {page['page']}: {bg_name}")
            else:
                self.list.addItem(f"页面 {page['page']}: 无背景")

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange:
            self.cfg['x'] = value.x()
            self.cfg['y'] = value.y()
        elif change == QGraphicsItem.ItemScenePositionHasChanged:
            self.cfg['x'] = self.scenePos().x()
            self.cfg['y'] = self.scenePos().y()
        return super().itemChange(change, value)

    def add_page(self):
        """Add a new page to the configuration"""
        pages = self.cfg['pages']
        new_id = max([p['page'] for p in pages], default=0) + 1
        new_page = {"page": new_id, "bg": "", "buttons": []}
        pages.append(new_page)
        
        # Refresh the page list in the dialog
        self.refresh()
        
        # Select the new page in the dialog's list
        for i, page in enumerate(sorted(self.cfg['pages'], key=lambda x: x['page'])):
            if page['page'] == new_id:
                self.list.setCurrentRow(i)
                break
                
        # Update the main editor's page list if we have a parent
        parent = self.parent()
        if hasattr(parent, 'refresh_page_list'):
            parent.refresh_page_list()
            
            # Switch to the new page
            for i, page in enumerate(parent.cfg['pages']):
                if page['page'] == new_id:
                    parent.page_list.setCurrentRow(i)
                    break

    def mousePressEvent(self, event):
        """Handle mouse press events for the dialog"""
        super().mousePressEvent(event)

    def remove_page(self):
        """删除当前选中的页面并更新主编辑器"""
        idx = self.list.currentRow()
        if 0 <= idx < len(self.cfg['pages']):
            if len(self.cfg['pages']) <= 1:
                QMessageBox.warning(self, "提示", "至少需要保留一个页面")
                return
                
            # 保存当前页面ID，用于后续选择
            current_page_id = self.cfg['pages'][idx]['page']
            
            # 删除页面
            del self.cfg['pages'][idx]
            
            # 刷新对话框的页面列表
            self.refresh()
            
            # 更新主编辑器的页面列表
            parent = self.parent()
            if hasattr(parent, 'refresh_page_list'):
                parent.refresh_page_list()
                
                # 选择前一个页面（如果删除的是第一页则选择第一页）
                new_idx = max(0, idx - 1)
                if parent.page_list.count() > 0:
                    parent.page_list.setCurrentRow(new_idx)
                    
                    # 确保主界面切换到正确的页面
                    if 0 <= new_idx < len(self.cfg['pages']):
                        page_id = self.cfg['pages'][new_idx]['page']
                        for i, page in enumerate(parent.cfg['pages']):
                            if page['page'] == page_id:
                                parent.switch_page(i)
                                break

    def set_bg(self):
        idx = self.list.currentRow()
        if idx < 0:
            return
            
        # 获取当前背景路径，转换为绝对路径作为初始目录
        current_bg = self.cfg['pages'][idx].get('bg', '')
        start_dir = os.path.dirname(full_path(current_bg)) if current_bg else DATA_DIR
        
        # 如果起始目录不存在，使用默认目录
        if not os.path.isdir(start_dir):
            start_dir = os.getcwd()
            
        # 支持的文件类型
        file_filter = "媒体文件 (*.mp4 *.avi *.mov *.mkv *.mpg *.mpeg *.wmv *.flv *.png *.jpg *.jpeg *.bmp *.gif);;\
                      视频文件 (*.mp4 *.avi *.mov *.mkv *.mpg *.mpeg *.wmv *.flv);;\
                      图片文件 (*.png *.jpg *.jpeg *.bmp *.gif);;\
                      所有文件 (*.*)"
                      
        path, _ = QFileDialog.getOpenFileName(
            self, 
            "选择背景文件", 
            start_dir, 
            file_filter
        )
        
        if path:
            # 计算相对于项目根目录的路径
            rel_path = os.path.relpath(path, os.getcwd())
            # 如果路径以data/开头，去掉data/前缀
            if rel_path.startswith('data/'):
                rel_path = rel_path[5:]  # 去掉'data/'前缀
            
            # 保存相对路径
            self.cfg['pages'][idx]['bg'] = rel_path

            # 更新列表显示
            self.refresh()
            self.list.setCurrentRow(idx)

    def on_button_clicked(self, button):
        """处理按钮点击事件"""
        if button == self.bb.button(QDialogButtonBox.Apply):
            self.apply_changes()
    
    def apply_changes(self):
        """应用所有更改到主窗口"""
        # 更新分辨率设置
        self.cfg['resolution']['width'] = self.w_spin.value()
        self.cfg['resolution']['height'] = self.h_spin.value()
        
        # 保存配置
        save_cfg(self.cfg)
        
        # 通知主窗口更新
        main_window = None
        parent = self.parent()
        
        # 找到主窗口实例
        while parent is not None:
            if hasattr(parent, 'refresh_page_list'):
                main_window = parent
                break
            parent = parent.parent()
        
        if main_window:
            # 重新加载配置以确保数据一致性
            main_window.cfg = load_cfg()
            # 刷新主窗口
            main_window.refresh_page_list()
            
            # 尝试切换到当前选中的页面
            idx = self.list.currentRow()
            if 0 <= idx < len(self.cfg['pages']):
                page_id = self.cfg['pages'][idx]['page']
                for i, page in enumerate(main_window.cfg['pages']):
                    if page['page'] == page_id:
                        main_window.page_list.setCurrentRow(i)
                        # 强制触发页面切换
                        main_window.switch_page(i)
                        break
    
    def accept(self):
        """点击确定时应用更改并关闭"""
        self.apply_changes()
        # 确保主窗口已经完成更新
        QApplication.processEvents()
        super().accept()
        
    def reject(self):
        """点击取消时恢复原始配置"""
        # 恢复原始配置
        parent = self.parent()
        if hasattr(parent, 'refresh_page_list'):
            parent.cfg = copy.deepcopy(self.original_cfg)
            save_cfg(parent.cfg)
            parent.refresh_page_list()
        super().reject()


class Editor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.cfg = load_cfg()
        self.setWindowTitle("Touch Panel Configurator")

        tb = self.addToolBar("工具")
        # 添加控件子菜单
        add_widget_menu = QMenu("添加控件", self)
        add_widget_menu.addAction("添加按钮", self.add_button)
        add_widget_menu.addAction("添加网页", self.add_webpage)
        add_widget_menu.addAction("添加开关", self.add_switch)
        add_widget_menu.addAction("添加空调面板", self.add_aircon)
        # 在PySide6中，需要通过QAction来添加菜单到工具栏
        add_widget_action = QAction("添加控件", self)
        add_widget_action.setMenu(add_widget_menu)
        tb.addAction(add_widget_action)
        tb.addAction("页面管理", self.page_mgr)
        tb.addAction("网络设置", self.network_settings)
        tb.addAction("转发", self.forward_settings)
        # 创建指令菜单
        cmd_menu = QMenu("指令", self)
        cmd_menu.addAction("指令表", self.udp_commands)
        cmd_menu.addAction("指令组", self.udp_groups)
        cmd_menu.addAction("设备", self.device_management)
        # 在PySide6中，需要通过QAction来添加菜单到工具栏
        cmd_menu_action = QAction("指令", self)
        cmd_menu_action.setMenu(cmd_menu)
        tb.addAction(cmd_menu_action)
        tb.addAction("定时", self.schedule_settings)
        tb.addAction("上传到服务器", self.upload)
        tb.addAction("保存 (Ctrl+S)", self.save)
        QShortcut(QKeySequence.Save, self).activated.connect(self.save)

        self.page_list = QListWidget()
        self.page_list.currentRowChanged.connect(self.switch_page)
        self.page_list.setStyleSheet("""
            QListWidget { background:#222; color:#eee; border:none; outline:0; }
            QListWidget::item:selected { background:#0a84ff; }
        """)
        dock = QDockWidget("页面")
        dock.setWidget(self.page_list)
        dock.setFeatures(QDockWidget.NoDockWidgetFeatures)
        self.addDockWidget(Qt.LeftDockWidgetArea, dock)

        self.view = View(self.cfg['resolution']['width'], self.cfg['resolution']['height'])
        self.setCentralWidget(self.view)

        # 初始化当前页面行号
        self.last_current_row = -1

        self.refresh_page_list()
        # 加载第一个页面的配置
        if self.cfg['pages']:
            self.switch_page(0)
        self.resize(1200, 800)
        self.show()

    class PageListItemWidget(QWidget):
        def __init__(self, page_data, parent=None):
            super().__init__(parent)
            self.page_data = page_data
            self.setup_ui()
            
        def setup_ui(self):
            layout = QHBoxLayout()
            layout.setContentsMargins(5, 2, 5, 2)
            
            # 页面标签
            bg = self.page_data.get('bg', '')
            self.label = QLabel(f"页面 {self.page_data['page']} - {os.path.basename(bg) if bg else '无背景'}")
            self.label.setStyleSheet("color: #eee;")
            layout.addWidget(self.label, 1)
            
            # 下拉按钮
            self.dropdown_btn = QPushButton("▼")
            self.dropdown_btn.setFixedSize(24, 24)
            self.dropdown_btn.setStyleSheet("""
                QPushButton {
                    background: #444;
                    color: #eee;
                    border: 1px solid #666;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background: #555;
                }
            """)
            layout.addWidget(self.dropdown_btn)
            
            self.setLayout(layout)
    
    def show_buttons_menu(self, page_data, pos):
        """显示页面中的按钮列表菜单"""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #333;
                color: #eee;
                border: 1px solid #555;
                padding: 5px;
            }
            QMenu::item {
                padding: 5px 20px 5px 10px;
            }
            QMenu::item:selected {
                background-color: #0a84ff;
            }
        """)
        
        buttons = page_data.get('buttons', [])
        if not buttons:
            action = menu.addAction("此页面没有按钮")
            action.setEnabled(False)
        else:
            # 使用自然排序，确保数字按数值大小排序
            def natural_sort_key(btn):
                import re
                # 提取数字部分进行排序
                match = re.search(r'\d+', btn['id'])
                return int(match.group(0)) if match else 0
                
            for btn in sorted(buttons, key=natural_sort_key):
                btn_text = f"{btn['id']} - ({btn['x']}, {btn['y']}) - {btn['w']}x{btn['h']}"
                action = menu.addAction(btn_text)
                action.setData(btn['id'])
        
        # 在按钮下方显示菜单
        action = menu.exec_(pos)
        if action and action.data():
            # 切换到按钮所在的页面
            for i, p in enumerate(self.cfg['pages']):
                if p['page'] == page_data['page']:
                    # 切换到该页面
                    self.page_list.setCurrentRow(i)
                    # 找到对应的按钮并显示虚线框
                    scene = self.view.scene()
                    for item in scene.items():
                        if isinstance(item, ButtonItem) and item.cfg['id'] == action.data():
                            # 显示该按钮的虚线框
                            scene.on_button_clicked(item, None)
                            # 滚动视图到该按钮
                            self.view.centerOn(item)
                            break
                    break
    
    def refresh_page_list(self):
        self.page_list.clear()
        for page in self.cfg['pages']:
            # 创建自定义的列表项
            item = QListWidgetItem()
            widget = self.PageListItemWidget(page, self.page_list)
            
            # 设置下拉按钮点击事件
            widget.dropdown_btn.clicked.connect(
                lambda checked, p=page, btn=widget.dropdown_btn: 
                self.show_buttons_menu(p, btn.mapToGlobal(btn.rect().bottomLeft()))
            )
            
            # 设置列表项大小
            item.setSizeHint(widget.sizeHint())
            
            # 添加列表项
            self.page_list.addItem(item)
            self.page_list.setItemWidget(item, widget)

    def switch_page(self, row):
        if 0 <= row < len(self.cfg['pages']):
            # 保存当前页面的按钮信息
            # 使用last_current_row变量存储上一个当前页面的行号
            if hasattr(self, 'last_current_row') and 0 <= self.last_current_row < len(self.cfg['pages']):
                scene = self.view.scene()
                if scene:
                    # 同步scene的buttons到cfg
                    btn_list = []
                    for item in scene.items():
                        if isinstance(item, ButtonItem):
                            btn_list.append(item.cfg)
                    self.cfg['pages'][self.last_current_row]['buttons'] = btn_list
            
            # 切换到新页面
            self.view.set_page(self.cfg['pages'][row],
                               self.cfg['resolution']['width'],
                               self.cfg['resolution']['height'])
            # 保存新的当前页面行号
            self.last_current_row = row
            # 切换页面后，自动选择第一个按钮显示虚线框(如果有按钮)
            scene = self.view.scene()
            buttons = [item for item in scene.items() if isinstance(item, ButtonItem)]
            if buttons:
                scene.on_button_clicked(buttons[0], None)
            else:
                if scene.current_frame:
                    scene.removeItem(scene.current_frame)
                    scene.current_frame = None

    def add_button(self):
        row = self.page_list.currentRow()
        if row < 0 or row >= len(self.cfg['pages']):
            QMessageBox.warning(self, "提示", "请先选择一个有效的页面！")
            return
        page = self.cfg['pages'][row]

        # 生成唯一ID和名称
        existing_ids = {btn['id'].split('_')[0] for btn in page.get('buttons', [])}
        idx = 1
        while f"button{idx}" in existing_ids:
            idx += 1
        btn_name = f"按钮{idx}"
        btn_id = f"button{idx}_{btn_name}"  # 使用下划线分隔ID和名称

        cfg = {
            "id": btn_id,  # ID格式: button1_按钮1
            "x": 100,
            "y": 100,
            "w": 160,
            "h": 80,
            "src": "",
            "pressed_src": "",
            "type": "switch",
            "switch_page": 1,
            "commands": []
        }
        page.setdefault('buttons', []).append(cfg)
        self.view.scene().add_button(cfg)
        self.view.scene().update()

    def add_webpage(self):
        row = self.page_list.currentRow()
        if row < 0 or row >= len(self.cfg['pages']):
            QMessageBox.warning(self, "提示", "请先选择一个有效的页面！")
            return
        page = self.cfg['pages'][row]

        # 生成唯一ID和名称
        existing_ids = {btn['id'].split('_')[0] for btn in page.get('buttons', [])}
        idx = 1
        while f"webpage{idx}" in existing_ids:
            idx += 1
        btn_name = f"网页{idx}"
        btn_id = f"webpage{idx}_{btn_name}"  # 使用下划线分隔ID和名称

        cfg = {
            "id": btn_id,  # ID格式: webpage1_网页1
            "x": 100,
            "y": 100,
            "w": 600,
            "h": 400,
            "src": "",
            "pressed_src": "",
            "type": "webpage",
            "url": "",
            "commands": []
        }
        page.setdefault('buttons', []).append(cfg)
        item = self.view.scene().add_button(cfg)
        # 为网页控件添加特殊的右键菜单
        def context_menu_event(event, item=item):
            menu = QMenu()
            menu.addAction("属性").triggered.connect(item.edit_props)
            menu.addAction("复制").triggered.connect(item.duplicate)
            menu.addAction("删除").triggered.connect(item.delete)
            menu.exec(event.screenPos())
        item.contextMenuEvent = context_menu_event
        self.view.scene().update()

    def add_switch(self):
        row = self.page_list.currentRow()
        if row < 0 or row >= len(self.cfg['pages']):
            QMessageBox.warning(self, "提示", "请先选择一个有效的页面！")
            return
        page = self.cfg['pages'][row]

        # 生成唯一ID和名称
        existing_ids = {btn['id'].split('_')[0] for btn in page.get('buttons', [])}
        idx = 1
        while f"switch{idx}" in existing_ids:
            idx += 1
        btn_name = f"开关{idx}"
        btn_id = f"switch{idx}_{btn_name}"  # 使用下划线分隔ID和名称

        cfg = {
            "id": btn_id,  # ID格式: switch1_开关1
            "x": 100,
            "y": 100,
            "w": 100,
            "h": 50,
            "src": "",
            "pressed_src": "",
            "type": "switch",
            "commands": []
        }
        page.setdefault('buttons', []).append(cfg)
        self.view.scene().add_button(cfg)
        self.view.scene().update()

    def add_aircon(self):
        row = self.page_list.currentRow()
        if row < 0 or row >= len(self.cfg['pages']):
            QMessageBox.warning(self, "提示", "请先选择一个有效的页面！")
            return
        page = self.cfg['pages'][row]

        # 生成唯一ID和名称
        existing_ids = {btn['id'].split('_')[0] for btn in page.get('buttons', [])}
        idx = 1
        while f"aircon{idx}" in existing_ids:
            idx += 1
        btn_name = f"空调面板{idx}"
        btn_id = f"aircon{idx}_{btn_name}"  # 使用下划线分隔ID和名称

        cfg = {
            "id": btn_id,  # ID格式: aircon1_空调面板1
            "x": 100,
            "y": 100,
            "w": 300,
            "h": 400,
            "src": "",
            "pressed_src": "",
            "type": "aircon",
            "commands": [],
            # 空调面板特有属性
            "mode": "auto",  # 模式: auto, cool, heat, fan, dry
            "temperature": 26,  # 温度: 16-30
            "fan_speed": "medium",  # 风速: low, medium, high, auto
            "power": "off"  # 电源状态: on, off
        }
        page.setdefault('buttons', []).append(cfg)
        self.view.scene().add_button(cfg)
        self.view.scene().update()



    def page_mgr(self):
        dlg = PageManagerDlg(self.cfg)
        if dlg.exec():
            self.cfg = load_cfg()
            self.refresh_page_list()
            self.switch_page(0)
            


    def network_settings(self):
        # 确保有network配置
        if 'network' not in self.cfg:
            self.cfg['network'] = {
                'udp_listen_port': '5005'
            }
            
        dlg = NetworkSettingsDialog(self.cfg, self)
        if dlg.exec() == QDialog.Accepted:
            network_settings = dlg.get_settings()
            # 更新整个配置，而不仅仅是network部分
            self.cfg = network_settings
            save_cfg(self.cfg)
            QMessageBox.information(self, "提示", "网络设置已保存！")

    def forward_settings(self):
        # 确保有forward配置
        if 'udp_matches' not in self.cfg:
            self.cfg['udp_matches'] = []
            
        dlg = ForwardSettingsDialog(self.cfg, self)
        if dlg.exec() == QDialog.Accepted:
            forward_settings = dlg.get_settings()
            # 更新整个配置
            self.cfg = forward_settings
            save_cfg(self.cfg)
            QMessageBox.information(self, "提示", "转发设置已保存！")

    def udp_commands(self):
        # 确保有udp_commands配置
        if 'udp_commands' not in self.cfg:
            self.cfg['udp_commands'] = []
            
        dlg = UDPCommandsEditor(self.cfg, self)
        if dlg.exec() == QDialog.Accepted:
            save_cfg(self.cfg)
            QMessageBox.information(self, "提示", "UDP指令表已保存！")

    def udp_groups(self):
        # 确保有udp_groups配置
        if 'udp_groups' not in self.cfg:
            self.cfg['udp_groups'] = []
            
        dlg = UDPGroupsEditor(self.cfg, self)
        if dlg.exec() == QDialog.Accepted:
            save_cfg(self.cfg)
            QMessageBox.information(self, "提示", "UDP指令组已保存！")

    def device_management(self):
        # 确保有devices配置
        if 'devices' not in self.cfg:
            self.cfg['devices'] = []
            
        dlg = DeviceManagementDialog(self.cfg, self)
        if dlg.exec() == QDialog.Accepted:
            save_cfg(self.cfg)
            QMessageBox.information(self, "提示", "设备配置已保存！")
    
    def schedule_settings(self):
        # 确保有schedules配置
        if 'schedules' not in self.cfg:
            self.cfg['schedules'] = []
            
        dlg = ScheduleSettingsDialog(self.cfg, self)
        if dlg.exec() == QDialog.Accepted:
            # 保存配置
            save_cfg(self.cfg)
            QMessageBox.information(self, "提示", "定时设置已保存！")

    def status_image_settings(self):
        """显示状态图片设置对话框"""
        dlg = QDialog(self)
        dlg.setWindowTitle("状态图片设置")
        lay = QFormLayout(dlg)
        
        # 开状态图片设置
        status_on_edit = QLineEdit(self.cfg.get('status_on_src', ''))
        status_on_browse = QPushButton("浏览")
        status_on_browse.clicked.connect(lambda: self.browse(status_on_edit))
        status_on_layout = QHBoxLayout()
        status_on_layout.addWidget(status_on_edit)
        status_on_layout.addWidget(status_on_browse)
        lay.addRow("开状态图片:", status_on_layout)
        
        # 关状态图片设置
        status_off_edit = QLineEdit(self.cfg.get('status_off_src', ''))
        status_off_browse = QPushButton("浏览")
        status_off_browse.clicked.connect(lambda: self.browse(status_off_edit))
        status_off_layout = QHBoxLayout()
        status_off_layout.addWidget(status_off_edit)
        status_off_layout.addWidget(status_off_browse)
        lay.addRow("关状态图片:", status_off_layout)
        
        # 状态图片位置和大小设置
        status_pos_size_layout = QGridLayout()
        status_pos_size_layout.addWidget(QLabel("位置 X:"), 0, 0)
        status_x_spin = QSpinBox()
        status_x_spin.setRange(0, self.cfg['resolution']['width'])
        status_x_spin.setValue(self.cfg.get('status_x', 0))
        status_pos_size_layout.addWidget(status_x_spin, 0, 1)
        
        status_pos_size_layout.addWidget(QLabel("位置 Y:"), 0, 2)
        status_y_spin = QSpinBox()
        status_y_spin.setRange(0, self.cfg['resolution']['height'])
        status_y_spin.setValue(self.cfg.get('status_y', 0))
        status_pos_size_layout.addWidget(status_y_spin, 0, 3)
        
        status_pos_size_layout.addWidget(QLabel("宽度:"), 1, 0)
        status_width_spin = QSpinBox()
        status_width_spin.setRange(1, self.cfg['resolution']['width'])
        status_width_spin.setValue(self.cfg.get('status_width', 32))
        status_pos_size_layout.addWidget(status_width_spin, 1, 1)
        
        status_pos_size_layout.addWidget(QLabel("高度:"), 1, 2)
        status_height_spin = QSpinBox()
        status_height_spin.setRange(1, self.cfg['resolution']['height'])
        status_height_spin.setValue(self.cfg.get('status_height', 32))
        status_pos_size_layout.addWidget(status_height_spin, 1, 3)
        lay.addRow("状态图片位置和大小:", status_pos_size_layout)
        
        # 按钮
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        lay.addWidget(bb)
        
        if dlg.exec() == QDialog.Accepted:
            # 保存状态图片设置
            self.cfg['status_on_src'] = status_on_edit.text()
            self.cfg['status_off_src'] = status_off_edit.text()
            self.cfg['status_x'] = status_x_spin.value()
            self.cfg['status_y'] = status_y_spin.value()
            self.cfg['status_width'] = status_width_spin.value()
            self.cfg['status_height'] = status_height_spin.value()
            save_cfg(self.cfg)
            
            # 更新所有按钮的状态显示
            scene = self.view.scene()
            if scene:
                for item in scene.items():
                    if isinstance(item, ButtonItem):
                        item.update_status_display()
            
            QMessageBox.information(self, "提示", "状态图片设置已保存！")
    
    def browse(self, line_edit):
        """浏览文件并填充到输入框"""
        path, _ = QFileDialog.getOpenFileName(self, "选择图片", DATA_DIR, "图片 (*.png *.jpg *.jpeg *.bmp *.gif)")
        if path:
            filename = os.path.basename(path)
            line_edit.setText(filename)

    def save(self):
        # 保存当前页面的按钮信息
        current_row = self.page_list.currentRow()
        if 0 <= current_row < len(self.cfg['pages']):
            scene = self.view.scene()
            if scene:
                # 同步scene的buttons到cfg
                btn_list = []
                for item in scene.items():
                    if isinstance(item, ButtonItem):
                        btn_list.append(item.cfg)
                self.cfg['pages'][current_row]['buttons'] = btn_list
        
        # 保存配置文件
        save_cfg(self.cfg)
        self.setWindowModified(False)
        QMessageBox.information(self, "提示", "已保存！")

    def upload(self):
        """上传配置到服务器"""
        # 首先保存配置
        self.save()
        
        # 创建服务器设置对话框
        dlg = QDialog(self)
        dlg.setWindowTitle("上传到服务器")
        dlg.resize(400, 200)
        
        lay = QFormLayout(dlg)
        
        # 服务器IP地址
        server_ip_edit = QLineEdit("127.0.0.1")
        lay.addRow("服务器IP地址:", server_ip_edit)
        
        # 服务器端口
        server_port_edit = QLineEdit("5000")
        lay.addRow("服务器端口:", server_port_edit)
        
        # 上传选项
        upload_config_check = QCheckBox("上传配置文件 (config.ini)")
        upload_config_check.setChecked(True)
        lay.addRow(upload_config_check)
        
        upload_data_check = QCheckBox("上传资源文件 (data目录)")
        upload_data_check.setChecked(True)
        lay.addRow(upload_data_check)
        
        # 进度条
        progress_bar = QProgressBar()
        progress_bar.setMinimum(0)
        progress_bar.setMaximum(100)
        progress_bar.setValue(0)
        progress_bar.setVisible(False)
        lay.addRow("上传进度:", progress_bar)
        
        # 状态标签
        status_label = QLabel("")
        status_label.setWordWrap(True)
        lay.addRow("状态:", status_label)
        
        # 按钮
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        lay.addWidget(bb)
        
        # 上传函数
        def do_upload():
            # 禁用按钮
            ok_button = bb.button(QDialogButtonBox.Ok)
            cancel_button = bb.button(QDialogButtonBox.Cancel)
            ok_button.setEnabled(False)
            cancel_button.setEnabled(False)
            
            # 显示进度条
            progress_bar.setVisible(True)
            status_label.setText("准备上传...")
            QApplication.processEvents()
            
            try:
                import requests
                import os
                
                server_ip = server_ip_edit.text().strip()
                server_port = server_port_edit.text().strip()
                server_url = f"http://{server_ip}:{server_port}/upload"
                
                # 准备文件
                files = {}
                opened_files = []
                
                # 上传配置文件
                if upload_config_check.isChecked():
                    # 先保存当前配置
                    save_cfg(self.cfg)
                    # 添加配置文件
                    if os.path.exists(CONFIG):
                        config_file = open(CONFIG, 'rb')
                        files['config_file'] = config_file
                        opened_files.append(config_file)
                
                # 上传资源文件
                if upload_data_check.isChecked():
                    if os.path.exists(DATA_DIR):
                        for root, dirs, filenames in os.walk(DATA_DIR):
                            for filename in filenames:
                                file_path = os.path.join(root, filename)
                                # 计算相对路径
                                rel_path = os.path.relpath(file_path, DATA_DIR)
                                # 使用正确的文件上传格式
                                data_file = open(file_path, 'rb')
                                # 使用不同的键名来避免覆盖
                                files[f'data_file_{rel_path.replace(os.sep, "_")}'] = (rel_path, data_file)
                                opened_files.append(data_file)
                
                # 开始上传
                status_label.setText("正在上传...")
                QApplication.processEvents()
                
                # 发送请求
                response = requests.post(server_url, files=files, timeout=30)
                
                # 关闭文件
                for file in opened_files:
                    file.close()
                
                # 处理响应
                if response.status_code == 200:
                    result = response.json()
                    if result.get('success'):
                        status_label.setText("上传成功！")
                        progress_bar.setValue(100)
                        QApplication.processEvents()
                        QMessageBox.information(self, "成功", "配置已成功上传到服务器！")
                        dlg.accept()
                    else:
                        status_label.setText(f"上传失败: {result.get('message', '未知错误')}")
                else:
                    status_label.setText(f"上传失败: 服务器返回状态码 {response.status_code}")
                    
            except ImportError:
                status_label.setText("上传失败: 缺少requests库，请先安装")
                QMessageBox.warning(self, "错误", "缺少requests库，请先运行: pip install requests")
            except Exception as e:
                status_label.setText(f"上传失败: {str(e)}")
                QMessageBox.warning(self, "错误", f"上传失败: {str(e)}")
            finally:
                # 启用按钮
                ok_button.setEnabled(True)
                cancel_button.setEnabled(True)
        
        # 连接信号
        def on_ok():
            do_upload()
        
        bb.accepted.connect(on_ok)
        bb.rejected.connect(dlg.reject)
        
        # 显示对话框
        dlg.exec()
    
    def closeEvent(self, ev):
        if self.isWindowModified():
            if QMessageBox.question(self, "退出", "有未保存的更改，是否保存？",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) \
                    == QMessageBox.StandardButton.Yes:
                self.save()
        ev.accept()


class ScheduleSettingsDialog(QDialog):
    def __init__(self, cfg, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self.parent = parent
        self.setWindowTitle("定时设置")
        self.resize(800, 500)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["名称", "日期", "星期", "时间", "指令类型", "指令", "启用"])
        self.table.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed)
        self.table.cellChanged.connect(self.on_cell_changed)
        self.table.cellDoubleClicked.connect(self.on_cell_double_clicked)
        # 启用表头排序
        self.table.setSortingEnabled(True)
        layout.addWidget(self.table)
        
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("添加")
        add_btn.clicked.connect(self.add_schedule)
        edit_btn = QPushButton("编辑")
        edit_btn.clicked.connect(self.edit_schedule)
        del_btn = QPushButton("删除")
        del_btn.clicked.connect(self.del_schedule)
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(edit_btn)
        btn_layout.addWidget(del_btn)
        
        layout.addLayout(btn_layout)
        
        self.refresh()
    
    def refresh(self):
        # 禁用排序，避免行索引混乱
        self.table.setSortingEnabled(False)
        
        # 获取指令表和指令组
        udp_commands = self.cfg.get('udp_commands', [])
        udp_groups = self.cfg.get('udp_groups', [])
        
        # 创建指令ID到名称的映射
        cmd_id_to_name = {}
        for cmd in udp_commands:
            cmd_id_to_name[cmd.get('id', '')] = cmd.get('name', cmd.get('id', ''))
        for group in udp_groups:
            cmd_id_to_name[group.get('id', '')] = group.get('name', group.get('id', ''))
        
        self.table.setRowCount(0)
        for schedule in self.cfg.get('schedules', []):
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            # 名称
            name_item = QTableWidgetItem(schedule.get('name', ''))
            self.table.setItem(row, 0, name_item)
            
            # 日期
            date_item = QTableWidgetItem(schedule.get('date', ''))
            self.table.setItem(row, 1, date_item)
            
            # 星期
            week_item = QTableWidgetItem(schedule.get('week', ''))
            self.table.setItem(row, 2, week_item)
            
            # 时间
            time_item = QTableWidgetItem(schedule.get('time', ''))
            self.table.setItem(row, 3, time_item)
            
            # 指令类型
            cmd_type_item = QTableWidgetItem(schedule.get('cmd_type', ''))
            self.table.setItem(row, 4, cmd_type_item)
            
            # 指令
            cmd_id = schedule.get('cmd_id', '')
            # 通过ID从映射中获取指令名称
            cmd_name = cmd_id_to_name.get(cmd_id, cmd_id)
            cmd_item = QTableWidgetItem(cmd_name)
            # 保存指令ID到表格的隐藏数据
            cmd_item.setData(Qt.UserRole, cmd_id)
            self.table.setItem(row, 5, cmd_item)
            
            # 启用
            enable_item = QTableWidgetItem(str(schedule.get('enable', True)))
            enable_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 6, enable_item)
        
        # 调整列宽
        self.table.resizeColumnsToContents()
        
        # 重新启用排序
        self.table.setSortingEnabled(True)
    
    def add_schedule(self):
        # 生成唯一ID和名称
        existing_ids = {sched.get('id', '') for sched in self.cfg.get('schedules', [])}
        
        # 使用time1、time2这样的格式生成ID
        idx = 1
        while True:
            unique_id = f"time{idx}"
            if unique_id not in existing_ids:
                break
            idx += 1
        
        sched_name = f"定时{len(self.cfg.get('schedules', [])) + 1}"
        new_schedule = {
            'id': unique_id,
            'name': sched_name,
            'date': '',
            'week': '',
            'time': '00:00',
            'cmd_type': '指令表',
            'cmd_id': '',
            'cmd_name': '',
            'enable': True
        }
        self.cfg.setdefault('schedules', []).append(new_schedule)
        self.refresh()
    
    def edit_schedule(self):
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "提示", "请先选择要编辑的定时任务")
            return
        
        self.open_edit_dialog(current_row)
    
    def open_edit_dialog(self, row):
        """打开编辑对话框"""
        if row < 0 or row >= self.table.rowCount():
            return
        
        # 获取选中行的定时任务名称
        name_item = self.table.item(row, 0)
        if not name_item:
            return
        
        # 根据名称查找对应的定时任务
        sched_name = name_item.text()
        target_sched = None
        for sched in self.cfg.get('schedules', []):
            if sched.get('name', '') == sched_name:
                target_sched = sched
                break
        
        if not target_sched:
            QMessageBox.warning(self, "错误", "找不到对应的定时任务")
            return
        
        dlg = QDialog(self)
        dlg.setWindowTitle("编辑定时任务")
        dlg.resize(500, 400)
        
        layout = QVBoxLayout(dlg)
        
        # 名称
        name_layout = QHBoxLayout()
        name_label = QLabel("名称:")
        name_edit = QLineEdit(target_sched.get('name', ''))
        name_layout.addWidget(name_label)
        name_layout.addWidget(name_edit)
        layout.addLayout(name_layout)
        
        # 定时类型选择
        schedule_type_group = QGroupBox("定时类型")
        schedule_type_layout = QVBoxLayout()
        
        # 单选按钮组
        schedule_type = QButtonGroup()
        
        # 每天
        daily_radio = QRadioButton("每天")
        schedule_type.addButton(daily_radio)
        
        # 指定日期
        specific_date_radio = QRadioButton("指定")
        schedule_type.addButton(specific_date_radio)
        
        # 每年
        yearly_radio = QRadioButton("每年")
        schedule_type.addButton(yearly_radio)
        
        # 每月
        monthly_radio = QRadioButton("每月")
        schedule_type.addButton(monthly_radio)
        
        # 每周
        weekly_radio = QRadioButton("每周")
        schedule_type.addButton(weekly_radio)
        
        # 添加到布局
        schedule_type_layout.addWidget(daily_radio)
        
        # 指定日期布局
        specific_date_layout = QHBoxLayout()
        specific_date_layout.addWidget(specific_date_radio)
        specific_date_edit = QDateEdit()
        specific_date_edit.setCalendarPopup(True)
        specific_date_edit.setDisplayFormat("yyyy年MM月dd日")
        specific_date_layout.addWidget(specific_date_edit)
        schedule_type_layout.addLayout(specific_date_layout)
        
        # 每年布局
        yearly_layout = QHBoxLayout()
        yearly_layout.addWidget(yearly_radio)
        # 月份下拉菜单
        yearly_month_combo = QComboBox()
        for i in range(1, 13):
            yearly_month_combo.addItem(f"{i:02d}月")
        # 日期下拉菜单
        yearly_day_combo = QComboBox()
        
        # 月份变更时更新日期选项
        def update_yearly_days():
            # 清空日期选项
            yearly_day_combo.clear()
            # 获取当前选中的月份
            month_idx = yearly_month_combo.currentIndex()
            month = month_idx + 1
            # 计算该月的天数
            if month in [1, 3, 5, 7, 8, 10, 12]:
                days = 31
            elif month in [4, 6, 9, 11]:
                days = 30
            else:  # 2月
                days = 29  # 简单处理，按闰年计算
            # 添加日期选项
            for i in range(1, days + 1):
                yearly_day_combo.addItem(f"{i:02d}日")
        
        # 初始化日期选项
        update_yearly_days()
        # 连接月份变更信号
        yearly_month_combo.currentIndexChanged.connect(lambda: update_yearly_days())
        
        yearly_layout.addWidget(yearly_month_combo)
        yearly_layout.addWidget(yearly_day_combo)
        schedule_type_layout.addLayout(yearly_layout)
        
        # 每月布局
        monthly_layout = QHBoxLayout()
        monthly_layout.addWidget(monthly_radio)
        # 日期下拉菜单
        monthly_day_combo = QComboBox()
        # 对于每月选项，允许选择1-28日，因为这些日期在所有月份中都有效
        for i in range(1, 29):
            monthly_day_combo.addItem(f"{i:02d}日")
        # 添加29-31日作为可选，但会在保存时提示
        for i in range(29, 32):
            monthly_day_combo.addItem(f"{i:02d}日")
        monthly_layout.addWidget(monthly_day_combo)
        schedule_type_layout.addLayout(monthly_layout)
        
        # 每周布局
        weekly_layout = QHBoxLayout()
        weekly_layout.addWidget(weekly_radio)
        
        # 星期复选框
        week_checkboxes = []
        week_days = ["一", "二", "三", "四", "五", "六", "日"]
        for day in week_days:
            checkbox = QCheckBox(day)
            week_checkboxes.append(checkbox)
            weekly_layout.addWidget(checkbox)
        
        schedule_type_layout.addLayout(weekly_layout)
        
        schedule_type_group.setLayout(schedule_type_layout)
        layout.addWidget(schedule_type_group)
        
        # 发送时间
        time_layout = QHBoxLayout()
        time_label = QLabel("发送时间:")
        time_edit = QTimeEdit()
        time_edit.setDisplayFormat("HH:mm:ss")
        time_layout.addWidget(time_label)
        time_layout.addWidget(time_edit)
        layout.addLayout(time_layout)
        
        # 指令类型和选择
        cmd_layout = QVBoxLayout()
        
        # 指令类型
        cmd_type_layout = QHBoxLayout()
        cmd_type_label = QLabel("指令类型:")
        cmd_type_combo = QComboBox()
        cmd_type_combo.addItems(["指令表", "组指令"])
        cmd_type_idx = cmd_type_combo.findText(target_sched.get('cmd_type', '指令表'))
        if cmd_type_idx >= 0:
            cmd_type_combo.setCurrentIndex(cmd_type_idx)
        cmd_type_layout.addWidget(cmd_type_label)
        cmd_type_layout.addWidget(cmd_type_combo)
        cmd_layout.addLayout(cmd_type_layout)
        
        # 指令选择
        cmd_select_layout = QHBoxLayout()
        cmd_select_btn = QPushButton("选择指令")
        selected_cmd_label = QLabel(target_sched.get('cmd_name', '未选择指令'))
        selected_cmd_label.setStyleSheet("color: #666")
        cmd_select_layout.addWidget(cmd_select_btn)
        cmd_select_layout.addWidget(selected_cmd_label)
        cmd_layout.addLayout(cmd_select_layout)
        
        layout.addLayout(cmd_layout)
        
        # 启用
        enable_layout = QHBoxLayout()
        enable_check = QCheckBox("启用")
        enable_check.setChecked(target_sched.get('enable', True))
        enable_layout.addWidget(enable_check)
        layout.addLayout(enable_layout)
        
        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        ok_btn = QPushButton("确定")
        cancel_btn = QPushButton("取消")
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
        # 初始化定时类型
        date = target_sched.get('date', '')
        week = target_sched.get('week', '')
        
        if not date and not week:
            # 每天
            daily_radio.setChecked(True)
        elif date and len(date) == 10:  # yyyy-MM-DD
            # 指定日期
            specific_date_radio.setChecked(True)
            try:
                year, month, day = map(int, date.split('-'))
                specific_date_edit.setDate(QDate(year, month, day))
            except:
                pass
        elif date and len(date) == 5:  # MM-DD
            # 每年
            yearly_radio.setChecked(True)
            try:
                month, day = map(int, date.split('-'))
                yearly_month_combo.setCurrentIndex(month - 1)
                yearly_day_combo.setCurrentIndex(day - 1)
            except:
                yearly_month_combo.setCurrentIndex(0)
                yearly_day_combo.setCurrentIndex(0)
        elif date and len(date) == 2:  # DD
            # 每月
            monthly_radio.setChecked(True)
            try:
                day = int(date)
                monthly_day_combo.setCurrentIndex(day - 1)
            except:
                monthly_day_combo.setCurrentIndex(29)  # 默认30日
        elif week:
            # 每周
            weekly_radio.setChecked(True)
            # 解析多个星期几（逗号分隔）
            selected_weeks = week.split(',')
            for i, day in enumerate(week_days):
                if f"周{day}" in selected_weeks:
                    week_checkboxes[i].setChecked(True)
        else:
            # 指定日期
            specific_date_radio.setChecked(True)
            try:
                # 尝试解析日期
                if date:
                    if len(date) == 5:  # MM-DD
                        # 假设是今年
                        today = QDate.currentDate()
                        year = today.year()
                        month, day = map(int, date.split('-'))
                        specific_date_edit.setDate(QDate(year, month, day))
            except:
                pass
        
        # 初始化时间
        time_str = target_sched.get('time', '00:00')
        try:
            if len(time_str) == 5:  # HH:MM
                hour, minute = map(int, time_str.split(':'))
                time_edit.setTime(QTime(hour, minute, 0))
            elif len(time_str) == 8:  # HH:MM:SS
                hour, minute, second = map(int, time_str.split(':'))
                time_edit.setTime(QTime(hour, minute, second))
        except:
            time_edit.setTime(QTime(0, 0, 0))
        
        # 选择指令
        def select_command():
            # 获取配置
            cfg = load_cfg()
            
            # 根据选择的类型获取指令列表
            if cmd_type_combo.currentText() == "指令表":
                commands = cfg.get('udp_commands', [])
            else:
                commands = cfg.get('udp_groups', [])
            
            # 创建带搜索功能的选择对话框
            select_dlg = QDialog(self)
            select_dlg.setWindowTitle("选择指令")
            select_dlg.resize(400, 300)
            
            select_layout = QVBoxLayout(select_dlg)
            
            # 搜索框
            search_layout = QHBoxLayout()
            search_label = QLabel("搜索:")
            search_edit = QLineEdit()
            search_edit.setPlaceholderText("输入指令名称搜索...")
            search_layout.addWidget(search_label)
            search_layout.addWidget(search_edit)
            select_layout.addLayout(search_layout)
            
            # 指令列表
            list_widget = QListWidget()
            select_layout.addWidget(list_widget)
            
            # 按钮
            select_btn_layout = QHBoxLayout()
            select_btn_layout.addStretch()
            select_ok_btn = QPushButton("确定")
            select_cancel_btn = QPushButton("取消")
            select_btn_layout.addWidget(select_ok_btn)
            select_btn_layout.addWidget(select_cancel_btn)
            select_layout.addLayout(select_btn_layout)
            
            # 加载指令列表
            def load_cmd_list():
                list_widget.clear()
                for cmd in commands:
                    item = QListWidgetItem(cmd.get('name', cmd.get('id', '')))
                    item.setData(Qt.UserRole, cmd.get('id', ''))
                    list_widget.addItem(item)
            
            load_cmd_list()
            
            # 搜索功能
            def update_list():
                search_text = search_edit.text().lower()
                
                for i in range(list_widget.count()):
                    item = list_widget.item(i)
                    item_text = item.text().lower()
                    
                    # 按空格分割搜索关键字
                    keywords = [kw.strip() for kw in search_text.split() if kw.strip()]
                    
                    if not keywords:
                        # 搜索框为空，显示所有指令
                        item.setHidden(False)
                    else:
                        # 检查指令是否包含所有关键字（大小写不敏感）
                        if all(keyword in item_text for keyword in keywords):
                            item.setHidden(False)
                        else:
                            item.setHidden(True)
            
            search_edit.textChanged.connect(update_list)
            
            # 连接信号
            selected_item = None
            
            def on_ok():
                nonlocal selected_item
                items = list_widget.selectedItems()
                if items:
                    selected_item = items[0]
                    select_dlg.accept()
                else:
                    QMessageBox.warning(select_dlg, "提示", "请选择一个指令")
            
            select_ok_btn.clicked.connect(on_ok)
            select_cancel_btn.clicked.connect(select_dlg.reject)
            
            # 双击选择
            def on_item_double_clicked(item):
                nonlocal selected_item
                selected_item = item
                select_dlg.accept()
            
            list_widget.itemDoubleClicked.connect(on_item_double_clicked)
            
            # 执行对话框
            if select_dlg.exec() == QDialog.Accepted and selected_item:
                cmd_id = selected_item.data(Qt.UserRole)
                cmd_name = selected_item.text()
                target_sched['cmd_id'] = cmd_id
                # 不再保存cmd_name，通过ID在UI中显示名称
                selected_cmd_label.setText(f"已选择: {cmd_name}")
                selected_cmd_label.setStyleSheet("color: #000")
        
        cmd_select_btn.clicked.connect(select_command)
        
        def on_ok():
            # 验证指令
            if not target_sched.get('cmd_id'):
                QMessageBox.warning(dlg, "错误", "请选择指令")
                return
            
            # 确定定时类型
            date = ""
            week = ""
            
            if daily_radio.isChecked():
                # 每天
                pass
            elif specific_date_radio.isChecked():
                # 指定日期
                selected_date = specific_date_edit.date()
                date = selected_date.toString("yyyy-MM-dd")
            elif yearly_radio.isChecked():
                # 每年
                # 从下拉菜单获取月份和日期
                yearly_month_text = yearly_month_combo.currentText()
                yearly_day_text = yearly_day_combo.currentText()
                # 提取数字部分
                import re
                month_match = re.search(r'(\d{2})月', yearly_month_text)
                day_match = re.search(r'(\d{2})日', yearly_day_text)
                if month_match and day_match:
                    month = month_match.group(1)
                    day = day_match.group(1)
                    date = f"{month}-{day}"
                else:
                    QMessageBox.warning(dlg, "错误", "请选择有效的日期")
                    return
            elif monthly_radio.isChecked():
                # 每月
                # 从下拉菜单获取日期
                monthly_day_text = monthly_day_combo.currentText()
                # 提取数字部分
                import re
                match = re.search(r'(\d{2})日', monthly_day_text)
                if match:
                    day = match.group(1)
                    day_num = int(day)
                    # 对于每月选项，检查日期是否有效
                    if day_num > 28:
                        QMessageBox.information(dlg, "提示", "注意：选择的日期在某些月份中可能不存在，系统会在该月跳过此任务")
                    date = day
                else:
                    QMessageBox.warning(dlg, "错误", "请选择有效的日期")
                    return
            elif weekly_radio.isChecked():
                # 每周
                selected_days = []
                for i, checkbox in enumerate(week_checkboxes):
                    if checkbox.isChecked():
                        selected_days.append(f"周{week_days[i]}")
                if selected_days:
                    # 保存所有选中的星期
                    week = ",".join(selected_days)
                else:
                    QMessageBox.warning(dlg, "错误", "请选择至少一个星期")
                    return
            
            # 获取时间
            time = time_edit.time()
            time_str = time.toString("HH:mm")
            
            # 更新定时任务
            target_sched['name'] = name_edit.text().strip()
            target_sched['date'] = date
            target_sched['week'] = week
            target_sched['time'] = time_str
            target_sched['cmd_type'] = cmd_type_combo.currentText()
            target_sched['enable'] = enable_check.isChecked()
            
            self.refresh()
            dlg.accept()
        
        ok_btn.clicked.connect(on_ok)
        cancel_btn.clicked.connect(dlg.reject)
        
        dlg.exec_()
    
    def del_schedule(self):
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "提示", "请先选择要删除的定时任务")
            return
        
        # 获取选中行的定时任务名称
        name_item = self.table.item(current_row, 0)
        if not name_item:
            return
        
        # 根据名称查找对应的定时任务索引
        sched_name = name_item.text()
        target_index = -1
        for i, sched in enumerate(self.cfg.get('schedules', [])):
            if sched.get('name', '') == sched_name:
                target_index = i
                break
        
        if target_index == -1:
            return
        
        if QMessageBox.question(self, "确认", "确定要删除选中的定时任务吗？") == QMessageBox.Yes:
            del self.cfg['schedules'][target_index]
            self.refresh()
    
    def on_cell_changed(self, row, column):
        if row < 0 or row >= self.table.rowCount():
            return
        
        # 获取选中行的定时任务名称
        name_item = self.table.item(row, 0)
        if not name_item:
            return
        
        # 根据名称查找对应的定时任务
        sched_name = name_item.text()
        target_sched = None
        for sched in self.cfg.get('schedules', []):
            if sched.get('name', '') == sched_name:
                target_sched = sched
                break
        
        if not target_sched:
            return
        
        item = self.table.item(row, column)
        if not item:
            return
        
        value = item.text()
        if column == 0:
            # 修改名称
            target_sched['name'] = value
        elif column == 1:
            target_sched['date'] = value
        elif column == 2:
            target_sched['week'] = value
        elif column == 3:
            target_sched['time'] = value
        elif column == 4:
            target_sched['cmd_type'] = value
        elif column == 5:
            target_sched['cmd_name'] = value
        elif column == 6:
            target_sched['enable'] = value.lower() == 'true'
    
    def on_cell_double_clicked(self, row, column):
        """处理单元格双击事件"""
        # 双击名称列打开编辑对话框
        if column == 0:
            self.open_edit_dialog(row)
    
    def accept(self):
        super().accept()

class UDPCommandsEditor(QDialog):
    def __init__(self, cfg, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self.parent = parent
        self.setWindowTitle("指令表")
        self.resize(800, 500)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["名称", "IP地址", "端口", "指令", "编码", "模式"])
        self.table.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed)
        self.table.cellChanged.connect(self.on_cell_changed)
        self.table.cellDoubleClicked.connect(self.on_cell_double_clicked)
        # 启用表头排序
        self.table.setSortingEnabled(True)
        # 设置表头点击事件
        self.table.horizontalHeader().sectionClicked.connect(self.on_header_clicked)
        layout.addWidget(self.table)
        
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("添加")
        add_btn.clicked.connect(self.add_command)
        edit_btn = QPushButton("编辑")
        edit_btn.clicked.connect(self.edit_command)
        copy_btn = QPushButton("复制")
        copy_btn.clicked.connect(self.copy_command)
        del_btn = QPushButton("删除")
        del_btn.clicked.connect(self.del_command)
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(edit_btn)
        btn_layout.addWidget(copy_btn)
        btn_layout.addWidget(del_btn)
        
        # 导出CSV按钮
        export_btn = QPushButton("导出CSV")
        export_btn.clicked.connect(self.export_to_csv)
        btn_layout.addWidget(export_btn)
        
        # 导入CSV按钮
        import_btn = QPushButton("导入CSV")
        import_btn.clicked.connect(self.import_from_csv)
        btn_layout.addWidget(import_btn)
        
        layout.addLayout(btn_layout)
        
        self.refresh()

    def refresh(self):
        # 禁用排序，避免行索引混乱
        self.table.setSortingEnabled(False)
        
        self.table.setRowCount(0)
        for cmd in self.cfg.get('udp_commands', []):
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            # 名称
            name_item = QTableWidgetItem(cmd.get('name', cmd.get('id', '')))
            self.table.setItem(row, 0, name_item)
            
            # IP地址
            ip_item = QTableWidgetItem(cmd.get('ip', ''))
            self.table.setItem(row, 1, ip_item)
            
            # 端口
            port_item = QTableWidgetItem(str(cmd.get('port', 5000)))
            port_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 2, port_item)
            
            # 指令
            payload_item = QTableWidgetItem(cmd.get('payload', ''))
            self.table.setItem(row, 3, payload_item)
            
            # 编码
            encoding = cmd.get('encoding', '16进制')
            # 确保编码值有效
            valid_encodings = ['16进制', '字符串']
            if encoding not in valid_encodings:
                encoding = '16进制'
            encoding_item = QTableWidgetItem(encoding)
            self.table.setItem(row, 4, encoding_item)
            
            # 模式
            mode = cmd.get('mode', 'UDP')
            # 确保模式值有效
            valid_modes = ['UDP', 'TCP', '网络唤醒', 'PJLINK']
            if mode not in valid_modes:
                mode = 'UDP'
            mode_item = QTableWidgetItem(mode)
            self.table.setItem(row, 5, mode_item)
        
        # 调整列宽
        self.table.resizeColumnsToContents()
        
        # 重新启用排序
        self.table.setSortingEnabled(True)

    def add_command(self):
        # 生成10位字母数字组合的唯一ID
        import random
        import string
        
        def generate_id(length=10):
            characters = string.ascii_letters + string.digits
            return ''.join(random.choice(characters) for _ in range(length))
        
        # 确保ID唯一
        existing_ids = {cmd.get('id', '') for cmd in self.cfg.get('udp_commands', [])}
        unique_id = None
        while not unique_id or unique_id in existing_ids:
            unique_id = generate_id(10)
        
        # 生成友好名称
        cmd_name = f"cmd{len(self.cfg.get('udp_commands', [])) + 1}"
        new_cmd = {'id': unique_id, 'name': cmd_name, 'payload': '', 'encoding': '16进制', 'mode': 'UDP', 'ip': '192.168.0.15', 'port': 5000}
        self.cfg.setdefault('udp_commands', []).append(new_cmd)
        self.refresh()

    def edit_command(self):
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "提示", "请先选择要编辑的指令")
            return
        
        self.open_edit_dialog(current_row)

    def open_edit_dialog(self, row):
        """打开编辑对话框"""
        if row < 0 or row >= self.table.rowCount():
            return
        
        # 获取选中行的指令ID
        name_item = self.table.item(row, 0)
        if not name_item:
            return
        
        # 根据名称查找对应的指令
        cmd_name = name_item.text()
        target_cmd = None
        for cmd in self.cfg.get('udp_commands', []):
            if cmd.get('name', '') == cmd_name:
                target_cmd = cmd
                break
        
        # 如果找不到，尝试根据ID查找
        if not target_cmd:
            for cmd in self.cfg.get('udp_commands', []):
                if cmd.get('id', '') == cmd_name:
                    target_cmd = cmd
                    break
        
        if not target_cmd:
            QMessageBox.warning(self, "错误", "找不到对应的指令")
            return
        
        dlg = QDialog(self)
        dlg.setWindowTitle("编辑UDP指令")
        dlg.resize(400, 250)
        
        layout = QVBoxLayout(dlg)
        
        form = QFormLayout()
        
        # 名称
        name_edit = QLineEdit(target_cmd.get('name', ''))
        form.addRow("名称", name_edit)
        
        # IP地址
        ip_edit = QLineEdit(target_cmd.get('ip', ''))
        form.addRow("IP地址", ip_edit)
        
        # 端口
        port_spin = QSpinBox()
        port_spin.setRange(1, 65535)
        port_spin.setValue(target_cmd.get('port', 5000))
        form.addRow("端口", port_spin)
        
        # 指令
        payload_edit = QLineEdit(target_cmd.get('payload', ''))
        form.addRow("指令", payload_edit)
        
        # 编码
        encoding_combo = QComboBox()
        encoding_combo.addItems(['16进制', '字符串'])
        encoding_idx = encoding_combo.findText(target_cmd.get('encoding', '16进制'))
        if encoding_idx >= 0:
            encoding_combo.setCurrentIndex(encoding_idx)
        form.addRow("编码", encoding_combo)
        
        # 模式
        mode_combo = QComboBox()
        mode_combo.addItems(['UDP', 'TCP', '网络唤醒', 'PJLINK'])
        mode_idx = mode_combo.findText(target_cmd.get('mode', 'UDP'))
        if mode_idx >= 0:
            mode_combo.setCurrentIndex(mode_idx)
        form.addRow("模式", mode_combo)
        
        layout.addLayout(form)
        
        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        ok_btn = QPushButton("确定")
        cancel_btn = QPushButton("取消")
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
        # 处理模式改变事件
        def on_mode_changed():
            mode = mode_combo.currentText()
            if mode == 'PJLINK':
                # 当选择PJLINK模式时，禁用编码字段
                encoding_combo.setEnabled(False)
                # 同时清空编码值，因为PJLINK不使用编码
                encoding_combo.setCurrentText('16进制')
            else:
                # 其他模式启用编码字段
                encoding_combo.setEnabled(True)
        
        # 初始状态
        on_mode_changed()
        
        # 连接信号
        mode_combo.currentTextChanged.connect(on_mode_changed)
        
        def on_ok():
            # 验证输入
            try:
                port = port_spin.value()
            except ValueError:
                QMessageBox.warning(dlg, "错误", "请输入有效的端口号")
                return
            
            # 更新指令
            target_cmd['name'] = name_edit.text().strip()
            target_cmd['ip'] = ip_edit.text().strip()
            target_cmd['port'] = port
            target_cmd['payload'] = payload_edit.text().strip()
            target_cmd['encoding'] = encoding_combo.currentText()
            target_cmd['mode'] = mode_combo.currentText()
            
            self.refresh()
            dlg.accept()
        
        ok_btn.clicked.connect(on_ok)
        cancel_btn.clicked.connect(dlg.reject)
        
        dlg.exec_()

    def copy_command(self):
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "提示", "请先选择要复制的指令")
            return
        
        # 获取选中行的指令名称
        name_item = self.table.item(current_row, 0)
        if not name_item:
            return
        
        # 根据名称查找对应的指令
        cmd_name = name_item.text()
        original_cmd = None
        for cmd in self.cfg.get('udp_commands', []):
            if cmd.get('name', '') == cmd_name:
                original_cmd = cmd
                break
        
        # 如果找不到，尝试根据ID查找
        if not original_cmd:
            for cmd in self.cfg.get('udp_commands', []):
                if cmd.get('id', '') == cmd_name:
                    original_cmd = cmd
                    break
        
        if not original_cmd:
            return
        
        new_cmd = copy.deepcopy(original_cmd)
        
        # 生成新的ID
        cmd_id = f"cmd{len(self.cfg.get('udp_commands', [])) + 1}"
        new_cmd['id'] = cmd_id
        
        self.cfg['udp_commands'].append(new_cmd)
        self.refresh()

    def del_command(self):
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "提示", "请先选择要删除的指令")
            return
        
        # 获取选中行的指令名称
        name_item = self.table.item(current_row, 0)
        if not name_item:
            return
        
        # 根据名称查找对应的指令索引
        cmd_name = name_item.text()
        target_index = -1
        for i, cmd in enumerate(self.cfg.get('udp_commands', [])):
            if cmd.get('name', '') == cmd_name:
                target_index = i
                break
        
        # 如果找不到，尝试根据ID查找
        if target_index == -1:
            for i, cmd in enumerate(self.cfg.get('udp_commands', [])):
                if cmd.get('id', '') == cmd_name:
                    target_index = i
                    break
        
        if target_index == -1:
            return
        
        if QMessageBox.question(self, "确认", "确定要删除选中的指令吗？") == QMessageBox.Yes:
            del self.cfg['udp_commands'][target_index]
            self.refresh()

    def on_cell_changed(self, row, column):
        if row < 0 or row >= self.table.rowCount():
            return
        
        # 获取选中行的指令名称
        name_item = self.table.item(row, 0)
        if not name_item:
            return
        
        # 根据名称查找对应的指令
        cmd_name = name_item.text()
        target_cmd = None
        for cmd in self.cfg.get('udp_commands', []):
            if cmd.get('name', '') == cmd_name:
                target_cmd = cmd
                break
        
        # 如果找不到，尝试根据ID查找
        if not target_cmd:
            for cmd in self.cfg.get('udp_commands', []):
                if cmd.get('id', '') == cmd_name:
                    target_cmd = cmd
                    break
        
        if not target_cmd:
            return
        
        item = self.table.item(row, column)
        if not item:
            return
        
        value = item.text()
        if column == 0:
            # 修改名称
            target_cmd['name'] = value
        elif column == 1:
            target_cmd['ip'] = value
        elif column == 2:
            try:
                target_cmd['port'] = int(value)
            except ValueError:
                QMessageBox.warning(self, "错误", "请输入有效的端口号")
                self.refresh()
        elif column == 3:
            target_cmd['payload'] = value
        elif column == 4:
            # 确保编码值有效
            valid_encodings = ['16进制', '字符串']
            if value not in valid_encodings:
                QMessageBox.warning(self, "错误", "请输入有效的编码值: 16进制, 字符串")
                self.refresh()
            else:
                target_cmd['encoding'] = value
        elif column == 5:
            # 确保模式值有效
            valid_modes = ['UDP', 'TCP', '网络唤醒', 'PJLINK']
            if value not in valid_modes:
                QMessageBox.warning(self, "错误", "请输入有效的模式值: UDP, TCP, 网络唤醒, PJLINK")
                self.refresh()
            else:
                target_cmd['mode'] = value

    def on_cell_double_clicked(self, row, column):
        """处理单元格双击事件"""
        # 双击名称列打开编辑对话框
        if column == 0:
            self.open_edit_dialog(row)
    
    def on_header_clicked(self, logical_index):
        """处理表头点击事件，实现排序"""
        # 排序功能由Qt自动处理，不需要手动实现
        pass

    def accept(self):
        save_cfg(self.cfg)
        super().accept()

    def export_to_csv(self):
        """导出指令表为CSV格式"""
        if not self.cfg.get('udp_commands', []):
            QMessageBox.information(self, "提示", "没有指令可以导出")
            return
        
        # 打开文件保存对话框
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出CSV", "udp_commands.csv", "CSV文件 (*.csv)"
        )
        
        if not file_path:
            return
        
        try:
            import csv
            
            with open(file_path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                # 写入表头
                writer.writerow(['ID', '名称', 'IP地址', '端口', '指令', '编码', '模式'])
                
                # 写入数据
                for cmd in self.cfg.get('udp_commands', []):
                    writer.writerow([
                        cmd.get('id', ''),
                        cmd.get('name', ''),
                        cmd.get('ip', ''),
                        cmd.get('port', ''),
                        cmd.get('payload', ''),
                        cmd.get('encoding', ''),
                        cmd.get('mode', '')
                    ])
            
            QMessageBox.information(self, "成功", f"指令表已导出到：{file_path}")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"导出失败：{str(e)}")

    def import_from_csv(self):
        """从CSV文件导入指令表"""
        # 打开文件选择对话框
        file_path, _ = QFileDialog.getOpenFileName(
            self, "导入CSV", "", "CSV文件 (*.csv)"
        )
        
        if not file_path:
            return
        
        try:
            import csv
            import uuid
            
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.reader(f)
                # 跳过表头
                next(reader)
                
                # 清空现有指令
                self.cfg['udp_commands'] = []
                
                # 导入数据
                for row in reader:
                    if len(row) >= 6:
                        # 使用原有ID或生成新ID
                        cmd_id = row[0].strip()
                        if not cmd_id:
                            # 生成10位字母数字组合的唯一ID
                            import random
                            import string
                            
                            def generate_id(length=10):
                                characters = string.ascii_letters + string.digits
                                return ''.join(random.choice(characters) for _ in range(length))
                            
                            # 确保ID唯一
                            existing_ids = {cmd.get('id', '') for cmd in self.cfg.get('udp_commands', [])}
                            unique_id = None
                            while not unique_id or unique_id in existing_ids:
                                unique_id = generate_id(10)
                            cmd_id = unique_id
                        
                        cmd = {
                            'id': cmd_id,
                            'name': row[1].strip(),
                            'ip': row[2].strip(),
                            'port': int(row[3]) if row[3].strip().isdigit() else 5000,
                            'payload': row[4].strip(),
                            'encoding': row[5].strip() or '16进制',
                            'mode': row[6].strip() or 'UDP'
                        }
                        # 确保编码值有效
                        valid_encodings = ['16进制', '字符串']
                        if cmd['encoding'] not in valid_encodings:
                            cmd['encoding'] = '16进制'
                        # 确保模式值有效
                        valid_modes = ['UDP', 'TCP', '网络唤醒', 'PJLINK']
                        if cmd['mode'] not in valid_modes:
                            cmd['mode'] = 'UDP'
                        self.cfg['udp_commands'].append(cmd)
                    elif len(row) >= 5:
                        # 兼容旧格式（没有ID列）
                        unique_id = str(uuid.uuid4())[:8]
                        cmd = {
                            'id': unique_id,
                            'name': row[0].strip(),
                            'ip': row[1].strip(),
                            'port': int(row[2]) if row[2].strip().isdigit() else 5000,
                            'payload': row[3].strip(),
                            'encoding': row[4].strip() or '16进制',
                            'mode': row[5].strip() or 'UDP' if len(row) > 5 else 'UDP'
                        }
                        # 确保编码值有效
                        valid_encodings = ['16进制', '字符串']
                        if cmd['encoding'] not in valid_encodings:
                            cmd['encoding'] = '16进制'
                        # 确保模式值有效
                        valid_modes = ['UDP', 'TCP', '网络唤醒', 'PJLINK']
                        if cmd['mode'] not in valid_modes:
                            cmd['mode'] = 'UDP'
                        self.cfg['udp_commands'].append(cmd)
            
            self.refresh()
            QMessageBox.information(self, "成功", f"指令表已从：{file_path} 导入")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"导入失败：{str(e)}")


class NetworkSettingsDialog(QDialog):
    def __init__(self, cfg, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self.parent = parent
        self.setWindowTitle("网络设置")
        self.resize(600, 400)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # UDP监听端口设置
        udp_layout = QHBoxLayout()
        udp_label = QLabel("UDP监听端口:")
        self.udp_port_edit = QLineEdit(self.cfg.get('network', {}).get('udp_listen_port', '5005'))
        udp_layout.addWidget(udp_label)
        udp_layout.addWidget(self.udp_port_edit)
        layout.addLayout(udp_layout)
        
        # 服务器端口设置
        server_layout = QHBoxLayout()
        server_label = QLabel("服务器端口:")
        self.server_port_edit = QLineEdit(self.cfg.get('network', {}).get('server_port', '5000'))
        server_layout.addWidget(server_label)
        server_layout.addWidget(self.server_port_edit)
        layout.addLayout(server_layout)
        
        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        ok_btn = QPushButton("确定")
        cancel_btn = QPushButton("取消")
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
        # 连接信号
        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)

    def get_settings(self):
        # 更新网络设置
        network_settings = {
            'udp_listen_port': self.udp_port_edit.text(),
            'server_port': self.server_port_edit.text()
        }
        self.cfg['network'] = network_settings
        return self.cfg

class ForwardSettingsDialog(QDialog):
    def __init__(self, cfg, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self.parent = parent
        self.setWindowTitle("转发设置")
        self.resize(600, 400)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # UDP指令匹配设置
        udp_match_group = QGroupBox("UDP指令匹配设置")
        udp_match_layout = QVBoxLayout()
        
        # 指令匹配表格
        self.match_table = QTableWidget(0, 5)
        self.match_table.setHorizontalHeaderLabels(["监听指令", "模式", "指令类型", "转发指令", "操作"])
        udp_match_layout.addWidget(self.match_table)
        
        # 添加/删除按钮
        match_btn_layout = QHBoxLayout()
        add_match_btn = QPushButton("添加匹配")
        add_match_btn.clicked.connect(self.add_match)
        del_match_btn = QPushButton("删除匹配")
        del_match_btn.clicked.connect(self.del_match)
        match_btn_layout.addWidget(add_match_btn)
        match_btn_layout.addWidget(del_match_btn)
        udp_match_layout.addLayout(match_btn_layout)
        
        udp_match_group.setLayout(udp_match_layout)
        layout.addWidget(udp_match_group)
        
        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        ok_btn = QPushButton("确定")
        cancel_btn = QPushButton("取消")
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
        # 连接信号
        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        
        # 加载现有匹配规则
        self.load_matches()

    def load_matches(self):
        """加载现有的UDP指令匹配规则"""
        matches = self.cfg.get('udp_matches', [])
        self.match_table.setRowCount(0)
        
        # 获取指令表和指令组
        udp_commands = self.cfg.get('udp_commands', [])
        udp_groups = self.cfg.get('udp_groups', [])
        
        # 创建指令ID到名称的映射
        cmd_id_to_name = {}
        for cmd in udp_commands:
            cmd_id_to_name[cmd.get('id', '')] = cmd.get('name', cmd.get('id', ''))
        for group in udp_groups:
            cmd_id_to_name[group.get('id', '')] = group.get('name', group.get('id', ''))
        
        for match in matches:
            row = self.match_table.rowCount()
            self.match_table.insertRow(row)
            
            # 监听指令
            match_cmd_item = QTableWidgetItem(match.get('match_cmd', ''))
            # 保存匹配规则ID到表格的隐藏数据
            match_cmd_item.setData(Qt.UserRole, match.get('id', ''))
            self.match_table.setItem(row, 0, match_cmd_item)
            
            # 模式
            mode_combo = QComboBox()
            mode_combo.addItems(["字符串", "16进制"])
            mode = match.get('mode', '字符串')
            mode_idx = mode_combo.findText(mode)
            if mode_idx >= 0:
                mode_combo.setCurrentIndex(mode_idx)
            self.match_table.setCellWidget(row, 1, mode_combo)
            
            # 指令类型
            cmd_type_combo = QComboBox()
            cmd_type_combo.addItems(["指令表", "组指令"])
            cmd_type = match.get('cmd_type', '指令表')
            cmd_type_idx = cmd_type_combo.findText(cmd_type)
            if cmd_type_idx >= 0:
                cmd_type_combo.setCurrentIndex(cmd_type_idx)
            self.match_table.setCellWidget(row, 2, cmd_type_combo)
            
            # 转发指令
            exec_cmd_id = match.get('exec_cmd_id', '')
            # 通过ID从映射中获取指令名称
            exec_cmd = cmd_id_to_name.get(exec_cmd_id, exec_cmd_id)
            exec_cmd_item = QTableWidgetItem(exec_cmd)
            # 设置指令ID到表格的隐藏数据
            exec_cmd_item.setData(Qt.UserRole, exec_cmd_id)
            self.match_table.setItem(row, 3, exec_cmd_item)
            
            # 操作 - 选择指令
            select_btn = QPushButton("选择")
            select_btn.clicked.connect(lambda checked, r=row: self.select_exec_cmd(r))
            self.match_table.setCellWidget(row, 4, select_btn)

    def add_match(self):
        """添加新的UDP指令匹配规则"""
        row = self.match_table.rowCount()
        self.match_table.insertRow(row)
        
        # 监听指令
        match_cmd_item = QTableWidgetItem('')
        self.match_table.setItem(row, 0, match_cmd_item)
        
        # 模式
        mode_combo = QComboBox()
        mode_combo.addItems(["字符串", "16进制"])
        self.match_table.setCellWidget(row, 1, mode_combo)
        
        # 指令类型
        cmd_type_combo = QComboBox()
        cmd_type_combo.addItems(["指令表", "组指令"])
        self.match_table.setCellWidget(row, 2, cmd_type_combo)
        
        # 转发指令
        exec_cmd_item = QTableWidgetItem('')
        self.match_table.setItem(row, 3, exec_cmd_item)
        
        # 操作 - 选择指令
        select_btn = QPushButton("选择")
        select_btn.clicked.connect(lambda checked, r=row: self.select_exec_cmd(r))
        self.match_table.setCellWidget(row, 4, select_btn)

    def del_match(self):
        """删除选中的UDP指令匹配规则"""
        rows = set(item.row() for item in self.match_table.selectedItems())
        for row in sorted(rows, reverse=True):
            self.match_table.removeRow(row)

    def select_exec_cmd(self, row):
        """选择执行指令"""
        # 获取指令类型
        cmd_type_combo = self.match_table.cellWidget(row, 2)
        if not cmd_type_combo:
            return
        
        cmd_type = cmd_type_combo.currentText()
        
        # 获取配置
        cfg = load_cfg()
        
        # 根据选择的类型获取指令列表
        if cmd_type == "指令表":
            commands = cfg.get('udp_commands', [])
        else:
            commands = cfg.get('udp_groups', [])
        
        if not commands:
            QMessageBox.information(self, "提示", "没有可用的指令")
            return
        
        # 创建带搜索功能的选择对话框
        dlg = QDialog(self)
        dlg.setWindowTitle("选择转发指令")
        dlg.resize(400, 300)
        
        layout = QVBoxLayout(dlg)
        
        # 搜索框
        search_layout = QHBoxLayout()
        search_label = QLabel("搜索:")
        search_edit = QLineEdit()
        search_edit.setPlaceholderText("输入指令名称搜索...")
        search_layout.addWidget(search_label)
        search_layout.addWidget(search_edit)
        layout.addLayout(search_layout)
        
        # 指令列表
        list_widget = QListWidget()
        layout.addWidget(list_widget)
        
        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        ok_btn = QPushButton("确定")
        cancel_btn = QPushButton("取消")
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
        # 加载指令列表
        def load_cmd_list():
            list_widget.clear()
            for cmd in commands:
                item = QListWidgetItem(cmd.get('name', cmd.get('id', '')))
                item.setData(Qt.UserRole, cmd.get('id', ''))
                list_widget.addItem(item)
        
        load_cmd_list()
        
        # 搜索功能
        def update_list():
            search_text = search_edit.text().lower()
            
            for i in range(list_widget.count()):
                item = list_widget.item(i)
                item_text = item.text().lower()
                
                # 按空格分割搜索关键字
                keywords = [kw.strip() for kw in search_text.split() if kw.strip()]
                
                if not keywords:
                    # 搜索框为空，显示所有指令
                    item.setHidden(False)
                else:
                    # 检查指令是否包含所有关键字（大小写不敏感）
                    if all(keyword in item_text for keyword in keywords):
                        item.setHidden(False)
                    else:
                        item.setHidden(True)
        
        search_edit.textChanged.connect(update_list)
        
        # 连接信号
        selected_item = None
        
        def on_ok():
            nonlocal selected_item
            items = list_widget.selectedItems()
            if items:
                selected_item = items[0]
                dlg.accept()
            else:
                QMessageBox.warning(dlg, "提示", "请选择一个指令")
        
        ok_btn.clicked.connect(on_ok)
        cancel_btn.clicked.connect(dlg.reject)
        
        # 双击选择
        def on_item_double_clicked(item):
            nonlocal selected_item
            selected_item = item
            dlg.accept()
        
        list_widget.itemDoubleClicked.connect(on_item_double_clicked)
        
        # 执行对话框
        if dlg.exec() == QDialog.Accepted and selected_item:
            cmd_id = selected_item.data(Qt.UserRole)
            cmd_name = selected_item.text()
            
            # 更新表格
            exec_cmd_item = self.match_table.item(row, 3)
            if exec_cmd_item:
                exec_cmd_item.setText(cmd_name)
            
            # 保存指令ID到表格的隐藏数据
            self.match_table.item(row, 3).setData(Qt.UserRole, cmd_id)

    def get_settings(self):
        # 更新UDP指令匹配规则
        matches = []
        for row in range(self.match_table.rowCount()):
            # 监听指令
            match_cmd_item = self.match_table.item(row, 0)
            match_cmd = match_cmd_item.text().strip() if match_cmd_item else ''
            # 获取匹配规则ID
            match_id = match_cmd_item.data(Qt.UserRole) if (match_cmd_item and match_cmd_item.data(Qt.UserRole) is not None) else ''
            
            # 模式
            mode_combo = self.match_table.cellWidget(row, 1)
            mode = mode_combo.currentText() if mode_combo else '字符串'
            
            # 指令类型
            cmd_type_combo = self.match_table.cellWidget(row, 2)
            cmd_type = cmd_type_combo.currentText() if cmd_type_combo else '指令表'
            
            # 转发指令
            exec_cmd_item = self.match_table.item(row, 3)
            exec_cmd = exec_cmd_item.text().strip() if exec_cmd_item else ''
            exec_cmd_id = exec_cmd_item.data(Qt.UserRole) if (exec_cmd_item and exec_cmd_item.data(Qt.UserRole) is not None) else ''
            
            if match_cmd and exec_cmd_id:
                matches.append({
                    'id': match_id,
                    'match_cmd': match_cmd,
                    'mode': mode,
                    'cmd_type': cmd_type,
                    'exec_cmd_id': exec_cmd_id
                })
        
        self.cfg['udp_matches'] = matches
        return self.cfg


class UDPGroupsEditor(QDialog):
    def __init__(self, cfg, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self.parent = parent
        self.setWindowTitle("指令组")
        self.resize(600, 500)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # 组列表
        self.list = QListWidget()
        layout.addWidget(self.list)
        
        # 组操作按钮
        group_btn_layout = QHBoxLayout()
        add_btn = QPushButton("添加组")
        add_btn.clicked.connect(self.add_group)
        del_btn = QPushButton("删除组")
        del_btn.clicked.connect(self.del_group)
        group_btn_layout.addWidget(add_btn)
        group_btn_layout.addWidget(del_btn)
        layout.addLayout(group_btn_layout)
        
        # 组信息
        form = QFormLayout()
        self.name_edit = QLineEdit()
        self.name_edit.textChanged.connect(self.on_name_changed)
        form.addRow("组名称", self.name_edit)
        layout.addLayout(form)
        

        
        # 组内指令管理
        self.command_table = QTableWidget(0, 4)
        self.command_table.setHorizontalHeaderLabels(["指令名称", "延时(ms)", "操作", ""])
        layout.addWidget(self.command_table)
        
        # 指令操作按钮
        cmd_btn_layout = QHBoxLayout()
        add_cmd_btn = QPushButton("添加指令到组")
        add_cmd_btn.clicked.connect(self.add_command_to_group)
        up_btn = QPushButton("上移")
        up_btn.clicked.connect(self.move_command_up)
        down_btn = QPushButton("下移")
        down_btn.clicked.connect(self.move_command_down)
        del_cmd_btn = QPushButton("从组中删除")
        del_cmd_btn.clicked.connect(self.remove_command_from_group)
        cmd_btn_layout.addWidget(add_cmd_btn)
        cmd_btn_layout.addWidget(up_btn)
        cmd_btn_layout.addWidget(down_btn)
        cmd_btn_layout.addWidget(del_cmd_btn)
        layout.addLayout(cmd_btn_layout)
        
        self.list.currentRowChanged.connect(self.on_selection_changed)
        self.refresh()

    def refresh(self):
        """刷新组列表"""
        self.list.clear()
        for group in self.cfg.get('udp_groups', []):
            self.list.addItem(f"{group.get('name', group.get('id', ''))}")

    def refresh_command_table(self, group):
        """刷新组内指令表格"""
        self.command_table.setRowCount(0)
        if not group:
            return
        
        # 创建指令ID到名称的映射，提高查找效率
        cmd_id_to_name = {}
        for udp_cmd in self.cfg.get('udp_commands', []):
            cmd_id_to_name[udp_cmd.get('id', '')] = udp_cmd.get('name', udp_cmd.get('id', ''))
        
        for i, cmd in enumerate(group.get('commands', [])):
            row = self.command_table.rowCount()
            self.command_table.insertRow(row)
            
            # 指令名称（显示友好名称）
            cmd_id = cmd.get('id', '')
            # 通过ID查找对应的指令名称
            cmd_name = cmd_id_to_name.get(cmd_id, cmd_id)
            cmd_name_item = QTableWidgetItem(cmd_name)
            self.command_table.setItem(row, 0, cmd_name_item)
            
            # 延时
            delay = cmd.get('delay', 0)
            delay_item = QTableWidgetItem(str(delay))
            delay_item.setTextAlignment(Qt.AlignCenter)
            self.command_table.setItem(row, 1, delay_item)
            
            # 操作 - 编辑延时
            edit_btn = QPushButton("编辑")
            edit_btn.clicked.connect(lambda checked, r=row: self.edit_command_delay(r))
            self.command_table.setCellWidget(row, 2, edit_btn)
        
        # 连接单元格修改信号
        self.command_table.itemChanged.connect(self.on_delay_item_changed)
        
        # 调整列宽
        self.command_table.resizeColumnsToContents()

    def add_group(self):
        group_id = f"group{len(self.cfg.get('udp_groups', [])) + 1}"
        new_group = {'id': group_id, 'name': f'组{len(self.cfg.get("udp_groups", [])) + 1}', 'commands': []}
        self.cfg.setdefault('udp_groups', []).append(new_group)
        self.refresh()

    def del_group(self):
        idx = self.list.currentRow()
        if idx < 0:
            return
        del self.cfg['udp_groups'][idx]
        self.refresh()
        self.refresh_command_table(None)

    def on_selection_changed(self, row):
        if row < 0:
            self.name_edit.clear()
            self.refresh_command_table(None)
            return
        groups = self.cfg.get('udp_groups', [])
        if row < len(groups):
            group = groups[row]
            self.name_edit.blockSignals(True)
            self.name_edit.setText(group.get('name', ''))
            self.name_edit.blockSignals(False)
            self.refresh_command_table(group)

    def on_name_changed(self, text):
        idx = self.list.currentRow()
        if idx < 0:
            return
        self.cfg['udp_groups'][idx]['name'] = text
        self.refresh()

    def add_command_to_group(self):
        """添加指令到组"""
        current_row = self.list.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "提示", "请先选择一个组")
            return
        
        group = self.cfg['udp_groups'][current_row]
        
        # 获取所有指令列表（显示名称，保存ID）
        all_commands = []
        cmd_id_map = {}
        for cmd in self.cfg.get('udp_commands', []):
            cmd_name = cmd.get('name', cmd.get('id', ''))
            cmd_id = cmd.get('id', '')
            all_commands.append(cmd_name)
            cmd_id_map[cmd_name] = cmd_id
        
        if not all_commands:
            QMessageBox.information(self, "提示", "没有可用的指令可以添加")
            return
        
        # 创建带搜索功能的选择对话框
        dlg = QDialog(self)
        dlg.setWindowTitle("选择指令")
        dlg.resize(400, 300)
        
        layout = QVBoxLayout(dlg)
        
        # 搜索框
        search_layout = QHBoxLayout()
        search_label = QLabel("搜索:")
        search_edit = QLineEdit()
        search_edit.setPlaceholderText("输入指令名称搜索...")
        search_layout.addWidget(search_label)
        search_layout.addWidget(search_edit)
        layout.addLayout(search_layout)
        
        # 指令列表
        list_widget = QListWidget()
        list_widget.addItems(all_commands)
        layout.addWidget(list_widget)
        
        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        ok_btn = QPushButton("确定")
        cancel_btn = QPushButton("取消")
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
        # 搜索功能
        def update_list():
            search_text = search_edit.text().lower()
            list_widget.clear()
            
            # 按空格分割搜索关键字
            keywords = [kw.strip() for kw in search_text.split() if kw.strip()]
            
            for cmd_name in all_commands:
                cmd_name_lower = cmd_name.lower()
                
                if not keywords:
                    # 搜索框为空，显示所有指令
                    list_widget.addItem(cmd_name)
                else:
                    # 检查指令是否包含所有关键字（大小写不敏感）
                    if all(keyword in cmd_name_lower for keyword in keywords):
                        list_widget.addItem(cmd_name)
        
        search_edit.textChanged.connect(update_list)
        
        # 连接信号
        selected_cmd_name = None
        
        def on_ok():
            nonlocal selected_cmd_name
            selected_items = list_widget.selectedItems()
            if selected_items:
                selected_cmd_name = selected_items[0].text()
                dlg.accept()
            else:
                QMessageBox.warning(dlg, "提示", "请选择一个指令")
        
        ok_btn.clicked.connect(on_ok)
        cancel_btn.clicked.connect(dlg.reject)
        
        # 双击选择
        def on_item_double_clicked(item):
            nonlocal selected_cmd_name
            selected_cmd_name = item.text()
            dlg.accept()
        
        list_widget.itemDoubleClicked.connect(on_item_double_clicked)
        
        # 执行对话框
        if dlg.exec() == QDialog.Accepted and selected_cmd_name:
            # 添加指令到组
            cmd_id = cmd_id_map.get(selected_cmd_name, selected_cmd_name)
            new_cmd = {'id': cmd_id, 'delay': 0}
            group.setdefault('commands', []).append(new_cmd)
            self.refresh_command_table(group)

    def remove_command_from_group(self):
        """从组中删除指令"""
        current_row = self.list.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "提示", "请先选择一个组")
            return
        
        group = self.cfg['udp_groups'][current_row]
        cmd_row = self.command_table.currentRow()
        if cmd_row < 0:
            QMessageBox.warning(self, "提示", "请先选择要删除的指令")
            return
        
        if QMessageBox.question(self, "确认", "确定要从组中删除此指令吗？") == QMessageBox.Yes:
            del group['commands'][cmd_row]
            self.refresh_command_table(group)

    def move_command_up(self):
        """上移指令"""
        current_row = self.list.currentRow()
        if current_row < 0:
            return
        
        group = self.cfg['udp_groups'][current_row]
        cmd_row = self.command_table.currentRow()
        if cmd_row > 0:
            # 交换位置
            group['commands'][cmd_row], group['commands'][cmd_row - 1] = \
                group['commands'][cmd_row - 1], group['commands'][cmd_row]
            self.refresh_command_table(group)

    def move_command_down(self):
        """下移指令"""
        current_row = self.list.currentRow()
        if current_row < 0:
            return
        
        group = self.cfg['udp_groups'][current_row]
        cmd_row = self.command_table.currentRow()
        if 0 <= cmd_row < len(group['commands']) - 1:
            # 交换位置
            group['commands'][cmd_row], group['commands'][cmd_row + 1] = \
                group['commands'][cmd_row + 1], group['commands'][cmd_row]
            self.refresh_command_table(group)

    def edit_command_delay(self, row):
        """编辑指令延时"""
        current_group_row = self.list.currentRow()
        if current_group_row < 0:
            return
        
        group = self.cfg['udp_groups'][current_group_row]
        if row < 0 or row >= len(group['commands']):
            return
        
        cmd = group['commands'][row]
        current_delay = cmd.get('delay', 0)
        
        delay, ok = QInputDialog.getInt(self, "编辑延时", "请输入延时(ms):", current_delay, 0, 10000, 100)
        if ok:
            cmd['delay'] = delay
            self.refresh_command_table(group)
    
    def on_delay_item_changed(self, item):
        """处理延时单元格修改事件"""
        # 只处理延时列（列索引为1）的修改
        if item.column() != 1:
            return
        
        current_group_row = self.list.currentRow()
        if current_group_row < 0:
            return
        
        group = self.cfg['udp_groups'][current_group_row]
        row = item.row()
        if row < 0 or row >= len(group['commands']):
            return
        
        # 尝试将修改后的值转换为整数
        try:
            delay = int(item.text())
            # 确保延时值在合理范围内
            if delay < 0:
                delay = 0
            if delay > 10000:
                delay = 10000
            # 更新配置
            group['commands'][row]['delay'] = delay
        except ValueError:
            # 如果输入不是有效的数字，恢复原来的值
            original_delay = group['commands'][row].get('delay', 0)
            item.setText(str(original_delay))

    def accept(self):
        save_cfg(self.cfg)
        super().accept()


class UploadDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("上传配置")
        self.resize(400, 150)
        self.setModal(True)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # 上传状态标签
        self.status_label = QLabel("准备上传...")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        # 取消按钮
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)
        
        # 启动上传动画
        self.start_upload()
    
    def start_upload(self):
        """开始上传动画"""
        self.progress = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_progress)
        self.timer.start(50)  # 50ms更新一次
    
    def update_progress(self):
        """更新上传进度"""
        self.progress += 1
        self.progress_bar.setValue(self.progress)
        
        # 更新状态文本
        if self.progress < 30:
            self.status_label.setText("正在准备上传...")
        elif self.progress < 70:
            self.status_label.setText("正在上传配置文件...")
        elif self.progress < 90:
            self.status_label.setText("正在验证上传结果...")
        else:
            self.status_label.setText("上传完成...")
        
        # 上传完成
        if self.progress >= 100:
            self.timer.stop()
            QMessageBox.information(self, "成功", "配置上传成功！")
            self.accept()


class DeviceManagementDialog(QDialog):
    def __init__(self, cfg, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self.parent = parent
        self.setWindowTitle("设备管理")
        self.resize(800, 600)
        self.setup_ui()

    def setup_ui(self):
        layout = QHBoxLayout(self)
        
        # 左侧布局：设备列表和操作按钮
        left_layout = QVBoxLayout()
        
        # 设备列表
        self.device_list = QListWidget()
        left_layout.addWidget(self.device_list)
        
        # 设备操作按钮
        device_btn_layout = QVBoxLayout()
        add_btn = QPushButton("添加设备")
        add_btn.clicked.connect(self.add_device)
        copy_btn = QPushButton("复制设备")
        copy_btn.clicked.connect(self.copy_device)
        modify_btn = QPushButton("修改设备")
        modify_btn.clicked.connect(self.modify_device)
        delete_btn = QPushButton("删除设备")
        delete_btn.clicked.connect(self.delete_device)
        device_btn_layout.addWidget(add_btn)
        device_btn_layout.addWidget(copy_btn)
        device_btn_layout.addWidget(modify_btn)
        device_btn_layout.addWidget(delete_btn)
        left_layout.addLayout(device_btn_layout)
        
        # 导入导出按钮
        import_export_layout = QVBoxLayout()
        import_btn = QPushButton("导入设备配置")
        import_btn.clicked.connect(self.import_devices)
        export_btn = QPushButton("导出设备配置")
        export_btn.clicked.connect(self.export_devices)
        import_export_layout.addWidget(import_btn)
        import_export_layout.addWidget(export_btn)
        left_layout.addLayout(import_export_layout)
        
        # 右侧布局：设备信息和指令设置
        right_layout = QVBoxLayout()
        
        # 设备信息
        self.device_info_group = QGroupBox("设备信息")
        self.device_info_layout = QFormLayout()
        
        # 设备名称
        self.name_edit = QLineEdit()
        self.device_info_layout.addRow("设备名称", self.name_edit)
        
        # IP地址
        self.ip_edit = QLineEdit()
        self.device_info_layout.addRow("IP地址", self.ip_edit)
        
        # 端口
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(5000)
        self.device_info_layout.addRow("端口", self.port_spin)
        
        # 模式
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["TCP", "UDP"])
        self.mode_combo.currentTextChanged.connect(self.on_mode_changed)
        self.device_info_layout.addRow("模式", self.mode_combo)
        
        # 指令数量
        self.cmd_count_spin = QSpinBox()
        self.cmd_count_spin.setRange(1, 10)
        self.cmd_count_spin.setValue(1)
        self.cmd_count_spin.valueChanged.connect(self.update_cmd_controls)
        self.device_info_layout.addRow("指令数量", self.cmd_count_spin)
        
        self.device_info_group.setLayout(self.device_info_layout)
        right_layout.addWidget(self.device_info_group)
        
        # 指令设置区域
        self.cmd_settings_group = QGroupBox("指令设置")
        self.cmd_settings_layout = QVBoxLayout()
        
        # 滚动区域
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_area.setWidget(self.scroll_content)
        self.cmd_settings_layout.addWidget(self.scroll_area)
        
        self.cmd_settings_group.setLayout(self.cmd_settings_layout)
        right_layout.addWidget(self.cmd_settings_group, 1)  # 占更多空间
        
        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        ok_btn = QPushButton("确定")
        cancel_btn = QPushButton("取消")
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        right_layout.addLayout(btn_layout)
        
        # 设置左侧宽度
        left_widget = QWidget()
        left_widget.setLayout(left_layout)
        left_widget.setFixedWidth(200)
        
        # 添加到主布局
        layout.addWidget(left_widget)
        layout.addLayout(right_layout, 1)  # 右侧占更多空间
        
        # 连接信号
        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        
        # 设备列表选中事件
        self.device_list.currentRowChanged.connect(self.on_device_selected)
        
        # 初始化设备列表
        self.refresh_device_list()
        
        # 初始化指令控件
        self.update_cmd_controls()

    def refresh_device_list(self):
        """刷新设备列表"""
        self.device_list.clear()
        for device in self.cfg.get('devices', []):
            device_name = device.get('name', '未命名设备')
            self.device_list.addItem(device_name)

    def on_mode_changed(self, mode):
        """模式变化事件处理"""
        # TCP/UDP模式：端口保持不变
        for i in range(self.device_info_layout.rowCount()):
            label = self.device_info_layout.labelForField(self.port_spin)
            if label:
                label.setText("端口")
                break
        # TCP/UDP模式：显示指令数量和指令设置
        self.cmd_count_spin.show()
        label = self.device_info_layout.labelForField(self.cmd_count_spin)
        if label:
            label.show()
        self.cmd_settings_group.show()
        
        # 更新指令控件
        self.update_cmd_controls()

    def update_cmd_controls(self):
        """更新指令控件"""
        # 保存现有指令内容
        existing_commands = []
        if hasattr(self, 'cmd_controls'):
            for controls in self.cmd_controls:
                cmd = {
                    'name': controls['name'].text(),
                    'on': controls.get('on', {}).text() if isinstance(controls.get('on'), QWidget) else '',
                    'off': controls.get('off', {}).text() if isinstance(controls.get('off'), QWidget) else '',
                    'check': controls.get('check', {}).text() if isinstance(controls.get('check'), QWidget) else '',
                    'feedback': controls.get('feedback', {}).text() if isinstance(controls.get('feedback'), QWidget) else '',
                    'encoding': controls.get('encoding', {}).currentText() if isinstance(controls.get('encoding'), QWidget) else '16进制'
                }
                existing_commands.append(cmd)
        
        # 清空现有控件
        for i in reversed(range(self.scroll_layout.count())):
            widget = self.scroll_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        
        # 获取当前模式
        mode = self.mode_combo.currentText()
        
        # 添加新的指令控件
        cmd_count = self.cmd_count_spin.value()
        self.cmd_controls = []
        
        for i in range(cmd_count):
            cmd_group = QGroupBox(f"指令 {i+1}")
            cmd_layout = QFormLayout()
            
            # 指令名称
            name_edit = QLineEdit()
            
            # 开指令
            on_edit = QLineEdit()
            
            # 关指令
            off_edit = QLineEdit()
            
            # 检测指令
            check_edit = QLineEdit()
            
            # 反馈指令
            feedback_edit = QLineEdit()
            
            # 编码方式（16进制/字符串）
            encoding_combo = QComboBox()
            encoding_combo.addItems(["16进制", "字符串"])
            
            # 恢复现有指令内容
            if i < len(existing_commands):
                existing_cmd = existing_commands[i]
                name_edit.setText(existing_cmd.get('name', f"{i+1}路指令"))
                on_edit.setText(existing_cmd.get('on', ''))
                off_edit.setText(existing_cmd.get('off', ''))
                check_edit.setText(existing_cmd.get('check', ''))
                feedback_edit.setText(existing_cmd.get('feedback', ''))
                if 'encoding' in existing_cmd:
                    encoding = existing_cmd.get('encoding', '16进制')
                    encoding_idx = encoding_combo.findText(encoding)
                    if encoding_idx >= 0:
                        encoding_combo.setCurrentIndex(encoding_idx)
            else:
                # 新指令，设置默认值
                name_edit.setText(f"{i+1}路指令")
            
            # 显示所有输入框
            cmd_layout.addRow("指令名称", name_edit)
            cmd_layout.addRow("开指令", on_edit)
            cmd_layout.addRow("关指令", off_edit)
            cmd_layout.addRow("检测指令", check_edit)
            cmd_layout.addRow("反馈指令", feedback_edit)
            cmd_layout.addRow("编码方式", encoding_combo)
            
            cmd_group.setLayout(cmd_layout)
            self.scroll_layout.addWidget(cmd_group)
            
            # 保存控件引用
            cmd_controls = {
                'name': name_edit,
                'on': on_edit,
                'off': off_edit,
                'check': check_edit,
                'feedback': feedback_edit,
                'encoding': encoding_combo
            }
            self.cmd_controls.append(cmd_controls)
        
        # 添加拉伸
        self.scroll_layout.addStretch()

    def add_device(self):
        """添加设备"""
        # 生成设备ID
        import uuid
        device_id = str(uuid.uuid4())[:8]
        
        # 创建新设备
        new_device = {
            'id': device_id,
            'name': f'设备{len(self.cfg.get("devices", [])) + 1}',
            'ip': '192.168.0.1',
            'port': 5000,
            'mode': 'UDP',
            'commands': []
        }
        
        # 添加到配置
        self.cfg.setdefault('devices', []).append(new_device)
        
        # 刷新列表
        self.refresh_device_list()
        
        # 选中新设备
        self.device_list.setCurrentRow(len(self.cfg['devices']) - 1)

    def copy_device(self):
        """复制设备"""
        current_row = self.device_list.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "提示", "请先选择一个设备")
            return
        
        # 获取选中设备
        selected_device = self.cfg['devices'][current_row]
        
        # 复制设备
        import uuid
        device_id = str(uuid.uuid4())[:8]
        
        copied_device = selected_device.copy()
        copied_device['id'] = device_id
        copied_device['name'] = f"{selected_device['name']}_副本"
        copied_device['commands'] = [cmd.copy() for cmd in copied_device.get('commands', [])]
        
        # 添加到配置
        self.cfg['devices'].append(copied_device)
        
        # 刷新列表
        self.refresh_device_list()
        
        # 选中新设备
        self.device_list.setCurrentRow(len(self.cfg['devices']) - 1)

    def modify_device(self):
        """修改设备"""
        current_row = self.device_list.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "提示", "请先选择一个设备")
            return
        
        # 保存设备信息
        self.save_device_info(current_row)
        
        # 刷新列表
        self.refresh_device_list()
        
        QMessageBox.information(self, "提示", "设备信息已更新")

    def delete_device(self):
        """删除设备"""
        current_row = self.device_list.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "提示", "请先选择一个设备")
            return
        
        # 确认删除
        if QMessageBox.question(self, "确认", "确定要删除此设备吗？") == QMessageBox.Yes:
            del self.cfg['devices'][current_row]
            self.refresh_device_list()
            self.clear_device_info()

    def on_device_selected(self, row):
        """设备列表选中事件"""
        if row < 0:
            self.clear_device_info()
            return
        
        # 保存当前设备信息
        if hasattr(self, 'last_selected_row') and 0 <= self.last_selected_row < len(self.cfg.get('devices', [])):
            # 只有当输入框不为空时才保存，避免用空值覆盖原始设备配置
            if self.name_edit.text() or self.ip_edit.text():
                self.save_device_info(self.last_selected_row)
        
        # 加载选中设备信息
        device = self.cfg['devices'][row]
        self.name_edit.setText(device.get('name', ''))
        self.ip_edit.setText(device.get('ip', ''))
        self.port_spin.setValue(device.get('port', 5000))
        
        # 设置模式
        mode = device.get('mode', 'UDP')
        mode_idx = self.mode_combo.findText(mode)
        if mode_idx >= 0:
            self.mode_combo.setCurrentIndex(mode_idx)
        
        # 设置指令数量
        commands = device.get('commands', [])
        self.cmd_count_spin.setValue(len(commands))
        
        # 等待指令控件更新后加载指令信息
        QTimer.singleShot(100, lambda: self.load_device_commands(commands))
        
        # 保存选中行
        self.last_selected_row = row

    def load_device_commands(self, commands):
        """加载设备指令"""
        # 确保指令控件已更新
        if hasattr(self, 'cmd_controls'):
            for i, cmd in enumerate(commands):
                if i < len(self.cmd_controls):
                    controls = self.cmd_controls[i]
                    controls['name'].setText(cmd.get('name', f"{i+1}路指令"))
                    if 'on' in controls:
                        controls['on'].setText(cmd.get('on', ''))
                    if 'off' in controls:
                        controls['off'].setText(cmd.get('off', ''))
                    if 'check' in controls:
                        controls['check'].setText(cmd.get('check', ''))
                    if 'feedback' in controls:
                        controls['feedback'].setText(cmd.get('feedback', ''))
                    if 'encoding' in controls:
                        encoding = cmd.get('encoding', '16进制')
                        encoding_idx = controls['encoding'].findText(encoding)
                        if encoding_idx >= 0:
                            controls['encoding'].setCurrentIndex(encoding_idx)

    def save_device_info(self, row):
        """保存设备信息"""
        if row < 0 or row >= len(self.cfg.get('devices', [])):
            return
        
        # 获取设备
        device = self.cfg['devices'][row]
        
        # 保存基本信息
        device['name'] = self.name_edit.text()
        device['ip'] = self.ip_edit.text()
        device['port'] = self.port_spin.value()
        device['mode'] = self.mode_combo.currentText()
        
        # 保存指令
        commands = []
        if hasattr(self, 'cmd_controls'):
            for i, controls in enumerate(self.cmd_controls):
                cmd = {
                    'name': controls['name'].text(),
                    'on': controls['on'].text(),
                    'off': controls['off'].text(),
                    'check': controls['check'].text(),
                    'feedback': controls['feedback'].text(),
                    'encoding': controls['encoding'].currentText()
                }
                commands.append(cmd)
        device['commands'] = commands

    def clear_device_info(self):
        """清空设备信息"""
        self.name_edit.clear()
        self.ip_edit.clear()
        self.port_spin.setValue(5000)
        self.mode_combo.setCurrentIndex(1)  # UDP
        self.cmd_count_spin.setValue(1)

    def import_devices(self):
        """导入设备配置"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "导入设备配置", "", "CSV文件 (*.csv)"
        )
        
        if not file_path:
            return
        
        try:
            import csv
            devices = []
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    device = {
                        'id': row.get('id', ''),
                        'name': row.get('name', ''),
                        'ip': row.get('ip', ''),
                        'port': int(row.get('port', 5000)),
                        'mode': row.get('mode', 'UDP'),
                        'commands': []
                    }
                    # 解析指令
                    cmd_idx = 1
                    while True:
                        cmd_name = row.get(f'cmd{cmd_idx}_name', '')
                        if not cmd_name:
                            break
                        cmd = {
                            'name': cmd_name,
                            'on': row.get(f'cmd{cmd_idx}_on', ''),
                            'off': row.get(f'cmd{cmd_idx}_off', ''),
                            'check': row.get(f'cmd{cmd_idx}_check', ''),
                            'feedback': row.get(f'cmd{cmd_idx}_feedback', ''),
                            'encoding': row.get(f'cmd{cmd_idx}_encoding', '16进制')
                        }
                        device['commands'].append(cmd)
                        cmd_idx += 1
                    devices.append(device)
            
            # 替换现有设备
            self.cfg['devices'] = devices
            self.refresh_device_list()
            QMessageBox.information(self, "成功", "设备配置导入成功")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"导入失败：{str(e)}")

    def export_devices(self):
        """导出设备配置"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出设备配置", "devices.csv", "CSV文件 (*.csv)"
        )
        
        if not file_path:
            return
        
        try:
            import csv
            devices = self.cfg.get('devices', [])
            
            # 确定最大指令数量
            max_cmds = 0
            for device in devices:
                max_cmds = max(max_cmds, len(device.get('commands', [])))
            
            # 生成表头
            fieldnames = ['id', 'name', 'ip', 'port', 'mode']
            for i in range(1, max_cmds + 1):
                fieldnames.extend([
                    f'cmd{i}_name', f'cmd{i}_on', f'cmd{i}_off', 
                    f'cmd{i}_check', f'cmd{i}_feedback', f'cmd{i}_encoding'
                ])
            
            # 写入CSV文件
            with open(file_path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for device in devices:
                    row = {
                        'id': device.get('id', ''),
                        'name': device.get('name', ''),
                        'ip': device.get('ip', ''),
                        'port': device.get('port', 5000),
                        'mode': device.get('mode', 'UDP')
                    }
                    # 写入指令
                    for i, cmd in enumerate(device.get('commands', []), 1):
                        row[f'cmd{i}_name'] = cmd.get('name', '')
                        row[f'cmd{i}_on'] = cmd.get('on', '')
                        row[f'cmd{i}_off'] = cmd.get('off', '')
                        row[f'cmd{i}_check'] = cmd.get('check', '')
                        row[f'cmd{i}_feedback'] = cmd.get('feedback', '')
                        row[f'cmd{i}_encoding'] = cmd.get('encoding', '16进制')
                    writer.writerow(row)
            
            QMessageBox.information(self, "成功", "设备配置导出成功")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"导出失败：{str(e)}")

    def accept(self):
        """确定按钮事件"""
        # 保存当前设备信息
        if hasattr(self, 'last_selected_row') and 0 <= self.last_selected_row < len(self.cfg.get('devices', [])):
            self.save_device_info(self.last_selected_row)
        
        super().accept()

class NetworkSettingsDialog(QDialog):
    def __init__(self, cfg, parent=None):
        super().__init__(parent)
        self.original_cfg = copy.deepcopy(cfg)
        self.cfg = copy.deepcopy(cfg)
        self.parent = parent
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("网络设置")
        self.resize(500, 500)

        layout = QVBoxLayout(self)

        # UDP监听端口设置
        udp_layout = QHBoxLayout()
        udp_layout.addWidget(QLabel("UDP监听端口:"))
        self.udp_port_edit = QLineEdit(self.cfg.get('network', {}).get('udp_listen_port', '5005'))
        udp_layout.addWidget(self.udp_port_edit)
        layout.addLayout(udp_layout)
        
        # 服务器地址设置
        server_layout = QHBoxLayout()
        server_layout.addWidget(QLabel("服务器地址:"))
        self.server_address_edit = QLineEdit(self.cfg.get('network', {}).get('server_address', '127.0.0.1'))
        server_layout.addWidget(self.server_address_edit)
        layout.addLayout(server_layout)
        
        # 服务器网页端口设置
        web_port_layout = QHBoxLayout()
        web_port_layout.addWidget(QLabel("网页端口（1-1024不可选）:"))
        self.web_port_edit = QLineEdit(self.cfg.get('network', {}).get('web_port', '5000'))
        web_port_layout.addWidget(self.web_port_edit)
        layout.addLayout(web_port_layout)

        # 等待图片设置
        wait_image_group = QGroupBox("等待图片设置")
        wait_image_layout = QVBoxLayout()
        
        # 等待图片路径设置
        wait_image_path_layout = QHBoxLayout()
        wait_image_path_layout.addWidget(QLabel("等待图片:"))
        self.wait_image_edit = QLineEdit(self.cfg.get('wait_image_src', ''))
        wait_image_browse = QPushButton("浏览")
        wait_image_browse.clicked.connect(lambda: self.browse(self.wait_image_edit))
        wait_image_path_layout.addWidget(self.wait_image_edit)
        wait_image_path_layout.addWidget(wait_image_browse)
        wait_image_layout.addLayout(wait_image_path_layout)
        
        # 等待图片位置和大小设置
        wait_image_pos_size_layout = QGridLayout()
        wait_image_pos_size_layout.addWidget(QLabel("位置 X:"), 0, 0)
        self.wait_image_x_spin = QSpinBox()
        self.wait_image_x_spin.setRange(0, self.cfg['resolution']['width'])
        self.wait_image_x_spin.setValue(self.cfg.get('wait_image_x', self.cfg['resolution']['width'] // 2 - 100))
        wait_image_pos_size_layout.addWidget(self.wait_image_x_spin, 0, 1)
        
        wait_image_pos_size_layout.addWidget(QLabel("位置 Y:"), 0, 2)
        self.wait_image_y_spin = QSpinBox()
        self.wait_image_y_spin.setRange(0, self.cfg['resolution']['height'])
        self.wait_image_y_spin.setValue(self.cfg.get('wait_image_y', self.cfg['resolution']['height'] // 2 - 100))
        wait_image_pos_size_layout.addWidget(self.wait_image_y_spin, 0, 3)
        
        wait_image_pos_size_layout.addWidget(QLabel("宽度:"), 1, 0)
        self.wait_image_width_spin = QSpinBox()
        self.wait_image_width_spin.setRange(1, self.cfg['resolution']['width'])
        self.wait_image_width_spin.setValue(self.cfg.get('wait_image_width', 200))
        wait_image_pos_size_layout.addWidget(self.wait_image_width_spin, 1, 1)
        
        wait_image_pos_size_layout.addWidget(QLabel("高度:"), 1, 2)
        self.wait_image_height_spin = QSpinBox()
        self.wait_image_height_spin.setRange(1, self.cfg['resolution']['height'])
        self.wait_image_height_spin.setValue(self.cfg.get('wait_image_height', 200))
        wait_image_pos_size_layout.addWidget(self.wait_image_height_spin, 1, 3)
        wait_image_layout.addLayout(wait_image_pos_size_layout)
        
        wait_image_group.setLayout(wait_image_layout)
        layout.addWidget(wait_image_group)

        # 状态图片设置
        status_image_group = QGroupBox("状态图片设置")
        status_image_layout = QVBoxLayout()
        
        # 开状态图片设置
        status_on_layout = QHBoxLayout()
        status_on_layout.addWidget(QLabel("开状态图:"))
        self.status_on_edit = QLineEdit(self.cfg.get('status_on_src', ''))
        status_on_browse = QPushButton("浏览")
        status_on_browse.clicked.connect(lambda: self.browse(self.status_on_edit))
        status_on_layout.addWidget(self.status_on_edit)
        status_on_layout.addWidget(status_on_browse)
        status_image_layout.addLayout(status_on_layout)
        
        # 关状态图片设置
        status_off_layout = QHBoxLayout()
        status_off_layout.addWidget(QLabel("关状态图:"))
        self.status_off_edit = QLineEdit(self.cfg.get('status_off_src', ''))
        status_off_browse = QPushButton("浏览")
        status_off_browse.clicked.connect(lambda: self.browse(self.status_off_edit))
        status_off_layout.addWidget(self.status_off_edit)
        status_off_layout.addWidget(status_off_browse)
        status_image_layout.addLayout(status_off_layout)
        
        # 状态图片位置和大小设置
        status_pos_size_layout = QGridLayout()
        status_pos_size_layout.addWidget(QLabel("位置 X:"), 0, 0)
        self.status_x_spin = QSpinBox()
        self.status_x_spin.setRange(0, self.cfg['resolution']['width'])
        self.status_x_spin.setValue(self.cfg.get('status_x', 0))
        status_pos_size_layout.addWidget(self.status_x_spin, 0, 1)
        
        status_pos_size_layout.addWidget(QLabel("位置 Y:"), 0, 2)
        self.status_y_spin = QSpinBox()
        self.status_y_spin.setRange(0, self.cfg['resolution']['height'])
        self.status_y_spin.setValue(self.cfg.get('status_y', 0))
        status_pos_size_layout.addWidget(self.status_y_spin, 0, 3)
        
        status_pos_size_layout.addWidget(QLabel("宽度:"), 1, 0)
        self.status_width_spin = QSpinBox()
        self.status_width_spin.setRange(1, self.cfg['resolution']['width'])
        self.status_width_spin.setValue(self.cfg.get('status_width', 32))
        status_pos_size_layout.addWidget(self.status_width_spin, 1, 1)
        
        status_pos_size_layout.addWidget(QLabel("高度:"), 1, 2)
        self.status_height_spin = QSpinBox()
        self.status_height_spin.setRange(1, self.cfg['resolution']['height'])
        self.status_height_spin.setValue(self.cfg.get('status_height', 32))
        status_pos_size_layout.addWidget(self.status_height_spin, 1, 3)
        status_image_layout.addLayout(status_pos_size_layout)
        
        status_image_group.setLayout(status_image_layout)
        layout.addWidget(status_image_group)

        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.ok_btn = QPushButton("确定")
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.ok_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

    def browse(self, line_edit):
        """浏览文件并填充到输入框"""
        path, _ = QFileDialog.getOpenFileName(self, "选择图片", DATA_DIR, "图片 (*.png *.jpg *.jpeg *.bmp *.gif)")
        if path:
            filename = os.path.basename(path)
            line_edit.setText(filename)

    def get_settings(self):
        # 更新配置
        if 'network' not in self.cfg:
            self.cfg['network'] = {}
        
        self.cfg['network']['udp_listen_port'] = self.udp_port_edit.text()
        self.cfg['network']['server_address'] = self.server_address_edit.text()
        self.cfg['network']['web_port'] = self.web_port_edit.text()
        
        # 保存等待图片设置
        self.cfg['wait_image_src'] = self.wait_image_edit.text()
        self.cfg['wait_image_x'] = self.wait_image_x_spin.value()
        self.cfg['wait_image_y'] = self.wait_image_y_spin.value()
        self.cfg['wait_image_width'] = self.wait_image_width_spin.value()
        self.cfg['wait_image_height'] = self.wait_image_height_spin.value()
        
        # 保存状态图片设置
        self.cfg['status_on_src'] = self.status_on_edit.text()
        self.cfg['status_off_src'] = self.status_off_edit.text()
        self.cfg['status_x'] = self.status_x_spin.value()
        self.cfg['status_y'] = self.status_y_spin.value()
        self.cfg['status_width'] = self.status_width_spin.value()
        self.cfg['status_height'] = self.status_height_spin.value()
        
        return self.cfg

    def accept(self):
        # 验证UDP端口号
        try:
            port = int(self.udp_port_edit.text())
            if port < 1 or port > 65535:
                QMessageBox.warning(self, "错误", "UDP端口号必须在1-65535之间！")
                return
        except ValueError:
            QMessageBox.warning(self, "错误", "请输入有效的UDP端口号！")
            return
        
        # 验证服务器网页端口号
        try:
            web_port = int(self.web_port_edit.text())
            if web_port < 1 or web_port > 65535:
                QMessageBox.warning(self, "错误", "服务器网页端口号必须在1-65535之间！")
                return
        except ValueError:
            QMessageBox.warning(self, "错误", "请输入有效的服务器网页端口号！")
            return
        
        # 更新配置
        self.get_settings()
        
        # 保存配置
        save_cfg(self.cfg)
        super().accept()

    def reject(self):
        # 恢复原始配置
        save_cfg(self.original_cfg)
        super().reject()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Editor()
    sys.exit(app.exec())
