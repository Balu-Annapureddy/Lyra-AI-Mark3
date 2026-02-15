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
        print(f"\n{Colors.BOLD}Goodbye!{Colors.RESET}\n")
    
    def _print_banner(self):
        """Print welcome banner"""
        banner = f"""
{self._colorize('╔═══════════════════════════════════════╗', Colors.CYAN)}
{self._colorize('║', Colors.CYAN)}  {self._colorize('Lyra AI v3.0', Colors.BOLD)}  {self._colorize('- Interactive Mode', Colors.CYAN)}  {self._colorize('║', Colors.CYAN)}
{self._colorize('╚═══════════════════════════════════════╝', Colors.CYAN)}
"""
        print(banner)
        print(f"\n{Colors.BOLD}Commands:{Colors.RESET}")
        print(f"  - Type your command naturally")
        print(f"  - Type 'help' for examples")
        print(f"  - Type 'simulate <command>' for dry-run")
        print(f"  - Type 'exit' to quit")
        print()
        print(f"{Colors.BOLD}Examples:{Colors.RESET}")
        print(f"  - create file test.txt with content \"Hello\"")
        print(f"  - open https://google.com")
        print(f"  - launch notepad")
        print()
    
    def _print_help(self):
        """Print help information"""
        help_text = f"""
{self._colorize('Available Commands:', Colors.BOLD)}
"""
        print(help_text)
        print(f"\n{Colors.BOLD}File Operations:{Colors.RESET}")
        print(f"  - create file <path> with content \"<text>\"")
        print(f"  - write to file <path>: <content>")
        print(f"  - read file <path>")
        print()
        print(f"{Colors.BOLD}Web & Apps:{Colors.RESET}")
        print(f"  - open <url>")
        print(f"  - launch <app_name>")
        print()
        print(f"{Colors.BOLD}System:{Colors.RESET}")
        print(f"  - simulate <command>  - Dry-run without execution")
        print(f"  - help              - Show this help")
        print(f"  - exit              - Quit Lyra")
        print()
        print(f"{Colors.BOLD}Examples:{Colors.RESET}")
        print(f"  {self._colorize('>', Colors.CYAN)} create file notes.txt with content \"Meeting notes\"")
        print(f"  {self._colorize('>', Colors.CYAN)} open https://github.com")
        print(f"  {self._colorize('>', Colors.CYAN)} launch notepad")
        print(f"  {self._colorize('>', Colors.CYAN)} simulate create file test.txt with content \"test\"")
        print()
    
    def _colorize(self, text: str, color: str) -> str:
        """Apply color to text"""
        return f"{color}{text}{Colors.RESET}"


def main():
    """Main entry point"""
    cli = InteractiveCLI()
    cli.start()


if __name__ == "__main__":
    main()
