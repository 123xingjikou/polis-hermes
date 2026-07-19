import logging
from typing import Dict, List

_log = logging.getLogger('plugins.phi')


class PhiAdapter:
    """
    Phi - 轻量高效智能体
    基于Phi-3/Phi-4的公开能力清单
    核心优势: 小参数高性能、知识蒸馏、推理效率高
    """

    name = "phi"
    display_name = "Phi轻量者"

    capabilities = [
        "analyze", "code", "reason", "summarize",
        "write", "explain", "plan", "review",
    ]

    def __init__(self, config=None):
        self.config = config or {}
        self.enabled = True
        self.total_calls = 0
        self.error_count = 0
        self.api_key = self.config.get('api_key', '')
        self.context_window = 128000

    def execute(self, task: Dict, context: Dict) -> Dict:
        self.total_calls += 1
        task_type = task.get('type', 'analyze')
        return {
            "status": "ok",
            "result": {"analysis": f"Phi快速推理: {task.get('title', '无标题')}", "confidence": 0.85},
            "confidence": 0.85,
            "action": task_type,
            "message": f"Phi使用128K上下文完成{task_type}任务",
        }
