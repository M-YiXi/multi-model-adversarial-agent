"""
项目管理界面 — 创建新项目（精简表单）
保留：项目名称、描述、核心目标、前置学习目录、迭代次数、期望分数
四角色配置来自设置页面的全局默认值
"""
from textual.screen import Screen
from textual.widgets import Static, Button, Input, Label
from textual.containers import ScrollableContainer, Horizontal
from textual.app import ComposeResult

from ...core.models import AppState, Project, ModelConfig, DEFAULT_SYSTEM_PROMPTS
from ...storage.store import ProjectStore
from ...commands.handler import CommandHandler
from ...config.settings import settings


class ProjectScreen(Screen):
    """创建新项目"""

    def __init__(self, state: AppState, store: ProjectStore,
                 cmd_handler: CommandHandler):
        super().__init__()
        self.state = state
        self.store = store
        self.cmd_handler = cmd_handler

    def compose(self) -> ComposeResult:
        yield Static("▸ 创建新项目", classes="section-title")

        with ScrollableContainer():
            yield Label("项目名称 *")
            yield Input(placeholder="输入唯一项目名称（不可重复）", id="input-name")
            yield Label("项目描述")
            yield Input(placeholder="简要描述项目用途", id="input-desc")
            yield Label("核心问题 / 主目标 *")
            yield Input(placeholder="描述要解决的核心问题...", id="input-goal")

            yield Label("前置学习目录（可选，只读参考）")
            yield Input(placeholder="例: D:\\论文\\项目资料\\  存放论文/PPT/代码等参考文件",
                        id="input-kb-dir")

            yield Static("")

            yield Static("▸ 引擎参数", classes="section-title")
            default_iter = settings.engine_defaults.get("max_iterations", 18)
            default_score = settings.engine_defaults.get("expected_score", 90)
            yield Label("迭代次数")
            yield Input(value=str(default_iter), id="input-max-rounds")
            yield Label("期望分数 (1~100)")
            yield Input(value=str(default_score), id="input-expected-score")

            yield Static("")

            with Horizontal(classes="button-row"):
                yield Button("创建项目", variant="primary", id="btn-create-submit")
                yield Button("返回", variant="default", id="btn-back")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-back":
            self.app.pop_screen()

        elif event.button.id == "btn-create-submit":
            project = Project()
            try:
                project.name = self.query_one("#input-name", Input).value.strip()
                project.description = self.query_one("#input-desc", Input).value.strip()
                project.core_goal = self.query_one("#input-goal", Input).value.strip()
                project.knowledge_base_dir = self.query_one("#input-kb-dir", Input).value.strip()
            except Exception:
                pass
            try:
                project.max_iterations = int(
                    self.query_one("#input-max-rounds", Input).value
                )
            except (ValueError, Exception):
                project.max_iterations = 18
            try:
                escore = int(self.query_one("#input-expected-score", Input).value)
                project.convergence_threshold = max(1, min(100, escore))
            except (ValueError, Exception):
                project.convergence_threshold = 90

            # 四角色使用全局默认配置（来自 config.yaml + 内置提示词）
            for role_id in ["MX1", "MX2", "MX3", "MX0"]:
                dr = settings.default_roles.get(role_id, {})
                cfg = ModelConfig(
                    model=dr.get("model", ""),
                    temperature=float(dr.get("temperature", 0.2)),
                    top_p=float(dr.get("top_p", 0.5)),
                    context_length=int(dr.get("context_length", 128000)),
                    max_output_tokens=int(dr.get("max_output_tokens", 16384)),
                    api_key=dr.get("api_key", ""),
                    openai_base_url=dr.get("openai_base_url", ""),
                    anthropic_base_url=dr.get("anthropic_base_url", ""),
                    system_prompt=DEFAULT_SYSTEM_PROMPTS.get(role_id, ""),
                )
                setattr(project, f"{role_id.lower()}_config", cfg)

            if not project.name:
                self.notify("项目名称不能为空", severity="error")
                return
            if not project.core_goal:
                self.notify("请输入核心问题/主目标", severity="error")
                return

            self.store.save_project(project)
            self.state.current_project = project
            self.notify(f"项目「{project.name}」创建成功", severity="information")
            self.app.pop_screen()

            from .chat import ChatScreen
            self.app.push_screen(
                ChatScreen(self.state, self.store, self.cmd_handler, self.app.logger))
