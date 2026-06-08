"""
Web后端服务 - FastAPI
提供REST API接口供前端调用
支持项目管理、引擎控制、对话交互
"""
import os
import sys
import json

# 路径处理
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from fastapi import FastAPI, HTTPException  # FastAPI框架
from fastapi.staticfiles import StaticFiles  # 静态文件服务
from fastapi.responses import HTMLResponse  # HTML响应
from pydantic import BaseModel  # 数据验证
from typing import Optional  # 类型注解

from ..core.models import AppState, Project, ModelConfig, EngineStatus
from ..storage.store import ProjectStore
from ..i18n.translator import t, set_language

# 创建FastAPI应用
app = FastAPI(title="多模三维对抗思维引擎 API",
              description="Multi-Model 3D Adversarial Thinking Engine Web API",
              version="1.0.0")

# 全局状态
state = AppState()
store = ProjectStore()

# 静态文件目录（前端HTML/CSS/JS）
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
os.makedirs(static_dir, exist_ok=True)


# ========== Pydantic请求模型 ==========

class CreateProjectRequest(BaseModel):
    """创建项目请求体"""
    name: str
    description: str = ""
    core_goal: str = ""
    max_iterations: int = 18
    convergence_threshold: int = 90


class MessageRequest(BaseModel):
    """发送消息请求体"""
    project_id: str
    content: str


class ConfigRoleRequest(BaseModel):
    """角色配置请求体"""
    provider: str
    model: str
    temperature: float = 0.2
    top_p: float = 0.5
    api_key: str = ""


# ========== API路由 ==========

@app.get("/")
async def root():
    """根路径返回前端页面"""  # 加载index.html
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    return HTMLResponse("<h1>三维对抗引擎 API 运行中</h1>")


@app.get("/api/health")
async def health_check():
    """健康检查接口"""  # 确认服务正常
    return {"status": "ok", "service": "三维对抗引擎"}


@app.get("/api/projects")
async def list_projects():
    """获取所有项目列表"""  # 返回项目摘要
    projects = store.list_projects()
    return {"projects": projects}


@app.post("/api/projects")
async def create_project(req: CreateProjectRequest):
    """创建新项目"""  # 保存到存储
    project = Project(
        name=req.name,
        description=req.description,
        core_goal=req.core_goal,
        max_iterations=req.max_iterations,
        convergence_threshold=req.convergence_threshold,
    )
    store.save_project(project)
    return {"id": project.id, "name": project.name, "message": "项目创建成功"}


@app.get("/api/projects/{project_id}")
async def get_project(project_id: str):
    """获取项目详情"""  # 加载完整项目数据
    project = store.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    return {
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "core_goal": project.core_goal,
        "rounds": len(project.rounds),
        "status": project.status,
    }


@app.delete("/api/projects/{project_id}")
async def delete_project(project_id: str):
    """删除项目"""  # 从存储中移除
    success = store.delete_project(project_id=project_id)
    if not success:
        raise HTTPException(status_code=404, detail="项目不存在")
    return {"message": "项目已删除"}


@app.get("/api/projects/{project_id}/messages")
async def get_messages(project_id: str):
    """获取项目对话消息"""  # 返回消息列表
    project = store.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    messages = [{
        "role": m.role.value,
        "role_type": m.role_type.value if m.role_type else None,
        "content": m.content[:500],  # 截断长内容
        "round_num": m.round_num,
        "timestamp": m.timestamp,
    } for m in project.messages[-50:]]
    return {"messages": messages}


@app.get("/api/status")
async def get_status():
    """获取引擎状态"""  # 返回运行状态
    return {
        "engine_status": state.engine_status.value,
        "current_round": state.current_round,
        "current_project": state.current_project.name if state.current_project else None,
        "language": state.language,
    }


@app.post("/api/lang/{lang}")
async def switch_language(lang: str):
    """切换语言"""  # zh/en
    if lang not in ("zh", "en"):
        raise HTTPException(status_code=400, detail="语言代码无效，仅支持 zh/en")
    set_language(lang)
    state.language = lang
    return {"message": t("lang_switched"), "language": lang}


# 挂载静态文件目录（必须在所有路由之后）
app.mount("/static", StaticFiles(directory=static_dir), name="static")
