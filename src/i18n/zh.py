"""
国际化翻译字典 - 中文
所有TUI界面文本、命令提示、错误消息的翻译
"""
# 中文翻译字典，每个key对应一个界面文本
translations = {
    # ========== 通用 ==========
    "app_title": "多模三维对抗思维引擎",
    "app_subtitle": "Multi-Model 3D Adversarial Thinking Engine",
    "yes": "是",
    "no": "否",
    "ok": "确定",
    "cancel": "取消",
    "back": "返回",
    "quit": "退出",
    "loading": "加载中...",
    "error": "错误",
    "warning": "警告",
    "success": "成功",
    "confirm": "确认",
    "save": "保存",
    "delete": "删除",
    "edit": "编辑",
    "create": "创建",
    "search": "搜索",
    "export": "导出",
    "import": "导入",
    "refresh": "刷新",
    "settings": "设置",
    "help": "帮助",

    # ========== 主界面 ==========
    "home_welcome": "欢迎使用多模三维对抗思维引擎",
    "home_desc": "基于\"温度分层+异质对抗+全局收敛\"原理的科研级问题求解系统",
    "home_new_project": "新建项目",
    "home_open_project": "打开项目",
    "home_recent_projects": "最近项目",
    "home_quick_start": "快速开始",

    # ========== 项目管理 ==========
    "project_name": "项目名称",
    "project_desc": "项目描述",
    "project_goal": "核心问题/主目标",
    "project_files": "项目文件",
    "project_create": "创建项目",
    "project_delete_confirm": "确认删除此项目？此操作不可撤销",
    "project_no_name": "项目名称不能为空",
    "project_list": "项目列表",
    "project_detail": "项目详情",
    "project_workspace": "工作空间",
    "project_knowledge_base": "知识库",

    # ========== 对抗引擎 ==========
    "engine_title": "对抗循环引擎",
    "engine_start": "启动对抗",
    "engine_stop": "停止对抗",
    "engine_pause": "暂停",
    "engine_resume": "继续",
    "engine_status": "引擎状态",
    "engine_round": "第 {round} 轮",
    "engine_max_rounds": "最大迭代轮次",
    "engine_convergence": "收敛阈值",
    "engine_single_step": "单步执行",
    "engine_auto_run": "自动运行",

    # ========== 角色配置 ==========
    "role_mx1": "殚虑的宰相*主理模型",
    "role_mx2": "敏疑的御史*纠错模型",
    "role_mx3": "谏官发言中*发散模型",
    "role_mx0": "入内都都知*总结模型",
    "role_mx1_desc": "提出初始方案、逐条回应质疑、迭代修正逻辑链",
    "role_mx2_desc": "寻找逻辑漏洞、反例、风险点、边界条件",
    "role_mx3_desc": "生成所有可能性、极端假设、跨界联想",
    "role_mx0_desc": "全链路质量评估、终止判断、生成最终报告",
    "role_provider": "模型厂商",
    "role_model": "模型名称",
    "role_temperature": "温度参数",
    "role_top_p": "Top P",
    "role_config": "角色配置",

    # ========== 对话界面 ==========
    "chat_input": "输入消息或 / 命令...",
    "chat_send": "发送",
    "chat_clear": "清空对话",
    "chat_export_log": "导出对话日志",
    "chat_history": "对话历史",
    "chat_no_history": "暂无对话记录",

    # ========== / 命令 ==========
    "cmd_help": "/help - 显示所有可用命令",
    "cmd_new": "/new - 创建新项目",
    "cmd_open": "/open <名称> - 打开项目",
    "cmd_config": "/config - 配置模型参数",
    "cmd_start": "/start - 启动对抗引擎",
    "cmd_stop": "/stop - 停止对抗引擎",
    "cmd_status": "/status - 查看引擎状态",
    "cmd_export": "/export - 导出对话日志",
    "cmd_lang": "/lang <zh/en> - 切换语言",
    "cmd_clear": "/clear - 清空当前对话",
    "cmd_quit": "/quit - 退出程序",
    "cmd_unknown": "未知命令：{cmd}，输入 /help 查看可用命令",
    "cmd_list_title": "可用命令列表",

    # ========== 语言切换 ==========
    "lang_switched": "语言已切换为：中文",
    "lang_current": "当前语言：中文",
    "lang_select": "选择语言",

    # ========== 设置 ==========
    "settings_title": "系统设置",
    "settings_api_keys": "API密钥配置",
    "settings_engine": "引擎参数",
    "settings_ui": "界面设置",
    "settings_theme": "主题",
    "settings_theme_dark": "暗色",
    "settings_theme_light": "亮色",
    "settings_save": "保存设置",
    "settings_saved": "设置已保存",

    # ========== 状态消息 ==========
    "status_idle": "空闲",
    "status_running": "运行中",
    "status_paused": "已暂停",
    "status_finished": "已完成",
    "status_error": "错误",
    "status_converged": "已收敛",

    # ========== 错误消息 ==========
    "err_api_key_missing": "缺少API密钥，请在设置中配置",
    "err_model_call_failed": "模型调用失败：{error}",
    "err_project_not_found": "项目不存在：{name}",
    "err_no_active_project": "没有活跃项目，请先创建或打开项目",
    "err_max_rounds_reached": "已达到最大迭代轮次",
}
