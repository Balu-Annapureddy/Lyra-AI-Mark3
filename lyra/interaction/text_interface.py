"""
Text Interface
Command-line interface for Lyra
"""

import sys
from typing import Optional
from lyra.core.logger import get_logger
from lyra.core.state_manager import StateManager, LyraState
from lyra.core.config import Config
from rich.console import Console
from rich.panel import Panel
from rich.text import Text


class TextInterface:
    """
    Text-based command-line interface
    Provides interactive session with Lyra
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.state_manager = StateManager()
        self.config = Config()
        self.console = Console()
        self.running = False
    
    def start(self):
        """Start interactive text interface"""
        self.running = True
        self._show_welcome()
        
        while self.running:
            try:
                user_input = self._get_input()
                
                if user_input:
                    yield user_input
            
            except KeyboardInterrupt:
                self._handle_interrupt()
                break
            except EOFError:
                break
    
    def stop(self):
        """Stop the interface"""
        self.running = False
        self._show_goodbye()
    
    def _show_welcome(self):
        """Display welcome message"""
        welcome_text = Text()
        welcome_text.append("Lyra AI Operating System\n", style="bold cyan")
        welcome_text.append("Version 0.1.0 - Phase 1\n\n", style="dim")
        welcome_text.append("I'm Lyra, your personal AI assistant.\n", style="white")
        welcome_text.append("Type 'help' for available commands or 'exit' to quit.\n", style="dim")
        
        panel = Panel(welcome_text, border_style="cyan", padding=(1, 2))
        self.console.print(panel)
    
    def _show_goodbye(self):
        """Display goodbye message"""
        self.console.print("\n[cyan]Goodbye! Lyra signing off.[/cyan]")
    
    def _get_input(self) -> Optional[str]:
        """
        Get user input
        
        Returns:
            User input string or None
        """
        try:
            # Show state indicator
            state = self.state_manager.current_state
            state_color = self._get_state_color(state)
            
            prompt = f"[{state_color}]●[/{state_color}] [bold]You:[/bold] "
            user_input = self.console.input(prompt).strip()
            
            # Handle special commands
            if user_input.lower() in ['exit', 'quit', 'bye']:
                self.running = False
                return None
            
            return user_input
        
        except Exception as e:
            self.logger.error(f"Input error: {e}")
            return None
    
    def _get_state_color(self, state: LyraState) -> str:
        """Get color for state indicator"""
        color_map = {
            LyraState.IDLE: "green",
            LyraState.LISTENING: "blue",
            LyraState.THINKING: "yellow",
            LyraState.EXECUTING: "magenta",
            LyraState.WAITING_CONFIRMATION: "cyan",
            LyraState.ERROR: "red"
        }
        return color_map.get(state, "white")
    
    def _handle_interrupt(self):
        """Handle Ctrl+C interrupt"""
        self.console.print("\n[yellow]Interrupted. Type 'exit' to quit.[/yellow]")
    
    def display_response(self, message: str, response_type: str = "info"):
        """
        Display Lyra's response
        
        Args:
            message: Response message
            response_type: Type of response (info, success, error, warning)
        """
        style_map = {
            "info": "white",
            "success": "green",
            "error": "red",
            "warning": "yellow"
        }
        
        style = style_map.get(response_type, "white")
        self.console.print(f"[bold cyan]Lyra:[/bold cyan] [{style}]{message}[/{style}]")
    
    def display_thinking(self, message: str = "Thinking..."):
        """Display thinking indicator"""
        self.console.print(f"[dim italic]{message}[/dim italic]")
    
    def display_error(self, error_message: str):
        """Display error message"""
        self.console.print(f"[bold red]Error:[/bold red] {error_message}")
    
    def display_dry_run_result(self, result: dict):
        """
        Display dry-run simulation result
        
        Args:
            result: Dry-run result dictionary
        """
        self.console.print("\n[bold yellow]DRY RUN SIMULATION[/bold yellow]")
        self.console.print(f"Intent: {result.get('intent')}")
        self.console.print(f"Risk Level: {result.get('estimated_risk')}")
        
        if result.get('steps'):
            self.console.print("\n[bold]Planned Actions:[/bold]")
            for i, step in enumerate(result['steps'], 1):
                action = step.get('action')
                side_effects = step.get('side_effects', [])
                self.console.print(f"  {i}. {action}")
                if side_effects:
                    for effect in side_effects:
                        self.console.print(f"     → {effect}", style="dim")
        
        self.console.print()
