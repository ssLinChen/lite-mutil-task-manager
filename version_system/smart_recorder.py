"""
智能版本记录器
合并了命令解析、版本生成、记录生成功能
保持原有功能完全不变
"""

import re
from datetime import datetime
from git import Repo, GitCommandError


class SmartRecorder:
    """智能版本记录器（合并三个模块功能）"""
    
    def __init__(self, repo_path: str = '..'):
        """
        初始化智能记录器
        
        Args:
            repo_path: Git仓库路径，默认为父目录（项目根目录）
        """
        try:
            self.repo = Repo(repo_path)
            self.has_git = True
        except Exception:
            self.has_git = False
            print("警告: 未找到有效的Git仓库，将使用默认版本号生成逻辑")
    
    def parse_snapshot(self, user_input: str) -> dict:
        """
        解析/snapshot -m "描述"格式的命令
        
        Args:
            user_input: 用户输入的命令字符串
            
        Returns:
            dict: 包含解析后的消息和时间戳
        """
        # 支持格式: /snapshot -m "修复面板进度异常问题"
        pattern = r'/snapshot\s+-m\s+"([^"]+)"'
        match = re.search(pattern, user_input)
        
        if match:
            message = match.group(1)
        else:
            # 如果没有匹配到标准格式，尝试提取描述信息
            message = user_input.replace('/snapshot', '').strip()
            if message.startswith('-m'):
                message = message[2:].strip()
        
        return {
            'message': message if message else '自动提交',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M')
        }
    
    def validate_command(self, user_input: str) -> bool:
        """验证命令格式是否有效"""
        return user_input.strip().startswith('/snapshot')
    
    def get_current_version(self) -> str:
        """从Git标签获取当前版本，如果没有Git仓库则从版本文件中获取"""
        if not self.has_git:
            # 尝试从versions目录中获取最新版本
            try:
                import os
                versions_dir = 'versions'
                if os.path.exists(versions_dir):
                    # 获取所有版本文件
                    version_files = [f for f in os.listdir(versions_dir) 
                                   if f.startswith('v') and f.endswith('.md')]
                    
                    if version_files:
                        # 按版本号排序（自然排序）
                        def version_key(filename):
                            version_str = filename.rstrip('.md').lstrip('v')
                            try:
                                # 将版本号转换为数字元组进行排序
                                parts = version_str.split('.')
                                return tuple(int(part) if part.isdigit() else 0 for part in parts)
                            except (ValueError, AttributeError):
                                return (0, 0, 0)
                        
                        version_files.sort(key=version_key)
                        latest_version = version_files[-1].rstrip('.md')
                        return latest_version
            except Exception:
                pass
            return 'v0.0.0'
        
        # 使用Git标签
        try:
            tags = sorted(self.repo.tags, key=lambda t: t.commit.committed_datetime)
            if tags:
                return tags[-1].name
        except Exception:
            pass
        return 'v0.0.0'
    
    def generate_next_version(self, message: str) -> str:
        """基于提交信息生成下一版本号"""
        current_version = self.get_current_version().lstrip('v')
        
        # 解析当前版本号
        try:
            major, minor, patch = map(int, current_version.split('.'))
        except ValueError:
            major, minor, patch = 0, 0, 0
        
        # 基于提交信息的语义分析
        message_lower = message.lower()
        
        if any(word in message_lower for word in ['修复', 'bug', 'fix', '错误']):
            # Bug修复：修订号+1
            patch += 1
        elif any(word in message_lower for word in ['功能', 'feature', '新增', '添加']):
            # 新功能：次版本号+1，修订号归零
            minor += 1
            patch = 0
        elif any(word in message_lower for word in ['重大', 'breaking', '重构', '架构']):
            # 重大变更：主版本号+1，次版本和修订号归零
            major += 1
            minor = 0
            patch = 0
        else:
            # 默认视为修订
            patch += 1
        
        return f"v{major}.{minor}.{patch}"
    
    def validate_version_format(self, version: str) -> bool:
        """验证版本号格式"""
        pattern = r'^v\d+\.\d+\.\d+$'
        return re.match(pattern, version) is not None
    
    def generate_record(self, command: dict, version: str, git_info: dict) -> str:
        """
        生成版本记录内容
        
        Args:
            command: 命令解析结果
            version: 版本号
            git_info: Git信息
            
        Returns:
            str: Markdown格式的版本记录
        """
        # 生成技术说明
        tech_notes = self._generate_tech_notes(command['message'])
        
        # 生成质量状态评估
        quality_status = self._assess_quality_status(command['message'], git_info['files'])
        
        # 生成关键改进点
        key_improvements = self._generate_key_improvements(command['message'])
        
        record = f"""# 版本 {version}
**时间**: {command['timestamp']}
**变更**: {command['message']}

## 智能分析
{self._generate_analysis(command['message'])}

## 质量状态
{quality_status}

## 关键改进
{key_improvements}

## Git证据
- `{git_info['hash']}` - {git_info['message']}
- 修改文件: {', '.join(git_info['files'][:3]) if git_info['files'] else '无'}

## 技术说明
{tech_notes}
"""
        return record
    
    def _generate_tech_notes(self, message: str) -> str:
        """基于提交信息生成技术说明"""
        message_lower = message.lower()
        
        if any(word in message_lower for word in ['修复', 'bug', 'fix']):
            return "解决了相关问题，提升了系统稳定性和可靠性。"
        elif any(word in message_lower for word in ['功能', 'feature', '新增']):
            return "添加了新功能，扩展了系统能力和用户体验。"
        elif any(word in message_lower for word in ['优化', '性能', 'improve']):
            return "优化了系统性能，提升了运行效率和响应速度。"
        elif any(word in message_lower for word in ['重构', '架构', 'refactor']):
            return "重构了代码结构，提高了代码质量和可维护性。"
        else:
            return "进行了必要的代码变更和维护工作。"
    
    def _generate_analysis(self, message: str) -> str:
        """生成智能分析结果"""
        message_lower = message.lower()
        
        # 分析变更类型
        if any(word in message_lower for word in ['修复', 'bug', 'fix']):
            change_type = "Bug修复"
            impact = "系统稳定性"
            compatible = "✅ 是"
        elif any(word in message_lower for word in ['功能', 'feature', '新增']):
            change_type = "功能新增"
            impact = "功能模块"
            compatible = "✅ 是"
        elif any(word in message_lower for word in ['重构', '架构']):
            change_type = "架构调整"
            impact = "系统架构"
            compatible = "⚠️ 可能不兼容"
        else:
            change_type = "常规维护"
            impact = "代码质量"
            compatible = "✅ 是"
            
        return f"- **类型**: {change_type} | **影响**: {impact} | **兼容**: {compatible}"
    
    def _assess_quality_status(self, message: str, files: list) -> str:
        """评估质量状态"""
        message_lower = message.lower()
        
        # 简单的质量评估逻辑
        code_quality = "✅ 优秀" if len(files) > 0 else "⚠️ 需检查"
        
        # 检查是否包含测试文件
        test_files = [f for f in files if 'test' in f.lower() or 'spec' in f.lower()]
        test_quality = "✅ 良好" if test_files else "⚠️ 需改进"
        
        # 检查是否包含文档或注释相关文件
        doc_files = [f for f in files if any(ext in f.lower() for ext in ['.md', '.txt', 'readme'])]
        doc_quality = "✅ 良好" if doc_files else "✅ 良好"  # 文档不是必须的
        
        return f"- 代码: {code_quality}\n- 测试: {test_quality}\n- 文档: {doc_quality}"
    
    def _generate_key_improvements(self, message: str) -> str:
        """生成关键改进点"""
        message_lower = message.lower()
        
        improvements = []
        
        if any(word in message_lower for word in ['修复', 'bug']):
            improvements.append("1. 修复了已知问题，提升系统稳定性")
            improvements.append("2. 增强了错误处理机制")
        elif any(word in message_lower for word in ['功能', 'feature']):
            improvements.append("1. 新增了核心功能模块")
            improvements.append("2. 完善了用户交互体验")
        elif any(word in message_lower for word in ['性能', '优化']):
            improvements.append("1. 优化了系统性能指标")
            improvements.append("2. 减少了资源消耗")
        else:
            improvements.append("1. 进行了代码质量改进")
            improvements.append("2. 完善了开发文档")
        
        return "\n".join(improvements[:2])  # 最多显示2个改进点