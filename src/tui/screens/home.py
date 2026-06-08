"""
首页界面 — 类Claude TUI风格
Logo + 新建项目/设置按钮 + 最近项目完整列表
"""
from textual.screen import Screen
from textual.widgets import Static, Button, ListView, ListItem
from textual.containers import Container, Horizontal, Vertical
from textual.app import ComposeResult

from ...core.models import AppState
from ...storage.store import ProjectStore
from ...commands.handler import CommandHandler
from .project import ProjectScreen
from .settings_screen import SettingsScreen
from .chat import ChatScreen


class HomeScreen(Screen):
    """首页 — Logo + 新建项目/设置 + 全部项目列表"""

    def __init__(self, state: AppState, store: ProjectStore,
                 cmd_handler: CommandHandler):
        super().__init__()
        self.state = state
        self.store = store
        self.cmd_handler = cmd_handler

    def compose(self) -> ComposeResult:
        with Container(id="home-container"):
            yield Static(
                "╔══════════════════════════════════════════════╗\n"
                "║    多模三维对抗思维引擎                      ║\n"
                "║    Multi-Model 3D Adversarial Engine          ║\n"
                "╚══════════════════════════════════════════════╝",
                id="home-logo"
            )
            yield Static("多模三维对抗思维引擎", id="home-welcome")
            yield Static("基于「温度分层 + 异质对抗 + 全局收敛」原理的科研级问题求解系统",
                         id="home-desc")

            # 操作按钮：新建项目 + 删除项目 + 设置
            with Horizontal(id="home-buttons"):
                yield Button("  新建项目  ", variant="primary", id="btn-new")
                yield Button("  删除项目  ", variant="error", id="btn-delete")
                yield Button("  设置  ", variant="default", id="btn-settings")

            # 最近项目列表 — 展示全部已创建项目
            with Vertical(id="home-project-section"):
                yield Static("▸ 最近项目", id="home-project-title")
                yield ListView(id="recent-projects")

            yield Static("GitHub作者主页：https://github.com/M-YiXi?tab=repositories",
                         id="home-hint")

    def on_mount(self) -> None:
        self._refresh_project_list()

    def _refresh_project_list(self):
        list_view = self.query_one("#recent-projects", ListView)
        list_view.clear()
        projects = self.store.list_projects()
        if not projects:
            list_view.append(ListItem(Static("  暂无项目 — 点击「新建项目」开始")))
            return

        for proj in projects:  # 展示全部项目
            # 精确到分钟：格式化为 MM-DD HH:MM
            ts = proj.get("updated_at", "")
            if len(ts) >= 16:
                ts = ts[5:16].replace("T", " ")  # "06-04 12:30"
            name_line = f"[bold]{proj['name']}[/bold]  [dim]{ts}[/dim]"
            desc = proj.get("description", "")
            if desc:
                name_line += f"\n  [dim]{desc[:60]}[/dim]"
            goal = proj.get("core_goal", "")
            if goal:
                name_line += f"\n  [dim]目标: {goal[:50]}[/dim]"
            list_view.append(ListItem(Static(name_line), name=proj["id"]))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-new":
            self.app.push_screen(
                ProjectScreen(self.state, self.store, self.cmd_handler))
        elif event.button.id == "btn-settings":
            self.app.push_screen(
                SettingsScreen(self.state, self.store, self.cmd_handler))
        elif event.button.id == "btn-delete":
            self._delete_selected_project()

    def _delete_selected_project(self):
        """删除当前选中的项目"""
        list_view = self.query_one("#recent-projects", ListView)
        if list_view.index is None or list_view.index < 0:
            self.notify("请先选择要删除的项目", severity="warning")
            return
        # 遍历 children 找到当前高亮项
        children = list_view.children
        idx = list_view.index
        if idx >= len(children):
            return
        selected_item = children[idx]
        proj_id = selected_item.name if hasattr(selected_item, 'name') else None
        if not proj_id:
            return
        # 查找项目名用于提示
        projects = self.store.list_projects()
        proj_name = ""
        for p in projects:
            if p["id"] == proj_id:
                proj_name = p["name"]
                break
        if not proj_name:
            self.notify("项目不存在", severity="error")
            return
        self.store.delete_project(project_id=proj_id)
        self.notify(f"项目「{proj_name}」已删除", severity="information")
        self._refresh_project_list()
        # 如果删除的是当前项目，清除引用
        if (self.state.current_project
                and self.state.current_project.id == proj_id):
            self.state.current_project = None

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        proj_id = event.item.name if event.item else None
        if not proj_id:
            return
        project = self.store.get_project(project_id=proj_id)
        if project:
            self.state.current_project = project
            self.app.push_screen(
                ChatScreen(self.state, self.store,
                           self.cmd_handler, self.app.logger))
