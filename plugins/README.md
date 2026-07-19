# plugins/ — 智能体插件目录

## 如何接入新智能体（3步）

### 第1步：创建适配器文件
在 `plugins/` 目录下创建 `xxx_adapter.py`:

```python
class MyAgentAdapter:
    name = "my_agent"              # 唯一ID
    display_name = "我的智能体"     # 显示名称
    capabilities = ["code", "debug"] # 能力列表
    
    def __init__(self, config=None):
        self.config = config or {}
        self.enabled = True
        self.total_calls = 0
        self.error_count = 0
    
    def execute(self, task, context):
        """
        核心方法 — 所有任务都通过这里执行
        
        task = {"task_id", "type", "title", "payload"}
        context = {"agents", "eco_state", "shared_db"}
        
        必须返回: {"status", "result", "confidence", "action", "message"}
        """
        # 调用你的智能体API
        result = call_my_agent_api(task)
        return {
            "status": "ok",
            "result": result,
            "confidence": 0.9,
            "action": "do_something",
            "message": "任务完成"
        }
    
    def health_check(self) -> bool:
        return True  # 检查API是否可用
    
    def get_status(self):
        return {
            'name': self.name,
            'display_name': self.display_name,
            'capabilities': self.capabilities,
            'enabled': self.enabled,
            'total_calls': self.total_calls,
            'error_count': self.error_count
        }
```

### 第2步：不需要改任何代码
插件管理器会自动发现 `plugins/*_adapter.py` 文件并注册。

### 第3步：验证
```python
from agent_adapter import get_adapter_registry
reg = get_adapter_registry()
reg.load_plugins('plugins')
print(reg.get_all_status())
```

## 已有插件

| 插件 | 能力 | 说明 |
|------|------|------|
| TRAE | analyze, plan, mediate, review, govern... | 城邦贤者 |
| Codex | code, debug, test, refactor, deploy... | 编码智能体 |
| Workbuddy | automate, data_process, api_call... | 工作流智能体 |

## 常见能力类型

```
analyze     — 分析状态
plan        — 制定规划
code        — 写代码
debug       — 调试
test        — 测试
automate    — 自动化
notify      — 通知
mediate     — 调解
review      — 审核
innovate    — 创新
oracle      — 问答
```
