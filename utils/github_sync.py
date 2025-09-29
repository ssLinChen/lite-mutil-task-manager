# github_sync.py
import json
import time
import os
import subprocess
import argparse
from git import Repo, GitCommandError
from datetime import datetime
import logging
import re
import sys


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
        self.repo = None

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

    def _generate_commit_msg(self, custom_message=None):
        """生成提交信息"""
        # 优先使用命令行参数提供的消息
        if custom_message:
            return custom_message
        
        # 否则使用配置文件中的模板
        template = self.config['commit']['messageTemplate']
        if self.config['commit']['includeTimestamp']:
            return template.format(timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        return template
        
    def _test_ssh_connection(self, url):
        """测试SSH连接是否正常"""
        try:
            # 从URL中提取主机名
            match = re.match(r'git@([^:]+):', url)
            if not match:
                logging.warning(f"无法从URL解析主机名: {url}")
                return False
                
            host = match.group(1)
            logging.info(f"测试SSH连接到: {host}")
            
            # 使用subprocess执行SSH连接测试
            result = subprocess.run(
                ['ssh', '-T', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=no', f'git@{host}'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=5,
                text=True
            )
            
            # GitHub通常返回错误码1，但这实际上表示连接成功
            if result.returncode in [1, 0]:
                logging.info(f"SSH连接测试成功: {host}")
                return True
            else:
                logging.warning(f"SSH连接测试失败: {result.stderr}")
                return False
        except Exception as e:
            logging.warning(f"SSH连接测试异常: {e}")
            return False
            
    def _check_repository_exists(self, url):
        """检查仓库是否存在且可访问"""
        try:
            # 从URL中提取用户名和仓库名
            match = re.match(r'git@([^:]+):([^/]+)/([^.]+)\.git', url)
            if not match:
                logging.warning(f"无法从URL解析仓库信息: {url}")
                return False
                
            host, username, repo_name = match.groups()
            logging.info(f"检查仓库是否存在: {username}/{repo_name} 在 {host}")
            
            # 尝试列出远程仓库的引用
            cmd = ['git', 'ls-remote', url, 'HEAD']
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=10,
                text=True
            )
            
            if result.returncode == 0:
                logging.info(f"仓库存在且可访问: {url}")
                return True
            else:
                logging.warning(f"仓库不存在或无法访问: {result.stderr}")
                return False
        except Exception as e:
            logging.warning(f"检查仓库存在性异常: {e}")
            return False

    def sync(self, commit_message=None):
        """执行同步操作"""
        # 初始化仓库
        try:
            self.repo = Repo.init('.')
            logging.info("Git仓库初始化成功")
        except Exception as e:
            logging.error(f"Git仓库初始化失败: {e}")
            raise
            
        # 获取远程仓库URL
        remote_url = self.config['remote']['url']
        logging.info(f"配置的远程仓库URL: {remote_url}")
        
        # 诊断SSH连接
        ssh_ok = self._test_ssh_connection(remote_url)
        if not ssh_ok:
            logging.warning("SSH连接测试失败，这可能导致推送失败")
            logging.info("请检查SSH密钥是否正确配置，并确保有权限访问该仓库")
        
        # 检查仓库是否存在
        repo_exists = self._check_repository_exists(remote_url)
        if not repo_exists:
            logging.warning("远程仓库不存在或无法访问")
            logging.info("请确认仓库URL是否正确，并且您有权限访问该仓库")
            
        # 开始同步过程
        for attempt in range(1, self.retry_count + 1):
            try:
                # 设置Git身份
                self._set_git_identity(self.repo)
                logging.info(f"Git身份设置为: {self.config['user']['name']} <{self.config['user']['email']}>")

                # 添加文件
                if self.config['commit']['autoAdd']:
                    self.repo.git.add(A=True)
                    logging.info("已添加所有更改到暂存区")

                # 提交更改
                if self.repo.is_dirty() or self.repo.untracked_files:
                    commit_msg = self._generate_commit_msg(commit_message)
                    
                    # 执行提交（让Git正常执行pre-commit钩子）
                    self.repo.git.commit('-m', commit_msg)
                    logging.info(f"已提交更改: {commit_msg}")
                else:
                    logging.info("没有需要提交的更改")

                # 确保远程仓库设置正确
                if 'origin' not in self.repo.remotes:
                    logging.info(f"创建新的远程仓库连接: origin -> {remote_url}")
                    self.repo.create_remote('origin', remote_url)
                else:
                    # 确保URL正确，如果不正确则更新
                    existing_url = self.repo.remotes.origin.url
                    if existing_url != remote_url:
                        logging.info(f"更新远程仓库URL: {existing_url} -> {remote_url}")
                        self.repo.remotes.origin.set_url(remote_url)
                    else:
                        logging.info(f"远程仓库URL已正确设置: {existing_url}")

                # 获取分支名称
                branch_name = self.config['branch']['default']
                logging.info(f"使用分支: {branch_name}")
                
                # 检查本地分支是否存在
                try:
                    self.repo.git.rev_parse('--verify', branch_name)
                    logging.info(f"本地分支 {branch_name} 已存在")
                except GitCommandError:
                    logging.info(f"本地分支 {branch_name} 不存在，创建新分支")
                    self.repo.git.checkout('-b', branch_name)
                
                # 先尝试拉取远程更改
                try:
                    logging.info(f"拉取远程仓库更改...")
                    # 检查远程分支是否存在
                    remote_refs = self.repo.git.ls_remote('--heads', 'origin', branch_name).strip()
                    
                    if remote_refs:  # 远程分支存在
                        logging.info(f"远程分支 {branch_name} 存在，执行拉取操作")
                        try:
                            # 尝试执行拉取操作
                            self.repo.git.pull('origin', branch_name, '--no-rebase')
                            logging.info(f"成功拉取远程更改")
                        except GitCommandError as pull_error:
                            if "refusing to merge unrelated histories" in str(pull_error):
                                logging.warning("检测到不相关的历史记录，尝试使用 --allow-unrelated-histories 选项")
                                self.repo.git.pull('origin', branch_name, '--allow-unrelated-histories')
                                logging.info("成功合并不相关的历史记录")
                            else:
                                # 如果是合并冲突，我们可以选择强制推送或中止
                                if "CONFLICT" in str(pull_error):
                                    logging.warning("拉取时发生合并冲突")
                                    if self.config.get('conflict', {}).get('forcePush', False):
                                        logging.warning("配置设置为强制推送，将覆盖远程更改")
                                    else:
                                        logging.error("合并冲突，需要手动解决")
                                        raise
                                else:
                                    raise
                    else:
                        logging.info(f"远程分支 {branch_name} 不存在，将创建新分支")
                except Exception as e:
                    logging.warning(f"拉取远程更改时出错: {e}")
                    # 如果拉取失败但配置允许强制推送，则继续
                    if not self.config.get('conflict', {}).get('forcePush', False):
                        raise
                    logging.warning("将尝试强制推送")
                
                # 推送到远程仓库
                logging.info(f"开始推送到远程仓库...")
                
                # 检查是否需要强制推送
                force_push = self.config.get('conflict', {}).get('forcePush', False)
                
                if force_push:
                    logging.warning("使用强制推送选项")
                    if self.config['branch']['createOnPush']:
                        self.repo.git.push('origin', branch_name, '--force', set_upstream=True)
                    else:
                        self.repo.git.push('origin', branch_name, '--force')
                else:
                    if self.config['branch']['createOnPush']:
                        logging.info(f"使用 --set-upstream 选项推送分支 {branch_name}")
                        self.repo.git.push('origin', branch_name, set_upstream=True)
                    else:
                        logging.info(f"推送分支 {branch_name}")
                        self.repo.remotes.origin.push(branch_name)
                
                logging.info("同步成功完成")
                return True

            except GitCommandError as e:
                logging.warning(f"尝试 {attempt}/{self.retry_count} 失败: {e}")
                
                # 提供更详细的错误诊断
                if "does not appear to be a git repository" in str(e):
                    logging.error("远程仓库URL格式错误或仓库不存在")
                    logging.info("请检查URL格式是否为: git@github.com:用户名/仓库名.git")
                elif "Permission denied" in str(e):
                    logging.error("SSH密钥验证失败，没有权限访问仓库")
                    logging.info("请确保您的SSH密钥已添加到GitHub账户")
                elif "Connection timed out" in str(e):
                    logging.error("连接超时，可能是网络问题")
                    logging.info("请检查您的网络连接")
                
                if attempt == self.retry_count:
                    logging.error("达到最大重试次数，同步最终失败")
                    raise
                
                # 指数退避
                wait_time = 2 ** attempt
                logging.info(f"等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)

def main():
    """命令行入口函数"""
    parser = argparse.ArgumentParser(description='GitHub同步工具')
    parser.add_argument('-m', '--message', type=str, 
                       help='自定义提交消息，例如：-m "实现了完整的版本记录自动化流程"')
    
    args = parser.parse_args()
    
    try:
        syncer = GitHubSyncer()
        syncer.sync(commit_message=args.message)
    except Exception as e:
        if syncer.config['errorHandling']['showDetails']:
            logging.exception("错误详情")
        exit(1)

if __name__ == '__main__':
    main()