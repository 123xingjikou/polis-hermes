from typing import Dict


class SubprocessCapability:
    """真实子进程执行（为安全，示例中限制）。"""

    ALLOWED_COMMANDS = {"echo", "date", "whoami", "pwd", "ls", "dir"}

    async def execute(self, context: Dict) -> Dict:
        import subprocess
        command = context.get("command", "echo hello")
        parts = command.strip().split()
        if not parts:
            return {"output": "", "status": "error", "message": "Empty command"}
        if parts[0] not in self.ALLOWED_COMMANDS:
            return {
                "output": "",
                "status": "denied",
                "message": f"Command '{parts[0]}' not in allowed list: {self.ALLOWED_COMMANDS}",
            }
        try:
            proc = subprocess.run(
                command, shell=True, capture_output=True, text=True, timeout=10
            )
            return {"output": proc.stdout, "returncode": proc.returncode, "status": "ok"}
        except Exception as e:
            return {"output": "", "status": "error", "message": str(e)}


class MockMCPCapability:
    """模拟 MCP 工具调用，真实集成时可替换。"""

    def __init__(self, registry: Dict[str, callable] = None):
        self._registry = registry or {}

    def register_tool(self, name: str, func: callable) -> None:
        self._registry[name] = func

    async def execute(self, context: Dict) -> Dict:
        tool_name = context.get("tool_name", "mock_tool")
        tool_args = context.get("args", {})
        if tool_name in self._registry:
            result = self._registry[tool_name](**tool_args)
            return {"result": result, "status": "ok"}
        return {
            "result": f"Executed {tool_name} with args {tool_args}",
            "status": "ok",
            "mock": True,
        }
