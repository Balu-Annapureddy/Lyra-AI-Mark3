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
    """Complete tool definition with metadata"""
    name: str
    description: str
    action_type: str  # Category: file, command, network, etc.
    risk_category: str  # LOW, MEDIUM, HIGH
    permission_level_required: str  # LOW, MEDIUM, HIGH
    reversible: bool
    parameters: List[ToolParameter]
    requires_confirmation: bool
    max_execution_time: float  # seconds
    enabled: bool


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
                        # Convert parameters
                        params = [
                            ToolParameter(**p) for p in tool_data.get("parameters", [])
                        ]
                        tool_data["parameters"] = params
                        tool = ToolDefinition(**tool_data)
                        self.tools[tool.name] = tool
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
        """Register built-in tools (stubs for Phase 4A)"""
        
        # File read tool (LOW risk)
        read_file = ToolDefinition(
            name="read_file",
            description="Read contents of a file",
            action_type="file",
            risk_category="LOW",
            permission_level_required="LOW",
            reversible=True,  # N/A for read
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
            requires_confirmation=True,
            max_execution_time=5.0,
            enabled=True
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
            parameters=[],
            requires_confirmation=False,
            max_execution_time=2.0,
            enabled=True
        )
        self.register_tool(get_system_info)
    
    def register_tool(self, tool: ToolDefinition) -> bool:
        """
        Register a tool
        
        Args:
            tool: Tool definition
        
        Returns:
            True if registered successfully
        """
        if tool.name in self.tools:
            self.logger.warning(f"Tool {tool.name} already registered, overwriting")
        
        self.tools[tool.name] = tool
        self._save_registry()
        self.logger.info(f"Tool registered: {tool.name}")
        return True
    
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
