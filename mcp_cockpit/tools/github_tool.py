"""
GitHub Tool - READ-ONLY
"""
import json
import subprocess
from typing import Dict, Any, List
from ..config import GITHUB_REPOS, get_timestamp
from ..utils import get_safe_logger

logger = get_safe_logger(__name__)

class GitHubTool:
    """Outil READ-ONLY pour GitHub"""
    
    def __init__(self):
        self.repos = GITHUB_REPOS
    
    def audit(self, repo_key: str) -> Dict[str, Any]:
        """
        iAPF.github.audit
        Audit d'un repository GitHub
        """
        if repo_key not in self.repos:
            return {
                "status": "error",
                "message": f"Unknown repo: {repo_key}",
                "timestamp": get_timestamp()
            }
        
        repo_config = self.repos[repo_key]
        logger.info(f"Auditing GitHub repo: {repo_config['repo']}")
        
        try:
            # Tentative d'utiliser gh CLI
            owner = repo_config["owner"]
            repo = repo_config["repo"]
            
            # Get repo info
            repo_info = self._get_repo_info(owner, repo)
            
            # Get recent commits
            commits = self._get_recent_commits(owner, repo, limit=10)
            
            # Get branches
            branches = self._get_branches(owner, repo)
            
            # Check for common security files
            security_files = self._check_security_files(owner, repo)
            
            return {
                "status": "success",
                "timestamp": get_timestamp(),
                "repo_key": repo_key,
                "repo": repo,
                "owner": owner,
                "url": repo_config["url"],
                "info": repo_info,
                "recent_commits": commits,
                "branches": branches,
                "security_files": security_files
            }
            
        except Exception as e:
            logger.error(f"Error auditing GitHub repo {repo_key}: {str(e)}")
            return self._fallback_audit(repo_key, repo_config)
    
    def _get_repo_info(self, owner: str, repo: str) -> Dict[str, Any]:
        """Récupère les infos du repo via gh CLI ou curl"""
        try:
            cmd = ["gh", "repo", "view", f"{owner}/{repo}", "--json", "name,description,isPrivate,updatedAt,defaultBranchRef"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                return json.loads(result.stdout)
            else:
                return self._fallback_repo_info(owner, repo)
        except FileNotFoundError:
            return self._fallback_repo_info(owner, repo)
        except Exception as e:
            logger.warning(f"Could not get repo info: {str(e)}")
            return {}
    
    def _fallback_repo_info(self, owner: str, repo: str) -> Dict[str, Any]:
        """Fallback info via API publique GitHub"""
        try:
            cmd = ["curl", "-s", f"https://api.github.com/repos/{owner}/{repo}"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                return {
                    "name": data.get("name"),
                    "description": data.get("description"),
                    "isPrivate": data.get("private"),
                    "updatedAt": data.get("updated_at"),
                    "defaultBranchRef": {"name": data.get("default_branch")}
                }
        except Exception as e:
            logger.warning(f"Fallback repo info failed: {str(e)}")
        
        return {"name": repo, "owner": owner}
    
    def _get_recent_commits(self, owner: str, repo: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Récupère les commits récents"""
        try:
            cmd = ["gh", "api", f"repos/{owner}/{repo}/commits?per_page={limit}"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                commits = json.loads(result.stdout)
                return [{
                    "sha": c.get("sha", "")[:7],
                    "message": c.get("commit", {}).get("message", "").split("\n")[0],
                    "author": c.get("commit", {}).get("author", {}).get("name", ""),
                    "date": c.get("commit", {}).get("author", {}).get("date", "")
                } for c in commits[:limit]]
        except Exception as e:
            logger.warning(f"Could not get commits: {str(e)}")
        
        return []
    
    def _get_branches(self, owner: str, repo: str) -> List[str]:
        """Liste les branches"""
        try:
            cmd = ["gh", "api", f"repos/{owner}/{repo}/branches"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                branches = json.loads(result.stdout)
                return [b.get("name") for b in branches]
        except Exception as e:
            logger.warning(f"Could not get branches: {str(e)}")
        
        return []
    
    def _check_security_files(self, owner: str, repo: str) -> Dict[str, bool]:
        """Vérifie la présence de fichiers de sécurité standard"""
        security_files = [
            ".gitignore",
            "requirements.txt",
            "package.json",
            "Dockerfile",
            ".dockerignore",
            "README.md"
        ]
        
        results = {}
        for filename in security_files:
            try:
                cmd = ["gh", "api", f"repos/{owner}/{repo}/contents/{filename}"]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                results[filename] = result.returncode == 0
            except Exception:
                results[filename] = False
        
        return results
    
    def _fallback_audit(self, repo_key: str, repo_config: Dict[str, Any]) -> Dict[str, Any]:
        """Audit fallback minimal"""
        return {
            "status": "limited",
            "timestamp": get_timestamp(),
            "repo_key": repo_key,
            "repo": repo_config["repo"],
            "owner": repo_config["owner"],
            "url": repo_config["url"],
            "message": "Limited audit - requires gh CLI or GitHub token"
        }
    
    def snapshot(self) -> Dict[str, Any]:
        """
        iAPF.github.snapshot
        Snapshot de tous les repos
        """
        logger.info("Creating GitHub snapshot for all repos")
        
        snapshots = {}
        for repo_key in self.repos.keys():
            snapshots[repo_key] = self.audit(repo_key)
        
        return {
            "status": "success",
            "timestamp": get_timestamp(),
            "repos": snapshots
        }

# Singleton
_github_tool = None

def get_github_tool() -> GitHubTool:
    """Factory pour GitHubTool"""
    global _github_tool
    if _github_tool is None:
        _github_tool = GitHubTool()
    return _github_tool
