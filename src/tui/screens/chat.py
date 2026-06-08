"""
对抗对话界面 — 核心交互屏幕
左栏：模型状态 + 思考链 | 中：聊天 | 右：引擎状态
数字统一使用暗黄色 #D29922
"""
import asyncio
import time
from textual.screen import Screen
from textual.widgets import (
    Static, Button, Input, RichLog, ListView, ListItem, Label, Checkbox
)
from textual.containers import Horizontal, Vertical, ScrollableContainer
from textual.app import ComposeResult

from ...core.models import (
    AppState, Message, MessageRole, RoleType, EngineStatus
)
from ...core.engine import AdversarialEngine
from ...storage.store import ProjectStore
from ...storage.logger import Logger
from ...commands.handler import CommandHandler
from ...i18n.translator import t

# 暗黄色数字格式
YN = "[rgb(210,153,34)]"  # dark yellow num open
_YN = "[/]"               # close

ROLE_LABELS = [
    ("MX1", "● 主理模型"),
    ("MX2", "▲ 纠错模型"),
    ("MX3", "◆ 发散模型"),
    ("MX0", "■ 总结模型"),
]

ROLE_COLORS = {
    "MX1": "cyan",
    "MX2": "rgb(224,33,138)",
    "MX3": "rgb(145,197,58)",
    "MX0": "rgb(145,207,213)",
}

ROLE_DISPLAY_NAMES = {
    "MX1": "● 主理模型",
    "MX2": "▲ 纠错模型",
    "MX3": "◆ 发散模型",
    "MX0": "■ 总结模型",
}


class ChatScreen(Screen):
    """对抗对话主屏幕"""

    def __init__(self, state, store, cmd_handler, logger):
        super().__init__()
        self.state = state
        self.store = store
        self.cmd_handler = cmd_handler
        self.logger = logger
        self.engine = AdversarialEngine(state)
        self._setup_engine_callbacks()
        # 思考计时器
        self._think_start_time: float = 0.0
        self._think_timer_task = None
        # 自动续行
        self._auto_continue = False
        # 当前正在运行的角色集合
        self._running_roles: set = set()

    def _setup_engine_callbacks(self):
        def on_message(role, content, rn):
            self._display_role_message(role, content, rn)
            self._refresh_model_status()

        def on_status(status, rn):
            self._update_status(status, rn)

        self.engine.set_callbacks(on_message, on_status)

    def compose(self):
        project = self.state.current_project
        pname = project.name if project else "未选择项目"
        yield Static(f"▸ {pname}", classes="panel-title")

        with Horizontal(id="main-container"):
            # ===== 左侧：模型状态 + 思考计时 + 自动续行 =====
            with Vertical(id="left-panel"):
                yield Static("模型状态", classes="panel-title")
                yield Static("", id="model-status-panel")
                yield Static("")
                yield Static("思考计时", classes="section-title")
                yield Static(f"  {YN}0.0{_YN} 秒", id="think-timer")
                yield Static("")
                yield Checkbox(" 自动模式", id="chk-auto-continue")

            # ===== 中间：聊天 =====
            with Vertical(id="center-panel"):
                yield RichLog(id="chat-log", highlight=True, markup=True,
                              max_lines=3000, auto_scroll=True)

            # ===== 右侧：引擎状态 =====
            with Vertical(id="right-panel"):
                with ScrollableContainer():
                    yield Static("引擎状态", classes="section-title")
                    yield Static("  空闲", id="status-text")
                    yield Static(f"  第 {YN}0{_YN} 轮", id="round-text")
                    yield Static("")
                    yield Static("角色状态", classes="section-title")
                    for rid, label in ROLE_LABELS:
                        color = ROLE_COLORS.get(rid, "")
                        yield Static(
                            f" [{color}]{label}[/]  "
                            f"[rgb(139,148,158)]空闲[/]",
                            id=f"role-{rid}-status")
                    yield Static("")
                    if project:
                        yield Static("项目信息", classes="section-title")
                        yield Static(f"  名称: {project.name}")
                        yield Static(f"  目标: {project.core_goal[:38]}..")
                        # 数字用暗黄色
                        yield Static(
                            f"  最大轮次: "
                            f"{YN}{project.max_iterations}{_YN}")
                        yield Static(
                            f"  期望分数: "
                            f"{YN}{project.convergence_threshold}分{_YN}")

        with Horizontal(id="input-area"):
            yield Button("回到主页", variant="default", id="btn-home")
            yield Input(placeholder="输入消息或 / 命令...", id="chat-input")
            yield Button("发送", variant="primary", id="btn-send")
            yield Button("启动", variant="success", id="btn-start")
            yield Button("停止", variant="error", id="btn-stop")
            yield Button("测试", variant="default", id="btn-test")

    def on_mount(self):
        self._refresh_model_status()
        self._load_chat_history()

    # ==========================================
    # 模型状态面板 — 暗黄色数字
    # ==========================================
    def _refresh_model_status(self):
        try:
            panel = self.query_one("#model-status-panel", Static)
        except Exception:
            return
        project = self.state.current_project
        if not project:
            panel.update("  无项目")
            return

        stats = self.engine.get_token_stats()
        lines = []
        role_cfgs = [
            ("MX1", project.mx1_config),
            ("MX2", project.mx2_config),
            ("MX3", project.mx3_config),
            ("MX0", project.mx0_config),
        ]
        role_colors = {
            "MX1": "cyan",
            "MX2": "rgb(224,33,138)",
            "MX3": "rgb(145,197,58)",
            "MX0": "rgb(145,207,213)",
        }
        for rid, cfg in role_cfgs:
            if not cfg:
                continue
            # 使用引擎的精确估算（按角色 context_length 计算）
            pct = self.engine._estimate_usage_pct(project, rid)
            s = stats.get(rid, {})
            rate = s.get("avg_tokens_per_sec", 0)
            color = role_colors.get(rid, "")
            lines.append(
                f"  [{color}][bold]{rid}[/bold][/{color}]\n"
                f"  上下文: {YN}{pct}%{_YN}\n"
                f"  token/s: {YN}{rate}{_YN}"
            )
        panel.update("\n".join(lines) if lines else "  暂无数据")

    # ==========================================
    # 历史 / 聊天颜色
    # ==========================================
    def _load_chat_history(self):
        chat_log = self.query_one("#chat-log", RichLog)
        project = self.state.current_project
        if not project:
            return
        for msg in project.messages[-50:]:
            self._write_to_chat(msg.role, msg.content, msg.role_type)

    def _write_to_chat(self, role, content, role_type=None):
        chat_log = self.query_one("#chat-log", RichLog)
        chat_log.write("─" * 60)
        if role_type == RoleType.MX1:
            chat_log.write("[bold cyan]● 殚虑的宰相*主理模型[/bold cyan]")
            for line in content.split("\n"):
                if line.strip():
                    chat_log.write(f"[cyan]{line}[/cyan]")
        elif role_type == RoleType.MX2:
            chat_log.write("[bold rgb(224,33,138)]▲ 敏疑的御史*纠错模型[/]")
            for line in content.split("\n"):
                if line.strip():
                    chat_log.write(f"[rgb(224,33,138)]{line}[/]")
        elif role_type == RoleType.MX3:
            chat_log.write("[bold rgb(145,197,58)]◆ 谏官发言中*发散模型[/]")
            for line in content.split("\n"):
                if line.strip():
                    chat_log.write(f"[rgb(145,197,58)]{line}[/]")
        elif role_type == RoleType.MX0:
            chat_log.write("[bold rgb(145,207,213)]■ 入内都都知*总结模型[/]")
            for line in content.split("\n"):
                if line.strip():
                    chat_log.write(f"[rgb(145,207,213)]{line}[/]")
        elif role == MessageRole.USER:
            chat_log.write("[bold cyan]▼ 用户[/bold cyan]")
            for line in content.split("\n"):
                if line.strip():
                    chat_log.write(f"[cyan]{line}[/cyan]")
        else:
            chat_log.write("[dim]· 系统[/dim]")
            for line in content.split("\n"):
                if line.strip():
                    chat_log.write(f"[dim]{line}[/dim]")

    def _display_role_message(self, role, content, round_num):
        try:
            self._write_to_chat(MessageRole.ASSISTANT, content, role)
            if self.state.current_project:
                msg = Message(role=MessageRole.ASSISTANT, content=content,
                              role_type=role, round_num=round_num)
                self.state.current_project.messages.append(msg)
                self.store.save_project(self.state.current_project)
        except Exception:
            pass

    # ==========================================
    # 状态更新 — 暗黄色数字
    # ==========================================
    def _update_status(self, status, round_num):
        """状态更新：追踪运行中角色，正确刷新角色状态+全局状态+计时器"""
        try:
            # 处理收敛/最大轮次等特殊状态
            if status in ("converged", "max_rounds"):
                self._stop_think_timer()
                self._running_roles.clear()
                label = "已收敛" if status == "converged" else "已达最大轮次"
                try:
                    self.query_one("#status-text", Static).update(
                        f"  [bold rgb(88,166,255)]{label}[/]")
                except Exception:
                    pass
                # 全部角色设为完成
                for rid, lbl in ROLE_DISPLAY_NAMES.items():
                    color = ROLE_COLORS.get(rid, "")
                    try:
                        w = self.query_one(f"#role-{rid}-status", Static)
                        w.update(f" [{color}]{lbl}[/]  "
                                 f"[bold rgb(88,166,255)]完成[/]")
                    except Exception:
                        pass
                return

            # 处理 MX1:running / MX1:idle 格式
            if ":" in status:
                rid, state = status.split(":", 1)

                # 更新运行中角色集合
                if state == "running":
                    self._running_roles.add(rid)
                elif state == "idle":
                    self._running_roles.discard(rid)

                # 更新该角色标签
                state_colors = {
                    "idle": "[rgb(139,148,158)]空闲[/]",
                    "running": "[bold rgb(63,185,80)]运行中[/]",
                    "paused": "[rgb(210,153,34)]暂停[/]",
                    "finished": "[bold rgb(88,166,255)]完成[/]",
                    "error": "[bold rgb(248,81,73)]错误[/]",
                }
                state_text = state_colors.get(state, state)
                color = ROLE_COLORS.get(rid, "")
                label = ROLE_DISPLAY_NAMES.get(rid, rid)
                try:
                    widget = self.query_one(f"#role-{rid}-status", Static)
                    widget.update(f" [{color}]{label}[/]  {state_text}")
                except Exception:
                    pass

                # 全局状态文字：有角色在运行就显示运行中，否则空闲
                try:
                    if self._running_roles:
                        running_name = ROLE_DISPLAY_NAMES.get(
                            next(iter(self._running_roles)), "")
                        self.query_one("#status-text", Static).update(
                            f"  [bold rgb(63,185,80)]运行中[/]")
                    else:
                        self.query_one("#status-text", Static).update(
                            f"  [rgb(139,148,158)]空闲[/]")
                except Exception:
                    pass

                # 计时器：running → 重置启动，idle → 若无其他角色运行则停止
                if state == "running":
                    self._start_think_timer(rid)
                elif state == "idle" and not self._running_roles:
                    self._stop_think_timer()

                # 轮次
                if round_num > 0:
                    try:
                        self.query_one("#round-text", Static).update(
                            f"  第 {YN}{round_num}{_YN} 轮")
                    except Exception:
                        pass
                    self.state.current_round = round_num

                # 刷新模型状态面板（含上下文百分比）
                self._refresh_model_status()
            else:
                # 兼容旧格式
                try:
                    self.query_one("#status-text", Static).update("  运行中")
                    self.query_one("#round-text", Static).update(
                        f"  第 {YN}{round_num}{_YN} 轮")
                except Exception:
                    pass
                self.state.current_round = round_num
        except Exception:
            pass

    # ── 思考计时器 ──────────────────────────────────────
    def _start_think_timer(self, rid):
        """角色开始思考时重置计时器"""
        self._think_start_time = time.time()
        self._stop_think_timer()
        self._think_timer_task = asyncio.create_task(self._tick_think_timer())

    def _stop_think_timer(self):
        """停止计时器更新，保留最后的时间显示"""
        if self._think_timer_task and not self._think_timer_task.done():
            self._think_timer_task.cancel()
        self._think_timer_task = None

    async def _tick_think_timer(self):
        """每0.5秒刷新思考计时器"""
        try:
            while True:
                await asyncio.sleep(0.5)
                elapsed = time.time() - self._think_start_time
                try:
                    timer_widget = self.query_one("#think-timer", Static)
                    timer_widget.update(f"  {YN}{elapsed:.1f}{_YN} 秒")
                except Exception:
                    pass
        except asyncio.CancelledError:
            pass

    # ==========================================
    # 按钮
    # ==========================================
    def on_checkbox_changed(self, event):
        """自动续行复选框"""
        if event.checkbox.id == "chk-auto-continue":
            self._auto_continue = event.value

    def on_button_pressed(self, event):
        bid = event.button.id
        if bid == "btn-home":
            self._stop_think_timer()
            self.engine.stop(); self.app.pop_screen()
        elif bid == "btn-send":
            asyncio.create_task(self._handle_send())
        elif bid == "btn-start":
            asyncio.create_task(self._handle_start_engine())
        elif bid == "btn-stop":
            self._handle_stop_engine()
        elif bid == "btn-test":
            asyncio.create_task(self._handle_test())

    async def _handle_test(self):
        project = self.state.current_project
        if not project:
            self.notify("请先选择或创建项目", severity="error"); return
        self._write_to_chat(MessageRole.SYSTEM, "[bold]连通性测试...[/bold]")
        try:
            result = await self.engine.run_tests(project)
            self._write_to_chat(MessageRole.SYSTEM,
                                f"[bold blue]结果:[/]\n{result}")
        except Exception as e:
            self._write_to_chat(MessageRole.SYSTEM,
                                f"[bold red]异常: {e}[/]")

    async def _handle_send(self):
        inp = self.query_one("#chat-input", Input)
        text = inp.value.strip()
        if not text: return
        inp.value = ""
        result = self.cmd_handler.process(text)
        if result:
            await self._handle_command_result(result); return
        self._write_to_chat(MessageRole.USER, text)
        if self.state.current_project:
            msg = Message(role=MessageRole.USER, content=text)
            self.state.current_project.messages.append(msg)
            self.store.save_project(self.state.current_project)

    async def _handle_command_result(self, result):
        ct = result.get("type", ""); msg = result.get("message", "")
        if ct == "help":
            self._write_to_chat(MessageRole.SYSTEM, msg)
        elif ct == "new_project":
            from .project import ProjectScreen
            self.app.push_screen(
                ProjectScreen(self.state, self.store, self.cmd_handler))
        elif ct == "open_project":
            from .project import ProjectScreen
            self.app.push_screen(
                ProjectScreen(self.state, self.store, self.cmd_handler))
        elif ct == "open_config":
            from .settings_screen import SettingsScreen
            self.app.push_screen(
                SettingsScreen(self.state, self.store, self.cmd_handler))
        elif ct == "start_engine":
            asyncio.create_task(self._handle_start_engine())
        elif ct == "stop_engine":
            self._handle_stop_engine()
        elif ct == "export_log":
            self._handle_export_log()
        elif ct == "lang_changed":
            self.notify(msg); self._write_to_chat(MessageRole.SYSTEM, msg)
        elif ct == "clear_chat":
            self.query_one("#chat-log", RichLog).clear()
        elif ct == "quit":
            self.app.exit()
        elif ct == "error":
            self._write_to_chat(MessageRole.SYSTEM, f"[bold red]{msg}[/]")
        elif ct in ("info", "status"):
            self._write_to_chat(MessageRole.SYSTEM, msg)

    async def _handle_start_engine(self):
        project = self.state.current_project
        if not project:
            self.notify("请先选择或创建项目", severity="error"); return

        if self._auto_continue:
            # 自动续行模式：运行完整周期
            self._write_to_chat(MessageRole.SYSTEM,
                                f"[bold]引擎启动（自动续行）[/]\n核心问题：{project.core_goal}\n"
                                f"最大轮次：{YN}{project.max_iterations}{_YN}\n"
                                f"期望分数：{YN}{project.convergence_threshold}分{_YN}")
            try:
                report = await self.engine.run_full_cycle(project)
                self._stop_think_timer()
                # 显示最终报告
                self._write_to_chat(MessageRole.SYSTEM, f"[bold blue]全部轮次完成[/]")
                for line in report.split("\n"):
                    if line.strip():
                        self._write_to_chat(MessageRole.SYSTEM, line)
                self.store.save_project(project)
                self._refresh_model_status()
                self._reset_all_role_status()
            except Exception as e:
                self._stop_think_timer()
                self._write_to_chat(MessageRole.SYSTEM, f"[red]错误: {e}[/]")
                self._reset_all_role_status()
        else:
            # 单轮模式
            self._write_to_chat(MessageRole.SYSTEM,
                                f"[bold]引擎启动[/]\n核心问题：{project.core_goal}\n"
                                f"最大轮次：{YN}{project.max_iterations}{_YN}")
            try:
                record = await self.engine.run_round(project)
                self._stop_think_timer()
                self._write_to_chat(MessageRole.SYSTEM,
                                    f"[green]第{YN}{record.round_num}{_YN}轮完成[/]")
                self.store.save_project(project)
                self._refresh_model_status()
                self._reset_all_role_status()
            except Exception as e:
                self._stop_think_timer()
                self._write_to_chat(MessageRole.SYSTEM, f"[red]错误: {e}[/]")
                self._reset_all_role_status()

    def _reset_all_role_status(self):
        """重置所有角色状态为空闲"""
        self._running_roles.clear()
        for rid, lbl in ROLE_DISPLAY_NAMES.items():
            color = ROLE_COLORS.get(rid, "")
            try:
                widget = self.query_one(f"#role-{rid}-status", Static)
                widget.update(
                    f" [{color}]{lbl}[/]  "
                    f"[rgb(139,148,158)]空闲[/]")
            except Exception:
                pass
        try:
            self.query_one("#status-text", Static).update("  空闲")
        except Exception:
            pass

    def _handle_stop_engine(self):
        self.engine.stop()
        self._stop_think_timer()
        self._write_to_chat(MessageRole.SYSTEM, "[yellow]引擎已停止[/]")
        self._reset_all_role_status()
        # 重置思考计时器显示
        try:
            self.query_one("#think-timer", Static).update(
                f"  {YN}0.0{_YN} 秒")
        except Exception:
            pass

    def _handle_export_log(self):
        project = self.state.current_project
        if not project: return
        import json, os
        from ...config.settings import DATA_DIR
        os.makedirs(os.path.join(DATA_DIR, "exports"), exist_ok=True)
        fp = os.path.join(DATA_DIR, "exports", f"{project.name}_日志.json")
        with open(fp, "w", encoding="utf-8") as f:
            json.dump({
                "项目": project.name, "核心目标": project.core_goal,
                "总轮次": len(project.rounds),
                "消息": [{"角色": m.role.value,
                           "对抗角色": m.role_type.value if m.role_type else None,
                           "轮次": m.round_num, "内容": m.content}
                          for m in project.messages],
            }, f, ensure_ascii=False, indent=2)
        self._write_to_chat(MessageRole.SYSTEM, f"[green]已导出 {fp}[/]")

    def on_input_submitted(self, event):
        if event.input.id == "chat-input":
            asyncio.create_task(self._handle_send())
