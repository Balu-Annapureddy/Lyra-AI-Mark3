"""
Test Phase 4B Step 2 - App Launcher Tool
Tests controlled app launching and URL opening with strict validation
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from lyra.tools.app_launcher_tool import AppLauncherTool
from lyra.planning.execution_planner import ExecutionStep
from lyra.execution.execution_gateway import ExecutionGateway


def test_url_validation():
    """Test URL validation"""
    print("\n=== Testing URL Validation ===")
    
    app_launcher = AppLauncherTool()
    
    # Test valid HTTPS URL
    print("\n1. Valid HTTPS URL:")
    is_valid, error = app_launcher._validate_url("https://www.google.com")
    print(f"   ✓ Valid: {is_valid}")
    assert is_valid, "HTTPS URL should be valid"
    
    # Test valid HTTP URL
    print("\n2. Valid HTTP URL:")
    is_valid, error = app_launcher._validate_url("http://example.com")
    print(f"   ✓ Valid: {is_valid}")
    assert is_valid, "HTTP URL should be valid"
    
    # Test blocked localhost
    print("\n3. Blocked Localhost:")
    is_valid, error = app_launcher._validate_url("http://localhost:8080")
    print(f"   ✓ Blocked: {not is_valid}")
    print(f"   ✓ Error: {error}")
    assert not is_valid, "Localhost should be blocked"
    
    # Test blocked 127.0.0.1
    print("\n4. Blocked 127.0.0.1:")
    is_valid, error = app_launcher._validate_url("http://127.0.0.1")
    print(f"   ✓ Blocked: {not is_valid}")
    print(f"   ✓ Error: {error}")
    assert not is_valid, "127.0.0.1 should be blocked"
    
    # Test blocked private IP
    print("\n5. Blocked Private IP (192.168.x.x):")
    is_valid, error = app_launcher._validate_url("http://192.168.1.1")
    print(f"   ✓ Blocked: {not is_valid}")
    print(f"   ✓ Error: {error}")
    assert not is_valid, "Private IP should be blocked"
    
    # Test invalid scheme
    print("\n6. Invalid Scheme (ftp):")
    is_valid, error = app_launcher._validate_url("ftp://example.com")
    print(f"   ✓ Blocked: {not is_valid}")
    print(f"   ✓ Error: {error}")
    assert not is_valid, "FTP scheme should be blocked"
    
    # Test suspicious pattern (javascript:)
    print("\n7. Suspicious Pattern (javascript:):")
    is_valid, error = app_launcher._validate_url("javascript:alert('xss')")
    print(f"   ✓ Blocked: {not is_valid}")
    print(f"   ✓ Error: {error}")
    assert not is_valid, "JavaScript URL should be blocked"
    
    # Test suspicious pattern (file://)
    print("\n8. Suspicious Pattern (file://):")
    is_valid, error = app_launcher._validate_url("file:///etc/passwd")
    print(f"   ✓ Blocked: {not is_valid}")
    print(f"   ✓ Error: {error}")
    assert not is_valid, "File URL should be blocked"
    
    print("\n✅ URL Validation: PASSED")


def test_app_allowlist():
    """Test application allowlist"""
    print("\n=== Testing App Allowlist ===")
    
    app_launcher = AppLauncherTool()
    
    # Test list allowed apps
    print("\n1. List Allowed Apps:")
    apps = app_launcher.list_allowed_apps()
    print(f"   ✓ Total apps: {len(apps)}")
    for app in apps:
        print(f"      - {app['name']}: {app['description']} ({app['risk_level']})")
    assert len(apps) > 0, "Should have default apps"
    
    # Test add app to allowlist
    print("\n2. Add App to Allowlist:")
    success = app_launcher.add_app_to_allowlist(
        name="test_app",
        path="/usr/bin/test" if os.name != 'nt' else "test.exe",
        description="Test application",
        risk_level="LOW"
    )
    print(f"   ✓ Added: {success}")
    assert success, "Should add app successfully"
    
    # Verify app was added
    apps = app_launcher.list_allowed_apps()
    test_app = next((a for a in apps if a['name'] == 'test_app'), None)
    assert test_app is not None, "Test app should be in allowlist"
    print(f"   ✓ Verified: {test_app['name']}")
    
    # Test remove app from allowlist
    print("\n3. Remove App from Allowlist:")
    success = app_launcher.remove_app_from_allowlist("test_app")
    print(f"   ✓ Removed: {success}")
    assert success, "Should remove app successfully"
    
    # Verify app was removed
    apps = app_launcher.list_allowed_apps()
    test_app = next((a for a in apps if a['name'] == 'test_app'), None)
    assert test_app is None, "Test app should not be in allowlist"
    print(f"   ✓ Verified: removed")
    
    print("\n✅ App Allowlist: PASSED")


def test_app_validation():
    """Test application validation"""
    print("\n=== Testing App Validation ===")
    
    app_launcher = AppLauncherTool()
    
    # Test valid app (from default allowlist)
    print("\n1. Valid App from Allowlist:")
    if os.name == 'nt':
        app_name = "notepad"
    else:
        app_name = "gedit"
    
    is_valid, error, path = app_launcher._validate_app_path(app_name)
    print(f"   ✓ Valid: {is_valid}")
    if is_valid:
        print(f"   ✓ Path: {path}")
    assert is_valid, "Default app should be valid"
    
    # Test invalid app (not in allowlist)
    print("\n2. Invalid App (Not in Allowlist):")
    is_valid, error, path = app_launcher._validate_app_path("nonexistent_app")
    print(f"   ✓ Blocked: {not is_valid}")
    print(f"   ✓ Error: {error}")
    assert not is_valid, "Nonexistent app should be blocked"
    
    print("\n✅ App Validation: PASSED")


def test_open_url_operation():
    """Test open_url operation (NOTE: This will actually open URLs)"""
    print("\n=== Testing Open URL Operation ===")
    print("   ⚠️  WARNING: This test will open URLs in your browser")
    print("   ⚠️  Skipping actual URL opening for automated testing")
    
    app_launcher = AppLauncherTool()
    
    # Test valid URL (but don't actually open)
    print("\n1. Valid URL (validation only):")
    is_valid, error = app_launcher._validate_url("https://www.example.com")
    print(f"   ✓ Would open: https://www.example.com")
    print(f"   ✓ Validation passed: {is_valid}")
    assert is_valid, "Valid URL should pass validation"
    
    # Test blocked URL
    print("\n2. Blocked URL:")
    result = app_launcher.open_url("http://localhost:8080")
    print(f"   ✓ Blocked: {not result.success}")
    print(f"   ✓ Error: {result.error}")
    assert not result.success, "Localhost URL should be blocked"
    
    print("\n✅ Open URL Operation: PASSED")


def test_launch_app_operation():
    """Test launch_app operation (NOTE: This will actually launch apps)"""
    print("\n=== Testing Launch App Operation ===")
    print("   ⚠️  WARNING: This test would launch applications")
    print("   ⚠️  Skipping actual app launching for automated testing")
    
    app_launcher = AppLauncherTool()
    
    # Test valid app (but don't actually launch)
    print("\n1. Valid App (validation only):")
    if os.name == 'nt':
        app_name = "notepad"
    else:
        app_name = "gedit"
    
    is_valid, error, path = app_launcher._validate_app_path(app_name)
    print(f"   ✓ Would launch: {app_name}")
    print(f"   ✓ Validation passed: {is_valid}")
    assert is_valid, "Valid app should pass validation"
    
    # Test blocked app
    print("\n2. Blocked App:")
    result = app_launcher.launch_app("nonexistent_app")
    print(f"   ✓ Blocked: {not result.success}")
    print(f"   ✓ Error: {result.error}")
    assert not result.success, "Nonexistent app should be blocked"
    
    print("\n✅ Launch App Operation: PASSED")


def test_gateway_integration():
    """Test execution gateway integration"""
    print("\n=== Testing Gateway Integration ===")
    
    gateway = ExecutionGateway()
    
    # Test open_url through gateway (validation only)
    print("\n1. Open URL Through Gateway (validation only):")
    open_url_step = ExecutionStep(
        step_id="open_url_test",
        step_number=1,
        action_type="app_launcher",
        tool_required="open_url",
        parameters={"url": "https://www.example.com"},
        risk_level="LOW",
        requires_confirmation=False,
        depends_on=[],
        reversible=True,
        estimated_duration=3.0,
        description="Open URL"
    )
    
    # Validate step
    validation = gateway.validate_step(open_url_step)
    print(f"   ✓ Validation passed: {validation.valid}")
    assert validation.valid, "open_url step should validate"
    
    # Test launch_app through gateway (validation only)
    print("\n2. Launch App Through Gateway (validation only):")
    if os.name == 'nt':
        app_name = "notepad"
    else:
        app_name = "gedit"
    
    launch_app_step = ExecutionStep(
        step_id="launch_app_test",
        step_number=2,
        action_type="app_launcher",
        tool_required="launch_app",
        parameters={"app_name": app_name},
        risk_level="MEDIUM",
        requires_confirmation=True,
        depends_on=[],
        reversible=True,
        estimated_duration=5.0,
        description="Launch app"
    )
    
    validation = gateway.validate_step(launch_app_step)
    print(f"   ✓ Validation passed: {validation.valid}")
    assert validation.valid, "launch_app step should validate"
    
    # Test blocked URL through gateway
    print("\n3. Blocked URL Through Gateway:")
    blocked_url_step = ExecutionStep(
        step_id="blocked_url_test",
        step_number=3,
        action_type="app_launcher",
        tool_required="open_url",
        parameters={"url": "http://localhost:8080"},
        risk_level="LOW",
        requires_confirmation=False,
        depends_on=[],
        reversible=True,
        estimated_duration=3.0,
        description="Open blocked URL"
    )
    
    result = gateway._execute_app_launcher_operation(blocked_url_step)
    print(f"   ✓ Blocked: {not result.success}")
    print(f"   ✓ Error: {result.error}")
    assert not result.success, "Blocked URL should fail"
    
    print("\n✅ Gateway Integration: PASSED")


def test_tool_registry():
    """Test tool registry has new tools"""
    print("\n=== Testing Tool Registry ===")
    
    from lyra.tools.tool_registry import ToolRegistry
    
    registry = ToolRegistry()
    
    # Test open_url tool
    print("\n1. open_url Tool:")
    open_url = registry.get_tool("open_url")
    assert open_url is not None, "open_url should be registered"
    print(f"   ✓ Registered: {open_url.name}")
    print(f"   ✓ Risk: {open_url.risk_category}")
    print(f"   ✓ Permission: {open_url.permission_level_required}")
    print(f"   ✓ Enabled: {open_url.enabled}")
    assert open_url.risk_category == "LOW", "open_url should be LOW risk"
    assert open_url.enabled, "open_url should be enabled"
    
    # Test launch_app tool
    print("\n2. launch_app Tool:")
    launch_app = registry.get_tool("launch_app")
    assert launch_app is not None, "launch_app should be registered"
    print(f"   ✓ Registered: {launch_app.name}")
    print(f"   ✓ Risk: {launch_app.risk_category}")
    print(f"   ✓ Permission: {launch_app.permission_level_required}")
    print(f"   ✓ Enabled: {launch_app.enabled}")
    assert launch_app.risk_category == "MEDIUM", "launch_app should be MEDIUM risk"
    assert launch_app.enabled, "launch_app should be enabled"
    
    # Verify run_command is still disabled
    print("\n3. run_command Still Disabled:")
    run_command = registry.get_tool("run_command")
    assert run_command is not None, "run_command should be registered"
    print(f"   ✓ Enabled: {run_command.enabled}")
    assert not run_command.enabled, "run_command should still be disabled"
    
    # Verify delete_file is still disabled
    print("\n4. delete_file Still Disabled:")
    delete_file = registry.get_tool("delete_file")
    assert delete_file is not None, "delete_file should be registered"
    print(f"   ✓ Enabled: {delete_file.enabled}")
    assert not delete_file.enabled, "delete_file should still be disabled"
    
    print("\n✅ Tool Registry: PASSED")


def main():
    """Run all Phase 4B Step 2 tests"""
    print("=" * 60)
    print("Phase 4B Step 2 Tests - App Launcher Tool")
    print("=" * 60)
    
    try:
        # Core validation tests
        test_url_validation()
        test_app_allowlist()
        test_app_validation()
        
        # Operation tests (validation only, no actual launching)
        test_open_url_operation()
        test_launch_app_operation()
        
        # Integration tests
        test_gateway_integration()
        test_tool_registry()
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED")
        print("=" * 60)
        print("\nPhase 4B Step 2: Complete!")
        print("- App launcher tool ✅")
        print("- Application allowlist (configurable JSON) ✅")
        print("- URL validation (http/https, no localhost/internal IPs) ✅")
        print("- Application validation ✅")
        print("- Gateway integration ✅")
        print("- Tool registry updated ✅")
        print("\nRisks:")
        print("- open_url: LOW ✅")
        print("- launch_app: MEDIUM ✅")
        print("- run_command: DISABLED ✅")
        print("- delete_file: DISABLED ✅")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
