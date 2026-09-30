"""檢查公開展示資料的基本一致性與獎金門檻測試情境。"""

import csv
from collections import defaultdict
from pathlib import Path


DATA = Path(__file__).resolve().parent / "data"


def rows(name):
    with (DATA / name).open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


employees = rows("employees.csv")
services = rows("services.csv")
calendar = rows("demo_calendar.csv")
assert len(employees) == 5
assert len(services) == 85
assert len(calendar) == 2
assert {row["員工代碼"] for row in employees} == {f"E{i:02d}" for i in range(1, 6)}
assert len({row["紀錄編號"] for row in services}) == len(services)
assert sum(row["服務狀態"] == "取消" for row in services) == 1

monthly = defaultdict(int)
daily = defaultdict(int)
for row in services:
    assert row["員工代碼"] in {item["員工代碼"] for item in employees}
    assert row["服務日期"].startswith("2025-05-")
    assert row["地點代碼"] in {"SITE-A", "SITE-B", "SITE-C"}
    if row["服務狀態"] == "已簽退":
        minutes = int(row["服務分鐘"])
        monthly[row["員工代碼"]] += minutes
        daily[(row["員工代碼"], row["服務日期"])] += minutes

assert dict(monthly) == {"E01": 6000, "E02": 5700, "E03": 7200, "E04": 6000, "E05": 6120}
assert all(minutes <= 720 for minutes in daily.values())
assert [row["地點代碼"] for row in services if row["員工代碼"] == "E03" and row["服務日期"] == "2025-05-01"] == ["SITE-A", "SITE-B", "SITE-A"]
assert {row["示範日別"] for row in calendar} == {"示範假日", "示範補班日"}

bonus = {employee: 1000 if minutes >= 6000 else 0 for employee, minutes in monthly.items()}
assert bonus == {"E01": 1000, "E02": 0, "E03": 1000, "E04": 1000, "E05": 1000}
print("模擬資料檢查通過：5 位員工、85 筆紀錄、工時及示範獎金門檻皆符合預期。")
