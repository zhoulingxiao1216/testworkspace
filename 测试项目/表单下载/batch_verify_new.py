import pandas as pd
import os
import warnings
warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')

mapping = {
    "7182商业发票-20260514132428.xlsx": r"商业发票模板\7182商业发票模板.xlsx",
    "7182纳品书-20260514115016.xlsx": r"纳品书模板\7182纳品书模板.xlsx",
    "LDX发票-20260514132409.xlsx": r"商业发票模板\LDX商业发票.xlsx",
    "OCS发票-20260514132314.xlsx": r"商业发票模板\OCS商业发票.xlsx",
    "TW发票-20260514132330.xlsx": r"商业发票模板\TW商业发票.xlsx",
    "ZOZO纳品书-20260514115007.xlsx": r"纳品书模板\zozo纳品书WL-JPN34-260414-004.xlsx",
    "商品发票合并-20260514132420.xlsx": r"商业发票模板\商业发票合并模板.xlsx",
    "带地址和附加项纳品书-20260514115023.xlsx": r"纳品书模板\带地址和附加项纳品书模板.xls",
    "流通王发票-20260514132340.xlsx": r"商业发票模板\流通王商业发票.xlsx",
    "海源发票-20260514132400.xlsx": r"商业发票模板\海源商业发票.xlsx",
    "纳品书-20260514114950.xlsx": r"纳品书模板\納品書模板.xlsx",
    "收支明细-20260514131355.xlsx": r"收支明细.xlsx"
}

dl_base = r"C:\Users\Administrator\Downloads\20260504"
tpl_base = r"D:\test_workspace\表单下载\表单下载模板"

def get_headers(file_path):
    try:
        xls = pd.ExcelFile(file_path)
        headers = {}
        for sheet in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name=sheet, header=None)
            for i, row in df.iterrows():
                if row.count() >= 2:
                    headers[sheet] = [str(x).strip().replace('\n', '') if pd.notnull(x) else "" for x in row.tolist()]
                    break
        return headers
    except Exception as e:
        return {"Error": [str(e)]}

results = []
for dl_file, tpl_rel in mapping.items():
    dl_path = os.path.join(dl_base, dl_file)
    tpl_path = os.path.join(tpl_base, tpl_rel)
    
    if not os.path.exists(dl_path):
        results.append(f"MISSING DOWNLOAD FILE: {dl_file}")
        continue
    if not os.path.exists(tpl_path):
        results.append(f"MISSING TEMPLATE FILE: {tpl_rel}")
        continue

    dl_headers = get_headers(dl_path)
    tpl_headers = get_headers(tpl_path)

    results.append(f"\n--- {dl_file} ---")
    
    for sheet in dl_headers:
        if sheet in tpl_headers or len(dl_headers) == 1:
            dl_cols = dl_headers[sheet]
            tpl_cols = tpl_headers[sheet] if sheet in tpl_headers else list(tpl_headers.values())[0]
            
            while dl_cols and dl_cols[-1] == "": dl_cols.pop()
            while tpl_cols and tpl_cols[-1] == "": tpl_cols.pop()
            
            if dl_cols == tpl_cols:
                results.append(f"✅ PASS: Headers Match Perfectly ({sheet})")
            else:
                results.append(f"❌ FAIL: Headers Differ ({sheet})")
                results.append(f"  DL : {dl_cols}")
                results.append(f"  TPL: {tpl_cols}")

with open(r'D:\test_workspace\表单下载\verification_results_20260504.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(results))
print("Verification complete.")
