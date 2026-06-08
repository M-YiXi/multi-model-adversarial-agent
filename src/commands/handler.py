"""
/ 命令处理系统
支持类似Claude TUI的斜杠命令交互方式
用户输入 / 开头的内容即触发命令处理
"""
from typing import Optional  # 类型注解
from ..core.models import AppState, Project  # 导入状态模型
from ..i18n.translator import t, set_language  # 导入翻译


class CommandHandler:
    """
    命令处理器
    解析和处理所有 / 开头的用户命令
    """

    def __init__(self, state: AppState):
        self.state = state  # 全局应用状态
        # 注册所有命令及其处理函数和帮助文本
        self._commands = {
            "help": (self._cmd_help, "cmd_help"),
            "new": (self._cmd_new, "cmd_new"),
            "open": (self._cmd_open, "cmd_open"),
            "config": (self._cmd_config, "cmd_config"),
            "start": (self._cmd_start, "cmd_start"),
            "stop": (self._cmd_stop, "cmd_stop"),
            "status": (self._cmd_status, "cmd_status"),
            "export": (self._cmd_export, "cmd_export"),
            "lang": (self._cmd_lang, "cmd_lang"),
            "clear": (self._cmd_clear, "cmd_clear"),
            "quit": (self._cmd_quit, "cmd_quit"),
        }

    def process(self, text: str) -> Optional[dict]:
        """
        处理用户输入，判断是否为命令
        :param text: 用户输入文本
        :return: 命令处理结果字典，非命令返回None
        """
        text = text.strip()  # 去除首尾空白
        if not text.startswith("/"):
            return None  # 不是命令，交给普通消息处理

        # 解析命令和参数
        parts = text[1:].split(maxsplit=1)  # 去掉 / 后按空格拆分
        cmd_name = parts[0].lower()  # 命令名（小写）
        args = parts[1] if len(parts) > 1 else ""  # 命令参数

        if cmd_name in self._commands:
            handler, _ = self._commands[cmd_name]  # 获取处理函数
            return handler(args)  # 执行处理函数
        else:
            return {"type": "error",
                    "message": t("cmd_unknown", cmd=cmd_name)}

    def get_help_text(self) -> str:
        """获取所有命令的帮助文本"""  # 生成帮助列表
        lines = [t("cmd_list_title"), "-" * 40]
        for cmd_name, (_, help_key) in self._commands.items():
            lines.append(t(help_key))  # 添加每个命令的帮助
        return "\n".join(lines)

    def _cmd_help(self, args: str) -> dict:
        """处理 /help 命令"""  # 显示所有可用命令
        return {"type": "help", "message": self.get_help_text()}

    def _cmd_new(self, args: str) -> dict:
        """处理 /new 命令 - 创建新项目"""  # 进入新建项目流程
        return {"type": "new_project", "message": t("home_new_project")}

    def _cmd_open(self, args: str) -> dict:
        """处理 /open 命令 - 打开指定项目"""  # 按名称打开项目
        if not args:
            return {"type": "error", "message": "用法: /open <项目名称>"}
        return {"type": "open_project", "name": args}

    def _cmd_config(self, args: str) -> dict:
        """处理 /config 命令 - 打开配置界面"""  # 进入设置页面
        return {"type": "open_config", "message": t("settings_title")}

    def _cmd_start(self, args: str) -> dict:
        """处理 /start 命令 - 启动对抗引擎"""  # 开始对抗流程
        if not self.state.current_project:
            return {"type": "error", "message": t("err_no_active_project")}
        return {"type": "start_engine", "message": t("engine_start")}

    def _cmd_stop(self, args: str) -> dict:
        """处理 /stop 命令 - 停止对抗引擎"""  # 停止当前对抗
        return {"type": "stop_engine", "message": t("engine_stop")}

    def _cmd_status(self, args: str) -> dict:
        """处理 /status 命令 - 查看引擎状态"""  # 显示当前状态
        if not self.state.current_project:
            return {"type": "info", "message": t("err_no_active_project")}
        status = self.state.engine_status.value
        round_num = self.state.current_round
        return {"type": "info",
                "message": f"{t('engine_status')}: {status}\n{t('engine_round', round=round_num)}"}

    def _cmd_export(self, args: str) -> dict:
        """处理 /export 命令 - 导出对话日志"""  # 导出当前项目日志
        if not self.state.current_project:
            return {"type": "error", "message": t("err_no_active_project")}
        return {"type": "export_log", "message": t("chat_export_log")}

    def _cmd_lang(self, args: str) -> dict:
        """
        处理 /lang 命令 - 切换语言
        :param args: "zh" 或 "en"
        """
        if args.lower() in ("zh", "en"):
            set_language(args.lower())  # 切换翻译语言
            self.state.language = args.lower()
            from ..config.settings import settings
            settings.language = args.lower()
            msg = t("lang_switched")
            return {"type": "lang_changed", "message": msg,
                    "lang": args.lower()}
        else:
            return {"type": "error",
                    "message": "用法: /lang zh 或 /lang en"}

    def _cmd_clear(self, args: str) -> dict:
        """处理 /clear 命令 - 清空当前对话"""  # 清空聊天记录
        return {"type": "clear_chat", "message": t("chat_clear")}

    def _cmd_quit(self, args: str) -> dict:
        """处理 /quit 命令 - 退出程序"""  # 安全退出
        return {"type": "quit", "message": t("quit")}
