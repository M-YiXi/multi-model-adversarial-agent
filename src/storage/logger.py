"""
日志记录模块
记录API调用日志、引擎运行日志、错误日志
"""
import os  # 文件操作
import json  # JSON格式化
from datetime import datetime  # 时间戳
from ..config.settings import DATA_DIR  # 数据目录


class Logger:
    """
    应用日志管理器
    记录所有API调用、引擎事件和错误信息
    """

    def __init__(self):
        self._log_dir = os.path.join(DATA_DIR, "logs")  # 日志目录
        os.makedirs(self._log_dir, exist_ok=True)  # 确保目录存在

    def _write_log(self, category: str, data: dict):
        """
        写入一条日志记录
        :param category: 日志类别（api/engine/error）
        :param data: 日志数据
        """
        # 按日期分文件
        date_str = datetime.now().strftime("%Y%m%d")
        log_path = os.path.join(self._log_dir, f"{category}_{date_str}.jsonl")

        data["timestamp"] = datetime.now().isoformat()  # 添加时间戳
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(data, ensure_ascii=False) + "\n")  # JSONL格式

    def log_api_call(self, role: str, model: str, tokens: int,
                     duration: float, success: bool, error: str = ""):
        """
        记录API调用日志
        :param role: 角色（MX0~MX3）
        :param model: 模型名称
        :param tokens: Token消耗
        :param duration: 调用耗时(秒)
        :param success: 是否成功
        :param error: 错误信息
        """
        self._write_log("api", {
            "role": role,
            "model": model,
            "tokens": tokens,
            "duration": round(duration, 2),
            "success": success,
            "error": error,
        })

    def log_engine_event(self, event: str, round_num: int, details: str = ""):
        """
        记录引擎事件日志
        :param event: 事件名称
        :param round_num: 当前轮次
        :param details: 详细信息
        """
        self._write_log("engine", {
            "event": event,
            "round": round_num,
            "details": details,
        })

    def log_error(self, source: str, error_msg: str):
        """
        记录错误日志
        :param source: 错误来源
        :param error_msg: 错误消息
        """
        self._write_log("error", {
            "source": source,
            "error": error_msg,
        })
