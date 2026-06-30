#!/usr/bin/env python3
import sys
import mammoth
import html2text

def convert(input_path, output_path):
    with open(input_path, "rb") as docx_file:
        result = mammoth.convert_to_html(docx_file)
        html = result.value
    h = html2text.HTML2Text()
    h.ignore_images = False
    h.body_width = 0
    md = h.handle(html)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md)
    print("转换完成，已保存：", output_path)

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("用法: python docx_to_md.py 输入.docx 输出.md")
        sys.exit(1)
    convert(sys.argv[1], sys.argv[2])
