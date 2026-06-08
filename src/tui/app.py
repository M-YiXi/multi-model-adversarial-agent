"""
TUI主应用入口 - Textual框架
类Claude TUI风格的深色终端界面，全功能多面板布局
"""
from textual.app import App, ComposeResult  # Textual应用基类
from textual.widgets import Header, Footer, Static  # 内置组件
from textual.containers import Container, Horizontal, Vertical  # 布局容器
from textual.binding import Binding  # 快捷键绑定

from .screens.home import HomeScreen  # 首页界面
from .screens.project import ProjectScreen  # 项目管理
from .screens.chat import ChatScreen  # 对抗对话
from .screens.settings_screen import SettingsScreen  # 设置
from ..i18n.translator import t, set_language  # 翻译
from ..config.settings import settings  # 全局配置
from ..core.models import AppState, Project  # 数据模型
from ..commands.handler import CommandHandler  # 命令处理
from ..storage.store import ProjectStore  # 数据存储
from ..storage.logger import Logger  # 日志


class AdversarialTUI(App):
    """
    多模三维对抗思维引擎 — TUI主应用
    类Claude TUI风格：深色底 + 蓝调强调 + 三栏布局
    """
    CSS = """
    /* ===== 全局基础 ===== */
    Screen {
        background: #0d1117;
        color: #c9d1d9;
    }

    /* 顶部/底部栏 */
    Header {
        background: #0d1117;
        color: #58a6ff;
        text-style: bold;
        dock: top;
        height: 1;
    }
    Footer {
        background: #0d1117;
        color: #484f58;
        dock: bottom;
        height: 1;
    }

    /* ===== 首页容器 ===== */
    #home-container {
        align: center middle;
        height: 1fr;
        width: 1fr;
        padding: 2 4;
    }
    #home-logo {
        content-align: center middle;
        color: #58a6ff;
        text-style: bold;
        width: 1fr;
        height: auto;
        margin-bottom: 1;
    }
    #home-welcome {
        content-align: center middle;
        color: #58a6ff;
        text-style: bold;
        width: 1fr;
    }
    #home-desc {
        content-align: center middle;
        color: #8b949e;
        width: 1fr;
        margin-bottom: 1;
    }

    /* 首页操作按钮行 */
    #home-buttons {
        width: 1fr;
        align: center middle;
        height: auto;
        margin-bottom: 2;
    }
    #home-buttons Button {
        margin: 0 1;
        min-width: 18;
    }

    /* 首页项目列表区 */
    #home-project-section {
        width: 1fr;
        height: 1fr;
        border: solid #21262d;
        padding: 1;
    }
    #home-project-title {
        color: #58a6ff;
        text-style: bold;
        margin-bottom: 1;
    }
    #recent-projects {
        height: 1fr;
    }
    #recent-projects ListItem {
        padding: 0 1;
    }
    #recent-projects ListItem:hover {
        background: #1c2128;
    }

    /* 首页底部提示 */
    #home-hint {
        content-align: center middle;
        color: #484f58;
        width: 1fr;
        margin-top: 1;
    }

    /* ===== 通用三栏布局 ===== */
    #main-container {
        height: 1fr;
    }

    /* 左侧面板 */
    #left-panel {
        width: 22;
        background: #161b22;
        border-right: solid #21262d;
    }
    #left-panel Static {
        color: #8b949e;
    }
    #left-panel .section-title {
        color: #58a6ff;
        text-style: bold;
    }
    #left-panel .panel-title {
        color: #58a6ff;
        text-style: bold;
        padding: 0 1;
        height: 1;
    }
    /* 中间面板 */
    #center-panel {
        width: 1fr;
        background: #0d1117;
    }
    /* 右侧面板 */
    #right-panel {
        width: 22;
        background: #161b22;
        border-left: solid #21262d;
    }
    #right-panel Static {
        color: #8b949e;
    }
    #right-panel .section-title {
        color: #58a6ff;
        text-style: bold;
    }

    /* 暗黄色数字 */
    .num {
        color: #D29922;
        text-style: bold;
    }

    /* 面板通用 */
    .panel-title {
        color: #58a6ff;
        text-style: bold;
        padding: 1;
        border-bottom: solid #21262d;
        height: 1;
    }
    .panel-scroll {
        height: 1fr;
        overflow-y: auto;
    }

    /* ===== 通用组件 ===== */
    Input {
        background: #0d1117;
        color: #c9d1d9;
        border: solid #30363d;
        margin: 0 1;
    }
    Input:focus {
        border: solid #58a6ff;
    }

    Button {
        background: #21262d;
        color: #c9d1d9;
        border: solid #30363d;
        min-width: 10;
    }
    Button:hover {
        background: #30363d;
        border: solid #58a6ff;
    }

    /* 主要按钮 */
    .btn-primary {
        background: #1f6feb;
        color: #ffffff;
        border: solid #1f6feb;
    }
    .btn-primary:hover {
        background: #388bfd;
    }
    .btn-success {
        background: #1a7f37;
        color: #ffffff;
    }
    .btn-success:hover {
        background: #2ea043;
    }
    .btn-danger {
        background: #cf222e;
        color: #ffffff;
    }
    .btn-danger:hover {
        background: #da3633;
    }

    /* 静态文本 */
    Static {
        color: #c9d1d9;
    }

    /* 标签文字 */
    Label {
        color: #8b949e;
        padding: 0 1;
    }

    /* Select下拉框 */
    Select {
        margin: 0 1;
        background: #0d1117;
        color: #c9d1d9;
        border: solid #30363d;
    }

    /* 列表项 */
    ListView {
        background: transparent;
    }
    ListView ListItem {
        color: #c9d1d9;
    }
    ListView ListItem:hover {
        background: #1c2128;
    }
    ListView ListItem.--highlight {
        background: #1c2128;
        border-left: solid #58a6ff;
    }

    /* 标题文字 */
    .section-title {
        color: #58a6ff;
        text-style: bold;
        padding: 0 1;
        margin-top: 1;
    }
    .hint-text {
        color: #8b949e;
    }
    .divider {
        color: #21262d;
        margin: 0 1;
    }

    /* 滚动条 */
    ScrollableContainer {
        scrollbar-color: #30363d;
        scrollbar-background: #0d1117;
        scrollbar-size: 1 1;
    }

    /* 输入区域 */
    #input-area {
        dock: bottom;
        height: auto;
        background: #161b22;
        border-top: solid #21262d;
        padding: 1;
    }
    #chat-input {
        width: 2fr;
    }

    /* 按钮行 */
    .button-row {
        height: auto;
        padding: 1;
        align: center middle;
    }
    .button-row Button {
        margin: 0 1;
    }

    /* 语言切换按钮行 */
    .lang-row {
        height: auto;
        padding: 0 1;
        margin-bottom: 1;
    }

    /* 项目详情卡片 */
    .detail-row {
        padding: 0 1;
        height: 1;
    }
    .detail-label {
        color: #8b949e;
        width: 12;
    }
    .detail-value {
        color: #c9d1d9;
        width: 1fr;
    }

    /* 角色配置卡片 */
    .role-card {
        border: solid #21262d;
        margin: 1;
        padding: 1;
    }
    .role-card-title {
        color: #58a6ff;
        text-style: bold;
    }

    /* 聊天消息各角色颜色 */
    .mx1-color { color: #00FFFF; }
    .mx2-color { color: #E0218A; }
    .mx3-color { color: #91C53A; }
    .mx0-color { color: #91CFD5; }

    /* 状态栏 */
    #status-bar {
        dock: bottom;
        height: 1;
        background: #0d1117;
        color: #484f58;
        padding: 0 1;
    }

    /* RichLog聊天区 */
    RichLog {
        background: #0d1117;
        scrollbar-color: #30363d;
        scrollbar-background: #0d1117;
        scrollbar-size: 1 1;
        padding: 1;
    }

    /* 模型状态区 */
    #model-status-panel {
        height: auto;
    }

    /* Checkbox — 去掉标签默认选中高亮背景 */
    Checkbox {
        background: transparent;
        color: #8b949e;
        padding: 0 1;
    }
    Checkbox:hover {
        background: #1c2128;
    }
    Checkbox .toggle--switch {
        background: #30363d;
    }
    Checkbox .toggle--switch.on {
        background: #1f6feb;
    }
    Checkbox .toggle--label {
        background: transparent;
        color: #8b949e;
    }
    Checkbox:focus .toggle--label {
        background: transparent;
    }

    """

    BINDINGS = [
        Binding("ctrl+c", "quit", "退出"),
        Binding("ctrl+n", "new_project", "新建项目"),
        Binding("ctrl+s", "start_engine", "启动对抗"),
        Binding("ctrl+e", "open_settings", "设置"),
        Binding("ctrl+l", "toggle_lang", "切换语言"),
        Binding("escape", "back", "返回"),
        Binding("f1", "show_help", "帮助"),
    ]

    def __init__(self):
        super().__init__()
        self.state = AppState()
        self.store = ProjectStore()
        self.logger = Logger()
        self.cmd_handler = CommandHandler(self.state)
        # 初始化语言
        lang = settings.language
        set_language(lang)
        self.state.language = lang

    def compose(self) -> ComposeResult:
        """构建界面布局"""
        yield Header(show_clock=True)
        # 主内容由子屏幕接管，这里仅提供框架
        yield Static("", id="main-container")

    def on_mount(self) -> None:
        """启动后显示首页"""
        self.push_screen(HomeScreen(self.state, self.store, self.cmd_handler))

    # ===== 快捷键动作 =====
    def action_new_project(self):
        self.push_screen(ProjectScreen(self.state, self.store, self.cmd_handler))

    def action_open_settings(self):
        self.push_screen(SettingsScreen(self.state, self.store, self.cmd_handler))

    def action_start_engine(self):
        if self.state.current_project:
            self.push_screen(ChatScreen(self.state, self.store, self.cmd_handler, self.logger))
        else:
            self.notify(t("err_no_active_project"), severity="warning")

    def action_toggle_lang(self):
        new_lang = "en" if self.state.language == "zh" else "zh"
        set_language(new_lang)
        self.state.language = new_lang
        settings.language = new_lang
        self.notify(t("lang_switched"), severity="information")

    def action_show_help(self):
        help_text = self.cmd_handler.get_help_text()
        self.notify(help_text, title=t("cmd_list_title"), severity="information", timeout=10)

    def action_back(self):
        if len(self.screen_stack) > 1:
            self.pop_screen()
