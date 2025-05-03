import git
import os
import shutil
import logging
from typing import Optional
from pathlib import Path
from uuid import UUID

from f_operator_service.core.config import Settings

logger = logging.getLogger(__name__)

class GitServiceError(Exception):
    """Base exception for GitService errors."""
    pass

class RepoNotFoundError(GitServiceError):
    """Raised when a repository cannot be found or accessed."""
    pass

class AuthenticationError(GitServiceError):
    """Raised for Git authentication failures."""
    pass

class GitCommandError(GitServiceError):
    """Raised when a git command fails."""
    pass

class GitService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.base_path = Path(settings.GIT_REPO_BASE_PATH)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.git_ssh_cmd = None
        if settings.GIT_SSH_KEY_PATH:
            ssh_key_path = Path(settings.GIT_SSH_KEY_PATH).expanduser()
            if not ssh_key_path.is_file():
                logger.warning(f"SSH key not found at {ssh_key_path}, SSH auth disabled.")
            else:
                # Ensure correct permissions (e.g., 600)
                os.chmod(ssh_key_path, 0o600)
                self.git_ssh_cmd = f'ssh -i {ssh_key_path} -o StrictHostKeyChecking=no'
                logger.info(f"Using SSH key for Git authentication: {ssh_key_path}")

    def _get_repo_local_path(self, agent_id: str) -> Path:
        """Determines the local path for an agent's repository."""
        return self.base_path / agent_id

    def _get_git_env(self) -> Optional[Dict[str, str]]:
        """Prepares environment variables for Git commands (e.g., for auth)."""
        env = os.environ.copy()
        if self.git_ssh_cmd:
            env['GIT_SSH_COMMAND'] = self.git_ssh_cmd
            # Unset potential HTTPS creds if using SSH
            env.pop('GIT_ASKPASS', None)
            env.pop('GIT_USERNAME', None)
            env.pop('GIT_PASSWORD', None)
        elif self.settings.GIT_ACCESS_TOKEN:
            # Simplest way for HTTPS with token is often embedding in URL or using credential helper.
            # GitPython doesn't directly use an env var for the token typically.
            # We might need to configure credential helper or modify URL, 
            # or rely on user configuring system credential helper.
            # For now, log a warning if SSH isn't set but token is.
            logger.warning("GIT_ACCESS_TOKEN provided but HTTPS auth helper not explicitly configured. Git may prompt or fail if credentials aren't cached.")
            # If needed, could explore git credential helpers.
        return env

    def clone_or_pull(self, repo_url: str, agent_id: str) -> str:
        """Clones repo if not present locally, otherwise pulls latest changes."""
        local_path = self._get_repo_local_path(agent_id)
        git_env = self._get_git_env()
        repo = None

        try:
            if local_path.exists() and local_path.is_dir():
                logger.info(f"Repository for agent {agent_id} exists locally at {local_path}. Pulling latest changes.")
                repo = git.Repo(local_path)
                # Ensure we are on the default branch (or handle detatched HEAD)
                try:
                    repo.git.checkout(repo.remotes[self.settings.GIT_DEFAULT_REMOTE].refs[0].remote_head)
                except Exception:
                    logger.warning(f"Could not checkout default branch for {agent_id}, attempting pull anyway.")
                
                origin = repo.remotes[self.settings.GIT_DEFAULT_REMOTE]
                origin.pull(env=git_env)
                logger.info(f"Successfully pulled updates for agent {agent_id}.")
            else:
                logger.info(f"Cloning repository {repo_url} for agent {agent_id} to {local_path}.")
                repo = git.Repo.clone_from(repo_url, local_path, env=git_env)
                logger.info(f"Successfully cloned repository for agent {agent_id}.")
            return str(local_path)
        except git.GitCommandError as e:
            logger.error(f"Git command failed for agent {agent_id}: {e}", exc_info=True)
            if "Authentication failed" in str(e) or "Permission denied" in str(e):
                raise AuthenticationError(f"Git authentication failed for {repo_url}. Check SSH key or access token.") from e
            elif "not found" in str(e).lower():
                 raise RepoNotFoundError(f"Repository not found at {repo_url}.") from e
            raise GitCommandError(f"Git command failed for {repo_url}: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error during clone/pull for agent {agent_id}: {e}", exc_info=True)
            raise GitServiceError(f"Failed to clone or pull {repo_url}: {e}") from e

    def create_branch(self, local_path_str: str, branch_name: str, base_branch: Optional[str] = None) -> None:
        """Creates and checks out a new branch from base_branch (defaults to current)."""
        local_path = Path(local_path_str)
        if not local_path.is_dir():
            raise RepoNotFoundError(f"Local repository not found at {local_path}")
        
        repo = git.Repo(local_path)
        base = base_branch if base_branch else repo.active_branch
        logger.info(f"Creating branch '{branch_name}' from '{base}' in {local_path}")
        try:
            new_branch = repo.create_head(branch_name, commit=base)
            new_branch.checkout()
            logger.info(f"Successfully created and checked out branch '{branch_name}'.")
        except git.GitCommandError as e:
            logger.error(f"Failed to create branch '{branch_name}' in {local_path}: {e}", exc_info=True)
            raise GitCommandError(f"Failed to create branch '{branch_name}': {e}") from e
        except Exception as e:
             # Catch potential issues like branch already exists
            logger.error(f"Error creating branch '{branch_name}': {e}", exc_info=True)
            if "already exists" in str(e):
                 raise GitCommandError(f"Branch '{branch_name}' already exists.") from e
            raise GitServiceError(f"Failed to create branch '{branch_name}': {e}") from e

    def checkout_branch(self, local_path_str: str, branch_name: str) -> None:
        """Checks out an existing branch."""
        local_path = Path(local_path_str)
        if not local_path.is_dir():
            raise RepoNotFoundError(f"Local repository not found at {local_path}")
        
        repo = git.Repo(local_path)
        logger.info(f"Checking out branch '{branch_name}' in {local_path}")
        try:
            repo.git.checkout(branch_name)
            logger.info(f"Successfully checked out branch '{branch_name}'.")
        except git.GitCommandError as e:
            logger.error(f"Failed to checkout branch '{branch_name}' in {local_path}: {e}", exc_info=True)
            raise GitCommandError(f"Failed to checkout branch '{branch_name}': {e}") from e

    def add_and_commit(self, local_path_str: str, message: str, author_name: str = "F Operator", author_email: str = "f-operator@kfm.system") -> str:
        """Stages all changes and commits them."""
        local_path = Path(local_path_str)
        if not local_path.is_dir():
            raise RepoNotFoundError(f"Local repository not found at {local_path}")
        
        repo = git.Repo(local_path)
        logger.info(f"Staging and committing changes in {local_path} with message: '{message}'")
        try:
            # Check for changes
            if not repo.is_dirty(untracked_files=True):
                 logger.warning(f"No changes detected in {local_path}, skipping commit.")
                 return repo.head.commit.hexsha

            repo.git.add(A=True) # Stage all changes
            author = git.Actor(author_name, author_email)
            commit = repo.index.commit(message, author=author, committer=author)
            logger.info(f"Successfully committed changes. Commit hash: {commit.hexsha}")
            return commit.hexsha
        except git.GitCommandError as e:
            logger.error(f"Failed to commit changes in {local_path}: {e}", exc_info=True)
            raise GitCommandError(f"Failed to commit changes: {e}") from e

    def push_branch(self, local_path_str: str, branch_name: str) -> None:
        """Pushes the specified local branch to the default remote."""
        local_path = Path(local_path_str)
        if not local_path.is_dir():
            raise RepoNotFoundError(f"Local repository not found at {local_path}")
        
        repo = git.Repo(local_path)
        git_env = self._get_git_env()
        logger.info(f"Pushing branch '{branch_name}' to remote '{self.settings.GIT_DEFAULT_REMOTE}' from {local_path}")
        try:
            origin = repo.remotes[self.settings.GIT_DEFAULT_REMOTE]
            # Push the current branch to the remote, setting upstream if needed
            result = origin.push(refspec=f'{branch_name}:{branch_name}', env=git_env, set_upstream=True)
            
            # Check push result flags for errors
            push_failed = False
            for info in result:
                if info.flags & (git.PushInfo.ERROR | git.PushInfo.REJECTED | git.PushInfo.REMOTE_FAILURE):
                    logger.error(f"Failed to push branch '{branch_name}': {info.summary}")
                    push_failed = True
            
            if push_failed:
                raise GitCommandError(f"Failed to push branch '{branch_name}'. Check logs for details.")
                
            logger.info(f"Successfully pushed branch '{branch_name}'.")
        except git.GitCommandError as e:
            logger.error(f"Failed to push branch '{branch_name}': {e}", exc_info=True)
            if "Authentication failed" in str(e) or "Permission denied" in str(e):
                raise AuthenticationError(f"Git authentication failed during push. Check SSH key or access token.") from e
            raise GitCommandError(f"Failed to push branch '{branch_name}': {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error during push for branch '{branch_name}': {e}", exc_info=True)
            raise GitServiceError(f"Failed to push branch '{branch_name}': {e}") from e

    def get_current_commit(self, local_path_str: str) -> str:
        """Gets the hexsha of the current HEAD commit."""
        local_path = Path(local_path_str)
        if not local_path.is_dir():
            raise RepoNotFoundError(f"Local repository not found at {local_path}")
        
        try:
            repo = git.Repo(local_path)
            return repo.head.commit.hexsha
        except Exception as e:
            logger.error(f"Failed to get current commit hash for {local_path}: {e}", exc_info=True)
            raise GitServiceError(f"Could not get current commit hash: {e}") from e

    def delete_local_repo(self, agent_id: str) -> None:
        """Deletes the local repository clone for the given agent ID."""
        local_path = self._get_repo_local_path(agent_id)
        if local_path.exists() and local_path.is_dir():
            logger.warning(f"Deleting local repository clone at {local_path}")
            try:
                shutil.rmtree(local_path)
                logger.info(f"Successfully deleted {local_path}.")
            except Exception as e:
                logger.error(f"Failed to delete local repository {local_path}: {e}", exc_info=True)
                # Don't raise, just log error, as it's cleanup
        else:
            logger.info(f"Local repository clone not found at {local_path}, skipping deletion.") 