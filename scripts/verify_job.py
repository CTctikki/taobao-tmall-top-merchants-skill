import argparse
import json
import re
from pathlib import Path
from zipfile import ZipFile

from openpyxl import load_workbook

from common import load_job


SECRET_PATTERN = re.compile(r"Bearer\s+[A-Za-z0-9._-]{12,}|Authorization\s*[=:]", re.I)


def verify(job_dir, workbook_path=None):
    job_dir = Path(job_dir).resolve()
    job = load_job(job_dir)
    audit = json.loads((job_dir / "assortment_audit.json").read_text(encoding="utf-8"))
    formal_records = [row for row in audit.values() if row.get("passes_minimum")]
    for row in formal_records:
        assert row["target_spu"] >= job["min_spu"], row["shop_name"]
        assert row["target_share"] >= job["min_share"], row["shop_name"]
    workbook_path = Path(workbook_path) if workbook_path else job_dir / "outputs" / f'{job["category"]}_淘宝天猫TOP商家招商表.xlsx'
    with ZipFile(workbook_path) as archive:
        bad = archive.testzip()
        assert bad is None, bad
    formula_book = load_workbook(workbook_path, data_only=False)
    value_book = load_workbook(workbook_path, data_only=True)
    required = ["概览", "正式招商商家", "主体核验", "未确认字段", "淘汰商家", "口径与复用"]
    assert formula_book.sheetnames == required, formula_book.sheetnames
    errors = []
    for sheet in value_book.worksheets:
        for row in sheet.iter_rows():
            for cell in row:
                if isinstance(cell.value, str) and cell.value in {"#REF!", "#DIV/0!", "#VALUE!", "#NAME?", "#N/A"}:
                    errors.append((sheet.title, cell.coordinate, cell.value))
    assert not errors, errors
    for path in job_dir.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".json", ".txt", ".log", ".md", ".py"}:
            text = path.read_text(encoding="utf-8", errors="ignore")
            assert not SECRET_PATTERN.search(text), f"possible secret in {path}"
    return {"ok": True, "category": job["category"], "formal_records": len(formal_records), "platforms": sorted({row["platform"] for row in formal_records}), "workbook": str(workbook_path), "formula_errors": 0}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--job-dir", required=True)
    parser.add_argument("--workbook")
    args = parser.parse_args()
    print(json.dumps(verify(args.job_dir, args.workbook), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

