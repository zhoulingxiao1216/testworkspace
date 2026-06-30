#!/usr/bin/env python3
import sys
import mammoth

def convert_raw(input_path, output_path):
    with open(input_path, "rb") as docx_file:
        result = mammoth.extract_raw_text(docx_file)
        text = result.value
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(text)
    print("原始文本提取完成，已保存：", output_path)

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("用法: python docx_to_md_fix.py 输入.docx 输出_fixed.md")
        sys.exit(1)
    convert_raw(sys.argv[1], sys.argv[2])
