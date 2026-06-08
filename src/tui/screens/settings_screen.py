"""
设置界面 — 集中管理所有配置
"""
from textual.screen import Screen
from textual.widgets import Static, Button, Input, Label, TabbedContent, TabPane
from textual.containers import ScrollableContainer
from textual.app import ComposeResult

from ...core.models import AppState
from ...storage.store import ProjectStore
from ...commands.handler import CommandHandler
from ...config.settings import settings
from ...i18n.translator import set_language

ROLES = [
    ("MX1", "殚虑的宰相*主理模型", "提出方案、回应质疑、迭代修正"),
    ("MX2", "敏疑的御史*纠错模型", "寻找漏洞、反例、风险点"),
    ("MX3", "谏官发言中*发散模型", "生成所有可能性、跨界联想"),
    ("MX0", "入内都都知*总结模型", "全链路评估、终止判断、最终报告"),
]


class SettingsScreen(Screen):

    def __init__(self, state, store, cmd):
        super().__init__()
        self.state = state; self.store = store; self.cmd_handler = cmd

    def compose(self) -> ComposeResult:
        with ScrollableContainer():
            yield Static("▸ 系统设置", classes="section-title")

            # ===== 语言 =====
            yield Static("▼ 界面语言", classes="section-title")
            lang_hint = f"当前语言：{'中文' if self.state.language == 'zh' else 'English'}"
            yield Static(lang_hint, classes="hint-text")
            zh_v = "primary" if self.state.language == "zh" else "default"
            en_v = "primary" if self.state.language == "en" else "default"
            yield Button("  中文  ", variant=zh_v, id="btn-lang-zh")
            yield Button("  English  ", variant=en_v, id="btn-lang-en")

            yield Static("")

            # ===== 引擎参数 =====
            yield Static("▼ 引擎默认参数", classes="section-title")
            max_iter = settings.engine_defaults.get("max_iterations", 18)
            expected = settings.engine_defaults.get("expected_score", 90)
            yield Label("迭代次数")
            yield Input(value=str(max_iter), id="input-max-rounds")
            yield Label("期望分数 (1~100)")
            yield Input(value=str(expected), id="input-expected-score")

            yield Static("")

            # ===== 四角色配置 =====
            yield Static("▼ 四角色模型配置（每个角色独立密钥与端点）",
                         classes="section-title")
            with TabbedContent():
                for rid, rname, rdesc in ROLES:
                    with TabPane(f" {rname} ", id=f"tab-{rid}"):
                        yield from self._pane(rid, rdesc)

            yield Static("")
            yield Button("保存设置", variant="primary", id="btn-save")
            yield Button("返回", variant="default", id="btn-back")

    def _pane(self, rid: str, rdesc: str):
        d = settings.default_roles.get(rid, {})
        yield Static(f"  {rdesc}", classes="hint-text")

        yield Label("模型名称")
        yield Input(value=d.get("model", ""),
                    placeholder="模型名称", id=f"input-model-{rid}")
        yield Label("API 密钥")
        yield Input(value=d.get("api_key", ""),
                    placeholder="sk-...", id=f"input-apikey-{rid}", password=True)
        yield Label("OpenAI 兼容 API 地址")
        yield Input(value=d.get("openai_base_url", ""),
                    placeholder="留空使用默认", id=f"input-openai-url-{rid}")
        yield Label("Anthropic API 地址")
        yield Input(value=d.get("anthropic_base_url", ""),
                    placeholder="留空使用默认", id=f"input-anthropic-url-{rid}")

        yield Label("温度 (0~2)")
        yield Input(value=str(d.get("temperature", "0.2")),
                    id=f"input-temp-{rid}")
        yield Label("Top P (0~1)")
        yield Input(value=str(d.get("top_p", "0.5")),
                    id=f"input-topp-{rid}")
        yield Label("上下文 (Token)")
        yield Input(value=str(d.get("context_length", "1000000")),
                    id=f"input-ctx-{rid}")
        yield Label("输出限制 (Token)")
        yield Input(value=str(d.get("max_output_tokens", "380000")),
                    id=f"input-maxout-{rid}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id
        if bid == "btn-back":
            self.app.pop_screen()
        elif bid == "btn-lang-zh":
            set_language("zh"); self.state.language = "zh"; settings.language = "zh"
            settings.save()
            self.notify("语言已切换为中文。部分界面文本需重启应用后完全生效。",
                        severity="warning", timeout=6)
            self.app.pop_screen()
        elif bid == "btn-lang-en":
            set_language("en"); self.state.language = "en"; settings.language = "en"
            settings.save()
            self.notify("Language switched. Restart for full effect.",
                        severity="warning", timeout=6)
            self.app.pop_screen()
        elif bid == "btn-save":
            self._save()

    def _save(self):
        try:
            settings.set("engine_defaults.max_iterations",
                         int(self.query_one("#input-max-rounds", Input).value))
        except (ValueError, Exception): pass
        try:
            val = int(self.query_one("#input-expected-score", Input).value)
            settings.set("engine_defaults.expected_score", max(1, min(100, val)))
        except (ValueError, Exception): pass
        for rid, _, _ in ROLES:
            for fid, ckey in [("model", "model"), ("apikey", "api_key"),
                              ("openai-url", "openai_base_url"),
                              ("anthropic-url", "anthropic_base_url")]:
                try:
                    settings.set(f"default_roles.{rid}.{ckey}",
                                 self.query_one(f"#input-{fid}-{rid}", Input).value.strip())
                except Exception: pass
            for fid, ckey, cast in [("temp", "temperature", float), ("topp", "top_p", float),
                                     ("ctx", "context_length", int), ("maxout", "max_output_tokens", int)]:
                try:
                    settings.set(f"default_roles.{rid}.{ckey}",
                                 cast(self.query_one(f"#input-{fid}-{rid}", Input).value))
                except (ValueError, Exception): pass
        settings.save()
        self.notify("设置已保存", severity="information")
        self.app.pop_screen()
