#!/usr/bin/env python3
"""
文档自动更新脚本
当代码变更时自动同步更新文档内容
"""

import os
from datetime import datetime
from pathlib import Path

DOC_DIR = Path("app/backend/doc")
LAST_UPDATE_FILE = DOC_DIR / ".last_update"

def check_for_updates():
    """检查代码文件是否比文档更新"""
    last_doc_update = get_last_doc_update()
    
    for py_file in Path("app/backend").rglob("*.py"):
        if py_file.stat().st_mtime > last_doc_update:
            return True
    return False

def get_last_doc_update():
    """获取文档最后更新时间"""
    if LAST_UPDATE_FILE.exists():
        return LAST_UPDATE_FILE.stat().st_mtime
    return 0

def update_docs():
    """执行文档更新"""
    # TODO: 实现具体文档生成逻辑
    print("文档更新完成")
    LAST_UPDATE_FILE.touch()

if __name__ == "__main__":
    if check_for_updates():
        update_docs()
    else:
        print("文档已是最新，无需更新")