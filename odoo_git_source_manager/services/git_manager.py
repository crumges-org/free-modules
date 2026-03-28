# -*- coding: utf-8 -*-

import logging
import os
import subprocess
import re
import platform
from pathlib import Path
from odoo import models, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class GitManager(models.AbstractModel):
    """Git Manager Service

    Provides safe wrapper methods for git operations including clone, pull,
    fetch, checkout, and status checks with proper authentication handling.
    """

    _name = "git.manager"
    _description = "Git Manager Service"

    def _get_git_timeout(self):
        """Get git command timeout from configuration"""
        timeout = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("git_mgr.update_timeout", default="300")
        )
        return int(timeout)

    @staticmethod
    def _normalize_path(path):
        """Normalize path for cross-platform compatibility

        Args:
            path (str): Input path

        Returns:
            str: Normalized path
        """
        if not path:
            return path

        # Convert to Path object and normalize
        path_obj = Path(path)

        # Expand user home directory if needed (~)
        path_obj = path_obj.expanduser()

        # Resolve to absolute path
        normalized = str(path_obj.resolve())

        return normalized

    @staticmethod
    def _is_windows():
        """Check if running on Windows

        Returns:
            bool: True if Windows platform
        """
        return platform.system() == "Windows"

    def _prepare_env(self, auth_config):
        """Prepare environment variables for git command

        Args:
            auth_config (dict): Authentication configuration

        Returns:
            dict: Environment variables
        """
        env = os.environ.copy()

        if auth_config.get("type") == "ssh" and auth_config.get("ssh_key_path"):
            # Normalize SSH key path
            ssh_key_path = self._normalize_path(auth_config["ssh_key_path"])

            # Set SSH command to use specific key
            # On Windows, use forward slashes in Git SSH command
            if self._is_windows():
                # Convert Windows path to Git-compatible format
                ssh_key_path = ssh_key_path.replace("\\", "/")

            env["GIT_SSH_COMMAND"] = (
                f"ssh -i {ssh_key_path} "
                f"-o StrictHostKeyChecking=no "
                f"-o UserKnownHostsFile=/dev/null"
            )

        return env

    def _format_repo_url(self, repo_url, auth_config):
        """Format repository URL with authentication if needed

        Args:
            repo_url (str): Original repository URL
            auth_config (dict): Authentication configuration

        Returns:
            str: Formatted URL with authentication
        """
        if auth_config.get("type") == "token" and auth_config.get("token"):
            # Insert token into HTTPS URL
            token = auth_config["token"]

            # Handle different URL formats
            if repo_url.startswith("https://"):
                # Extract domain and path
                parts = repo_url.replace("https://", "").split("/", 1)
                if len(parts) == 2:
                    domain, path = parts
                    # Format: https://token@domain/path
                    return f"https://{token}@{domain}/{path}"

        return repo_url

    def safe_command(self, cmd, cwd=None, env=None, timeout=None):
        """Execute git command safely with logging and error handling

        Args:
            cmd (list): Command and arguments as list
            cwd (str): Working directory
            env (dict): Environment variables
            timeout (int): Command timeout in seconds

        Returns:
            dict: {'returncode': int, 'stdout': str, 'stderr': str}
        """
        if timeout is None:
            timeout = self._get_git_timeout()

        # Log command (mask sensitive data)
        safe_cmd = self._mask_sensitive_data(cmd)
        _logger.info(f"Executing git command: {' '.join(safe_cmd)}")

        try:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                env=env or os.environ,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
                check=False,  # Don't raise on non-zero exit
            )

            stdout = result.stdout.decode("utf-8", errors="replace")
            stderr = result.stderr.decode("utf-8", errors="replace")

            if result.returncode != 0:
                _logger.warning(
                    f"Git command failed with code {result.returncode}: {stderr}"
                )
            else:
                _logger.info("Git command completed successfully")

            return {
                "returncode": result.returncode,
                "stdout": stdout,
                "stderr": stderr,
            }

        except subprocess.TimeoutExpired:
            _logger.error(f"Git command timed out after {timeout} seconds")
            return {
                "returncode": -1,
                "stdout": "",
                "stderr": f"Command timed out after {timeout} seconds",
            }
        except Exception as e:
            _logger.error(f"Error executing git command: {str(e)}", exc_info=True)
            return {
                "returncode": -1,
                "stdout": "",
                "stderr": str(e),
            }

    @staticmethod
    def _mask_sensitive_data(cmd):
        """Mask sensitive data in command for logging

        Args:
            cmd (list): Command arguments

        Returns:
            list: Command with sensitive data masked
        """
        masked = []
        for arg in cmd:
            # Mask tokens in URLs
            if "@" in arg and ("http://" in arg or "https://" in arg):
                # Replace token with asterisks
                arg = re.sub(r"//[^@]+@", "//***@", arg)
            masked.append(arg)
        return masked

    def is_git_repo(self, path):
        """Check if path is a valid git repository

        Args:
            path (str): Directory path

        Returns:
            bool: True if valid git repository
        """
        # Normalize path for the current OS
        normalized_path = self._normalize_path(path)

        if not os.path.exists(normalized_path):
            return False

        git_dir = os.path.join(normalized_path, ".git")
        return os.path.isdir(git_dir)

    def test_connection(self, repo_url, auth_config):
        """Test connection to repository using git ls-remote

        Args:
            repo_url (str): Repository URL
            auth_config (dict): Authentication configuration

        Returns:
            dict: {'success': bool, 'message': str}
        """
        try:
            # Prepare URL and environment
            formatted_url = self._format_repo_url(repo_url, auth_config)
            env = self._prepare_env(auth_config)

            # Execute ls-remote
            cmd = ["git", "ls-remote", "--heads", formatted_url]
            result = self.safe_command(cmd, env=env, timeout=30)

            if result["returncode"] == 0:
                return {
                    "success": True,
                    "message": "Successfully connected to repository",
                }
            else:
                return {
                    "success": False,
                    "message": result["stderr"] or "Failed to connect to repository",
                }

        except Exception as e:
            return {"success": False, "message": str(e)}

    def clone_or_pull(self, repo_url, branch, path, auth_config):
        """Clone repository if not exists, otherwise pull updates

        Args:
            repo_url (str): Repository URL
            branch (str): Branch name
            path (str): Local directory path
            auth_config (dict): Authentication configuration

        Returns:
            dict: {
                'success': bool,
                'message': str,
                'commit': str,
                'action': str (clone/pull)
            }
        """
        try:
            # Prepare URL and environment
            formatted_url = self._format_repo_url(repo_url, auth_config)
            env = self._prepare_env(auth_config)

            # Normalize path
            path = self._normalize_path(path)

            if not self.is_git_repo(path):
                # Clone new repository
                _logger.info(f"Cloning repository {repo_url} to {path}")

                # Ensure parent directory exists
                parent_dir = os.path.dirname(path)
                if not os.path.exists(parent_dir):
                    # Use exist_ok=True for better cross-platform compatibility
                    # Don't use mode parameter on Windows (not fully supported)
                    if self._is_windows():
                        os.makedirs(parent_dir, exist_ok=True)
                    else:
                        os.makedirs(parent_dir, mode=0o755, exist_ok=True)

                # Clone command
                cmd = [
                    "git",
                    "clone",
                    "--branch",
                    branch,
                    "--depth",
                    "1",  # Shallow clone for efficiency
                    formatted_url,
                    path,
                ]

                result = self.safe_command(cmd, env=env)

                if result["returncode"] == 0:
                    commit = self.get_current_commit(path)
                    return {
                        "success": True,
                        "message": "Repository cloned successfully",
                        "commit": commit,
                        "action": "clone",
                    }
                else:
                    return {
                        "success": False,
                        "message": result["stderr"] or "Clone failed",
                        "commit": "",
                        "action": "clone",
                    }
            else:
                # Pull updates
                _logger.info(f"Pulling updates for {path}")

                # Fetch latest changes
                fetch_cmd = ["git", "fetch", "origin", branch]
                fetch_result = self.safe_command(fetch_cmd, cwd=path, env=env)

                if fetch_result["returncode"] != 0:
                    return {
                        "success": False,
                        "message": fetch_result["stderr"] or "Fetch failed",
                        "commit": "",
                        "action": "pull",
                    }

                # Reset to remote branch (hard reset)
                reset_cmd = ["git", "reset", "--hard", f"origin/{branch}"]
                reset_result = self.safe_command(reset_cmd, cwd=path, env=env)

                if reset_result["returncode"] == 0:
                    commit = self.get_current_commit(path)
                    return {
                        "success": True,
                        "message": "Repository updated successfully",
                        "commit": commit,
                        "action": "pull",
                    }
                else:
                    return {
                        "success": False,
                        "message": reset_result["stderr"] or "Reset failed",
                        "commit": "",
                        "action": "pull",
                    }

        except Exception as e:
            _logger.error(f"Error in clone_or_pull: {str(e)}", exc_info=True)
            return {
                "success": False,
                "message": str(e),
                "commit": "",
                "action": "unknown",
            }

    def get_current_commit(self, path):
        """Get current commit hash

        Args:
            path (str): Repository path

        Returns:
            str: Commit hash or None
        """
        # Normalize path
        path = self._normalize_path(path)

        if not self.is_git_repo(path):
            return None

        cmd = ["git", "rev-parse", "HEAD"]
        result = self.safe_command(cmd, cwd=path, timeout=10)

        if result["returncode"] == 0:
            return result["stdout"].strip()

        return None

    def checkout(self, path, ref):
        """Checkout specific reference (branch, tag, commit)

        Args:
            path (str): Repository path
            ref (str): Git reference

        Returns:
            dict: {'success': bool, 'message': str}
        """
        # Normalize path
        path = self._normalize_path(path)

        if not self.is_git_repo(path):
            return {"success": False, "message": "Not a git repository"}

        cmd = ["git", "checkout", ref]
        result = self.safe_command(cmd, cwd=path)

        if result["returncode"] == 0:
            return {"success": True, "message": f"Checked out {ref} successfully"}
        else:
            return {"success": False, "message": result["stderr"] or "Checkout failed"}

    def get_status(self, path):
        """Get repository status

        Args:
            path (str): Repository path

        Returns:
            dict: {
                'clean': bool,
                'changes': list,
                'branch': str
            }
        """
        # Normalize path
        path = self._normalize_path(path)

        if not self.is_git_repo(path):
            return {"clean": False, "changes": ["Not a git repository"], "branch": None}

        # Get status
        status_cmd = ["git", "status", "--porcelain"]
        status_result = self.safe_command(status_cmd, cwd=path, timeout=10)

        # Get branch
        branch_cmd = ["git", "rev-parse", "--abbrev-ref", "HEAD"]
        branch_result = self.safe_command(branch_cmd, cwd=path, timeout=10)

        changes = []
        if status_result["returncode"] == 0:
            stdout = status_result["stdout"].strip()
            if stdout:
                changes = stdout.split("\n")

        branch = None
        if branch_result["returncode"] == 0:
            branch = branch_result["stdout"].strip()

        return {"clean": len(changes) == 0, "changes": changes, "branch": branch}

    def fetch(self, path, remote="origin"):
        """Fetch updates from remote

        Args:
            path (str): Repository path
            remote (str): Remote name

        Returns:
            dict: {'success': bool, 'message': str}
        """
        # Normalize path
        path = self._normalize_path(path)

        if not self.is_git_repo(path):
            return {"success": False, "message": "Not a git repository"}

        cmd = ["git", "fetch", remote]
        result = self.safe_command(cmd, cwd=path)

        if result["returncode"] == 0:
            return {"success": True, "message": "Fetch completed successfully"}
        else:
            return {"success": False, "message": result["stderr"] or "Fetch failed"}
