# -*- coding: utf-8 -*-
"""
Quick Test - Phase 5A
Run this after the asdict fix
"""

import sys
sys.path.insert(0, '.')

from lyra.core.pipeline import LyraPipeline

print("\n" + "="*60)
print("QUICK TEST - Phase 5A Pipeline")
print("="*60)

pipeline = LyraPipeline()

# Test 1: Simulation
print("\n[Test 1] Simulation Mode")
print("-" * 40)
result = pipeline.simulate_command('create file test.txt with content "hello"')
if result and result.success:
    print("✓ PASS: Simulation works")
else:
    print(f"✗ FAIL: {result.error if result else 'No result'}")

# Test 2: URL (simulation)
print("\n[Test 2] URL Opening (simulated)")
print("-" * 40)
result = pipeline.simulate_command('open https://google.com')
if result and result.success:
    print("✓ PASS: URL simulation works")
else:
    print(f"✗ FAIL: {result.error if result else 'No result'}")

# Test 3: App launch (simulation)
print("\n[Test 3] App Launch (simulated)")
print("-" * 40)
result = pipeline.simulate_command('launch notepad')
if result and result.success:
    print("✓ PASS: App launch simulation works")
else:
    print(f"✗ FAIL: {result.error if result else 'No result'}")

# Test 4: Invalid input
print("\n[Test 4] Error Handling")
print("-" * 40)
result = pipeline.process_command('random gibberish', auto_confirm=True)
if result and not result.success:
    print("✓ PASS: Invalid input handled gracefully")
else:
    print(f"✗ FAIL: Should have failed gracefully")

print("\n" + "="*60)
print("TESTS COMPLETE")
print("="*60)
print("\nIf all 4 tests passed, the pipeline is working!")
print("You can now try the interactive CLI:\n")
print("  python quick_cli.py\n")
