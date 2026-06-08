"""
Internationalization Translation Dictionary - English
Translations for all TUI interface text, command prompts, and error messages
"""
# English translation dictionary, each key maps to an interface text
translations = {
    # ========== General ==========
    "app_title": "Multi-Model 3D Adversarial Thinking Engine",
    "app_subtitle": "Multi-Model 3D Adversarial Thinking Engine",
    "yes": "Yes",
    "no": "No",
    "ok": "OK",
    "cancel": "Cancel",
    "back": "Back",
    "quit": "Quit",
    "loading": "Loading...",
    "error": "Error",
    "warning": "Warning",
    "success": "Success",
    "confirm": "Confirm",
    "save": "Save",
    "delete": "Delete",
    "edit": "Edit",
    "create": "Create",
    "search": "Search",
    "export": "Export",
    "import": "Import",
    "refresh": "Refresh",
    "settings": "Settings",
    "help": "Help",

    # ========== Home Screen ==========
    "home_welcome": "Welcome to Multi-Model 3D Adversarial Thinking Engine",
    "home_desc": "A research-grade problem-solving system based on \"temperature layering + heterogeneous adversarial + global convergence\"",
    "home_new_project": "New Project",
    "home_open_project": "Open Project",
    "home_recent_projects": "Recent Projects",
    "home_quick_start": "Quick Start",

    # ========== Project Management ==========
    "project_name": "Project Name",
    "project_desc": "Project Description",
    "project_goal": "Core Problem / Main Goal",
    "project_files": "Project Files",
    "project_create": "Create Project",
    "project_delete_confirm": "Confirm deletion of this project? This action cannot be undone",
    "project_no_name": "Project name cannot be empty",
    "project_list": "Project List",
    "project_detail": "Project Details",
    "project_workspace": "Workspace",
    "project_knowledge_base": "Knowledge Base",

    # ========== Adversarial Engine ==========
    "engine_title": "Adversarial Loop Engine",
    "engine_start": "Start Adversarial",
    "engine_stop": "Stop Adversarial",
    "engine_pause": "Pause",
    "engine_resume": "Resume",
    "engine_status": "Engine Status",
    "engine_round": "Round {round}",
    "engine_max_rounds": "Max Iterations",
    "engine_convergence": "Convergence Threshold",
    "engine_single_step": "Single Step",
    "engine_auto_run": "Auto Run",

    # ========== Role Configuration ==========
    "role_mx1": "Chancellor*Main Model",
    "role_mx2": "Censor*Critical Model",
    "role_mx3": "Divergent Thinker*Expand Model",
    "role_mx0": "Grand Arbiter*Summary Model",
    "role_mx1_desc": "Propose initial solutions, respond to criticism point by point, iteratively refine logic chains",
    "role_mx2_desc": "Find logical flaws, counterexamples, risks, and boundary conditions",
    "role_mx3_desc": "Generate all possibilities, extreme hypotheses, cross-domain associations",
    "role_mx0_desc": "Full-chain quality assessment, termination judgment, generate final report",
    "role_provider": "Provider",
    "role_model": "Model Name",
    "role_temperature": "Temperature",
    "role_top_p": "Top P",
    "role_config": "Role Configuration",

    # ========== Chat Interface ==========
    "chat_input": "Type message or / command...",
    "chat_send": "Send",
    "chat_clear": "Clear Chat",
    "chat_export_log": "Export Chat Log",
    "chat_history": "Chat History",
    "chat_no_history": "No chat history",

    # ========== / Commands ==========
    "cmd_help": "/help - Show all available commands",
    "cmd_new": "/new - Create new project",
    "cmd_open": "/open <name> - Open project",
    "cmd_config": "/config - Configure model parameters",
    "cmd_start": "/start - Start adversarial engine",
    "cmd_stop": "/stop - Stop adversarial engine",
    "cmd_status": "/status - View engine status",
    "cmd_export": "/export - Export chat log",
    "cmd_lang": "/lang <zh/en> - Switch language",
    "cmd_clear": "/clear - Clear current chat",
    "cmd_quit": "/quit - Quit program",
    "cmd_unknown": "Unknown command: {cmd}, type /help for available commands",
    "cmd_list_title": "Available Commands",

    # ========== Language Switching ==========
    "lang_switched": "Language switched to: English",
    "lang_current": "Current language: English",
    "lang_select": "Select Language",

    # ========== Settings ==========
    "settings_title": "System Settings",
    "settings_api_keys": "API Key Configuration",
    "settings_engine": "Engine Parameters",
    "settings_ui": "UI Settings",
    "settings_theme": "Theme",
    "settings_theme_dark": "Dark",
    "settings_theme_light": "Light",
    "settings_save": "Save Settings",
    "settings_saved": "Settings saved",

    # ========== Status Messages ==========
    "status_idle": "Idle",
    "status_running": "Running",
    "status_paused": "Paused",
    "status_finished": "Finished",
    "status_error": "Error",
    "status_converged": "Converged",

    # ========== Error Messages ==========
    "err_api_key_missing": "API key missing, please configure in settings",
    "err_model_call_failed": "Model call failed: {error}",
    "err_project_not_found": "Project not found: {name}",
    "err_no_active_project": "No active project, please create or open a project first",
    "err_max_rounds_reached": "Maximum iterations reached",
}
