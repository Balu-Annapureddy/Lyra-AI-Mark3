"""
App Launcher Tool - Phase 4B Step 2
Controlled application and URL launching with strict allowlisting
NO shell commands, NO arbitrary execution
"""

import os
import json
import subprocess
import webbrowser
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from urllib.parse import urlparse
import ipaddress
from lyra.core.logger import get_logger


@dataclass
class LaunchResult:
    """Result of app/URL launch"""
    success: bool
    output: Any
    error: Optional[str]
    target: str
    operation: str


class AppLauncherTool:
    """
    Controlled app and URL launcher with strict allowlisting
    Phase 4B Step 2: open_url (LOW), launch_app (MEDIUM)
    """
    
    # Allowed URL schemes
    ALLOWED_SCHEMES = {'http', 'https'}
    
    # Blocked IP ranges (localhost, private networks)
    BLOCKED_IP_RANGES = [
        '127.0.0.0/8',      # Localhost
        '10.0.0.0/8',       # Private network
        '172.16.0.0/12',    # Private network
        '192.168.0.0/16',   # Private network
        '169.254.0.0/16',   # Link-local
        '::1/128',          # IPv6 localhost
        'fc00::/7',         # IPv6 private
        'fe80::/10'         # IPv6 link-local
    ]
    
    def __init__(self, allowlist_path: Optional[str] = None):
        self.logger = get_logger(__name__)
        
        # Load app allowlist
        if allowlist_path is None:
            allowlist_path = Path(__file__).parent.parent.parent / "data" / "app_allowlist.json"
        
        self.allowlist_path = Path(allowlist_path)
        self.allowlist = self._load_allowlist()
        
        self.logger.info(f"App launcher initialized with {len(self.allowlist)} allowed apps")
    
    def _load_allowlist(self) -> Dict[str, Dict[str, Any]]:
        """Load application allowlist from JSON"""
        if not self.allowlist_path.exists():
            # Create default allowlist
            default_allowlist = self._create_default_allowlist()
            self._save_allowlist(default_allowlist)
            return default_allowlist
        
        try:
            with open(self.allowlist_path, 'r') as f:
                allowlist = json.load(f)
            self.logger.info(f"Loaded allowlist from {self.allowlist_path}")
            return allowlist
        except Exception as e:
            self.logger.error(f"Error loading allowlist: {e}")
            return {}
    
    def _save_allowlist(self, allowlist: Dict[str, Dict[str, Any]]):
        """Save allowlist to JSON"""
        try:
            self.allowlist_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.allowlist_path, 'w') as f:
                json.dump(allowlist, f, indent=2)
            self.logger.info(f"Saved allowlist to {self.allowlist_path}")
        except Exception as e:
            self.logger.error(f"Error saving allowlist: {e}")
    
    def _create_default_allowlist(self) -> Dict[str, Dict[str, Any]]:
        """Create default application allowlist"""
        # Platform-specific defaults
        if os.name == 'nt':  # Windows
            return {
                "notepad": {
                    "path": "notepad.exe",
                    "description": "Notepad text editor",
                    "risk_level": "LOW"
                },
                "calculator": {
                    "path": "calc.exe",
                    "description": "Windows Calculator",
                    "risk_level": "LOW"
                },
                "explorer": {
                    "path": "explorer.exe",
                    "description": "Windows Explorer",
                    "risk_level": "MEDIUM"
                }
            }
        else:  # Unix/Linux/Mac
            return {
                "gedit": {
                    "path": "/usr/bin/gedit",
                    "description": "GNOME text editor",
                    "risk_level": "LOW"
                },
                "gnome-calculator": {
                    "path": "/usr/bin/gnome-calculator",
                    "description": "GNOME Calculator",
                    "risk_level": "LOW"
                },
                "nautilus": {
                    "path": "/usr/bin/nautilus",
                    "description": "GNOME file manager",
                    "risk_level": "MEDIUM"
                }
            }
    
    def _validate_url(self, url: str) -> tuple[bool, Optional[str]]:
        """
        Validate URL for safety
        
        Args:
            url: URL to validate
        
        Returns:
            (is_valid, error_message)
        """
        try:
            parsed = urlparse(url)
            
            # Check scheme
            if parsed.scheme not in self.ALLOWED_SCHEMES:
                return False, f"URL scheme not allowed: {parsed.scheme} (allowed: {', '.join(self.ALLOWED_SCHEMES)})"
            
            # Check hostname exists
            if not parsed.netloc:
                return False, "URL missing hostname"
            
            # Extract hostname (remove port if present)
            hostname = parsed.netloc.split(':')[0]
            
            # Check for localhost
            if hostname.lower() in ['localhost', '127.0.0.1', '::1']:
                return False, "Localhost URLs not allowed"
            
            # Check if hostname is an IP address
            try:
                ip = ipaddress.ip_address(hostname)
                
                # Check against blocked ranges
                for blocked_range in self.BLOCKED_IP_RANGES:
                    network = ipaddress.ip_network(blocked_range)
                    if ip in network:
                        return False, f"IP address in blocked range: {hostname}"
            
            except ValueError:
                # Not an IP address, it's a domain name - that's fine
                pass
            
            # Check for suspicious patterns
            suspicious_patterns = ['file://', 'javascript:', 'data:', 'vbscript:']
            url_lower = url.lower()
            for pattern in suspicious_patterns:
                if pattern in url_lower:
                    return False, f"Suspicious URL pattern detected: {pattern}"
            
            return True, None
        
        except Exception as e:
            return False, f"URL validation error: {e}"
    
    def _validate_app_path(self, app_name: str) -> tuple[bool, Optional[str], Optional[str]]:
        """
        Validate application from allowlist
        
        Args:
            app_name: Application name from allowlist
        
        Returns:
            (is_valid, error_message, executable_path)
        """
        # Check if app is in allowlist
        if app_name not in self.allowlist:
            return False, f"Application not in allowlist: {app_name}", None
        
        app_info = self.allowlist[app_name]
        executable_path = app_info.get("path")
        
        if not executable_path:
            return False, f"No path specified for app: {app_name}", None
        
        # On Windows, check if executable exists (for full paths)
        # For system commands like notepad.exe, they're in PATH
        if os.name == 'nt' and not executable_path.startswith(('C:\\', 'D:\\')):
            # System command, assume it's in PATH
            return True, None, executable_path
        
        # For Unix or full paths, check existence
        if os.path.isabs(executable_path):
            if not os.path.exists(executable_path):
                return False, f"Executable not found: {executable_path}", None
            
            if not os.access(executable_path, os.X_OK):
                return False, f"Executable not executable: {executable_path}", None
        
        return True, None, executable_path
    
    def open_url(self, url: str) -> LaunchResult:
        """
        Open URL in default browser
        
        Args:
            url: URL to open
        
        Returns:
            LaunchResult
        """
        try:
            # Validate URL
            is_valid, error = self._validate_url(url)
            if not is_valid:
                return LaunchResult(
                    success=False,
                    output=None,
                    error=error,
                    target=url,
                    operation="open_url"
                )
            
            # Open URL in default browser
            webbrowser.open(url)
            
            self.logger.info(f"Opened URL: {url}")
            
            return LaunchResult(
                success=True,
                output=f"Opened URL in browser: {url}",
                error=None,
                target=url,
                operation="open_url"
            )
        
        except Exception as e:
            self.logger.error(f"Error opening URL: {e}")
            return LaunchResult(
                success=False,
                output=None,
                error=str(e),
                target=url,
                operation="open_url"
            )
    
    def launch_app(self, app_name: str) -> LaunchResult:
        """
        Launch application from allowlist
        
        Args:
            app_name: Application name from allowlist
        
        Returns:
            LaunchResult
        """
        try:
            # Validate app
            is_valid, error, executable_path = self._validate_app_path(app_name)
            if not is_valid:
                return LaunchResult(
                    success=False,
                    output=None,
                    error=error,
                    target=app_name,
                    operation="launch_app"
                )
            
            # Launch app (no arguments, no shell)
            if os.name == 'nt':  # Windows
                subprocess.Popen([executable_path], shell=False)
            else:  # Unix
                subprocess.Popen([executable_path], shell=False, 
                               stdout=subprocess.DEVNULL, 
                               stderr=subprocess.DEVNULL)
            
            self.logger.info(f"Launched app: {app_name} ({executable_path})")
            
            return LaunchResult(
                success=True,
                output=f"Launched application: {app_name}",
                error=None,
                target=app_name,
                operation="launch_app"
            )
        
        except Exception as e:
            self.logger.error(f"Error launching app: {e}")
            return LaunchResult(
                success=False,
                output=None,
                error=str(e),
                target=app_name,
                operation="launch_app"
            )
    
    def list_allowed_apps(self) -> List[Dict[str, Any]]:
        """Get list of allowed applications"""
        apps = []
        for name, info in self.allowlist.items():
            apps.append({
                "name": name,
                "description": info.get("description", ""),
                "risk_level": info.get("risk_level", "MEDIUM"),
                "path": info.get("path", "")
            })
        return apps
    
    def add_app_to_allowlist(self, name: str, path: str, 
                            description: str = "", 
                            risk_level: str = "MEDIUM") -> bool:
        """
        Add application to allowlist
        
        Args:
            name: Application name
            path: Executable path
            description: Description
            risk_level: Risk level (LOW/MEDIUM/HIGH)
        
        Returns:
            True if added successfully
        """
        try:
            self.allowlist[name] = {
                "path": path,
                "description": description,
                "risk_level": risk_level
            }
            self._save_allowlist(self.allowlist)
            self.logger.info(f"Added app to allowlist: {name}")
            return True
        except Exception as e:
            self.logger.error(f"Error adding app to allowlist: {e}")
            return False
    
    def remove_app_from_allowlist(self, name: str) -> bool:
        """
        Remove application from allowlist
        
        Args:
            name: Application name
        
        Returns:
            True if removed successfully
        """
        try:
            if name in self.allowlist:
                del self.allowlist[name]
                self._save_allowlist(self.allowlist)
                self.logger.info(f"Removed app from allowlist: {name}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Error removing app from allowlist: {e}")
            return False
    
    def verify(self, operation: str, result: LaunchResult) -> bool:
        """
        Tool-defined verification method
        Phase 4C: Verify expected result occurred
        
        Args:
            operation: Operation name (open_url, launch_app)
            result: Operation result
        
        Returns:
            True if verification passed
        """
        if not result.success:
            # Operation already failed, skip verification
            return False
        
        if operation == "open_url":
            # For URL opening, just verify it was called successfully
            # Can't easily verify browser actually opened
            return True
        
        elif operation == "launch_app":
            # For app launch, verify it was called successfully
            # Future: check process list for running app
            return True
        
        return True

