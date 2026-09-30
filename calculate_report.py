"""以虛構資料計算每月服務工時、轉場分鐘及示範獎金。"""

from __future__ import annotations

import csv
from collections import defaultdict
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
BONUS_THRESHOLD_MINUTES = 100 * 60
BONUS_AMOUNT = 1000
TRANSIT_MINUTES_PER_CHANGE = 15
MAX_DAILY_SERVICE_MINUTES = 12 * 60
CATEGORY_COLUMNS = ("一般服務分鐘", "平日延長前2小時分鐘", "平日延長後2小時分鐘", "休息日服務分鐘", "示範假日服務分鐘")
DEMO_HOURLY_RATE = Decimal("200")
DEMO_MULTIPLIERS = {
    "一般服務分鐘": Decimal("1"),
    "平日延長前2小時分鐘": Decimal("1.25"),
    "平日延長後2小時分鐘": Decimal("1.5"),
    "休息日服務分鐘": Decimal("1.25"),
    "示範假日服務分鐘": Decimal("1.5"),
}


def demo_amount(minutes: int, multiplier: Decimal = Decimal("1")) -> int:
    """每個顯示項目獨立四捨五入至整元，避免薪資單分項與總額不符。"""
    value = Decimal(minutes) * DEMO_HOURLY_RATE * multiplier / Decimal(60)
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def time_to_minutes(value: str) -> int:
    hour, minute = map(int, value.split(":"))
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError(f"開始時間無效：{value}")
    return hour * 60 + minute


def classify_day(day: date, employee_type: str, calendar_map: dict[date, str]) -> str:
    """作品自訂分類：類型1週末休息；類型2僅週日休息。"""
    override = calendar_map.get(day)
    if override == "示範假日":
        return "示範假日"
    if override == "示範補班日":
        return "一般工作日"
    if day.weekday() == 6 or (employee_type == "類型1" and day.weekday() == 5):
        return "休息日"
    return "一般工作日"


def classify_minutes(service_minutes: int, day_type: str) -> dict[str, int]:
    buckets = dict.fromkeys(CATEGORY_COLUMNS, 0)
    if day_type == "示範假日":
        buckets["示範假日服務分鐘"] = service_minutes
    elif day_type == "休息日":
        buckets["休息日服務分鐘"] = service_minutes
    else:
        buckets["一般服務分鐘"] = min(service_minutes, 480)
        buckets["平日延長前2小時分鐘"] = min(max(service_minutes - 480, 0), 120)
        buckets["平日延長後2小時分鐘"] = min(max(service_minutes - 600, 0), 120)
    if sum(buckets.values()) != service_minutes:
        raise AssertionError("工時分類分鐘未與服務分鐘一致")
    return buckets


def calculate(data_dir: Path = DATA) -> dict:
    employees = read_rows(data_dir / "employees.csv")
    services = read_rows(data_dir / "services.csv")
    calendar = read_rows(data_dir / "demo_calendar.csv")

    employee_map = {}
    for row in employees:
        code = row["員工代碼"]
        if code in employee_map:
            raise ValueError(f"重複的員工代碼：{code}")
        if row["上班類型"] not in {"類型1", "類型2"}:
            raise ValueError(f"上班類型無效：{code}")
        employee_map[code] = row

    calendar_map = {}
    for row in calendar:
        day = date.fromisoformat(row["日期"])
        if day in calendar_map:
            raise ValueError(f"示範行事曆日期重複：{day}")
        if row["示範日別"] not in {"示範假日", "示範補班日"}:
            raise ValueError(f"示範日別無效：{day}")
        calendar_map[day] = row["示範日別"]

    grouped = defaultdict(list)
    seen_ids = set()
    ignored = 0
    for row in services:
        record_id = row["紀錄編號"]
        if record_id in seen_ids:
            raise ValueError(f"重複的紀錄編號：{record_id}")
        seen_ids.add(record_id)
        code = row["員工代碼"]
        if code not in employee_map:
            raise ValueError(f"找不到員工設定：{code}")
        day = date.fromisoformat(row["服務日期"])
        minutes = int(row["服務分鐘"])
        start = time_to_minutes(row["開始時間"])
        if minutes <= 0 or start + minutes > 24 * 60:
            raise ValueError(f"服務時間無效：{record_id}")
        if not row["地點代碼"]:
            raise ValueError(f"缺少地點代碼：{record_id}")
        status = row["服務狀態"]
        if status == "取消":
            ignored += 1
            continue
        if status != "已簽退":
            raise ValueError(f"服務狀態無效：{record_id}")
        grouped[(code, day)].append((start, start + minutes, row["地點代碼"], record_id))

    daily = []
    totals = {code: {"服務分鐘": 0, "轉場分鐘": 0, **dict.fromkeys(CATEGORY_COLUMNS, 0)} for code in employee_map}
    for (code, day), entries in sorted(grouped.items()):
        entries.sort()
        service_minutes = sum(end - start for start, end, _, _ in entries)
        if service_minutes > MAX_DAILY_SERVICE_MINUTES:
            raise ValueError(f"單日服務超過 12 小時：{code} {day}")
        transfers = 0
        for previous, current in zip(entries, entries[1:]):
            if current[0] < previous[1]:
                raise ValueError(f"服務時段重疊：{code} {day}")
            if current[2] != previous[2]:
                transfers += 1
        day_type = classify_day(day, employee_map[code]["上班類型"], calendar_map)
        buckets = classify_minutes(service_minutes, day_type)
        daily.append({
            "員工代碼": code,
            "服務日期": day.isoformat(),
            "分類日別": day_type,
            "服務分鐘": service_minutes,
            **buckets,
            "轉場次數": transfers,
            "轉場分鐘": transfers * TRANSIT_MINUTES_PER_CHANGE,
        })
        totals[code]["服務分鐘"] += service_minutes
        totals[code]["轉場分鐘"] += transfers * TRANSIT_MINUTES_PER_CHANGE
        for category in CATEGORY_COLUMNS:
            totals[code][category] += buckets[category]

    monthly = []
    for code, employee in employee_map.items():
        item = totals[code]
        category_amounts = {
            category.replace("分鐘", "金額"): demo_amount(item[category], DEMO_MULTIPLIERS[category])
            for category in CATEGORY_COLUMNS
        }
        transit_amount = demo_amount(item["轉場分鐘"])
        bonus_amount = BONUS_AMOUNT if item["服務分鐘"] >= BONUS_THRESHOLD_MINUTES else 0
        monthly.append({
            "員工代碼": code,
            "顯示名稱": employee["顯示名稱"],
            "上班類型": employee["上班類型"],
            "服務分鐘": item["服務分鐘"],
            **{category: item[category] for category in CATEGORY_COLUMNS},
            "轉場分鐘": item["轉場分鐘"],
            "獎金達標": item["服務分鐘"] >= BONUS_THRESHOLD_MINUTES,
            "示範獎金": bonus_amount,
            **category_amounts,
            "轉場金額": transit_amount,
            "示範應發金額": sum(category_amounts.values()) + transit_amount + bonus_amount,
        })
    return {"每日": daily, "每月": monthly, "排除取消筆數": ignored}


if __name__ == "__main__":
    report = calculate()
    print(f"已計算 {len(report['每日'])} 筆員工每日工時；排除 {report['排除取消筆數']} 筆取消紀錄。")
    for row in report["每月"]:
        print(f"{row['顯示名稱']}：服務 {row['服務分鐘'] / 60:g} 小時，轉場 {row['轉場分鐘']} 分鐘，示範獎金 {row['示範獎金']:,} 元")
