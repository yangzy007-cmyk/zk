import sys
from PySide6.QtCore import *
from PySide6.QtWidgets import *
import edit

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 创建一个简单的配置
    cfg = {
        'devices': []
    }
    
    try:
        # 尝试创建DeviceManagementDialog
        print("Creating DeviceManagementDialog...")
        dlg = edit.DeviceManagementDialog(cfg)
        print("DeviceManagementDialog created successfully!")
        
        # 显示对话框
        # dlg.exec()
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    
    # app.exec()
