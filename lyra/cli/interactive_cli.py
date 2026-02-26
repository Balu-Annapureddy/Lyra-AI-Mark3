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
                user_input = input(f"\n{self._colorize('>', Colors.CYAN)} ").strip()
                
                if not user_input:
                    continue
                
                # Handle special commands
                if user_input.lower() in ['exit', 'quit']:
                    self.stop()
                    break
                
                if user_input.lower() == 'help':
                    self._print_help()
                    continue
                
                # Phase 5B: History command
                if user_input.lower() == 'history':
                    self._display_history()
                    continue
                
                # Phase 5B: Logs command
                if user_input.lower() == 'logs':
                    self._display_logs()
                    continue
                
                # Metrics command
                if user_input.lower() in ['metrics', 'show metrics', 'stats']:
                    self._display_metrics()
                    continue
                
                # Conversational fallback: questions Lyra can't execute
                lower = user_input.lower()
                if any(lower.startswith(q) for q in [
                    'how are', 'what is your name', 'who are you',
                    'what are you', 'are you', 'do you', 'can you tell me about yourself',
                ]):
                    print(self.formatter.format_info(
                        "I'm Lyra, an AI assistant that can manage files, open URLs, "
                        "and launch apps. Type 'help' to see what I can do!"
                    ))
                    continue
                
                # Handle simulation
                if user_input.lower().startswith('simulate '):
                    command = user_input[9:].strip()
                    result = self.pipeline.simulate_command(command)
                    print(result.output)
                    continue
                
                # Process normal command
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
{self._colorize('+=======================================+', Colors.CYAN)}
{self._colorize('|', Colors.CYAN)}  {self._colorize('Lyra AI v3.0', Colors.BOLD)}  {self._colorize('- Interactive Mode', Colors.CYAN)}  {self._colorize('|', Colors.CYAN)}
{self._colorize('+=======================================+', Colors.CYAN)}
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
        print(f"  - history           - Show command history")
        print(f"  - logs              - Show execution logs")
        print(f"  - metrics           - Show pipeline performance stats")
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
    
    def _display_history(self):
        """Display command history (Phase 5B)"""
        history = self.pipeline.get_history()
        
        if not history:
            print(f"\n{Colors.CYAN}No command history yet{Colors.RESET}")
            return
        
        print(f"\n{Colors.BOLD}Command History:{Colors.RESET}")
        print(f"{Colors.DIM}{'='*60}{Colors.RESET}")
        
        for i, entry in enumerate(history, 1):
            status = f"{Colors.GREEN}[OK]{Colors.RESET}" if entry.success else f"{Colors.RED}[FAIL]{Colors.RESET}"
            timestamp = entry.timestamp.split('T')[1].split('.')[0]  # HH:MM:SS
            print(f"{Colors.CYAN}{i:2d}.{Colors.RESET} {status} {Colors.DIM}{timestamp}{Colors.RESET} {entry.command}")
        
        print(f"{Colors.DIM}{'='*60}{Colors.RESET}\n")
    
    def _display_logs(self):
        """Display execution logs (Phase 5B)"""
        logs = self.pipeline.get_logs()
        
        if not logs:
            print(f"\n{Colors.CYAN}No execution logs yet{Colors.RESET}")
            return
        
        print(f"\n{Colors.BOLD}Execution Logs:{Colors.RESET}")
        print(f"{Colors.DIM}{'='*60}{Colors.RESET}")
        
        for i, entry in enumerate(logs, 1):
            status = f"{Colors.GREEN}[OK]{Colors.RESET}" if entry.success else f"{Colors.RED}[FAIL]{Colors.RESET}"
            timestamp = entry.timestamp.split('T')[1].split('.')[0]  # HH:MM:SS
            duration_str = f"{entry.duration:.2f}s"
            
            print(f"{Colors.CYAN}{i:2d}.{Colors.RESET} {status} {Colors.DIM}{timestamp}{Colors.RESET} {entry.command[:40]}")
            print(f"    Duration: {duration_str} | Plan: {entry.plan_id[:8]}...")
            if entry.error:
                print(f"    {Colors.RED}Error: {entry.error[:50]}{Colors.RESET}")
        
        print(f"{Colors.DIM}{'='*60}{Colors.RESET}\n")
    
    def _display_metrics(self):
        """Display pipeline metrics"""
        try:
            report = self.pipeline.metrics.get_report()
            print(f"\n{Colors.BOLD}Pipeline Metrics:{Colors.RESET}")
            print(f"{Colors.DIM}{'='*60}{Colors.RESET}")
            for line in report.strip().splitlines():
                print(f"  {line}")
            print(f"{Colors.DIM}{'='*60}{Colors.RESET}\n")
        except Exception as e:
            print(self.formatter.format_warning(f"Could not retrieve metrics: {e}"))
    
    def _colorize(self, text: str, color: str) -> str:
        """Apply color to text"""
        return f"{color}{text}{Colors.RESET}"


def main():
    """Main entry point"""
    cli = InteractiveCLI()
    cli.start()


if __name__ == "__main__":
    main()
