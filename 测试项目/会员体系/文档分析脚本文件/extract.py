import os
import re

directories = [
    r'c:\Users\23282\Desktop\AI\项目\global-v2\docs\pm\会员体系管理端',
    r'c:\Users\23282\Desktop\AI\项目\global-v2\docs\pm\会员体系用户端'
]

def extract_labels_and_inputs(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Try to find common labels, spans with text, or placeholders
    labels = set(re.findall(r'<div[^>]*class="[^"]*label[^"]*"[^>]*>(.*?)</div>', content, re.IGNORECASE))
    labels.update(set(re.findall(r'<span[^>]*class="[^"]*label[^"]*"[^>]*>(.*?)</span>', content, re.IGNORECASE)))
    
    # Find Axure specific strings if possible (usually in plain text spans)
    texts = re.findall(r'<span[^>]*>([^<]+)</span>', content)
    
    # Filter out empty or too long texts
    meaningful = [t.strip() for t in texts if t.strip() and len(t.strip()) < 20]
    # Get distinct
    return list(dict.fromkeys(meaningful))

for d in directories:
    if os.path.exists(d):
        print(f"\n--- {os.path.basename(d)} ---")
        for f in os.listdir(d):
            if f.endswith('.html'):
                fields = extract_labels_and_inputs(os.path.join(d, f))
                print(f"[{f}] Fields: {', '.join(fields[:15])}...")
