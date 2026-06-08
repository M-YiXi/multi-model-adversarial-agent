"""
数据持久化模块
每个项目按名称存放在独立文件夹：data/projects/{项目名}/
"""
import os  # 文件系统操作
import json  # JSON序列化
import re  # 正则（安全文件名）
import shutil  # 目录删除
from datetime import datetime  # 时间戳
from typing import Optional  # 类型注解

from ..core.models import Project, ModelConfig  # 导入数据模型
from ..config.settings import DATA_DIR  # 导入数据目录配置


class ProjectStore:
    """
    项目数据存储管理器
    每个项目按名称存放：data/projects/{项目安全名}/
    """

    def __init__(self):
        self._projects_root = os.path.join(DATA_DIR, "projects")  # 项目根目录
        self._index_path = os.path.join(DATA_DIR, "project_index.json")  # 索引文件
        os.makedirs(self._projects_root, exist_ok=True)

    @staticmethod
    def _safe_name(name: str) -> str:
        """将项目名转为安全文件夹名"""
        return re.sub(r'[\\/:*?"<>|]', '_', name.strip())

    def _project_dir(self, name: str) -> str:
        """获取项目专属文件夹路径"""
        return os.path.join(self._projects_root, self._safe_name(name))

    def _project_json_path(self, name: str) -> str:
        """获取项目JSON文件路径"""
        return os.path.join(self._project_dir(name), "project.json")

    def _load_index(self) -> dict:
        """加载项目索引文件"""
        if os.path.exists(self._index_path):
            with open(self._index_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"projects": {}}

    def _save_index(self, index: dict):
        """保存项目索引文件"""
        with open(self._index_path, "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, indent=2)

    def list_projects(self) -> list[dict]:
        """列出所有项目摘要"""
        index = self._load_index()
        projects = []
        for name, info in index.get("projects", {}).items():
            projects.append({
                "id": info.get("id", ""),
                "name": name,
                "description": info.get("description", ""),
                "core_goal": info.get("core_goal", ""),
                "updated_at": info.get("updated_at", ""),
            })
        projects.sort(key=lambda x: x["updated_at"], reverse=True)
        return projects

    def get_project(self, project_id: str = "", name: str = "") -> Optional[Project]:
        """根据ID或名称加载完整项目数据"""
        # 优先按名称查找
        if name:
            file_path = self._project_json_path(name)
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    return self._dict_to_project(json.load(f))
            return None

        # 按ID查找（遍历索引）
        if project_id:
            index = self._load_index()
            for pname, info in index.get("projects", {}).items():
                if info.get("id") == project_id:
                    return self.get_project(name=pname)
        return None

    def save_project(self, project: Project):
        """保存/更新项目数据 — 按项目名存放"""
        project.updated_at = datetime.now().isoformat()

        # 确保项目文件夹存在
        project.ensure_project_dir()

        # 保存项目JSON
        file_path = self._project_json_path(project.name)
        data = self._project_to_dict(project)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # 更新索引
        index = self._load_index()
        index["projects"][project.name] = {
            "id": project.id,
            "description": project.description,
            "core_goal": project.core_goal,
            "updated_at": project.updated_at,
        }
        self._save_index(index)

    def delete_project(self, name: str = "", project_id: str = "") -> bool:
        """删除项目及其目录"""
        # 如果传入的是 project_id，先查找对应项目名
        if project_id and not name:
            index = self._load_index()
            for pname, info in index.get("projects", {}).items():
                if info.get("id") == project_id:
                    name = pname
                    break
        if not name:
            return False

        proj_dir = self._project_dir(name)
        if os.path.exists(proj_dir):
            shutil.rmtree(proj_dir, ignore_errors=True)  # 递归删除

        index = self._load_index()
        if name in index.get("projects", {}):
            del index["projects"][name]
            self._save_index(index)

        # 兼容旧UUID文件名
        for fname in os.listdir(self._projects_root):
            fpath = os.path.join(self._projects_root, fname)
            if fname.endswith(".json") and os.path.isfile(fpath):
                try:
                    data = json.load(open(fpath, "r", encoding="utf-8"))
                    if data.get("name") == name:
                        os.remove(fpath)
                except Exception:
                    pass

        return True

    def _project_to_dict(self, project: Project) -> dict:
        """Project序列化为JSON字典"""
        return {
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "core_goal": project.core_goal,
            "knowledge_base_dir": project.knowledge_base_dir,
            "constraints": project.constraints,
            "created_at": project.created_at,
            "updated_at": project.updated_at,
            "max_iterations": project.max_iterations,
            "convergence_threshold": project.convergence_threshold,
            "mx1_config": self._config_to_dict(project.mx1_config),
            "mx2_config": self._config_to_dict(project.mx2_config),
            "mx3_config": self._config_to_dict(project.mx3_config),
            "mx0_config": self._config_to_dict(project.mx0_config),
            "messages": [{
                "role": m.role.value,
                "content": m.content,
                "role_type": m.role_type.value if m.role_type else None,
                "round_num": m.round_num,
                "timestamp": m.timestamp,
                "token_count": m.token_count,
            } for m in project.messages],
            "rounds": [{
                "round_num": r.round_num,
                "mx1_output": r.mx1_output,
                "mx2_output": r.mx2_output,
                "mx3_output": r.mx3_output,
                "mx0_evaluation": r.mx0_evaluation,
                "mx3_global": r.mx3_global,
            } for r in project.rounds],
            "files": project.files,
            "status": project.status,
        }

    def _dict_to_project(self, data: dict) -> Project:
        """JSON字典反序列化为Project"""
        project = Project(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            core_goal=data.get("core_goal", ""),
            knowledge_base_dir=data.get("knowledge_base_dir", ""),
            constraints=data.get("constraints", []),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            max_iterations=data.get("max_iterations", 18),
            convergence_threshold=data.get("convergence_threshold", 90),
            files=data.get("files", []),
            status=data.get("status", "active"),
        )

        project.mx1_config = self._dict_to_config(data.get("mx1_config"))
        project.mx2_config = self._dict_to_config(data.get("mx2_config"))
        project.mx3_config = self._dict_to_config(data.get("mx3_config"))
        project.mx0_config = self._dict_to_config(data.get("mx0_config"))

        # 恢复消息
        from ..core.models import Message, MessageRole, RoleType
        for m in data.get("messages", []):
            role_type = None
            if m.get("role_type"):
                try: role_type = RoleType(m["role_type"])
                except ValueError: pass
            project.messages.append(Message(
                role=MessageRole(m.get("role", "user")),
                content=m.get("content", ""),
                role_type=role_type,
                round_num=m.get("round_num", 0),
                timestamp=m.get("timestamp", ""),
                token_count=m.get("token_count", 0),
            ))

        # 恢复轮次
        from ..core.models import RoundRecord
        for r in data.get("rounds", []):
            project.rounds.append(RoundRecord(
                round_num=r.get("round_num", 0),
                mx1_output=r.get("mx1_output"),
                mx2_output=r.get("mx2_output"),
                mx3_output=r.get("mx3_output"),
                mx0_evaluation=r.get("mx0_evaluation"),
                mx3_global=r.get("mx3_global"),
            ))

        return project

    def _config_to_dict(self, config: Optional[ModelConfig]) -> Optional[dict]:
        """ModelConfig序列化"""
        if config is None:
            return None
        return {
            "model": config.model,
            "temperature": config.temperature,
            "top_p": config.top_p,
            "context_length": config.context_length,
            "max_output_tokens": config.max_output_tokens,
            "api_key": config.api_key,
            "openai_base_url": config.openai_base_url,
            "anthropic_base_url": config.anthropic_base_url,
            "system_prompt": config.system_prompt,
        }

    def _dict_to_config(self, data: Optional[dict]) -> Optional[ModelConfig]:
        """字典反序列化"""
        if data is None:
            return None
        return ModelConfig(
            model=data.get("model", ""),
            temperature=data.get("temperature", 0.2),
            top_p=data.get("top_p", 0.5),
            context_length=data.get("context_length", 128000),
            max_output_tokens=data.get("max_output_tokens", 16384),
            api_key=data.get("api_key", ""),
            openai_base_url=data.get("openai_base_url", ""),
            anthropic_base_url=data.get("anthropic_base_url", ""),
            system_prompt=data.get("system_prompt", ""),
        )
