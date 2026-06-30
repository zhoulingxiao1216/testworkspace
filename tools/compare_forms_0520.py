import datetime
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path


DL_BASE = Path(r"C:\Users\Administrator\Downloads\0520")
TPL_BASE = Path(r"D:\test_workspace\表单下载\表单下载模板")
OUT = Path(r"D:\test_workspace\output\0520_下载表单模板核对结果.md")

PAIRS = [
    ("7182商业发票", "7182商业发票-20260520104413.xlsx", r"商业发票模板\7182商业发票模板.xlsx"),
    ("7182纳品书", "7182纳品书-20260520104346.xlsx", r"纳品书模板\7182纳品书模板.xlsx"),
    ("LDX发票", "LDX发票-20260520104406.xlsx", r"商业发票模板\LDX商业发票.xlsx"),
    ("OCS发票", "OCS发票-20260520104356.xlsx", r"商业发票模板\OCS商业发票.xlsx"),
    ("TW发票", "TW发票-20260520104400.xlsx", r"商业发票模板\TW商业发票.xlsx"),
    ("ZOZO纳品书", "ZOZO纳品书-20260520104338.xlsx", r"纳品书模板\zozo纳品书WL-JPN34-260414-004.xlsx"),
    ("发货记录", "下载发货单WL-JPN34-260519-004.xlsx", r"数据导出模板\发货记录 .xlsx"),
    ("包裹明细", "包裹明细-20260520104353.xlsx", r"数据导出模板\包裹明细.xlsx"),
    ("商品发票合并", "商品发票合并-20260520104411.xlsx", r"商业发票模板\商业发票合并模板.xlsx"),
    ("流通王发票", "流通王发票-20260520104402.xlsx", r"商业发票模板\流通王商业发票.xlsx"),
    ("海源发票", "海源发票-20260520104404.xlsx", r"商业发票模板\海源商业发票.xlsx"),
    ("纳品书", "纳品书-20260520104228.xlsx", r"纳品书模板\納品書模板.xlsx"),
    ("配货单", "配货单-20260520104351.xlsx", r"数据导出模板\配货单WL-JPN34-260414-004.xlsx"),
]

XLS_PAIR = (
    "带地址和附加项纳品书",
    "带地址和附加项纳品书-20260520104348.xlsx",
    r"纳品书模板\带地址和附加项纳品书模板.xls",
)

NS = {
    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "rel": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}
REL_NS = {"r": "http://schemas.openxmlformats.org/package/2006/relationships"}
CELL_RE = re.compile(r"([A-Z]+)([0-9]+)")


def col_to_num(col: str) -> int:
    n = 0
    for ch in col:
        n = n * 26 + ord(ch) - 64
    return n


def parse_ref(ref: str):
    m = CELL_RE.match(ref or "")
    if not m:
        return None, None
    return int(m.group(2)), col_to_num(m.group(1))


def norm(value) -> str:
    if value is None:
        return ""
    return str(value).replace("\r", "").replace("\n", "").strip()


def is_dynamic(text: str) -> bool:
    t = norm(text)
    if not t:
        return True
    if len(t) > 90:
        return True
    if re.fullmatch(r"[-+]?\d[\d,.]*%?", t):
        return True
    if re.search(r"(19|20)\d{2}[-/]\d{1,2}[-/]\d{1,2}", t):
        return True
    if re.search(r"\d{4,}", t):
        return True
    if re.search(r"WL-|B2B-|https?://|@", t):
        return True
    if re.fullmatch(r"[A-Z0-9_\-/]{6,}", t):
        return True
    return False


def is_label(text: str) -> bool:
    t = norm(text)
    if is_dynamic(t):
        return False
    if len(t) <= 1:
        return False
    if re.search(r"[:：/（）()・]|[一-龥ぁ-んァ-ン]", t):
        return True
    if re.fullmatch(
        r"(NO\.?|PCS|QTY|PRICE|AMOUNT|TOTAL|SHIPPER|CONSIGNEE|DESCRIPTION|COUNTRY|DATE|INVOICE|HAWB|WEIGHT|CARTON|MARK|数量|单价|金额|品名|商品ID|订单号)",
        t,
        re.I,
    ):
        return True
    return False


def read_shared_strings(zip_file):
    if "xl/sharedStrings.xml" not in zip_file.namelist():
        return []
    root = ET.fromstring(zip_file.read("xl/sharedStrings.xml"))
    strings = []
    for si in root.findall("main:si", NS):
        strings.append("".join((t.text or "") for t in si.iter(f"{{{NS['main']}}}t")))
    return strings


def resolve_sheet_path(target: str) -> str:
    if target.startswith("/xl/"):
        return target[1:]
    if target.startswith("worksheets/"):
        return "xl/" + target
    return "xl/worksheets/" + target.split("/")[-1]


def read_xlsx(path: Path):
    with zipfile.ZipFile(path) as z:
        shared = read_shared_strings(z)
        workbook = ET.fromstring(z.read("xl/workbook.xml"))
        rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        rid_to_target = {
            rel.attrib["Id"]: rel.attrib["Target"]
            for rel in rels.findall("r:Relationship", REL_NS)
        }
        sheets = []
        for sheet_node in workbook.find("main:sheets", NS).findall("main:sheet", NS):
            name = sheet_node.attrib["name"]
            rid = sheet_node.attrib.get(f"{{{NS['rel']}}}id")
            sheet_path = resolve_sheet_path(rid_to_target[rid])
            root = ET.fromstring(z.read(sheet_path))
            dim = root.find("main:dimension", NS)
            dim_ref = dim.attrib.get("ref", "") if dim is not None else ""
            max_row = 0
            max_col = 0
            cells = {}
            for cell in root.findall(".//main:c", NS):
                row, col = parse_ref(cell.attrib.get("r", ""))
                if not row:
                    continue
                max_row = max(max_row, row)
                max_col = max(max_col, col)
                cell_type = cell.attrib.get("t")
                value = ""
                if cell_type == "s":
                    v = cell.find("main:v", NS)
                    if v is not None and v.text is not None:
                        idx = int(v.text)
                        value = shared[idx] if idx < len(shared) else ""
                elif cell_type == "inlineStr":
                    value = "".join((t.text or "") for t in cell.findall(".//main:t", NS))
                else:
                    v = cell.find("main:v", NS)
                    if v is not None and v.text is not None:
                        value = v.text
                value = norm(value)
                if value:
                    cells[(row, col)] = value

            merge_node = root.find("main:mergeCells", NS)
            merges = []
            if merge_node is not None:
                merges = [
                    m.attrib.get("ref", "")
                    for m in merge_node.findall("main:mergeCell", NS)
                ]

            labels = sorted({v for v in cells.values() if is_label(v)})
            row_signatures = []
            for row in range(1, min(max_row, 30) + 1):
                values = [cells.get((row, col), "") for col in range(1, min(max_col, 30) + 1)]
                if any(values):
                    while values and values[-1] == "":
                        values.pop()
                    row_signatures.append(
                        (row, len([v for v in values if v]), " | ".join(values))
                    )

            sheets.append(
                {
                    "name": name,
                    "dim": dim_ref,
                    "rows": max_row,
                    "cols": max_col,
                    "nonempty": len(cells),
                    "labels": labels,
                    "merges": merges,
                    "row_sigs": row_signatures,
                }
            )
        return {"path": str(path), "sheets": sheets}


def compare_pair(name: str, download_path: Path, template_path: Path):
    notes = []
    score = 0
    try:
        download = read_xlsx(download_path)
        template = read_xlsx(template_path)
    except Exception as exc:
        return {"name": name, "status": "读取失败", "score": 99, "notes": [str(exc)]}

    if len(download["sheets"]) != len(template["sheets"]):
        notes.append(f"sheet数量不同：下载{len(download['sheets'])}/模板{len(template['sheets'])}")
        score += 3

    sheet_count = min(len(download["sheets"]), len(template["sheets"]))
    for i in range(sheet_count):
        downloaded_sheet = download["sheets"][i]
        template_sheet = template["sheets"][i]
        prefix = downloaded_sheet["name"]

        if downloaded_sheet["cols"] != template_sheet["cols"]:
            notes.append(
                f"[{prefix}] 使用列不同：下载{downloaded_sheet['cols']} / 模板{template_sheet['cols']}"
            )
            score += 2

        missing_labels = [
            label
            for label in template_sheet["labels"]
            if label not in downloaded_sheet["labels"]
        ]
        if missing_labels:
            notes.append(
                f"[{prefix}] 模板静态标签缺失 {len(missing_labels)} 个："
                + "、".join(missing_labels[:10])
            )
            score += min(3, len(missing_labels))

        missing_merges = [
            merge for merge in template_sheet["merges"] if merge not in downloaded_sheet["merges"]
        ]
        extra_merges = [
            merge for merge in downloaded_sheet["merges"] if merge not in template_sheet["merges"]
        ]
        if missing_merges or extra_merges:
            notes.append(
                f"[{prefix}] 合并单元格差异：缺{len(missing_merges)} / 增{len(extra_merges)}"
            )
            score += 1

        notes.append(
            f"[{prefix}] 下载区域 {downloaded_sheet['rows']}x{downloaded_sheet['cols']}，"
            f"模板区域 {template_sheet['rows']}x{template_sheet['cols']}，"
            f"非空 {downloaded_sheet['nonempty']}/{template_sheet['nonempty']}，"
            f"合并 {len(downloaded_sheet['merges'])}/{len(template_sheet['merges'])}"
        )
        notes.append(
            "下载前几行："
            + " || ".join(
                [f"R{r}: {values[:160]}" for r, _, values in downloaded_sheet["row_sigs"][:5]]
            )
        )
        notes.append(
            "模板前几行："
            + " || ".join(
                [f"R{r}: {values[:160]}" for r, _, values in template_sheet["row_sigs"][:5]]
            )
        )

    if score == 0:
        status = "通过"
    elif score <= 2:
        status = "需人工确认"
    else:
        status = "不通过"
    return {"name": name, "status": status, "score": score, "notes": notes}


def main():
    results = []
    for name, download, template in PAIRS:
        results.append(compare_pair(name, DL_BASE / download, TPL_BASE / template))

    # This pair uses an .xls template. The script records it separately because
    # the OOXML parser intentionally handles .xlsx only.
    xls_name, xls_download, xls_template = XLS_PAIR
    results.insert(
        9,
        {
            "name": xls_name,
            "status": "需人工确认",
            "score": 2,
            "notes": [
                f"下载文件：{DL_BASE / xls_download}",
                f"模板文件为 .xls：{TPL_BASE / xls_template}",
                "该项需要用 Excel 打开核对版式；此前 5/14 已发现过发件方固定信息缺失风险，本次应重点复查顶部发件人/地址/邮编/电话区块。",
            ],
        },
    )

    lines = [
        "# 0520 下载表单 vs 表单下载模板 核对结果",
        "",
        f"生成时间：{datetime.datetime.now():%Y-%m-%d %H:%M:%S}",
        "",
        "说明：自动核对关注 sheet 数量、使用区域、合并区域、前置表头/静态标签。订单号、日期、客户名、金额等动态值不作为失败依据。",
        "",
        "| 表单 | 结论 | 差异评分 |",
        "|---|---:|---:|",
    ]
    for result in results:
        lines.append(f"| {result['name']} | {result['status']} | {result['score']} |")
    lines.append("")

    for result in results:
        lines.append(f"## {result['name']}：{result['status']}（评分 {result['score']}）")
        for note in result["notes"]:
            lines.append("- " + note)
        lines.append("")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines), encoding="utf-8")

    for result in results:
        print(f"{result['name']}\t{result['status']}\t{result['score']}")
    print("REPORT=" + str(OUT))


if __name__ == "__main__":
    main()
