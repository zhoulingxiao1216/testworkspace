import pandas as pd
import os
import warnings
warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')

mapping = {
    "7182发票-WL-JPN12-260513-004.xlsx": r"商业发票模板\7182商业发票模板.xlsx",
    "7182纳品书-WL-JPN12-260513-004.xlsx": r"纳品书模板\7182纳品书模板.xlsx",
    "LDX发票-WL-JPN12-260513-005.xlsx": r"商业发票模板\LDX商业发票.xlsx",
    "OCS发票-WL-JPN12-260513-005.xlsx": r"商业发票模板\OCS商业发票.xlsx",
    "TW发票-WL-JPN12-260513-005.xlsx": r"商业发票模板\TW商业发票.xlsx",
    "ZOZO纳品书-WL-JPN12-260513-005.xlsx": r"纳品书模板\zozo纳品书WL-JPN34-260414-004.xlsx",
    "包裹明细-WL-JPN12-260513-005.xlsx": r"数据导出模板\包裹明细.xlsx",
    "发货记录-shipping-records.xlsx": r"数据导出模板\发货记录 .xlsx",
    "发货记录-shipping-records (1).xlsx": r"数据导出模板\发货记录 .xlsx",
    "商业发票合并版-WL-JPN12-260513-005.xlsx": r"商业发票模板\商业发票合并模板.xlsx",
    "带地址和附加项纳品书-WL-JPN12-260513-005.xlsx": r"纳品书模板\带地址和附加项纳品书模板.xls",
    "流通王发票-WL-JPN12-260513-004.xlsx": r"商业发票模板\流通王商业发票.xlsx",
    "普通发票-WL-JPN12-260513-004.xlsx": r"商业发票模板\海源商业发票.xlsx",
    "物流清算-clearing-list.xlsx": r"数据导出模板\物流清算.xlsx",
    "纳品书-WL-JPN12-260513-004.xlsx": r"纳品书模板\納品書模板.xlsx",
    "订单清算-2026-05-14.xlsx": r"数据导出模板\订单清算.xlsx",
    "资金明细-2026-05-14.xlsx": r"个人中心\資金全履歴 .xlsx",
    "B2B-DD-JPN12-260513-004.xlsx": r"个人中心\订单详情-B2B-DD-KOR8-260414-104.xlsx",
    "配货单-WL-JPN12-260513-005.xlsx": r"数据导出模板\配货单WL-JPN34-260414-004.xlsx"
}

dl_base = r"C:\Users\Administrator\Downloads\新建文件夹"
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
    
    if dl_file == "发货记录-shipping-records (1).xlsx":
        dl_path = r"C:\Users\Administrator\Downloads\发货记录-shipping-records (1).xlsx"

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

with open(r'D:\test_workspace\表单下载\verification_results.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(results))
print("Verification complete.")
