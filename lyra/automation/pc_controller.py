"""
PC Controller
Handles PC automation tasks (file operations, applications, system control)
"""

import os
import subprocess
import platform
from pathlib import Path
from typing import List, Dict, Any, Optional
from lyra.core.logger import get_logger
from lyra.core.exceptions import AutomationError


class PCController:
    """
    PC automation controller
    Provides safe file operations, application control, and system commands
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.os_type = platform.system()  # Windows, Linux, Darwin (macOS)
    
    # File Operations
    
    def create_file(self, filename: str, content: str = "", directory: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a new file
        
        Args:
            filename: Name of file to create
            content: Optional file content
            directory: Optional directory (defaults to user's Documents)
        
        Returns:
            Result dictionary
        """
        try:
            if directory is None:
                directory = str(Path.home() / "Documents")
            
            filepath = Path(directory) / filename
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            self.logger.info(f"Created file: {filepath}")
            return {"success": True, "filepath": str(filepath)}
        
        except Exception as e:
            raise AutomationError(f"Failed to create file: {e}")
    
    def delete_file(self, filename: str, directory: Optional[str] = None) -> Dict[str, Any]:
        """
        Delete a file
        
        Args:
            filename: Name of file to delete
            directory: Optional directory
        
        Returns:
            Result dictionary
        """
        try:
            if directory is None:
                directory = str(Path.home() / "Documents")
            
            filepath = Path(directory) / filename
            
            if not filepath.exists():
                raise AutomationError(f"File not found: {filepath}")
            
            filepath.unlink()
            self.logger.info(f"Deleted file: {filepath}")
            return {"success": True, "filepath": str(filepath)}
        
        except Exception as e:
            raise AutomationError(f"Failed to delete file: {e}")
    
    def open_file(self, filename: str, directory: Optional[str] = None) -> Dict[str, Any]:
        """
        Open a file with default application
        
        Args:
            filename: Name of file to open
            directory: Optional directory
        
        Returns:
            Result dictionary
        """
        try:
            if directory is None:
                directory = str(Path.home() / "Documents")
            
            filepath = Path(directory) / filename
            
            if not filepath.exists():
                raise AutomationError(f"File not found: {filepath}")
            
            if self.os_type == "Windows":
                os.startfile(str(filepath))
            elif self.os_type == "Darwin":  # macOS
                subprocess.run(["open", str(filepath)])
            else:  # Linux
                subprocess.run(["xdg-open", str(filepath)])
            
            self.logger.info(f"Opened file: {filepath}")
            return {"success": True, "filepath": str(filepath)}
        
        except Exception as e:
            raise AutomationError(f"Failed to open file: {e}")
    
    def file_exists(self, filename: str, directory: Optional[str] = None) -> bool:
        """Check if file exists"""
        if directory is None:
            directory = str(Path.home() / "Documents")
        
        filepath = Path(directory) / filename
        return filepath.exists()
    
    def search_files(self, query: str, directory: Optional[str] = None, max_results: int = 10) -> List[str]:
        """
        Search for files
        
        Args:
            query: Search query
            directory: Directory to search (defaults to Documents)
            max_results: Maximum number of results
        
        Returns:
            List of matching file paths
        """
        try:
            if directory is None:
                directory = str(Path.home() / "Documents")
            
            search_path = Path(directory)
            results = []
            
            for filepath in search_path.rglob(f"*{query}*"):
                if filepath.is_file():
                    results.append(str(filepath))
                    if len(results) >= max_results:
                        break
            
            self.logger.info(f"Found {len(results)} files matching '{query}'")
            return results
        
        except Exception as e:
            raise AutomationError(f"Failed to search files: {e}")
    
    # Application Control
    
    def launch_application(self, app_name: str) -> Dict[str, Any]:
        """
        Launch an application
        
        Args:
            app_name: Application name
        
        Returns:
            Result dictionary
        """
        try:
            app_map = {
                "notepad": "notepad.exe" if self.os_type == "Windows" else "gedit",
                "calculator": "calc.exe" if self.os_type == "Windows" else "gnome-calculator",
                "chrome": "chrome.exe" if self.os_type == "Windows" else "google-chrome",
                "firefox": "firefox.exe" if self.os_type == "Windows" else "firefox",
            }
            
            executable = app_map.get(app_name.lower(), app_name)
            
            if self.os_type == "Windows":
                subprocess.Popen(executable, shell=True)
            else:
                subprocess.Popen([executable])
            
            self.logger.info(f"Launched application: {app_name}")
            return {"success": True, "app_name": app_name}
        
        except Exception as e:
            raise AutomationError(f"Failed to launch application: {e}")
    
    def close_application(self, app_name: str) -> Dict[str, Any]:
        """
        Close an application (Windows only for now)
        
        Args:
            app_name: Application name
        
        Returns:
            Result dictionary
        """
        try:
            if self.os_type == "Windows":
                subprocess.run(["taskkill", "/F", "/IM", f"{app_name}.exe"], 
                             capture_output=True)
            else:
                subprocess.run(["pkill", app_name])
            
            self.logger.info(f"Closed application: {app_name}")
            return {"success": True, "app_name": app_name}
        
        except Exception as e:
            raise AutomationError(f"Failed to close application: {e}")
    
    # System Control
    
    def shutdown_system(self, delay_seconds: int = 0) -> Dict[str, Any]:
        """
        Shutdown system
        
        Args:
            delay_seconds: Delay before shutdown
        
        Returns:
            Result dictionary
        """
        try:
            if self.os_type == "Windows":
                subprocess.run(["shutdown", "/s", "/t", str(delay_seconds)])
            else:
                subprocess.run(["shutdown", "-h", f"+{delay_seconds//60}"])
            
            self.logger.warning(f"System shutdown initiated (delay: {delay_seconds}s)")
            return {"success": True, "delay_seconds": delay_seconds}
        
        except Exception as e:
            raise AutomationError(f"Failed to shutdown system: {e}")
    
    def restart_system(self, delay_seconds: int = 0) -> Dict[str, Any]:
        """
        Restart system
        
        Args:
            delay_seconds: Delay before restart
        
        Returns:
            Result dictionary
        """
        try:
            if self.os_type == "Windows":
                subprocess.run(["shutdown", "/r", "/t", str(delay_seconds)])
            else:
                subprocess.run(["shutdown", "-r", f"+{delay_seconds//60}"])
            
            self.logger.warning(f"System restart initiated (delay: {delay_seconds}s)")
            return {"success": True, "delay_seconds": delay_seconds}
        
        except Exception as e:
            raise AutomationError(f"Failed to restart system: {e}")
