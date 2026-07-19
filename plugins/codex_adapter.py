"""
Codex 适配器 - 接入 OpenAI Codex / GPT-4 等编码智能体

接入步骤:
1. 继承 AgentAdapter
2. 定义 name / capabilities
3. 实现 execute()
4. 放入 plugins/ 目录

自动被插件管理器发现并注册
"""

import logging
from typing import Dict

_log = logging.getLogger('plugins.codex')


class CodexAdapter:
    """
    Codex - 编码智能体
    
    能力: 代码生成、调试、测试、重构、文档
    触发: 城邦需要技术开发时
    """
    
    name = "codex"
    display_name = "Codex工程师"
    capabilities = ["code", "debug", "test", "refactor", "document", "deploy", "review_code"]
    
    def __init__(self, config=None):
        self.config = config or {}
        self.enabled = True
        self.total_calls = 0
        self.error_count = 0
        self.api_key = self.config.get('api_key', '')
    
    def execute(self, task: Dict, context: Dict) -> Dict:
        """执行编码任务"""
        self.total_calls += 1
        task_type = task.get('type', 'code')
        
        # 实际场景: 调用 OpenAI API 或本地 Codex 服务
        # response = openai.ChatCompletion.create(
        #     model="gpt-4",
        #     messages=[...]
        # )
        
        if task_type == 'code':
            return {
                "status": "ok",
                "result": {
                    "language": task.get('payload', {}).get('language', 'python'),
                    "code": "# 自动生成的代码\ndef solve():\n    pass",
                    "explanation": "Codex已生成解决方案"
                },
                "confidence": 0.9,
                "action": "submit_code",
                "message": "Codex完成了代码生成任务"
            }
        elif task_type == 'debug':
            return {
                "status": "ok",
                "result": {
                    "bugs_found": 3,
                    "fixes": ["修复1", "修复2", "修复3"],
                    "severity": "medium"
                },
                "confidence": 0.85,
                "action": "submit_fix",
                "message": "Codex发现并修复了3个Bug"
            }
        elif task_type == 'review_code':
            return {
                "status": "ok",
                "result": {
                    "score": 85,
                    "issues": ["缺少注释", "可优化循环"],
                    "suggestions": ["增加单元测试"]
                },
                "confidence": 0.8,
                "action": "review_complete",
                "message": "Codex完成了代码审查"
            }
        else:
            return {"status": "error", "message": f"Codex不支持任务类型: {task_type}"}
    
    def health_check(self) -> bool:
        return bool(self.api_key)
    
    def get_status(self) -> Dict:
        return {
            'name': self.name,
            'display_name': self.display_name,
            'capabilities': self.capabilities,
            'enabled': self.enabled,
            'total_calls': self.total_calls,
            'error_count': self.error_count
        }
