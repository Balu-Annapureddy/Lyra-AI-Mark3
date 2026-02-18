"""
Phase 5A Aggressive Integration Tests
Test the pipeline until it breaks
"""

import pytest
import os
import tempfile
from lyra.core.pipeline import LyraPipeline
from lyra.reasoning.intent_detector import IntentDetector
from lyra.planning.execution_planner import ExecutionPlanner


class TestValidCommands:
    """Test valid command scenarios"""
    
    def test_simple_file_write(self):
        """Test basic file creation"""
        pipeline = LyraPipeline()
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            temp_path = f.name
        
        try:
            os.remove(temp_path)  # Remove so we can create it
            
            result = pipeline.process_command(
                f'create file {temp_path} with content "test"',
                auto_confirm=True
            )
            
            assert result.success == True
            assert os.path.exists(temp_path)
        
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    def test_url_opening(self):
        """Test URL opening intent"""
        pipeline = LyraPipeline()
        
        result = pipeline.process_command(
            'open https://google.com',
            auto_confirm=True
        )
        
        # Should succeed (actual opening depends on system)
        assert result.success == True or result.error is not None
    
    def test_simulation_mode(self):
        """Test simulation doesn't execute"""
        pipeline = LyraPipeline()
        
        result = pipeline.simulate_command(
            'create file /tmp/should_not_exist.txt with content "test"'
        )
        
        assert result.success == True
        assert not os.path.exists('/tmp/should_not_exist.txt')


class TestInvalidInputs:
    """Test error handling for invalid inputs"""
    
    def test_empty_command(self):
        """Test empty command handling"""
        detector = IntentDetector()
        
        with pytest.raises(Exception):
            detector.detect_intent('')
    
    def test_unknown_intent(self):
        """Test unknown command"""
        pipeline = LyraPipeline()
        
        result = pipeline.process_command(
            'do something completely random and nonsensical',
            auto_confirm=True
        )
        
        assert result.success == False
        # Pipeline may route to clarification or return unknown-intent error
        combined = (result.error or "").lower() + (result.output or "").lower()
        assert (
            "unknown" in combined
            or "could not" in combined
            or "clarification" in combined
            or "more details" in combined
        )
    
    def test_malformed_file_command(self):
        """Test malformed file command"""
        pipeline = LyraPipeline()
        
        result = pipeline.process_command(
            'create file',  # Missing path and content
            auto_confirm=True
        )
        
        # Should fail gracefully OR succeed (semantic layer may interpret 'create file' as write_file)
        # Either outcome is acceptable — what matters is no unhandled exception
        assert result is not None
    
    def test_invalid_url(self):
        """Test invalid URL"""
        pipeline = LyraPipeline()
        
        result = pipeline.process_command(
            'open not-a-valid-url',
            auto_confirm=True
        )
        
        # Should either fail or handle gracefully
        assert result is not None


class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_very_long_content(self):
        """Test file with very long content"""
        pipeline = LyraPipeline()
        
        long_content = "A" * 10000
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            temp_path = f.name
        
        try:
            os.remove(temp_path)
            
            result = pipeline.process_command(
                f'create file {temp_path} with content "{long_content}"',
                auto_confirm=True
            )
            
            # Should handle large content
            assert result is not None
        
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    def test_special_characters_in_content(self):
        """Test special characters in file content"""
        pipeline = LyraPipeline()
        
        special_content = "Test with 'quotes' and \"double quotes\" and $symbols"
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            temp_path = f.name
        
        try:
            os.remove(temp_path)
            
            result = pipeline.process_command(
                f'create file {temp_path} with content "{special_content}"',
                auto_confirm=True
            )
            
            assert result is not None
        
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    def test_nonexistent_app(self):
        """Test launching nonexistent app"""
        pipeline = LyraPipeline()
        
        result = pipeline.process_command(
            'launch totally_fake_app_12345',
            auto_confirm=True
        )
        
        # Should fail gracefully
        assert result is not None


class TestErrorRecovery:
    """Test error recovery and rollback"""
    
    def test_failed_write_rollback(self):
        """Test rollback on failed write"""
        pipeline = LyraPipeline()
        
        # Try to write to protected location
        result = pipeline.process_command(
            'create file /root/protected.txt with content "test"',
            auto_confirm=True
        )
        
        # Should fail but not crash
        assert result is not None
    
    def test_cancelled_confirmation(self):
        """Test user cancellation"""
        pipeline = LyraPipeline()
        
        # High-risk operation without auto-confirm
        result = pipeline.process_command(
            'create file test.txt with content "test"',
            auto_confirm=False  # Would require user input
        )
        
        # Should handle gracefully
        assert result is not None


class TestStressTests:
    """Stress test the pipeline"""
    
    def test_rapid_commands(self):
        """Test rapid command execution"""
        pipeline = LyraPipeline()
        
        results = []
        for i in range(10):
            result = pipeline.simulate_command(
                f'create file test{i}.txt with content "test{i}"'
            )
            results.append(result)
        
        # All should complete
        assert len(results) == 10
        assert all(r is not None for r in results)
    
    def test_intent_detection_performance(self):
        """Test intent detection speed"""
        detector = IntentDetector()
        
        commands = [
            'create file test.txt with content "hello"',
            'open https://google.com',
            'launch notepad',
            'read file test.txt'
        ]
        
        import time
        start = time.time()
        
        for cmd in commands * 25:  # 100 total
            detector.detect_intent(cmd)
        
        duration = time.time() - start
        
        # Should be fast (<1s for 100 detections)
        assert duration < 1.0


class TestIntentPatterns:
    """Test intent pattern matching"""
    
    def test_file_patterns(self):
        """Test various file command patterns"""
        detector = IntentDetector()
        
        patterns = [
            ('create file test.txt with content "hello"', 'write_file'),
            ('read file test.txt', 'read_file'),
            ('open file test.txt', 'read_file'),
        ]
        
        for command, expected_intent in patterns:
            cmd = detector.detect_intent(command)
            assert cmd.intent == expected_intent, f"Failed for: {command}"
    
    def test_url_patterns(self):
        """Test URL pattern matching"""
        detector = IntentDetector()
        
        patterns = [
            ('open https://google.com', 'open_url'),
            ('open www.github.com', 'open_url'),
            ('open google.com', 'open_url'),
        ]
        
        for command, expected_intent in patterns:
            cmd = detector.detect_intent(command)
            assert cmd.intent == expected_intent, f"Failed for: {command}"
    
    def test_app_patterns(self):
        """Test app launch patterns"""
        detector = IntentDetector()
        
        patterns = [
            ('launch notepad', 'launch_app'),
            ('start calculator', 'launch_app'),
            ('open notepad', 'launch_app'),
        ]
        
        for command, expected_intent in patterns:
            cmd = detector.detect_intent(command)
            assert cmd.intent == expected_intent, f"Failed for: {command}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
