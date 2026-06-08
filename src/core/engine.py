"""
对抗循环引擎 - 核心逻辑
MX1构建 → MX3发散 → MX2批判 → 每3轮MX0评估+全局发散
支持上下文阈值监控、token/s统计、压缩机制
"""
import os
import time
import asyncio
from typing import Optional, Callable

from .models import (
    Project, ModelConfig, Message, MessageRole,
    RoleType, EngineStatus, RoundRecord, AppState
)
from .api_client import ApiClient
from ..i18n.translator import t

# 角色显示名称映射
ROLE_DISPLAY = {
    "MX1": "殚虑的宰相*主理模型",
    "MX2": "敏疑的御史*纠错模型",
    "MX3": "谏官发言中*发散模型",
    "MX0": "入内都都知*总结模型",
}

ENCOURAGEMENT_PROMPT = """
【系统通知】表现非常出色！当前评估已达到或接近期望分数。
请继续保持此水平，精益求精，向最终收敛稳步推进。
"""

CONTEXT_WARNING_PROMPT = """
【系统警告】上下文窗口即将耗尽（已使用超过85%）。
请立即使用高保真压缩以下内容，保留所有关键结论、质疑点和修正点，压缩到原文的40%。
"""


class AdversarialEngine:
    """对抗循环引擎"""

    def __init__(self, state: AppState):
        self.state = state
        self._running = False
        self._on_message: Optional[Callable] = None
        self._on_status: Optional[Callable] = None
        self._on_think: Optional[Callable] = None
        # 各模型 token/s 统计
        self._token_stats = {
            "MX1": {"tokens": 0, "total_ms": 0},
            "MX2": {"tokens": 0, "total_ms": 0},
            "MX3": {"tokens": 0, "total_ms": 0},
            "MX0": {"tokens": 0, "total_ms": 0},
        }

    def set_callbacks(self, on_message=None, on_status=None, on_think=None):
        self._on_message = on_message
        self._on_status = on_status
        self._on_think = on_think

    def _notify_message(self, role, content, round_num):
        if self._on_message:
            self._on_message(role, content, round_num)

    def _notify_status(self, status, round_num):
        if self._on_status:
            self._on_status(status, round_num)

    def _think(self, text):
        if self._on_think:
            self._on_think(text)

    def _scan_knowledge_base(self, project):
        kb_dir = project.knowledge_base_dir
        if not kb_dir or not os.path.isdir(kb_dir):
            return ""
        lines = ["[知识库目录结构]\n"]
        try:
            for root, dirs, files in os.walk(kb_dir):
                level = root.replace(kb_dir, "").count(os.sep)
                indent = "  " * level
                folder_name = os.path.basename(root) or kb_dir
                lines.append(f"{indent}📁 {folder_name}/")
                for fn in sorted(files)[:50]:
                    lines.append(f"{indent}  📄 {fn}")
            return "\n".join(lines)
        except Exception:
            return ""

    def get_token_stats(self):
        """获取各模型 token/s 统计"""
        result = {}
        for role, stats in self._token_stats.items():
            total_tok = stats["tokens"]
            total_ms = stats["total_ms"]
            rate = (total_tok / (total_ms / 1000)) if total_ms > 0 else 0
            result[role] = {
                "total_tokens": total_tok,
                "avg_tokens_per_sec": round(rate, 1),
            }
        return result

    def _estimate_usage_pct(self, project, role_id):
        """估算某角色当前上下文的用量百分比"""
        config = getattr(project, f"{role_id.lower()}_config", None)
        if not config or config.context_length <= 0:
            return 0
        total_chars = sum(len(m.content) for m in project.messages)
        est_tokens = total_chars // 2  # 粗略估算：2 chars ≈ 1 token
        return min(100, int(est_tokens / config.context_length * 100))

    async def run_tests(self, project, on_thought=None):
        lines = []
        roles = [
            ("MX1", project.mx1_config,
             ROLE_DISPLAY["MX1"]),
            ("MX2", project.mx2_config,
             ROLE_DISPLAY["MX2"]),
            ("MX3", project.mx3_config,
             ROLE_DISPLAY["MX3"]),
            ("MX0", project.mx0_config,
             ROLE_DISPLAY["MX0"]),
        ]
        for role_id, config, display_name in roles:
            if on_thought:
                on_thought(f"正在测试 {display_name}")
            client = ApiClient(config)
            result = await client.test_connection()
            status = "✓ 连接正常" if result["ok"] else "✗ 连接失败"
            lines.append(
                f"[{display_name}]\n  模型: {config.model}\n"
                f"  状态: {status}\n  延迟: {result['latency']}ms"
            )
            if result.get("error"):
                lines.append(f"  错误: {result['error']}")
            await client.close()

        kb_dir = project.knowledge_base_dir
        if kb_dir:
            if on_thought:
                on_thought(f"正在检测知识库: {kb_dir}")
            if os.path.isdir(kb_dir):
                file_count = sum(len(files) for _, _, files in os.walk(kb_dir))
                lines.append(f"\n[知识库] {kb_dir}\n  状态: ✓ 载入成功 ({file_count}个文件)")
            else:
                lines.append(f"\n[知识库] {kb_dir}\n  状态: ✗ 目录不存在")
        else:
            lines.append("\n[知识库] 未配置")
        return "\n" + "\n".join(lines) + "\n"

    async def _call_role(self, role_id, config, messages, system_prompt):
        client = ApiClient(config)
        start = time.time()
        try:
            result = await client.call(messages, system_prompt)
            elapsed_ms = (time.time() - start) * 1000
            content = result.get("content", "[空响应]")
            tokens = result.get("tokens", 0)
            # 累计统计
            if role_id in self._token_stats:
                self._token_stats[role_id]["tokens"] += tokens
                self._token_stats[role_id]["total_ms"] += elapsed_ms
            # 思考链输出 token/s
            rate = (tokens / (elapsed_ms / 1000)) if elapsed_ms > 0 else 0
            self._think(
                f"[{role_id}] {config.model} "
                f"{tokens} tokens / {elapsed_ms:.0f}ms "
                f"({rate:.1f} tok/s)"
            )
            return content
        except Exception as e:
            return f"[{role_id}调用失败: {e}]"
        finally:
            await client.close()

    # ===== MX1 构建 =====
    async def _run_mx1(self, project, round_num,
                       mx2_previous=None, mx3_previous=None,
                       mx0_feedback=None):
        msgs = []
        goal_text = f"核心问题锚点（不可偏离）：{project.core_goal}"
        msgs.append(Message(role=MessageRole.SYSTEM, content=goal_text,
                            round_num=round_num))
        kb_content = self._scan_knowledge_base(project)
        if kb_content:
            msgs.append(Message(role=MessageRole.SYSTEM,
                                content=f"项目参考知识库：\n{kb_content}",
                                round_num=round_num))
        if mx0_feedback:
            msgs.append(Message(role=MessageRole.SYSTEM,
                                content=mx0_feedback, round_num=round_num))
        for msg in project.messages[-20:]:
            msgs.append(msg)
        if mx2_previous:
            msgs.append(Message(role=MessageRole.USER,
                                content=f"[上一轮MX2完整批判]\n{mx2_previous}",
                                round_num=round_num))
        if mx3_previous:
            msgs.append(Message(role=MessageRole.USER,
                                content=f"[MX3发散思维层]\n{mx3_previous}",
                                round_num=round_num))
        msgs.append(Message(
            role=MessageRole.USER,
            content=f"当前第{round_num}轮，请输出修正后的完整方案。\n"
                    f"强制要求：1.所有结论附带推理步骤 "
                    f"2.逐条回应上一轮MX2的全部质疑 "
                    f"3.表达务必简练精炼",
            round_num=round_num))
        prompt = (project.mx1_config.get_system_prompt("MX1")
                  if project.mx1_config else "")
        return await self._call_role("MX1", project.mx1_config, msgs, prompt)

    # ===== MX3 发散 =====
    async def _run_mx3(self, project, round_num, mx1_output):
        from ..config.settings import settings
        div_count = settings.engine_defaults.get("mx3_divergence_count", 10)
        if isinstance(div_count, float):
            div_count = 10
        msgs = [
            Message(role=MessageRole.SYSTEM,
                    content=f"核心问题：{project.core_goal}",
                    round_num=round_num),
            Message(role=MessageRole.USER,
                    content=f"[MX1方案]\n{mx1_output}\n\n"
                            f"从正反两方面同时发散，至少{div_count}条，每行一条：\n"
                            f"正向：扩展/优化/新应用\n反向：风险/替代路径/反向思考\n"
                            f"不考虑逻辑、可行性、道德成本。",
                    round_num=round_num),
        ]
        prompt = (project.mx3_config.get_system_prompt("MX3")
                  if project.mx3_config else "")
        return await self._call_role("MX3", project.mx3_config, msgs, prompt)

    # ===== MX2 批判 =====
    async def _run_mx2(self, project, round_num, mx1_output, mx3_output):
        msgs = [
            Message(role=MessageRole.SYSTEM,
                    content=f"核心问题：{project.core_goal}",
                    round_num=round_num),
            Message(role=MessageRole.USER,
                    content=f"[MX1方案]\n{mx1_output}\n\n"
                            f"[MX3发散列表（正反双向）]\n{mx3_output}\n\n"
                            f"逐条评估发散点（认同/不解/否认），"
                            f"找出漏洞并给出回应清单，表达简要直击要害。",
                    round_num=round_num),
        ]
        prompt = (project.mx2_config.get_system_prompt("MX2")
                  if project.mx2_config else "")
        return await self._call_role("MX2", project.mx2_config, msgs, prompt)

    # ===== MX0 评估（每3轮）— 上下文阈值监控 + 高保真压缩 =====
    async def _run_mx0_evaluation(self, project, round_num):
        usage_pct = self._estimate_usage_pct(project, "MX0")
        self._think(f"[MX0] 上下文用量: {usage_pct}%")

        # 接近阈值时弹警告
        if usage_pct >= 85:
            self._think(f"[MX0] ⚠ 上下文占用 {usage_pct}%，触发高保真压缩")
            self._notify_message(RoleType.MX0,
                                 f"[系统] ⚠ MX0上下文已达{usage_pct}%，启用压缩",
                                 round_num)

        # 构建摘要：根据用量决定是否压缩
        all_msgs = project.messages
        if usage_pct >= 85:
            # 高保真压缩：保留最新轮次完整 + 历史压缩
            summary_lines = []
            cutoff = max(0, len(all_msgs) - 15)
            for m in all_msgs[:cutoff]:
                tag = (f"[{m.role.value}]"
                       + (f"({m.role_type.value})" if m.role_type else ""))
                # 压缩到 200 字符
                summary_lines.append(f"{tag} {m.content[:200]}")
            for m in all_msgs[cutoff:]:
                tag = (f"[{m.role.value}]"
                       + (f"({m.role_type.value})" if m.role_type else ""))
                summary_lines.append(f"{tag} {m.content[:800]}")
            summary = "\n".join(summary_lines)
        else:
            summary_lines = []
            for m in all_msgs:
                tag = (f"[{m.role.value}]"
                       + (f"({m.role_type.value})" if m.role_type else ""))
                summary_lines.append(f"{tag} {m.content[:800]}")
            summary = "\n".join(summary_lines)

        msgs = [
            Message(role=MessageRole.SYSTEM,
                    content=f"核心问题：{project.core_goal}\n"
                            f"当前轮次：{round_num}\n"
                            f"期望分数：{project.convergence_threshold}分\n"
                            + (f"上下文已压缩（原用量{usage_pct}%）。"
                               if usage_pct >= 85 else ""),
                    round_num=round_num),
            Message(role=MessageRole.USER,
                    content=f"请评估以下对话质量（0~100分）：\n{summary}",
                    round_num=round_num),
        ]
        prompt = (project.mx0_config.get_system_prompt("MX0")
                  if project.mx0_config else "")
        result = await self._call_role("MX0", project.mx0_config, msgs, prompt)
        score = 50
        try:
            import re
            match = re.search(r'(\d+)\s*分|评分[：:]\s*(\d+)',
                              result, re.IGNORECASE)
            if match:
                score = int(match.group(1) or match.group(2))
        except Exception:
            pass
        return {"score": min(max(score, 0), 100), "evaluation": result}

    # ===== MX3 全局发散（每3轮）=====
    async def _run_mx3_global(self, project, round_num):
        context_parts = []
        for r in reversed(project.rounds[-5:]):
            if r.mx1_output:
                context_parts.append(
                    f"[MX1第{r.round_num}轮] {r.mx1_output[:600]}")
                break
        for r in reversed(project.rounds[-5:]):
            if r.mx2_output:
                context_parts.append(
                    f"[MX2第{r.round_num}轮批判要点] {r.mx2_output[:600]}")
                break
        context_text = "\n".join(context_parts) if context_parts else "（无历史）"
        msgs = [
            Message(role=MessageRole.SYSTEM,
                    content=f"核心问题：{project.core_goal}",
                    round_num=round_num),
            Message(role=MessageRole.USER,
                    content=f"以下是当前对抗的最新全局上下文：\n{context_text}\n\n"
                            f"忽略所有历史细节，生成全新的发散列表，按类别分类：\n"
                            f"1.[技术路线] 2.[风险反例] 3.[跨界联想] 4.[极端假设]\n"
                            f"每类至少3条，每条一行，简练表达。",
                    round_num=round_num),
        ]
        prompt = (project.mx3_config.get_system_prompt("MX3")
                  if project.mx3_config else "")
        return await self._call_role("MX3", project.mx3_config, msgs, prompt)

    # ===== 单轮执行 =====
    async def run_round(self, project):
        round_num = len(project.rounds) + 1
        self.state.current_round = round_num
        record = RoundRecord(round_num=round_num)

        mx2_prev = None; mx3_prev = None
        if project.rounds:
            mx2_prev = project.rounds[-1].mx2_output
            mx3_prev = project.rounds[-1].mx3_output

        mx0_feedback = None
        prev_round = project.rounds[-1] if project.rounds else None
        if (prev_round and prev_round.mx0_evaluation
                and prev_round.mx0_evaluation["score"]
                < project.convergence_threshold):
            mx0_feedback = (
                f"[MX0评估反馈] 上轮质量评分 "
                f"{prev_round.mx0_evaluation['score']}分，"
                f"未达到期望{project.convergence_threshold}分。\n"
                f"改进方向：{prev_round.mx0_evaluation['evaluation'][:500]}"
            )

        self._notify_status("MX1:running", round_num)
        record.mx1_output = await self._run_mx1(
            project, round_num, mx2_previous=mx2_prev,
            mx3_previous=mx3_prev, mx0_feedback=mx0_feedback)
        self._notify_message(RoleType.MX1, record.mx1_output, round_num)
        self._notify_status("MX1:idle", round_num)

        self._notify_status("MX3:running", round_num)
        record.mx3_output = await self._run_mx3(
            project, round_num, record.mx1_output)
        self._notify_message(RoleType.MX3, record.mx3_output, round_num)
        self._notify_status("MX3:idle", round_num)

        self._notify_status("MX2:running", round_num)
        record.mx2_output = await self._run_mx2(
            project, round_num, record.mx1_output, record.mx3_output)
        self._notify_message(RoleType.MX2, record.mx2_output, round_num)
        self._notify_status("MX2:idle", round_num)

        if round_num % 3 == 0:
            self._notify_status("MX0:running", round_num)
            record.mx0_evaluation = await self._run_mx0_evaluation(
                project, round_num)
            score = record.mx0_evaluation["score"]
            eval_text = record.mx0_evaluation["evaluation"]
            if score >= project.convergence_threshold:
                msg = (f"[质量评分: {score}分 ✓ 已达标]\n{eval_text}\n"
                       f"{ENCOURAGEMENT_PROMPT}")
            else:
                msg = (f"[质量评分: {score}分 ✗ 未达标]\n{eval_text}\n"
                       f"低分原因将反馈给MX1供下轮改进。")
            self._notify_message(RoleType.MX0, msg, round_num)
            self._notify_status("MX0:idle", round_num)

        if round_num % 3 == 0:
            self._notify_status("MX3:running", round_num)
            record.mx3_global = await self._run_mx3_global(project, round_num)
            self._notify_message(RoleType.MX3,
                                 f"[全局分类发散]\n{record.mx3_global}",
                                 round_num)
            self._notify_status("MX3:idle", round_num)

        project.rounds.append(record)
        return record

    async def run_full_cycle(self, project):
        self._running = True
        self.state.engine_status = EngineStatus.RUNNING
        consecutive_high_scores = 0
        while self._running:
            rn = len(project.rounds) + 1
            if rn > project.max_iterations:
                self._notify_status("max_rounds", rn); break
            record = await self.run_round(project)
            if record.mx0_evaluation:
                s = record.mx0_evaluation["score"]
                if s >= project.convergence_threshold:
                    consecutive_high_scores += 1
                else:
                    consecutive_high_scores = 0
                if consecutive_high_scores >= 3:
                    self.state.engine_status = EngineStatus.FINISHED
                    self._notify_status("converged", rn); break
            if record.mx2_output and "无进一步质疑" in record.mx2_output:
                self.state.engine_status = EngineStatus.FINISHED
                self._notify_status("converged", rn); break
        self._running = False
        if self.state.engine_status != EngineStatus.FINISHED:
            self.state.engine_status = EngineStatus.FINISHED
        final_eval = await self._run_mx0_evaluation(project, len(project.rounds))
        return self._generate_final_report(project, final_eval)

    def _generate_final_report(self, project, final_eval):
        lines = [
            "=" * 60,
            "多模三维对抗思维引擎 — 最终报告",
            "=" * 60,
            f"项目名称：{project.name}",
            f"核心问题：{project.core_goal}",
            f"总迭代轮次：{len(project.rounds)}",
            f"最终质量评分：{final_eval.get('score', 'N/A')}分",
            "", "--- 最终评估 ---",
            final_eval.get('evaluation', ''),
            "", "--- 对抗历程摘要 ---",
        ]
        for r in project.rounds[-5:]:
            lines.append(f"\n第{r.round_num}轮：")
            if r.mx1_output: lines.append(f"  MX1: {r.mx1_output[:200]}...")
            if r.mx2_output: lines.append(f"  MX2: {r.mx2_output[:200]}...")
            if r.mx0_evaluation: lines.append(f"  MX0评分: {r.mx0_evaluation['score']}分")
        return "\n".join(lines)

    def stop(self):
        self._running = False
        self.state.engine_status = EngineStatus.IDLE
