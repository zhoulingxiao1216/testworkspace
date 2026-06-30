#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OCR全量校验（修正版）：cv2加载图片 → rapidocr提取SKU → 与订单ExternalID比对
"""
import os, sys, json, re

os.environ["PYTHONIOENCODING"] = "utf-8"
sys.stdout.reconfigure(encoding="utf-8")

import cv2
import numpy as np
from rapidocr_onnxruntime import RapidOCR

IMG_DIR = r"d:\test_workspace\8160_模板核对\sticker_images"
MAPPING_FILE = r"d:\test_workspace\8160_模板核对\sticker_mapping.json"

ocr = RapidOCR()

with open(MAPPING_FILE, "r", encoding="utf-8") as f:
    mapping = json.load(f)

print(f"共 {len(mapping)} 个商品, 开始OCR比对...\n")

mismatches = []
matches = []
errors = []

for i, m in enumerate(mapping, 1):
    oid = m.get("order_id", "?")
    expected_sku = m.get("sku", "")
    img_path = m.get("local_img", "")
    
    if not img_path or not os.path.exists(img_path):
        errors.append({"order_id": oid, "sku": expected_sku, "error": "no image"})
        continue
    
    try:
        # 使用 numpy + imdecode 解决 cv2 在 Windows 下无法读取中文路径的问题
        img_array = np.fromfile(img_path, dtype=np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        if img is None:
            errors.append({"order_id": oid, "sku": expected_sku, "error": "cv2 load failed"})
            continue
        result, _ = ocr(img)
    except Exception as e:
        errors.append({"order_id": oid, "sku": expected_sku, "error": str(e)})
        continue
    
    if not result:
        errors.append({"order_id": oid, "sku": expected_sku, "error": "OCR returned empty"})
        continue
    
    # 提取所有识别到的文本
    all_text = [item[1] for item in result]
    
    # 查找SKU行: 通常包含连字符、以品牌前缀开头
    found_sku = ""
    for text in all_text:
        text_clean = text.strip()
        # SKU特征: 包含至少2个连字符, 以品牌前缀开头
        if re.match(r'^[a-z0-9]+-[a-z0-9]+-', text_clean, re.IGNORECASE):
            found_sku = text_clean
            break
    
    if not found_sku:
        for text in all_text:
            text_clean = text.strip()
            if any(text_clean.lower().startswith(p) for p in ['sbg-', 'bdo-', 'ar-', '7j-']):
                found_sku = text_clean
                break
    
    if not found_sku:
        errors.append({"order_id": oid, "sku": expected_sku, "error": f"SKU not found: {all_text[:5]}"})
        continue
    
    # 比对(大小写不敏感)
    if found_sku.lower() == expected_sku.lower():
        matches.append({"order_id": oid, "sku": expected_sku})
    else:
        mismatches.append({
            "order_id": oid,
            "expected_sku": expected_sku,
            "actual_sku_on_image": found_sku,
            "all_ocr_text": all_text[:6],
        })
        print(f"  X #{oid}  expected='{expected_sku}'  actual='{found_sku}'")
    
    if i % 50 == 0:
        print(f"  --- progress: {i}/{len(mapping)} OK={len(matches)} NG={len(mismatches)} ERR={len(errors)} ---")

# 汇总
print(f"\n{'='*80}")
print(f"OCR SKU Verification Results")
print(f"{'='*80}")
print(f"  Total:      {len(mapping)}")
print(f"  OK:         {len(matches)}")
print(f"  MISMATCH:   {len(mismatches)}")
print(f"  ERROR:      {len(errors)}")

if mismatches:
    print(f"\n--- MISMATCH DETAILS ({len(mismatches)}) ---")
    for j, m in enumerate(mismatches, 1):
        print(f"  [{j}] #{m['order_id']}")
        print(f"      Expected: {m['expected_sku']}")
        print(f"      Actual:   {m['actual_sku_on_image']}")

if errors:
    print(f"\n--- ERROR DETAILS ({len(errors)}) ---")
    for e in errors[:20]:
        print(f"  #{e['order_id']} SKU='{e['sku']}' => {str(e['error'])[:80]}")

# 保存结果
result_data = {
    "order_id": "816026043058",
    "total": len(mapping),
    "matched": len(matches),
    "mismatched": len(mismatches),
    "errors": len(errors),
    "mismatch_details": mismatches,
    "error_details": errors,
}
out_path = r"d:\test_workspace\8160_模板核对\sku_verify_result.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(result_data, f, ensure_ascii=False, indent=2)
print(f"\n=> Results saved to {out_path}")
