"""
文件管理模块
负责版本记录文件的存储和管理
"""

import os
from datetime import datetime


class FileManager:
    """文件管理器"""
    
    def __init__(self, base_dir='versions'):
        """
        初始化文件管理器
        
        Args:
            base_dir: 版本记录存储的基础目录
        """
        # 使用绝对路径，确保文件创建在正确的位置
        self.base_dir = os.path.abspath(base_dir)
    
    def save_version_record(self, version: str, content: str):
        """
        保存版本记录到文件
        
        Args:
            version: 版本号
            content: 版本记录内容
        """
        # 确保目录存在
        os.makedirs(self.base_dir, exist_ok=True)
        
        # 保存版本记录文件
        filename = os.path.join(self.base_dir, f"{version}.md")
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # 更新总变更日志
        self._update_changelog(version, content)
    
    def _update_changelog(self, version: str, content: str):
        """更新总变更日志文件"""
        changelog_file = 'CHANGELOG.md'
        
        # 提取版本记录的关键信息
        lines = content.split('\n')
        title = next((line for line in lines if line.startswith('# 版本')), '')
        time_line = next((line for line in lines if line.startswith('**时间**:')), '')
        
        # 提取Git证据信息
        git_evidence_line = next((line for line in lines if line.startswith('- `') and '` -' in line), '')
        if git_evidence_line:
            # 使用Git证据作为变更描述
            change_line = f"**变更**: {git_evidence_line}"
        else:
            # 如果没有Git证据，使用原始变更描述
            change_line = next((line for line in lines if line.startswith('**变更**:')), '')
        
        # 生成变更日志条目（紧凑格式）
        changelog_entry = f"""# 版本 {version}
{time_line}
{change_line}
[查看详情](versions/{version}.md)"""
        
        if os.path.exists(changelog_file):
            # 读取现有变更日志
            with open(changelog_file, 'r', encoding='utf-8') as f:
                existing_content = f.read()
            
            # 在文件开头插入新条目
            new_content = f"# 变更日志\n\n{changelog_entry}\n\n{existing_content.split('# 变更日志', 1)[-1]}"
        else:
            new_content = f"# 变更日志\n\n{changelog_entry}"
        
        with open(changelog_file, 'w', encoding='utf-8') as f:
            f.write(new_content)
    
    def get_version_content(self, version: str) -> str:
        """获取指定版本的记录内容"""
        filename = os.path.join(self.base_dir, f"{version}.md")
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                return f.read()
        return f"版本 {version} 的记录文件不存在"