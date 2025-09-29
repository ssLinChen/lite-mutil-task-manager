"""
Git集成模块
简化的Git信息提取和Hook管理
保持向后兼容
"""

from git import Repo
import os


class GitIntegration:
    """Git集成管理器"""
    
    def __init__(self, repo_path=None):
        """
        初始化Git集成器
        
        Args:
            repo_path: Git仓库路径，如果为None则自动检测
        """
        try:
            if repo_path is None:
                # 尝试从当前目录向上查找Git仓库
                current_dir = os.getcwd()
                while current_dir and current_dir != os.path.dirname(current_dir):
                    git_dir = os.path.join(current_dir, '.git')
                    if os.path.exists(git_dir):
                        self.repo = Repo(current_dir)
                        self.has_git = True
                        break
                    current_dir = os.path.dirname(current_dir)
                else:
                    # 如果没找到，尝试当前目录
                    self.repo = Repo('.')
                    self.has_git = True
            else:
                self.repo = Repo(repo_path)
                self.has_git = True
        except Exception:
            self.has_git = False
            print("警告: 未找到有效的Git仓库，将使用默认Git信息")
    
    def get_commit_info(self) -> dict:
        """
        获取提交信息（简化版）
        
        Returns:
            dict: 包含提交哈希、消息和修改文件的信息
        """
        if not self.has_git:
            import datetime
            return {
                'hash': 'local',
                'message': f'Auto-commit at {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
                'files': ['sync.log']
            }
            
        try:
            commit = self.repo.head.commit
            return {
                'hash': commit.hexsha[:7],
                'message': commit.message.strip(),
                'files': list(commit.stats.files.keys())[:5]  # 最多显示5个文件
            }
        except Exception:
            return {
                'hash': 'unknown',
                'message': '无法获取提交信息',
                'files': []
            }
    
    def get_modified_files(self) -> list:
        """
        获取工作区中修改的文件列表
        
        Returns:
            list: 修改的文件路径列表
        """
        try:
            # 获取未暂存的修改
            modified = [item.a_path for item in self.repo.index.diff(None)]
            # 获取未跟踪的文件
            untracked = self.repo.untracked_files
            return modified + untracked
        except Exception:
            return []
    

    
    def validate_repository(self) -> bool:
        """验证当前目录是否为有效的Git仓库"""
        if not hasattr(self, 'has_git') or not self.has_git:
            return True
            
        try:
            return not self.repo.bare and hasattr(self.repo, 'git_dir')
        except Exception:
            return False
    
    # 向后兼容的方法
    def get_latest_commit(self) -> dict:
        """向后兼容：获取最新提交信息"""
        return self.get_commit_info()
    
    def get_branch_info(self) -> dict:
        """向后兼容：获取分支信息"""
        try:
            branch = self.repo.active_branch
            return {
                'name': branch.name,
                'is_dirty': self.repo.is_dirty(),
                'ahead': len(list(self.repo.iter_commits(f'{branch.name}@{{u}}..{branch.name}'))),
                'behind': len(list(self.repo.iter_commits(f'{branch.name}..{branch.name}@{{u}}')))
            }
        except Exception:
            return {
                'name': 'unknown',
                'is_dirty': False,
                'ahead': 0,
                'behind': 0
            }