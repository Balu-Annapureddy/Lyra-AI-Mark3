"""
Phase 5A Demo Workflows
Demonstrates end-to-end integration with 3 example workflows
"""

from lyra.core.pipeline import LyraPipeline
from lyra.cli.output_formatter import OutputFormatter, Colors


def demo_file_creation():
    """Demo 1: File creation/edit"""
    print(f"\n{Colors.BOLD}=== Demo 1: File Creation ==={Colors.RESET}\n")
    
    pipeline = LyraPipeline()
    
    # Test command
    command = 'create file test_demo.txt with content "Hello from Lyra AI!"'
    print(f"{Colors.CYAN}Command:{Colors.RESET} {command}\n")
    
    # Process
    result = pipeline.process_command(command, auto_confirm=True)
    print(result.output)
    
    return result.success


def demo_open_website():
    """Demo 2: Open approved website"""
    print(f"\n{Colors.BOLD}=== Demo 2: Open Website ==={Colors.RESET}\n")
    
    pipeline = LyraPipeline()
    
    # Test command
    command = 'open https://google.com'
    print(f"{Colors.CYAN}Command:{Colors.RESET} {command}\n")
    
    # Process
    result = pipeline.process_command(command, auto_confirm=True)
    print(result.output)
    
    return result.success


def demo_launch_app():
    """Demo 3: Launch allowlisted app"""
    print(f"\n{Colors.BOLD}=== Demo 3: Launch Application ==={Colors.RESET}\n")
    
    pipeline = LyraPipeline()
    
    # Test command
    command = 'launch notepad'
    print(f"{Colors.CYAN}Command:{Colors.RESET} {command}\n")
    
    # Process
    result = pipeline.process_command(command, auto_confirm=True)
    print(result.output)
    
    return result.success


def demo_simulation_mode():
    """Demo 4: Simulation mode (dry-run)"""
    print(f"\n{Colors.BOLD}=== Demo 4: Simulation Mode ==={Colors.RESET}\n")
    
    pipeline = LyraPipeline()
    
    # Test command
    command = 'create file simulation_test.txt with content "This is a test"'
    print(f"{Colors.CYAN}Command (simulated):{Colors.RESET} {command}\n")
    
    # Simulate
    result = pipeline.simulate_command(command)
    print(result.output)
    
    return result.success


def run_all_demos():
    """Run all demo workflows"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}╔═══════════════════════════════════════╗{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}║  Phase 5A - Demo Workflows           ║{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}╚═══════════════════════════════════════╝{Colors.RESET}\n")
    
    results = []
    
    # Run demos
    results.append(("File Creation", demo_file_creation()))
    results.append(("Open Website", demo_open_website()))
    results.append(("Launch App", demo_launch_app()))
    results.append(("Simulation Mode", demo_simulation_mode()))
    
    # Summary
    print(f"\n{Colors.BOLD}=== Demo Summary ==={Colors.RESET}\n")
    for name, success in results:
        status = f"{Colors.GREEN}✓ PASS{Colors.RESET}" if success else f"{Colors.RED}✗ FAIL{Colors.RESET}"
        print(f"  {name}: {status}")
    
    total_passed = sum(1 for _, success in results if success)
    print(f"\n{Colors.BOLD}Total: {total_passed}/{len(results)} passed{Colors.RESET}\n")


if __name__ == "__main__":
    run_all_demos()
