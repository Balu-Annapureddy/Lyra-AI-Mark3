# -*- coding: utf-8 -*-
"""
Output Formatter - Phase 5A/5B
Formats execution results for user display
Color-coded, structured output
"""

from typing import Dict, Any, List
from dataclasses import dataclass


class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    RESET = '\033[0m'


class OutputFormatter:
    """
    Format execution results for user display
    Phase 5A: Clean, structured output
    Phase 5B: Improved confirmation flow
    """
    
    def __init__(self, use_colors: bool = True):
        self.use_colors = use_colors
    
    def format_result(self, result) -> str:
        """
        Format execution result for display
        
        Args:
            result: Execution result (ExecutionResult object)
        
        Returns:
            Formatted string
        """
        if result.success:
            return self._format_success(result)
        else:
            return self._format_error(result)
    
    def _format_success(self, result) -> str:
        """Format successful execution"""
        lines = []
        
        # Success header
        lines.append(self._colorize("[OK] Success", Colors.GREEN + Colors.BOLD))
        
        # Step details
        for step_result in result.results:
            if step_result.success and step_result.output:
                lines.append(f"  {step_result.output}")
        
        # Duration
        duration_str = f"Duration: {result.total_duration:.2f}s"
        lines.append(f"  {self._colorize(duration_str, Colors.CYAN)}")
        
        return "\n".join(lines)
    
    def _format_error(self, result) -> str:
        """Format failed execution"""
        lines = []
        
        # Error header
        lines.append(self._colorize("[ERROR] Failed", Colors.RED + Colors.BOLD))
        
        # Error message
        if result.error:
            lines.append(f"  {self._colorize('Reason:', Colors.YELLOW)} {result.error}")
        
        # Failed step details
        for step_result in result.results:
            if not step_result.success and step_result.error:
                lines.append(f"  {self._colorize('Step failed:', Colors.YELLOW)} {step_result.error}")
        
        return "\n".join(lines)
    
    def format_plan(self, plan_description: str, steps: int, risk: float) -> str:
        """Format execution plan for confirmation"""
        lines = []
        
        lines.append(self._colorize("Execution Plan:", Colors.BOLD))
        lines.append(f"  {plan_description}")
        lines.append(f"  Steps: {steps}")
        lines.append(f"  Risk: {self._format_risk(risk)}")
        
        return "\n".join(lines)
    
    def format_confirmation(self, action: str, risk: float, details: str = "") -> str:
        """
        Format confirmation request with risk level (Phase 5B)
        
        Args:
            action: Action description
            risk: Risk score (0.0-1.0)
            details: Additional details
        
        Returns:
            Formatted confirmation message
        """
        lines = []
        
        # Risk level badge
        if risk < 0.3:
            risk_badge = self._colorize("[LOW RISK]", Colors.GREEN)
            risk_label = "LOW"
        elif risk < 0.6:
            risk_badge = self._colorize("[MEDIUM RISK]", Colors.YELLOW)
            risk_label = "MEDIUM"
        else:
            risk_badge = self._colorize("[HIGH RISK]", Colors.RED)
            risk_label = "HIGH"
        
        lines.append(f"\n{risk_badge} Confirmation Required")
        lines.append(f"{Colors.DIM}{'='*50}{Colors.RESET}")
        lines.append(f"\n{Colors.BOLD}Action:{Colors.RESET} {action}")
        
        if details:
            lines.append(f"{Colors.DIM}{details}{Colors.RESET}")
        
        lines.append(f"\n{Colors.BOLD}Risk Level:{Colors.RESET} {risk_label} ({risk:.0%})")
        lines.append(f"{Colors.DIM}{'='*50}{Colors.RESET}")
        
        return "\n".join(lines)
    
    def format_confirmation_prompt(self) -> str:
        """Format confirmation prompt (y/n)"""
        return self._colorize("\nProceed? (y/n): ", Colors.YELLOW + Colors.BOLD)
    
    def format_info(self, message: str) -> str:
        """Format info message"""
        return self._colorize(f"[INFO] {message}", Colors.CYAN)
    
    def format_cancellation(self) -> str:
        """Format cancellation message (Phase 5B)"""
        return self._colorize("\n[CANCELLED] Operation cancelled by user", Colors.YELLOW)
    
    def format_warning(self, message: str) -> str:
        """Format warning message"""
        return self._colorize(f"[WARN] {message}", Colors.YELLOW)
    
    def format_error(self, message: str) -> str:
        """Format error message"""
        return self._colorize(f"[ERROR] {message}", Colors.RED)
    
    def _format_risk(self, risk: float) -> str:
        """Format risk score with color"""
        if risk < 0.3:
            color = Colors.GREEN
            level = "LOW"
        elif risk < 0.6:
            color = Colors.YELLOW
            level = "MEDIUM"
        else:
            color = Colors.RED
            level = "HIGH"
        
        return self._colorize(f"{level} ({risk:.2f})", color)
    
    def _colorize(self, text: str, color: str) -> str:
        """Apply color to text if colors enabled"""
        if self.use_colors:
            return f"{color}{text}{Colors.RESET}"
        return text
    
    def format_error_from_exception(self, exception: Exception) -> str:
        """Format exception as error message"""
        return self._colorize(f"[ERROR] Error: {str(exception)}", Colors.RED)
