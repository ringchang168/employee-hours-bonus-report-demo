"""產生可公開展示的虛構員工、服務紀錄及示範行事曆。"""

from __future__ import annotations

import csv
from datetime import date, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"


def write_csv(filename: str, headers: list[str], rows: list[tuple]) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    with (DATA / filename).open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(headers)
        writer.writerows(rows)


def days(*, weekdays_only: bool) -> list[date]:
    result = []
    current = date(2025, 5, 1)
    while current.month == 5:
        if not weekdays_only or current.weekday() < 5:
            result.append(current)
        current += timedelta(days=1)
    return result


def main() -> None:
    employees = [
        ("E01", "示範員工A", "類型1"),
        ("E02", "示範員工B", "類型1"),
        ("E03", "示範員工C", "類型1"),
        ("E04", "示範員工D", "類型2"),
        ("E05", "示範員工E", "類型2"),
    ]
    write_csv("employees.csv", ["員工代碼", "顯示名稱", "上班類型"], employees)

    records: list[tuple] = []

    def add(employee: str, day: date, minutes: int, sites: tuple[str, ...] = ("SITE-A",), status: str = "已簽退") -> None:
        if minutes % len(sites):
            raise ValueError("服務分鐘必須能平均分配至地點")
        part = minutes // len(sites)
        start = 9 * 60
        for index, site in enumerate(sites):
            records.append((f"DEMO-{len(records)+1:04d}", employee, day.isoformat(), f"{start//60:02d}:{start%60:02d}", part, status, site))
            start += part + (15 if index < len(sites) - 1 else 0)

    weekdays = days(weekdays_only=True)
    calendar_days = days(weekdays_only=False)

    # 100、95、120、100、102 小時：跨越並命中 100 小時門檻。
    for index, day in enumerate(weekdays[:20]):
        add("E01", day, 300, ("SITE-A", "SITE-B") if index == 0 else ("SITE-A",))
    for day in weekdays[:19]:
        add("E02", day, 300, ("SITE-B",))
    for index, day in enumerate(weekdays[:16]):
        add("E03", day, 420, ("SITE-A", "SITE-B", "SITE-A") if index == 0 else ("SITE-C",))
    add("E03", weekdays[16], 480, ("SITE-C",))
    for day in calendar_days[:12]:
        add("E04", day, 480, ("SITE-B",))
    add("E04", date(2025, 5, 14), 240, ("SITE-B",))
    for day in weekdays[:10]:
        add("E05", day, 540, ("SITE-C",))
    add("E05", date(2025, 5, 10), 360, ("SITE-C",))
    add("E05", date(2025, 5, 17), 360, ("SITE-C",))
    add("E02", date(2025, 5, 31), 60, ("SITE-B",), "取消")

    records.sort(key=lambda row: (row[2], row[3], row[1], row[0]))
    write_csv("services.csv", ["紀錄編號", "員工代碼", "服務日期", "開始時間", "服務分鐘", "服務狀態", "地點代碼"], records)
    write_csv("demo_calendar.csv", ["日期", "示範日別", "說明"], [
        ("2025-05-14", "示範假日", "虛構測試日，非真實臺灣國定假日"),
        ("2025-05-17", "示範補班日", "虛構測試日，非真實臺灣補班日"),
    ])

    expected = {"E01": 6000, "E02": 5700, "E03": 7200, "E04": 6000, "E05": 6120}
    actual = {employee: sum(int(row[4]) for row in records if row[1] == employee and row[5] == "已簽退") for employee in expected}
    if actual != expected:
        raise AssertionError(f"模擬資料總分鐘不符：{actual}")
    print(f"已建立 {len(employees)} 位虛構員工、{len(records)} 筆服務紀錄。")
    print("有效服務時數：", {key: value / 60 for key, value in actual.items()})


if __name__ == "__main__":
    main()
