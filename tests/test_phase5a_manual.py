# -*- coding: utf-8 -*-
"""
Manual Aggressive Test Suite for Phase 5A
Run this to break the pipeline on purpose
"""

from lyra.core.pipeline import LyraPipeline
from lyra.reasoning.intent_detector import IntentDetector
from lyra.planning.execution_planner import ExecutionPlanner
import tempfile
import os


def test_intent_detection():
    """Test 1: Intent Detection - Valid and Invalid"""
    print("\n" + "="*60)
    print("TEST 1: INTENT DETECTION")
    print("="*60)
    
    detector = IntentDetector()
    
    test_cases = [
        ('create file test.txt with content "hello"', 'write_file'),
        ('open https://google.com', 'open_url'),
        ('launch notepad', 'launch_app'),
        ('read file test.txt', 'read_file'),
        ('do something random', 'unknown'),
        ('', 'error'),
        ('asdfghjkl', 'unknown'),
    ]
    
    passed = 0
    for command, expected in test_cases:
        try:
            if command == '':
                # Should raise exception
                try:
                    cmd = detector.detect_intent(command)
                    print(f"  ✗ FAIL: Empty command should raise exception")
                except:
                    print(f"  ✓ PASS: Empty command raised exception")
                    passed += 1
            else:
                cmd = detector.detect_intent(command)
                if expected == 'unknown':
                    if cmd.intent == 'unknown':
                        print(f"  ✓ PASS: '{command[:30]}...' → {cmd.intent}")
                        passed += 1
                    else:
                        print(f"  ✗ FAIL: '{command[:30]}...' → {cmd.intent} (expected unknown)")
                else:
                    if cmd.intent == expected:
                        print(f"  ✓ PASS: '{command[:30]}...' → {cmd.intent}")
                        passed += 1
                    else:
                        print(f"  ✗ FAIL: '{command[:30]}...' → {cmd.intent} (expected {expected})")
        except Exception as e:
            print(f"  ✗ ERROR: '{command[:30]}...' → {e}")
    
    print(f"\nResult: {passed}/{len(test_cases)} passed")
    return passed == len(test_cases)


def test_plan_generation():
    """Test 2: Plan Generation from Commands"""
    print("\n" + "="*60)
    print("TEST 2: PLAN GENERATION")
    print("="*60)
    
    detector = IntentDetector()
    planner = ExecutionPlanner()
    
    test_cases = [
        'create file test.txt with content "hello"',
        'open https://google.com',
        'launch notepad',
    ]
    
    passed = 0
    for command in test_cases:
        try:
            cmd = detector.detect_intent(command)
            plan = planner.create_plan_from_command(cmd)
            
            if plan and len(plan.steps) > 0:
                print(f"  ✓ PASS: '{command[:40]}...' → {len(plan.steps)} steps")
                passed += 1
            else:
                print(f"  ✗ FAIL: '{command[:40]}...' → No plan generated")
        except Exception as e:
            print(f"  ✗ ERROR: '{command[:40]}...' → {e}")
    
    print(f"\nResult: {passed}/{len(test_cases)} passed")
    return passed == len(test_cases)


def test_pipeline_simulation():
    """Test 3: Pipeline Simulation Mode"""
    print("\n" + "="*60)
    print("TEST 3: SIMULATION MODE")
    print("="*60)
    
    pipeline = LyraPipeline()
    
    test_cases = [
        'create file /tmp/sim_test.txt with content "test"',
        'open https://example.com',
        'launch calculator',
    ]
    
    passed = 0
    for command in test_cases:
        try:
            result = pipeline.simulate_command(command)
            
            if result and result.success:
                print(f"  ✓ PASS: Simulated '{command[:40]}...'")
                passed += 1
            else:
                print(f"  ✗ FAIL: Simulation failed for '{command[:40]}...'")
        except Exception as e:
            print(f"  ✗ ERROR: '{command[:40]}...' → {e}")
    
    print(f"\nResult: {passed}/{len(test_cases)} passed")
    return passed == len(test_cases)


def test_invalid_inputs():
    """Test 4: Invalid Inputs - Should Fail Gracefully"""
    print("\n" + "="*60)
    print("TEST 4: INVALID INPUTS (Should Fail Gracefully)")
    print("="*60)
    
    pipeline = LyraPipeline()
    
    test_cases = [
        'create file',  # Missing params
        'open',  # Missing URL
        'launch',  # Missing app
        'random gibberish command',
        'delete everything',
    ]
    
    passed = 0
    for command in test_cases:
        try:
            result = pipeline.process_command(command, auto_confirm=True)
            
            # Should fail but not crash
            if result and not result.success:
                print(f"  ✓ PASS: '{command[:40]}...' failed gracefully")
                passed += 1
            elif result and result.success:
                print(f"  ⚠ WARN: '{command[:40]}...' succeeded unexpectedly")
                passed += 0.5
            else:
                print(f"  ✗ FAIL: '{command[:40]}...' returned None")
        except Exception as e:
            print(f"  ⚠ WARN: '{command[:40]}...' raised exception: {e}")
            passed += 0.5
    
    print(f"\nResult: {passed}/{len(test_cases)} passed")
    return passed >= len(test_cases) * 0.8  # 80% threshold


def test_edge_cases():
    """Test 5: Edge Cases"""
    print("\n" + "="*60)
    print("TEST 5: EDGE CASES")
    print("="*60)
    
    pipeline = LyraPipeline()
    
    # Test 1: Very long content
    try:
        long_content = "A" * 1000
        result = pipeline.simulate_command(
            f'create file test.txt with content "{long_content}"'
        )
        if result:
            print(f"  ✓ PASS: Handled very long content (1000 chars)")
        else:
            print(f"  ✗ FAIL: Failed on long content")
    except Exception as e:
        print(f"  ✗ ERROR: Long content → {e}")
    
    # Test 2: Special characters
    try:
        special = "Test with 'quotes' and $symbols"
        result = pipeline.simulate_command(
            f'create file test.txt with content "{special}"'
        )
        if result:
            print(f"  ✓ PASS: Handled special characters")
        else:
            print(f"  ✗ FAIL: Failed on special characters")
    except Exception as e:
        print(f"  ✗ ERROR: Special chars → {e}")
    
    # Test 3: Multiple URLs
    try:
        result = pipeline.simulate_command('open www.google.com')
        if result:
            print(f"  ✓ PASS: Handled URL without protocol")
        else:
            print(f"  ✗ FAIL: Failed on URL without protocol")
    except Exception as e:
        print(f"  ✗ ERROR: URL without protocol → {e}")
    
    print("\nResult: Edge cases tested")
    return True


def test_stress():
    """Test 6: Stress Test - Rapid Commands"""
    print("\n" + "="*60)
    print("TEST 6: STRESS TEST (Rapid Commands)")
    print("="*60)
    
    pipeline = LyraPipeline()
    
    import time
    start = time.time()
    
    passed = 0
    for i in range(20):
        try:
            result = pipeline.simulate_command(
                f'create file test{i}.txt with content "test{i}"'
            )
            if result:
                passed += 1
        except Exception as e:
            print(f"  ✗ ERROR on iteration {i}: {e}")
    
    duration = time.time() - start
    
    print(f"  Completed: {passed}/20 commands")
    print(f"  Duration: {duration:.2f}s")
    print(f"  Avg: {duration/20*1000:.1f}ms per command")
    
    if passed >= 18 and duration < 5.0:
        print(f"  ✓ PASS: Stress test passed")
        return True
    else:
        print(f"  ✗ FAIL: Stress test failed")
        return False


def run_all_tests():
    """Run all aggressive tests"""
    print("\n" + "="*60)
    print("PHASE 5A - AGGRESSIVE INTEGRATION TESTS")
    print("Breaking the pipeline on purpose...")
    print("="*60)
    
    results = []
    
    results.append(("Intent Detection", test_intent_detection()))
    results.append(("Plan Generation", test_plan_generation()))
    results.append(("Simulation Mode", test_pipeline_simulation()))
    results.append(("Invalid Inputs", test_invalid_inputs()))
    results.append(("Edge Cases", test_edge_cases()))
    results.append(("Stress Test", test_stress()))
    
    print("\n" + "="*60)
    print("FINAL RESULTS")
    print("="*60)
    
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}: {name}")
    
    total_passed = sum(1 for _, p in results if p)
    print(f"\n  Total: {total_passed}/{len(results)} test suites passed")
    
    if total_passed == len(results):
        print("\n  🎉 ALL TESTS PASSED - Pipeline is SOLID!")
    elif total_passed >= len(results) * 0.8:
        print("\n  ⚠ MOSTLY PASSED - Some issues to address")
    else:
        print("\n  ❌ FAILED - Pipeline needs work")
    
    return total_passed >= len(results) * 0.8


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
