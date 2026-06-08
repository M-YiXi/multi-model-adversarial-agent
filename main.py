"""
多模三维对抗思维引擎 - 程序入口
启动TUI终端界面
"""
import sys  # 系统参数
import os  # 文件路径

# 将项目根目录添加到Python路径，确保模块导入正常
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.tui.app import AdversarialTUI  # 导入TUI主应用


def main():
    """
    程序主入口
    启动Textual TUI终端界面
    """
    # 创建TUI应用实例并运行
    app = AdversarialTUI()
    app.run()  # 启动Textual事件循环


if __name__ == "__main__":
    main()  # 执行入口函数
