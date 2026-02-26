"""
Tool Registry - Phase 4A
Central registry for all available tools with metadata
No execution - registration and validation only
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from lyra.core.logger import get_logger


@dataclass
class ToolParameter:
    """Parameter definition for a tool"""
    name: str
    type: str  # string, int, bool, path, etc.
    required: bool
    default: Any
    validation_pattern: Optional[str]  # Regex for validation
    description: str


@dataclass
class ToolDefinition:
    """Complete tool definition with metadata (Phase 3 Hardened, Phase 5 Version Pinned)"""
    name: str
    description: str
    action_type: str  # Category: file, command, network, etc.
    risk_category: str  # LOW, MEDIUM, HIGH, CRITICAL
    permission_level_required: str  # LOW, MEDIUM, HIGH
    reversible: bool
    idempotent: bool # Phase 3: Can tool be retried safely?
    parameters: List[ToolParameter]
    input_schema: Dict[str, Any] # Phase 3: Formal input schema
    output_schema: Dict[str, Any] # Phase 3: Formal output schema
    requires_confirmation: bool
    max_execution_time: float  # seconds
    enabled: bool
    version: str = "1.0.0"  # Phase 5: Tool version pinning
    sha256: str = ""  # Phase 5: Tool identity hash (computed at registration)


class ToolRegistry:
    """
    Central registry for all available tools
    Manages tool registration, validation, and metadata
    """
    
    def __init__(self, registry_path: Optional[str] = None):
        self.logger = get_logger(__name__)
        
        if registry_path is None:
            project_root = Path(__file__).parent.parent.parent
            registry_path = str(project_root / "data" / "tool_registry.json")
        
        self.registry_path = registry_path
        Path(registry_path).parent.mkdir(parents=True, exist_ok=True)
        
        self.tools: Dict[str, ToolDefinition] = {}
        self._load_registry()
        self._register_builtin_tools()
        
        self.logger.info(f"Tool registry initialized with {len(self.tools)} tools")
    
    def _load_registry(self):
        """Load registry from disk"""
        try:
            if Path(self.registry_path).exists():
                with open(self.registry_path, 'r') as f:
                    data = json.load(f)
                    for tool_data in data.get("tools", []):
                        try:
                            # Convert parameters
                            params = [
                                ToolParameter(**p) for p in tool_data.get("parameters", [])
                            ]
                            tool_data["parameters"] = params
                            # Ensure Phase 5 defaults for backward compatibility
                            tool_data.setdefault("version", "1.0.0")
                            tool_data.setdefault("sha256", "")
                            tool_data.setdefault("idempotent", False)
                            tool_data.setdefault("input_schema", {})
                            tool_data.setdefault("output_schema", {})
                            tool = ToolDefinition(**tool_data)
                            self.tools[tool.name] = tool
                        except Exception as te:
                            self.logger.warning(f"Skipping malformed tool entry: {te}")
                self.logger.info(f"Loaded {len(self.tools)} tools from registry")
        except Exception as e:
            self.logger.error(f"Failed to load registry: {e}")
    
    def _save_registry(self):
        """Save registry to disk"""
        try:
            data = {
                "tools": [
                    {
                        **asdict(tool),
                        "parameters": [asdict(p) for p in tool.parameters]
                    }
                    for tool in self.tools.values()
                ]
            }
            with open(self.registry_path, 'w') as f:
                json.dump(data, f, indent=2)
            self.logger.debug("Registry saved")
        except Exception as e:
            self.logger.error(f"Failed to save registry: {e}")
    
    def _register_builtin_tools(self):
        """Register built-in tools (Phase 4B: file + app launcher)"""
        
        # File read tool (LOW risk)
        read_file = ToolDefinition(
            name="read_file",
            description="Read contents of a file",
            action_type="file",
            risk_category="LOW",
            permission_level_required="LOW",
            reversible=True,
            idempotent=True,
            parameters=[
                ToolParameter(
                    name="path",
                    type="path",
                    required=True,
                    default=None,
                    validation_pattern=r"^[a-zA-Z0-9_/\.\-]+$",
                    description="Path to file"
                )
            ],
            input_schema={"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
            output_schema={"type": "object", "properties": {"content": {"type": "string"}}},
            requires_confirmation=False,
            max_execution_time=5.0,
            enabled=True
        )
        self.register_tool(read_file)
        
        # File write tool (MEDIUM risk)
        write_file = ToolDefinition(
            name="write_file",
            description="Write contents to a file",
            action_type="file",
            risk_category="MEDIUM",
            permission_level_required="MEDIUM",
            reversible=False,
            idempotent=True, # Overwriting same content is idempotent
            parameters=[
                ToolParameter(
                    name="path",
                    type="path",
                    required=True,
                    default=None,
                    validation_pattern=r"^[a-zA-Z0-9_/\.\-]+$",
                    description="Path to file"
                ),
                ToolParameter(
                    name="content",
                    type="string",
                    required=True,
                    default=None,
                    validation_pattern=None,
                    description="Content to write"
                )
            ],
            input_schema={"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]},
            output_schema={"type": "object", "properties": {"status": {"type": "string"}}},
            requires_confirmation=True,
            max_execution_time=10.0,
            enabled=True
        )
        self.register_tool(write_file)
        
        # File delete tool (HIGH risk)
        delete_file = ToolDefinition(
            name="delete_file",
            description="Delete a file",
            action_type="file",
            risk_category="HIGH",
            permission_level_required="HIGH",
            reversible=False,
            idempotent=False,
            parameters=[
                ToolParameter(
                    name="path",
                    type="path",
                    required=True,
                    default=None,
                    validation_pattern=r"^[a-zA-Z0-9_/\.\-]+$",
                    description="Path to file"
                )
            ],
            input_schema={"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
            output_schema={"type": "object", "properties": {"status": {"type": "string"}}},
            requires_confirmation=True,
            max_execution_time=5.0,
            enabled=False  # Disabled - not implemented yet
        )
        self.register_tool(delete_file)
        
        # Command run tool (HIGH risk)
        run_command = ToolDefinition(
            name="run_command",
            description="Execute a system command",
            action_type="command",
            risk_category="HIGH",
            permission_level_required="HIGH",
            reversible=False,
            idempotent=False, # Commands generally not idempotent
            parameters=[
                ToolParameter(
                    name="command",
                    type="string",
                    required=True,
                    default=None,
                    validation_pattern=None,
                    description="Command to execute"
                )
            ],
            input_schema={"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]},
            output_schema={"type": "object", "properties": {"stdout": {"type": "string"}, "stderr": {"type": "string"}, "exit_code": {"type": "integer"}}},
            requires_confirmation=True,
            max_execution_time=30.0,
            enabled=False  # Disabled by default for safety
        )
        self.register_tool(run_command)
        
        # System info tool (LOW risk)
        get_system_info = ToolDefinition(
            name="get_system_info",
            description="Get system information",
            action_type="system",
            risk_category="LOW",
            permission_level_required="LOW",
            reversible=True,  # N/A for read
            idempotent=True,
            parameters=[],
            input_schema={"type": "object", "properties": {}},
            output_schema={"type": "object", "properties": {"os": {"type": "string"}, "hostname": {"type": "string"}}},
            requires_confirmation=False,
            max_execution_time=2.0,
            enabled=True
        )
        self.register_tool(get_system_info)
        
        # Open URL tool (LOW risk) - Phase 4B Step 2
        open_url = ToolDefinition(
            name="open_url",
            description="Open URL in default browser",
            action_type="app_launcher",
            risk_category="LOW",
            permission_level_required="LOW",
            reversible=True,  # Can close browser
            idempotent=True,
            parameters=[
                ToolParameter(
                    name="url",
                    type="string",
                    required=True,
                    default=None,
                    validation_pattern=r"^https?://",
                    description="URL to open"
                )
            ],
            input_schema={"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]},
            output_schema={"type": "object", "properties": {"status": {"type": "string"}}},
            requires_confirmation=False,
            max_execution_time=3.0,
            enabled=True
        )
        self.register_tool(open_url)
        
        # Launch app tool (MEDIUM risk) - Phase 4B Step 2
        launch_app = ToolDefinition(
            name="launch_app",
            description="Launch application from allowlist",
            action_type="app_launcher",
            risk_category="MEDIUM",
            permission_level_required="MEDIUM",
            reversible=True,  # Can close app
            idempotent=True,
            parameters=[
                ToolParameter(
                    name="app_name",
                    type="string",
                    required=True,
                    default=None,
                    validation_pattern=r"^[a-zA-Z0-9_\-]+$",
                    description="Application name from allowlist"
                )
            ],
            input_schema={"type": "object", "properties": {"app_name": {"type": "string"}}, "required": ["app_name"]},
            output_schema={"type": "object", "properties": {"status": {"type": "string"}, "pid": {"type": "integer"}}},
            requires_confirmation=True,
            max_execution_time=5.0,
            enabled=True
        )
        self.register_tool(launch_app)

        # Software Installation tool (MEDIUM risk) - Phase 1 Stabilization
        install_software = ToolDefinition(
            name="install_software",
            description="Install new software or packages",
            action_type="system_modify",
            risk_category="MEDIUM",
            permission_level_required="MEDIUM",
            reversible=False,
            idempotent=False,
            parameters=[
                ToolParameter(
                    name="package",
                    type="string",
                    required=True,
                    default=None,
                    validation_pattern=r"^[a-zA-Z0-9_\-\.]+$",
                    description="Name of package to install"
                )
            ],
            input_schema={"type": "object", "properties": {"package": {"type": "string"}}, "required": ["package"]},
            output_schema={"type": "object", "properties": {"status": {"type": "string"}}},
            requires_confirmation=True,
            max_execution_time=60.0,
            enabled=True
        )
        self.register_tool(install_software)

        # Configuration Change tool (MEDIUM risk) - Phase 1 Stabilization
        change_config = ToolDefinition(
            name="change_config",
            description="Change system or application configuration",
            action_type="config_modify",
            risk_category="MEDIUM",
            permission_level_required="MEDIUM",
            reversible=True,
            idempotent=True,
            parameters=[
                ToolParameter(
                    name="setting",
                    type="string",
                    required=True,
                    default=None,
                    validation_pattern=r"^[a-zA-Z0-9_\-\.]+$",
                    description="Setting name"
                ),
                ToolParameter(
                    name="value",
                    type="string",
                    required=True,
                    default=None,
                    validation_pattern=None,
                    description="New value for setting"
                )
            ],
            input_schema={"type": "object", "properties": {"setting": {"type": "string"}, "value": {"type": "string"}}, "required": ["setting", "value"]},
            output_schema={"type": "object", "properties": {"status": {"type": "string"}, "previous_value": {"type": "string"}}},
            requires_confirmation=True,
            max_execution_time=5.0,
            enabled=True
        )
        self.register_tool(change_config)
    
    def register_tool(self, tool: ToolDefinition) -> bool:
        """
        Register a tool. Phase 5: Computes SHA256 identity hash at registration.
        
        Args:
            tool: Tool definition
        
        Returns:
            True if registered successfully
        """
        if tool.name in self.tools:
            self.logger.warning(f"Tool {tool.name} already registered, overwriting")
        
        # Phase 5: Compute tool identity hash
        if not tool.sha256:
            import hashlib, json
            identity_data = json.dumps({
                "name": tool.name,
                "version": tool.version,
                "action_type": tool.action_type,
                "input_schema": tool.input_schema,
                "output_schema": tool.output_schema,
            }, sort_keys=True)
            tool.sha256 = hashlib.sha256(identity_data.encode()).hexdigest()
        
        self.tools[tool.name] = tool
        self._save_registry()
        self.logger.info(f"Tool registered: {tool.name} v{tool.version} sha256={tool.sha256[:16]}...")
        return True
    
    def get_tool_identity(self, tool_name: str) -> Optional[Dict[str, str]]:
        """
        Phase 5: Get frozen tool identity for plan embedding.
        Returns {tool_id, version, sha256} or None.
        """
        tool = self.get_tool(tool_name)
        if tool is None:
            return None
        return {
            "tool_id": tool.name,
            "version": tool.version,
            "sha256": tool.sha256
        }
    
    def unregister_tool(self, tool_name: str) -> bool:
        """
        Unregister a tool
        
        Args:
            tool_name: Name of tool to unregister
        
        Returns:
            True if unregistered successfully
        """
        if tool_name not in self.tools:
            self.logger.warning(f"Tool {tool_name} not found")
            return False
        
        del self.tools[tool_name]
        self._save_registry()
        self.logger.info(f"Tool unregistered: {tool_name}")
        return True
    
    def get_tool(self, tool_name: str) -> Optional[ToolDefinition]:
        """
        Get tool definition
        
        Args:
            tool_name: Name of tool
        
        Returns:
            ToolDefinition or None
        """
        return self.tools.get(tool_name)
    
    def list_tools(self, filter_by: Dict[str, Any] = None) -> List[ToolDefinition]:
        """
        List tools with optional filtering
        
        Args:
            filter_by: Optional filter criteria
        
        Returns:
            List of ToolDefinition
        """
        tools = list(self.tools.values())
        
        if filter_by:
            if "risk_category" in filter_by:
                tools = [t for t in tools if t.risk_category == filter_by["risk_category"]]
            
            if "enabled" in filter_by:
                tools = [t for t in tools if t.enabled == filter_by["enabled"]]
            
            if "action_type" in filter_by:
                tools = [t for t in tools if t.action_type == filter_by["action_type"]]
        
        return tools
    
    def validate_tool_call(self, tool_name: str, parameters: Dict[str, Any]) -> bool:
        """
        Validate tool call parameters
        
        Args:
            tool_name: Name of tool
            parameters: Parameters to validate
        
        Returns:
            True if valid
        """
        tool = self.get_tool(tool_name)
        if not tool:
            self.logger.warning(f"Tool {tool_name} not found")
            return False
        
        # Check required parameters
        for param in tool.parameters:
            if param.required and param.name not in parameters:
                self.logger.warning(f"Missing required parameter: {param.name}")
                return False
        
        # TODO: Add regex validation for parameters
        
        return True
    
    def is_tool_enabled(self, tool_name: str) -> bool:
        """
        Check if tool is enabled
        
        Args:
            tool_name: Name of tool
        
        Returns:
            True if enabled
        """
        tool = self.get_tool(tool_name)
        return tool.enabled if tool else False
