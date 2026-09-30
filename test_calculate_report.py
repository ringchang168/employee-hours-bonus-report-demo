"""公開版計算規則的基本回歸測試。"""

import csv
import shutil
import tempfile
import unittest
from pathlib import Path

from calculate_report import CATEGORY_COLUMNS, DATA, calculate, classify_day, classify_minutes, demo_amount
from datetime import date


class ReportTests(unittest.TestCase):
    def test_expected_monthly_results(self):
        report = calculate()
        monthly = {row["員工代碼"]: row for row in report["每月"]}
        self.assertEqual({code: row["服務分鐘"] for code, row in monthly.items()},
                         {"E01": 6000, "E02": 5700, "E03": 7200, "E04": 6000, "E05": 6120})
        self.assertEqual({code: row["示範獎金"] for code, row in monthly.items()},
                         {"E01": 1000, "E02": 0, "E03": 1000, "E04": 1000, "E05": 1000})
        self.assertEqual(monthly["E01"]["轉場分鐘"], 15)
        self.assertEqual(monthly["E03"]["轉場分鐘"], 30)
        self.assertEqual(monthly["E01"]["示範應發金額"], 21550)
        self.assertEqual(monthly["E02"]["示範應發金額"], 19500)
        self.assertEqual(monthly["E03"]["示範應發金額"], 25800)
        self.assertEqual(report["排除取消筆數"], 1)
        daily = {(row["員工代碼"], row["服務日期"]): row for row in report["每日"]}
        self.assertEqual(daily[("E03", "2025-05-01")]["轉場次數"], 2)
        self.assertEqual(daily[("E04", "2025-05-14")]["分類日別"], "示範假日")
        self.assertEqual(daily[("E04", "2025-05-14")]["示範假日服務分鐘"], 240)
        self.assertEqual(daily[("E05", "2025-05-17")]["分類日別"], "一般工作日")
        self.assertEqual(daily[("E05", "2025-05-17")]["一般服務分鐘"], 360)
        self.assertEqual(daily[("E05", "2025-05-01")]["平日延長前2小時分鐘"], 60)
        self.assertEqual(daily[("E04", "2025-05-03")]["分類日別"], "一般工作日")
        self.assertEqual(daily[("E04", "2025-05-04")]["分類日別"], "休息日")
        for row in report["每日"] + report["每月"]:
            self.assertEqual(sum(row[key] for key in CATEGORY_COLUMNS), row["服務分鐘"])
        for row in report["每月"]:
            self.assertEqual(
                sum(row[key.replace("分鐘", "金額")] for key in CATEGORY_COLUMNS)
                + row["轉場金額"] + row["示範獎金"],
                row["示範應發金額"],
            )

    def test_demo_classification_boundaries(self):
        self.assertEqual(classify_day(date(2025, 5, 3), "類型1", {}), "休息日")
        self.assertEqual(classify_day(date(2025, 5, 3), "類型2", {}), "一般工作日")
        self.assertEqual(classify_minutes(600, "一般工作日")["平日延長前2小時分鐘"], 120)
        self.assertEqual(classify_minutes(720, "一般工作日")["平日延長後2小時分鐘"], 120)
        self.assertEqual(classify_minutes(300, "休息日")["休息日服務分鐘"], 300)
        self.assertEqual(demo_amount(15), 50)

    def test_missing_employee_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            data_dir = Path(temp)
            for name in ("employees.csv", "services.csv", "demo_calendar.csv"):
                shutil.copyfile(DATA / name, data_dir / name)
            with (data_dir / "services.csv").open(encoding="utf-8-sig", newline="") as file:
                rows = list(csv.DictReader(file))
            rows[0]["員工代碼"] = "E99"
            with (data_dir / "services.csv").open("w", encoding="utf-8-sig", newline="") as file:
                writer = csv.DictWriter(file, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
            with self.assertRaisesRegex(ValueError, "找不到員工設定"):
                calculate(data_dir)

    def test_over_12_hours_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            data_dir = Path(temp)
            for name in ("employees.csv", "services.csv", "demo_calendar.csv"):
                shutil.copyfile(DATA / name, data_dir / name)
            with (data_dir / "services.csv").open(encoding="utf-8-sig", newline="") as file:
                rows = list(csv.DictReader(file))
            row = next(row for row in rows if row["員工代碼"] == "E01" and row["服務日期"] == "2025-05-02")
            row["服務分鐘"] = "750"
            with (data_dir / "services.csv").open("w", encoding="utf-8-sig", newline="") as file:
                writer = csv.DictWriter(file, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
            with self.assertRaisesRegex(ValueError, "單日服務超過 12 小時"):
                calculate(data_dir)


if __name__ == "__main__":
    unittest.main()
