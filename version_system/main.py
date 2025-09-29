"""
智能版本记录系统主入口
重构后的简化架构，支持Git Hook自动触发
"""

import sys
import logging
import argparse
import os
from smart_recorder import SmartRecorder
from git_integration import GitIntegration
from file_manager import FileManager


class VersionSystem:
    """智能版本记录系统主类（重构版）"""
    
    def __init__(self):
        """初始化所有组件"""
        # 先配置日志
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s: %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # 再初始化其他组件
        self.recorder = SmartRecorder()
        self.git_integration = GitIntegration()
        self.file_manager = FileManager()
        
        # 最后设置Git Hook
        self.setup_git_hooks()
    
    def process_snapshot_command(self, user_input: str) -> dict:
        """
        处理/snapshot命令（重构版）
        
        Args:
            user_input: 用户输入的命令
            
        Returns:
            dict: 处理结果信息
        """
        try:
            self.logger.info(f"处理命令: {user_input}")
            
            # 1. 验证命令格式
            if not self.recorder.validate_command(user_input):
                return {'success': False, 'error': '无效的命令格式'}
            
            # 2. 解析命令
            command_data = self.recorder.parse_snapshot(user_input)
            self.logger.info(f"解析结果: {command_data}")
            
            # 3. 生成版本号
            version = self.recorder.generate_next_version(command_data['message'])
            self.logger.info(f"生成版本号: {version}")
            
            # 4. 验证版本号格式
            if not self.recorder.validate_version_format(version):
                return {'success': False, 'error': f'无效的版本号格式: {version}'}
            
            # 5. 提取Git信息
            git_info = self.git_integration.get_commit_info()
            self.logger.info(f"Git信息: {git_info}")
            
            # 6. 生成版本记录
            record_content = self.recorder.generate_record(command_data, version, git_info)
            self.logger.info("版本记录生成完成")
            
            # 7. 保存文件
            self.file_manager.save_version_record(version, record_content)
            self.logger.info(f"版本记录已保存: versions/{version}.md")
            
            return {
                'success': True,
                'version': version,
                'file_path': f"versions/{version}.md",
                'content_preview': record_content[:200] + "..." if len(record_content) > 200 else record_content
            }
            
        except Exception as e:
            self.logger.error(f"处理命令时出错: {e}")
            return {'success': False, 'error': str(e)}
    
    def setup_git_hooks(self):
        """设置Git Hook"""
        try:
            hook_success = self.git_integration.setup_hooks()
            if hook_success:
                self.logger.info("Git Hook设置成功")
            else:
                self.logger.warning("Git Hook设置失败或未找到Git仓库")
        except Exception as e:
            self.logger.warning(f"Git Hook设置失败: {e}")
    
    def list_versions(self) -> list:
        """列出所有版本记录"""
        return self.file_manager.list_versions()
    
    def get_version_content(self, version: str) -> str:
        """获取指定版本的记录内容"""
        return self.file_manager.get_version_content(version)
    
    def cleanup_old_versions(self, keep_count: int = 10):
        """清理旧版本记录"""
        self.file_manager.cleanup_old_versions(keep_count)


def main():
    """命令行入口函数"""
    if len(sys.argv) < 2:
        print("用法: python main.py /snapshot -m 描述")
        print("示例: python main.py '/snapshot -m 修复面板进度异常问题")
        print("自动记录: python main.py --auto-record")
        return
    
    user_input = sys.argv[1]
    system = VersionSystem()
    
    # 处理自动记录模式
    if user_input == '--auto-record':
        # 自动生成版本记录
        import datetime
        auto_message = f"自动记录提交于 {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"
        user_input = f'/snapshot -m "{auto_message}"'
    
    result = system.process_snapshot_command(user_input)
    
    if result['success']:
        print(f"✅ 版本记录创建成功: {result['version']}")
        print(f"📁 文件位置: {result['file_path']}")
        print("\n预览内容:")
        print(result['content_preview'])
    else:
        print(f"❌ 错误: {result['error']}")


if __name__ == '__main__':
    main()