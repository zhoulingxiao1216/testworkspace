import os
import time
import re

# 要监听的文件路径
FILE_PATH = r"c:\Users\23282\Desktop\AI\项目\global-v2\docs\pm\PRD提示词文档.md"

def format_markdown(content):
    """
    自动对 Markdown 文本进行排版和美化整理
    """
    original = content
    
    # 1. 自动加盘古之白 (在中英文、中文与数字之间自动增加空格，提升排版质感)
    # 中文接英文/数字
    content = re.sub(r'([\u4e00-\u9fa5])([a-zA-Z0-9])', r'\1 \2', content)
    # 英文/数字接中文
    content = re.sub(r'([a-zA-Z0-9])([\u4e00-\u9fa5])', r'\1 \2', content)
    
    # 2. 保证标题行（#）上方有空行（如果不是第一行的话）
    content = re.sub(r'([^\n])\n(#+ )', r'\1\n\n\2', content)
    
    # 3. 标准化提示词的代码块语法
    content = content.replace('``` markdown', '```markdown')
    
    # 去除多余的连续空行 (超过两个的空行压缩为两个)
    content = re.sub(r'\n{3,}', '\n\n', content)
    
    return content

def main():
    print("==================================================")
    print(f"👀 AI 自动化守护脚本已启动！")
    print(f"正在实时监听：{os.path.basename(FILE_PATH)}")
    print("功能：当您保存文件时，自动执行中英文排版、标题格式化等整理工作。")
    print("按下 Ctrl+C 即可退出监听")
    print("==================================================\n")
    
    if not os.path.exists(FILE_PATH):
        print(f"❌ 错误：找不到文件 {FILE_PATH}！请检查路径。")
        return

    # 获取初始修改时间
    last_mtime = os.path.getmtime(FILE_PATH)
    
    try:
        while True:
            time.sleep(1.5)  # 每 1.5 秒轮询一次
            current_mtime = os.path.getmtime(FILE_PATH)
            
            # 检测到文件被修改
            if current_mtime != last_mtime:
                print(f"[{time.strftime('%H:%M:%S')}] ✍️ 检测到您修改了内容，开始自动整理排版...")
                
                # 等待 0.5 秒确保编辑器已经彻底完成写入释放锁
                time.sleep(0.5) 
                
                try:
                    with open(FILE_PATH, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    new_content = format_markdown(content)
                    
                    # 如果格式有变化，则重新写入
                    if new_content != content:
                        with open(FILE_PATH, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        print(f"[{time.strftime('%H:%M:%S')}] ✅ 整理完成：已自动完成中英混排打磨和 MD 格式美化！")
                    else:
                        print(f"[{time.strftime('%H:%M:%S')}] ⚡ 整理完毕：当前格式已处于完美状态，无需修改。")
                        
                except Exception as e:
                    print(f"⚠️ 处理文件时发生小错误（可能文件被占用）: {e}")
                
                # 重新获取修改时间，忽略我们刚才程序自己写入产生的修改时间
                last_mtime = os.path.getmtime(FILE_PATH)
                
    except KeyboardInterrupt:
        print("\n\n⏹ 收到退出指令，已停止监听。祝您工作愉快！")

if __name__ == "__main__":
    main()
