# ecosystem/core/orchestrator.py
"""
任务编排器 - 复用 InterlockBus 实现任务分发

设计理念：
- 将 Hermes 的任务分发映射到 InterlockBus 事件
- 支持任务优先级和路由
"""

import json
import time
import hashlib
import logging
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass

logger = logging.getLogger("polis.orchestrator")

@dataclass
class Task:
    """任务定义"""
    task_id: str
    task_type: str
    payload: dict
    priority: int  # 0-10，越大越优先
    assigned_to: Optional[str]
    status: str  # pending, running, completed, failed
    created_at: float
    completed_at: Optional[float]

class Orchestrator:
    """
    任务编排器
    
    通过 InterlockBus 分发任务到合适的 Agent
    """
    
    def __init__(self, bus=None):
        self.bus = bus
        self._pending_tasks: List[Task] = []
        self._handlers: Dict[str, Callable] = {}
        self._stats = {"dispatched": 0, "completed": 0, "failed": 0}
    
    def register_handler(self, task_type: str, handler: Callable):
        """注册任务处理器"""
        self._handlers[task_type] = handler
        logger.info(f"Handler registered for task type: {task_type}")
    
    def dispatch(self, task: Dict) -> str:
        """
        分发任务
        
        Args:
            task: 任务字典，包含 type, payload, priority 等
        
        Returns:
            任务 ID
        """
        task_id = task.get("task_id") or hashlib.md5(
            f"{task}{time.time()}".encode()
        ).hexdigest()[:8]
        
        t = Task(
            task_id=task_id,
            task_type=task.get("type", "general"),
            payload=task.get("payload", {}),
            priority=task.get("priority", 5),
            assigned_to=task.get("assigned_to"),
            status="pending",
            created_at=time.time(),
            completed_at=None
        )
        
        # 添加到待处理队列
        self._pending_tasks.append(t)
        # 按优先级排序
        self._pending_tasks.sort(key=lambda x: -x.priority)
        
        # 如果有 InterlockBus，发送事件
        if self.bus:
            self.bus.emit("hermes", "task_dispatched", {
                "task_id": task_id,
                "task_type": t.task_type,
                "priority": t.priority
            })
        
        self._stats["dispatched"] += 1
        logger.debug(f"Task dispatched: {task_id} (type={t.task_type})")
        
        return task_id
    
    def process_next(self) -> Optional[Dict]:
        """处理下一个高优先级任务"""
        if not self._pending_tasks:
            return None
        
        task = self._pending_tasks.pop(0)
        task.status = "running"
        
        # 查找处理器
        handler = self._handlers.get(task.task_type)
        if handler:
            try:
                result = handler(task.payload)
                task.status = "completed"
                task.completed_at = time.time()
                self._stats["completed"] += 1
                return {"task_id": task.task_id, "status": "completed", "result": result}
            except Exception as e:
                task.status = "failed"
                task.completed_at = time.time()
                self._stats["failed"] += 1
                logger.error(f"Task {task.task_id} failed: {e}")
                return {"task_id": task.task_id, "status": "failed", "error": str(e)}
        else:
            # 无处理器，返回待分配
            return {"task_id": task.task_id, "status": "no_handler", "task": task.payload}
    
    def get_stats(self) -> Dict:
        """获取统计"""
        return {
            **self._stats,
            "pending": len(self._pending_tasks),
        }