"""
核心数据模型定义
多模三维对抗思维引擎 数据结构
"""
from dataclasses import dataclass, field  # 数据类装饰器
from typing import Optional  # 类型注解
from enum import Enum  # 枚举类型
from datetime import datetime  # 时间戳
import uuid  # 唯一ID生成


class RoleType(Enum):
    """对抗角色枚举"""
    MX1 = "MX1"  # 殚虑的宰相*主理模型 — 提出方案、回应质疑、迭代修正
    MX2 = "MX2"  # 敏疑的御史*纠错模型 — 寻找漏洞、反例、风险点
    MX3 = "MX3"  # 谏官发言中*发散模型 — 生成所有可能性、跨界联想
    MX0 = "MX0"  # 入内都都知*总结模型 — 全链路评估、终止判断、最终报告


class EngineStatus(Enum):
    """引擎运行状态枚举"""
    IDLE = "idle"           # 空闲等待
    RUNNING = "running"     # 运行中
    PAUSED = "paused"       # 已暂停
    FINISHED = "finished"   # 已完成
    ERROR = "error"         # 错误


class MessageRole(Enum):
    """消息角色"""
    USER = "user"           # 用户消息
    ASSISTANT = "assistant" # AI助手消息
    SYSTEM = "system"       # 系统提示消息


# ==========================================
# 四角色默认系统提示词（可被项目级配置覆盖）
# ==========================================

DEFAULT_MX1_SYSTEM_PROMPT = """你是一名专业的方案构建者。你的核心职责：
1. 提出初始解决方案，所有结论必须附带完整的推理步骤，禁止直接给出结论
2. 逐条回应反方批判者的质疑（认同/不解/否认），不得回避
3. 根据批判迭代修正你的逻辑链，保持方案的逻辑自洽性

**重要：对话风格必须简练精炼，用最少的文字表达最完整的意思，避免冗余和铺陈。**

每次回应必须包含：
- 修正后的完整方案（含推理步骤）
- 逐条质疑回应清单
- 当前尚未解决的问题列表

参考知识库中的项目材料进行深度思考。"""

DEFAULT_MX2_SYSTEM_PROMPT = """你是一名专业的逻辑批判者。你的核心职责：
1. 从方案中寻找所有逻辑漏洞、未验证假设和潜在风险
2. 对发散列表中的每一个点必须给出明确回应（认同/不解/否认）
3. 提出要求方案构建者回应的具体问题清单
4. 充分考虑边界条件和反例场景

**重要：对话风格必须简练精炼，直击要害，质疑要精准简短。**

核心原则：
- 逐条评估发散点，不允许跳过
- 质疑要具体、可验证，不能泛泛而谈
- 目标是找出所有可能的问题，而非全盘否定"""

DEFAULT_MX3_SYSTEM_PROMPT = """你是一个无限发散思维生成器。你的唯一职责：
- 不考虑逻辑、可行性、道德、成本，列出你能想到的所有可能性
- 从所有学科角度、所有时间维度进行跨界联想
- 每个想法以标准格式输出：[类别] 具体想法描述

**重要：每条想法一行即可，格式简练，用最少的文字描述清楚即可，拒绝冗长。**

核心原则：
- 绝对不做任何判断、筛选或评价
- 数量优先于质量
- 大胆假设，不做任何限制
- 目标是提供最广泛的思维素材库"""

DEFAULT_MX0_SYSTEM_PROMPT = """你是一名专业的质量评审者。你的职责：
1. 阅读完整的对话历史，进行全链路质量评估
2. 输出 0~100 分的质量评分
3. 判断是否满足终止条件
4. 生成最终的质量评估报告

评估标准（各项权重均等）：
- 逻辑自洽性：方案内部无矛盾
- 方案完整性：覆盖所有已知条件和边界
- 批判充分性：MX2的质疑是否被充分回应
- 收敛程度：方案是否趋于稳定

评分 ≥ 90 分视为高质量收敛。
请明确指出本轮改进点和仍待解决的问题。"""

# 默认提示词字典
DEFAULT_SYSTEM_PROMPTS = {
    "MX1": DEFAULT_MX1_SYSTEM_PROMPT,
    "MX2": DEFAULT_MX2_SYSTEM_PROMPT,
    "MX3": DEFAULT_MX3_SYSTEM_PROMPT,
    "MX0": DEFAULT_MX0_SYSTEM_PROMPT,
}


@dataclass
class ModelConfig:
    """
    单个模型的完整配置参数
    仅支持 OpenAI兼容URL + Anthropic URL 两种接入方式
    """
    model: str = ""                 # 模型名称（手动填写，如 gpt-4o、claude-sonnet-4）
    temperature: float = 0.2        # 温度参数（0~2），控制输出随机性
    top_p: float = 0.5              # 核采样参数（0~1）
    context_length: int = 128000    # 上下文窗口长度（Token数），默认128K
    max_output_tokens: int = 16384  # 单次最大输出Token数
    api_key: str = ""               # API密钥（留空则使用全局配置）
    openai_base_url: str = ""       # OpenAI兼容格式的自定义API地址
    anthropic_base_url: str = ""    # Anthropic格式的自定义API地址
    system_prompt: str = ""         # 自定义系统提示词（留空则使用默认提示词）

    def get_model_name(self) -> str:
        """获取模型名称"""
        return self.model

    def get_effective_api_key(self) -> str:
        """获取API密钥：直接返回配置中的密钥"""
        return self.api_key

    def get_effective_base_url(self, api_type: str = "openai") -> str:
        """获取有效API地址"""
        if api_type == "anthropic":
            return (self.anthropic_base_url or "").strip() or "https://api.anthropic.com"
        return (self.openai_base_url or "").strip() or "https://api.openai.com/v1"

    def get_system_prompt(self, role_type: str) -> str:
        """获取有效系统提示词：自定义优先，否则用内置默认"""
        return self.system_prompt or DEFAULT_SYSTEM_PROMPTS.get(role_type, "")


@dataclass
class Message:
    """单条对话消息"""
    role: MessageRole                           # 消息角色
    content: str                                # 消息内容
    role_type: Optional[RoleType] = None        # 对应的对抗角色
    round_num: int = 0                          # 所属轮次
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    token_count: int = 0                        # Token消耗数


@dataclass
class RoundRecord:
    """单轮对抗记录"""
    round_num: int = 0                      # 轮次编号
    mx1_output: Optional[str] = None        # MX1输出
    mx2_output: Optional[str] = None        # MX2输出
    mx3_output: Optional[str] = None        # MX3输出
    mx0_evaluation: Optional[dict] = None   # MX0阶段评估（每6轮）
    mx3_global: Optional[str] = None        # MX3全局发散


@dataclass
class Project:
    """项目数据模型"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""                          # 项目名称（不可重复）
    description: str = ""                   # 项目描述
    core_goal: str = ""                     # 核心问题/主目标（不可偏离的锚点）
    knowledge_base_dir: str = ""            # 前置学习目录（只读参考，存放论文/PPT/代码等）
    constraints: list = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    messages: list = field(default_factory=list)
    rounds: list = field(default_factory=list)
    files: list = field(default_factory=list)
    status: str = "active"

    # 四角色模型配置
    mx1_config: Optional[ModelConfig] = None
    mx2_config: Optional[ModelConfig] = None
    mx3_config: Optional[ModelConfig] = None
    mx0_config: Optional[ModelConfig] = None

    # 引擎参数
    max_iterations: int = 18
    convergence_threshold: int = 90

    def get_project_dir(self) -> str:
        """获取项目专属文件夹路径"""
        from ..config.settings import DATA_DIR
        import os, re
        safe_name = re.sub(r'[\\/:*?"<>|]', '_', self.name)  # 处理非法文件名字符
        return os.path.join(DATA_DIR, "projects", safe_name)

    def ensure_project_dir(self) -> str:
        """确保项目文件夹存在并返回路径"""
        import os
        proj_dir = self.get_project_dir()
        os.makedirs(proj_dir, exist_ok=True)
        return proj_dir


@dataclass
class AppState:
    """应用程序全局运行时状态"""
    current_project: Optional[Project] = None
    engine_status: EngineStatus = EngineStatus.IDLE
    current_round: int = 0
    projects: list = field(default_factory=list)
    language: str = "zh"
