"""
Safe File Tool - Phase 4B
Real file read/write implementation with strict sandboxing
NO shell execution, NO delete (yet)
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from lyra.core.logger import get_logger


@dataclass
class FileOperationResult:
    """Result of file operation"""
    success: bool
    output: Any
    error: Optional[str]
    bytes_read: int = 0
    bytes_written: int = 0
    operation: str = ""
    target_path: Optional[str] = None  # For verification


class SafeFileTool:
    """
    Safe file operations with strict sandboxing
    Phase 4B: read_file and write_file only
    """
    
    # Maximum file size (5MB default)
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
    
    # Allowed file extensions
    ALLOWED_EXTENSIONS = {
        '.txt', '.md', '.py', '.json', '.yaml', '.yml',
        '.csv', '.log', '.conf', '.cfg', '.ini'
    }
    
    # Blocked paths (system directories)
    BLOCKED_PATHS = [
        '/etc', '/sys', '/proc', '/boot', '/dev', '/root',
        'C:\\Windows', 'C:\\Program Files', 'C:\\Program Files (x86)',
        'C:\\ProgramData', '/System', '/Library/System'
    ]
    
    # Blocked path patterns
    BLOCKED_PATTERNS = [
        '/.', '\\.', 'node_modules', '__pycache__', '.git'
    ]
    
    def __init__(self):
        self.logger = get_logger(__name__)
        
        # Determine allowed base paths
        self.allowed_paths = self._get_allowed_paths()
        self.logger.info(f"Safe file tool initialized with {len(self.allowed_paths)} allowed paths")
    
    def _get_allowed_paths(self) -> List[Path]:
        """Get list of allowed base paths"""
        allowed = []
        
        # User home directory
        home = Path.home()
        allowed.append(home)
        
        # Current project directory (if identifiable)
        cwd = Path.cwd()
        allowed.append(cwd)
        
        # Explicitly allowed project directories
        # (Can be configured via environment or config file)
        project_root = Path(__file__).parent.parent.parent
        allowed.append(project_root)
        
        return allowed
    
    def _normalize_path(self, path: str) -> Path:
        """
        Normalize path and resolve to absolute
        Prevents traversal attacks
        """
        # Convert to Path object
        p = Path(path)
        
        # Resolve to absolute path (resolves .., symlinks, etc.)
        try:
            p = p.resolve()
        except Exception as e:
            raise ValueError(f"Invalid path: {e}")
        
        return p
    
    def _is_path_allowed(self, path: Path) -> bool:
        """
        Check if path is allowed
        
        Args:
            path: Normalized absolute path
        
        Returns:
            True if allowed
        """
        # Check if path is under any allowed base path
        is_under_allowed = False
        for allowed_base in self.allowed_paths:
            try:
                path.relative_to(allowed_base)
                is_under_allowed = True
                break
            except ValueError:
                continue
        
        if not is_under_allowed:
            self.logger.warning(f"Path not under allowed directories: {path}")
            return False
        
        # Check against blocked paths
        path_str = str(path)
        for blocked in self.BLOCKED_PATHS:
            if path_str.startswith(blocked):
                self.logger.warning(f"Path in blocked directory: {path}")
                return False
        
        # Check against blocked patterns
        for pattern in self.BLOCKED_PATTERNS:
            if pattern in path_str:
                self.logger.warning(f"Path contains blocked pattern '{pattern}': {path}")
                return False
        
        return True
    
    def _is_extension_allowed(self, path: Path) -> bool:
        """Check if file extension is allowed"""
        ext = path.suffix.lower()
        
        if ext not in self.ALLOWED_EXTENSIONS:
            self.logger.warning(f"File extension not allowed: {ext}")
            return False
        
        return True
    
    def _validate_file_size(self, path: Path) -> bool:
        """Check if file size is within limits"""
        if not path.exists():
            return True  # New file, will check on write
        
        size = path.stat().st_size
        if size > self.MAX_FILE_SIZE:
            self.logger.warning(f"File too large: {size} bytes > {self.MAX_FILE_SIZE}")
            return False
        
        return True
    
    def read_file(self, path: str) -> FileOperationResult:
        """
        Read file contents
        
        Args:
            path: File path to read
        
        Returns:
            FileOperationResult
        """
        try:
            # Normalize and validate path
            normalized_path = self._normalize_path(path)
            
            if not self._is_path_allowed(normalized_path):
                return FileOperationResult(
                    success=False,
                    output=None,
                    error="Path not allowed",
                    path=str(normalized_path),
                    operation="read"
                )
            
            if not self._is_extension_allowed(normalized_path):
                return FileOperationResult(
                    success=False,
                    output=None,
                    error=f"File extension not allowed (allowed: {', '.join(self.ALLOWED_EXTENSIONS)})",
                    path=str(normalized_path),
                    operation="read"
                )
            
            if not normalized_path.exists():
                return FileOperationResult(
                    success=False,
                    output=None,
                    error="File does not exist",
                    path=str(normalized_path),
                    operation="read"
                )
            
            if not normalized_path.is_file():
                return FileOperationResult(
                    success=False,
                    output=None,
                    error="Path is not a file",
                    path=str(normalized_path),
                    operation="read"
                )
            
            if not self._validate_file_size(normalized_path):
                return FileOperationResult(
                    success=False,
                    output=None,
                    error=f"File too large (max: {self.MAX_FILE_SIZE} bytes)",
                    path=str(normalized_path),
                    operation="read"
                )
            
            # Read file
            content = normalized_path.read_text(encoding='utf-8')
            bytes_read = len(content.encode('utf-8'))
            
            self.logger.info(f"Read file: {normalized_path} ({bytes_read} bytes)")
            
            return FileOperationResult(
                success=True,
                output=content,
                error=None,
                path=str(normalized_path),
                operation="read",
                bytes_read=bytes_read
            )
        
        except Exception as e:
            self.logger.error(f"Error reading file: {e}")
            return FileOperationResult(
                success=False,
                output=None,
                error=str(e),
                path=path,
                operation="read"
            )
    
    def write_file(self, path: str, content: str, append: bool = False) -> FileOperationResult:
        """
        Write file contents
        
        Args:
            path: File path to write
            content: Content to write
            append: If True, append to file
        
        Returns:
            FileOperationResult
        """
        try:
            # Normalize and validate path
            normalized_path = self._normalize_path(path)
            
            if not self._is_path_allowed(normalized_path):
                return FileOperationResult(
                    success=False,
                    output=None,
                    error="Path not allowed",
                    path=str(normalized_path),
                    operation="write"
                )
            
            if not self._is_extension_allowed(normalized_path):
                return FileOperationResult(
                    success=False,
                    output=None,
                    error=f"File extension not allowed (allowed: {', '.join(self.ALLOWED_EXTENSIONS)})",
                    path=str(normalized_path),
                    operation="write"
                )
            
            # Check content size
            content_bytes = len(content.encode('utf-8'))
            if content_bytes > self.MAX_FILE_SIZE:
                return FileOperationResult(
                    success=False,
                    output=None,
                    error=f"Content too large (max: {self.MAX_FILE_SIZE} bytes)",
                    path=str(normalized_path),
                    operation="write"
                )
            
            # Read existing content for diff logging
            old_content = None
            if normalized_path.exists():
                try:
                    old_content = normalized_path.read_text(encoding='utf-8')
                except Exception:
                    pass  # Ignore read errors for diff
            
            # Create parent directories if needed
            normalized_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file
            if append:
                with open(normalized_path, 'a', encoding='utf-8') as f:
                    f.write(content)
            else:
                normalized_path.write_text(content, encoding='utf-8')
            
            # Log diff
            self._log_file_diff(normalized_path, old_content, content, append)
            
            self.logger.info(f"Wrote file: {normalized_path} ({content_bytes} bytes, append={append})")
            
            return FileOperationResult(
                success=True,
                output=f"Written {content_bytes} bytes",
                error=None,
                path=str(normalized_path),
                operation="write",
                bytes_written=content_bytes
            )
        
        except Exception as e:
            self.logger.error(f"Error writing file: {e}")
            return FileOperationResult(
                success=False,
                output=None,
                error=str(e),
                path=path,
                operation="write"
            )
    
    def _log_file_diff(self, path: Path, old_content: Optional[str], 
                      new_content: str, append: bool):
        """Log file diff for auditability"""
        if old_content is None:
            self.logger.info(f"File created: {path}")
        elif append:
            added_lines = len(new_content.splitlines())
            self.logger.info(f"File appended: {path} (+{added_lines} lines)")
        else:
            old_lines = old_content.splitlines()
            new_lines = new_content.splitlines()
            self.logger.info(
                f"File modified: {path} "
                f"({len(old_lines)} -> {len(new_lines)} lines)"
            )
    
    def verify(self, operation: str, result: FileOperationResult) -> bool:
        """
        Tool-defined verification method
        Phase 4C: Verify expected result occurred
        
        Args:
            operation: Operation name (read_file, write_file)
            result: Operation result
        
        Returns:
            True if verification passed
        """
        if not result.success:
            # Operation already failed, skip verification
            return False
        
        if operation == "read_file":
            # Verify content was returned
            return result.output is not None and len(result.output) > 0
        
        elif operation == "write_file":
            # Verify file exists and has content
            if result.target_path and os.path.exists(result.target_path):
                try:
                    size = os.path.getsize(result.target_path)
                    return size > 0
                except:
                    return False
            return False
        
        return True

