/**
 * 多模三维对抗思维引擎 - Web端交互逻辑
 * 处理API调用、界面更新、命令解析
 */

// ===== 全局状态 =====
let currentProjectId = null;  // 当前活跃项目ID
let currentLanguage = 'zh';  // 当前语言

// ===== 界面初始化 =====
document.addEventListener('DOMContentLoaded', () => {
    loadProjects();  // 加载项目列表
    setupEventListeners();  // 绑定事件
    loadStatus();  // 加载引擎状态
});

// ===== 事件监听绑定 =====
function setupEventListeners() {
    // 新建项目按钮
    document.getElementById('btn-new-project').onclick = () => showModal('modal-new-project');

    // 发送按钮
    document.getElementById('btn-send').onclick = sendMessage;

    // 回车发送
    document.getElementById('chat-input').onkeydown = (e) => {
        if (e.key === 'Enter') sendMessage();  // 回车键发送
    };

    // 语言切换
    document.getElementById('btn-lang-zh').onclick = () => switchLang('zh');
    document.getElementById('btn-lang-en').onclick = () => switchLang('en');

    // 设置按钮
    document.getElementById('btn-settings').onclick = () => showModal('modal-settings');

    // 引擎控制按钮
    document.getElementById('btn-start').onclick = () => sendCommand('/start');
    document.getElementById('btn-stop').onclick = () => sendCommand('/stop');
    document.getElementById('btn-step').onclick = () => sendCommand('/step');

    // 弹窗外部点击关闭
    window.onclick = (e) => {
        if (e.target.classList.contains('modal')) e.target.style.display = 'none';
    };
}

// ===== 项目相关 =====

/** 加载项目列表到左侧面板 */
async function loadProjects() {
    try {
        const resp = await fetch('/api/projects');
        const data = await resp.json();
        renderProjectList(data.projects || []);
    } catch (err) {
        console.error('加载项目列表失败:', err);
    }
}

/** 渲染项目列表 */
function renderProjectList(projects) {
    const container = document.getElementById('project-list');
    if (projects.length === 0) {
        container.innerHTML = '<p class="empty-hint">暂无项目</p>';
        return;
    }
    container.innerHTML = projects.map(p => `
        <div class="project-item ${p.id === currentProjectId ? 'active' : ''}"
             onclick="selectProject('${p.id}')">
            <div class="project-item-row">
                <div class="project-item-info">
                    <div class="name">${escapeHtml(p.name)}</div>
                    <div class="desc">${escapeHtml(p.description || '无描述')}</div>
                </div>
                <button class="btn-delete-project" onclick="event.stopPropagation(); deleteProject('${p.id}', '${escapeHtml(p.name)}')" title="删除项目">&times;</button>
            </div>
        </div>
    `).join('');
}

/** 删除项目 */
async function deleteProject(projectId, projectName) {
    if (!confirm(`确定要删除项目「${projectName}」吗？此操作不可恢复。`)) return;
    try {
        const resp = await fetch(`/api/projects/${projectId}`, { method: 'DELETE' });
        if (resp.ok) {
            if (currentProjectId === projectId) {
                currentProjectId = null;
                document.getElementById('chat-log').innerHTML = `
                    <div class="welcome-msg">
                        <h2>欢迎使用多模三维对抗思维引擎</h2>
                        <p>基于"温度分层+异质对抗+全局收敛"原理的科研级问题求解系统</p>
                        <p class="hint">输入 /help 查看命令列表 | 选择一个项目开始</p>
                    </div>`;
                document.getElementById('chat-title').textContent = '对抗对话';
            }
            await loadProjects();
            addSystemMsg(`项目「${projectName}」已删除`);
        } else {
            addSystemMsg('删除失败：项目不存在', true);
        }
    } catch (err) {
        console.error('删除项目失败:', err);
        addSystemMsg('删除项目失败', true);
    }
}

/** 选中项目并加载其消息 */
async function selectProject(projectId) {
    currentProjectId = projectId;
    loadProjects();  // 刷新高亮
    // 加载该项目消息
    try {
        const resp = await fetch(`/api/projects/${projectId}/messages`);
        const data = await resp.json();
        renderMessages(data.messages || []);
        document.getElementById('chat-title').textContent = '对抗对话 #' + projectId;
    } catch (err) {
        console.error('加载消息失败:', err);
    }
}

/** 创建新项目 */
async function createProject() {
    const name = document.getElementById('new-name').value.trim();
    const desc = document.getElementById('new-desc').value.trim();
    const goal = document.getElementById('new-goal').value.trim();
    const maxRounds = parseInt(document.getElementById('new-max-rounds').value) || 18;
    const convergence = parseInt(document.getElementById('new-convergence').value) || 90;

    if (!name) { alert('请输入项目名称'); return; }
    if (!goal) { alert('请输入核心问题'); return; }

    try {
        const resp = await fetch('/api/projects', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name, description: desc, core_goal: goal,
                max_iterations: maxRounds, convergence_threshold: convergence
            })
        });
        const data = await resp.json();
        closeModal('modal-new-project');
        await loadProjects();
        selectProject(data.id);
        addSystemMsg(`项目 "${name}" 创建成功`);
    } catch (err) {
        console.error('创建项目失败:', err);
    }
}

// ===== 消息处理 =====

/** 发送消息或命令 */
function sendMessage() {
    const input = document.getElementById('chat-input');
    const text = input.value.trim();
    if (!text) return;
    input.value = '';  // 清空输入框

    // / 命令处理
    if (text.startsWith('/')) {
        handleCommand(text);
        return;
    }

    // 普通消息
    addUserMsg(text);
}

/** 发送 / 命令 */
function sendCommand(cmd) {
    handleCommand(cmd);
}

/** 处理命令 */
function handleCommand(cmd) {
    const parts = cmd.slice(1).split(/\s+/);
    const name = parts[0].toLowerCase();
    const args = parts.slice(1).join(' ');

    switch (name) {
        case 'help':
            addSystemMsg(
                '可用命令:\n' +
                '/help - 显示帮助\n' +
                '/new - 新建项目\n' +
                '/start - 启动引擎\n' +
                '/stop - 停止引擎\n' +
                '/status - 查看状态\n' +
                '/lang zh/en - 切换语言\n' +
                '/clear - 清空聊天\n' +
                '/config - 打开设置'
            );
            break;
        case 'new':
            showModal('modal-new-project');
            break;
        case 'start':
            if (!currentProjectId) {
                addSystemMsg('请先选择或创建一个项目', true);
            } else {
                addSystemMsg('引擎已启动...');
                // 模拟运行
                updateRoleStatus('running');
            }
            break;
        case 'stop':
            addSystemMsg('引擎已停止');
            updateRoleStatus('idle');
            break;
        case 'status':
            loadStatus();
            break;
        case 'lang':
            switchLang(args || 'zh');
            break;
        case 'clear':
            document.getElementById('chat-log').innerHTML = '';
            break;
        case 'config':
            showModal('modal-settings');
            break;
        default:
            addSystemMsg(`未知命令: /${name}，输入 /help 查看帮助`, true);
    }
}

/** 显示用户消息气泡 */
function addUserMsg(text) {
    const log = document.getElementById('chat-log');
    log.insertAdjacentHTML('beforeend', `
        <div class="msg msg-user">
            <div class="role-tag">▼ 用户</div>
            <div class="content">${escapeHtml(text)}</div>
        </div>
    `);
    scrollToBottom();
}

/** 显示系统消息 */
function addSystemMsg(text, isError = false) {
    const log = document.getElementById('chat-log');
    const cls = isError ? 'msg-system msg-error' : 'msg-system';
    log.insertAdjacentHTML('beforeend', `
        <div class="msg ${cls}">
            <div class="content">${escapeHtml(text)}</div>
        </div>
    `);
    scrollToBottom();
}

/** 渲染消息列表 */
function renderMessages(messages) {
    const log = document.getElementById('chat-log');
    log.innerHTML = '';

    const roleClassMap = {
        'user': 'msg-user',
        'MX1': 'msg-mx1',
        'MX2': 'msg-mx2',
        'MX3': 'msg-mx3',
        'MX0': 'msg-mx0',
    };

    const roleTagMap = {
        'MX1': '● 殚虑的宰相*主理模型',
        'MX2': '▲ 敏疑的御史*纠错模型',
        'MX3': '◆ 谏官发言中*发散模型',
        'MX0': '■ 入内都都知*总结模型',
    };

    messages.forEach(m => {
        const rt = m.role_type;
        const cls = roleClassMap[rt] || (m.role === 'user' ? 'msg-user' : 'msg-system');
        const tag = roleTagMap[rt] || (m.role === 'user' ? '▼ 用户' : '');

        log.insertAdjacentHTML('beforeend', `
            <div class="msg ${cls}">
                ${tag ? `<div class="role-tag">${tag}</div>` : ''}
                <div class="content">${escapeHtml(m.content).substring(0, 500)}</div>
            </div>
        `);
    });
    scrollToBottom();
}

// ===== 状态相关 =====

/** 加载引擎运行状态 */
async function loadStatus() {
    try {
        const resp = await fetch('/api/status');
        const data = await resp.json();
        updateEngineStatus(data.engine_status || 'idle');
        document.getElementById('current-round').textContent = data.current_round || 0;
    } catch (err) {
        console.error('获取状态失败:', err);
    }
}

/** 更新引擎状态显示 */
function updateEngineStatus(status) {
    const el = document.getElementById('engine-status');
    const map = {
        'idle': ['badge-idle', '空闲'],
        'running': ['badge-running', '运行中'],
        'error': ['badge-error', '错误'],
    };
    const [cls, text] = map[status] || map['idle'];
    el.className = 'badge ' + cls;
    el.textContent = text;
}

/** 更新角色状态 */
function updateRoleStatus(status) {
    const states = document.querySelectorAll('.role-state');
    const text = status === 'running' ? '运行中' : '空闲';
    states.forEach(el => el.textContent = text);
}

// ===== 语言切换 =====

async function switchLang(lang) {
    try {
        await fetch(`/api/lang/${lang}`, { method: 'POST' });
        currentLanguage = lang;
        location.reload();  // 刷新页面应用新语言
    } catch (err) {
        console.error('切换语言失败:', err);
    }
}

// ===== 设置 =====

function saveSettings() {
    // 保存API密钥（通过API接口）
    const keys = ['openai', 'anthropic', 'deepseek', 'google'];
    keys.forEach(k => {
        const val = document.getElementById(`api-${k}`).value.trim();
        if (val) {
            console.log(`保存 ${k} API密钥`);
            // 实际保存逻辑通过配置接口
        }
    });
    closeModal('modal-settings');
    addSystemMsg('设置已保存');
}

// ===== 工具函数 =====

/** HTML转义防XSS */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/** 显示弹窗 */
function showModal(id) {
    document.getElementById(id).style.display = 'flex';
}

/** 关闭弹窗 */
function closeModal(id) {
    document.getElementById(id).style.display = 'none';
}

/** 滚动聊天区到底部 */
function scrollToBottom() {
    const log = document.getElementById('chat-log');
    setTimeout(() => { log.scrollTop = log.scrollHeight; }, 50);
}
