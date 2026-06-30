# -*- coding: utf-8 -*-
"""Token 文件读写（带目录创建、原子写入、权限容错）"""
import json
import os
import tempfile
from datetime import datetime

from core.path_manager import TOKEN_DIR


def ensure_token_dir():
    """确保 token 目录存在；无权限时返回 False"""
    try:
        os.makedirs(TOKEN_DIR, mode=0o775, exist_ok=True)
        return True
    except OSError:
        return False


def _atomic_write_text(path, content):
    """同目录原子写入，避免半截文件"""
    target_dir = os.path.dirname(os.path.abspath(path))
    os.makedirs(target_dir, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=".token_", suffix=".tmp", dir=target_dir)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        raise


def save_account_token(mail, token_val):
    """
    保存单账号 token 文本文件。
    返回 (ok, error_message)
    """
    if not ensure_token_dir():
        return False, f"无法创建 token 目录: {TOKEN_DIR}"

    safe_mail = mail.replace("@", "_").replace(".", "_")
    timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M")
    file_path = os.path.join(TOKEN_DIR, f"{safe_mail}_{timestamp}.txt")

    try:
        for old_file in os.listdir(TOKEN_DIR):
            if old_file.startswith(f"{safe_mail}_") and old_file.endswith(".txt"):
                try:
                    os.remove(os.path.join(TOKEN_DIR, old_file))
                except OSError:
                    pass
        _atomic_write_text(file_path, str(token_val))
        return True, ""
    except PermissionError as e:
        return False, f"无写入权限: {file_path} ({e})"
    except OSError as e:
        return False, f"写入失败: {file_path} ({e})"


def save_current_tokens(tokens_dict):
    """
    保存 current_tokens.json 汇总。
    返回 (ok, error_message)
    """
    if not tokens_dict:
        return True, ""

    if not ensure_token_dir():
        return False, f"无法创建 token 目录: {TOKEN_DIR}"

    summary_path = os.path.join(TOKEN_DIR, "current_tokens.json")
    try:
        content = json.dumps(tokens_dict, ensure_ascii=False, indent=4)
        _atomic_write_text(summary_path, content)
        return True, ""
    except PermissionError as e:
        return False, f"无写入权限: {summary_path} ({e})"
    except OSError as e:
        return False, f"写入失败: {summary_path} ({e})"
