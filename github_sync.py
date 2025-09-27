# github_sync.py
import json
import time
from git import Repo, GitCommandError
from datetime import datetime
import logging

# 初始化日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler('sync.log'),
        logging.StreamHandler()
    ]
)

class GitHubSyncer:
    def __init__(self, config_path='git_config.json'):
        self.config = self._load_config(config_path)
        self.retry_count = self.config['errorHandling']['retryCount']

    def _load_config(self, path):
        """加载并验证配置文件"""
        try:
            with open(path) as f:
                config = json.load(f)
                assert config['remote']['url'], "仓库URL不能为空"
                return config
        except Exception as e:
            logging.error(f"配置加载失败: {e}")
            raise

    def _set_git_identity(self, repo):
        """配置提交身份"""
        repo.config_writer().set_value(
            "user", "name", self.config['user']['name']).release()
        repo.config_writer().set_value(
            "user", "email", self.config['user']['email']).release()

    def _generate_commit_msg(self):
        """生成提交信息"""
        template = self.config['commit']['messageTemplate']
        if self.config['commit']['includeTimestamp']:
            return template.format(timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        return template

    def sync(self):
        """执行同步操作"""
        for attempt in range(1, self.retry_count + 1):
            try:
                repo = Repo.init('.')
                self._set_git_identity(repo)

                if self.config['commit']['autoAdd']:
                    repo.git.add(A=True)

                if repo.is_dirty() or repo.untracked_files:
                    repo.index.commit(self._generate_commit_msg())

                if 'origin' not in repo.remotes:
                    repo.create_remote('origin', self.config['remote']['url'])

                # 正确构建 git push 参数
                branch_name = self.config['branch']['default']
                
                # 根据 GitPython 文档，push 方法需要正确区分 refspec 和选项
                if self.config['branch']['createOnPush']:
                    # 使用 set_upstream 选项正确设置上游分支
                    repo.git.push('origin', branch_name, set_upstream=True)
                else:
                    # 普通推送
                    repo.remotes.origin.push(branch_name)
                logging.info("同步成功")
                return True

            except GitCommandError as e:
                logging.warning(f"尝试 {attempt}/{self.retry_count} 失败: {e}")
                if attempt == self.retry_count:
                    logging.error("同步最终失败")
                    raise
                time.sleep(2 ** attempt)  # 指数退避

if __name__ == '__main__':
    try:
        syncer = GitHubSyncer()
        syncer.sync()
    except Exception as e:
        if syncer.config['errorHandling']['showDetails']:
            logging.exception("错误详情")
        exit(1)