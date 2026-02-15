"""
Interactive CLI - Phase 5A
Main command loop for Lyra AI
Continuous input, graceful exit, clear output
"""

import sys
import signal
from typing import Optional
from lyra.core.pipeline import LyraPipeline
from lyra.cli.output_formatter import OutputFormatter, Colors
from lyra.core.logger import get_logger


class InteractiveCLI:
    """
    Interactive command-line interface for Lyra AI
    Phase 5A: Main CLI loop
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.pipeline = LyraPipeline()
        self.formatter = OutputFormatter()
        self.running = False
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
    
    def _signal_handler(self, sig, frame):
        """Handle Ctrl+C gracefully"""
        print("\n" + self.formatter.format_info("Interrupted by user"))
        self.stop()
    
    def start(self):
        """Start interactive CLI loop"""
        self.running = True
        
        # Print banner
        self._print_banner()
        
        # Main loop
        while self.running:
            try:
                # Get user input
                user_input = input(self._colorize("\n> ", Colors.CYAN + Colors.BOLD))
                
                # Skip empty input
                if not user_input.strip():
                    continue
                
                # Check for exit commands
                if user_input.lower() in ['exit', 'quit', 'q']:
                    self.stop()
                    break
                
                # Check for help
                if user_input.lower() in ['help', 'h', '?']:
                    self._print_help()
                    continue
                
                # Check for simulation mode
                if user_input.lower().startswith('simulate '):
                    command = user_input[9:]  # Remove 'simulate '
                    result = self.pipeline.simulate_command(command)
                    print(result.output)
                    continue
                
                # Process command
                result = self.pipeline.process_command(user_input)
                print(result.output)
            
            except EOFError:
                # Handle Ctrl+D
                self.stop()
                break
            
            except Exception as e:
                self.logger.error(f"CLI error: {e}")
                print(self.formatter.format_warning(f"Error: {e}"))
    
    def stop(self):
        """Stop CLI gracefully"""
        self.running = False
        print(self._colorize("\nGoodbye! 👋", Colors.CYAN))
    
    def _print_banner(self):
        """Print welcome banner"""
        banner = f"""
{self._colorize('╔═══════════════════════════════════════╗', Colors.CYAN)}
{self._colorize('║', Colors.CYAN)}  {self._colorize('Lyra AI v3.0', Colors.BOLD)}  {self._colorize('- Interactive Mode', Colors.CYAN)}  {self._colorize('║', Colors.CYAN)}
{self._colorize('╚═══════════════════════════════════════╝', Colors.CYAN)}

{self._colorize('Commands:', Colors.BOLD)}
  • Type your command naturally
  • Type 'help' for examples
  • Type 'simulate <command>' for dry-run
  • Type 'exit' to quit

{self._colorize('Examples:', Colors.BOLD)}
  • create file test.txt with content "Hello"
  • open https://google.com
  • launch notepad
"""
        print(banner)
    
    def _print_help(self):
        """Print help information"""
        help_text = f"""
{self._colorize('Available Commands:', Colors.BOLD)}

{self._colorize('File Operations:', Colors.CYAN)}
  • create file <path> with content "<text>"
  • write to file <path>: <content>
  • read file <path>

{self._colorize('Web & Apps:', Colors.CYAN)}
  • open <url>
  • launch <app_name>

{self._colorize('System:', Colors.CYAN)}
  • simulate <command>  - Dry-run without execution
  • help              - Show this help
  • exit              - Quit Lyra

{self._colorize('Examples:', Colors.BOLD)}
  {self._colorize('>', Colors.CYAN)} create file notes.txt with content "Meeting notes"
  {self._colorize('>', Colors.CYAN)} open https://github.com
  {self._colorize('>', Colors.CYAN)} launch notepad
  {self._colorize('>', Colors.CYAN)} simulate create file test.txt with content "test"
"""
        print(help_text)
    
    def _colorize(self, text: str, color: str) -> str:
        """Apply color to text"""
        return f"{color}{text}{Colors.RESET}"


def main():
    """Main entry point"""
    cli = InteractiveCLI()
    cli.start()


if __name__ == "__main__":
    main()
