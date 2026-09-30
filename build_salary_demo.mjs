import fs from "node:fs/promises";
import path from "node:path";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const project = process.argv[2] || path.dirname(fileURLToPath(import.meta.url));
const python = process.argv[3] || process.env.PYTHON || "python";
const payload = JSON.parse(execFileSync(python, ["-c", "import json; from calculate_report import calculate, read_rows, DATA; print(json.dumps({'report': calculate(), 'services': read_rows(DATA/'services.csv'), 'employees': read_rows(DATA/'employees.csv')}, ensure_ascii=False))"], {cwd: project, encoding: "utf8", env: {...process.env, PYTHONIOENCODING: "utf-8"}}));
const {report, services, employees} = payload;
const wb = Workbook.create();
const overview = wb.worksheets.add("每月總覽");
const payroll = wb.worksheets.add("示範薪資計算");
const slips = wb.worksheets.add("示範薪資單");
const daily = wb.worksheets.add("每日工時");
const rules = wb.worksheets.add("示範規則");
const raw = wb.worksheets.add("虛構服務紀錄");

const navy = "#17324D", blue = "#285B87", light = "#E8F1F7", pale = "#F5F8FA", ink = "#1E2E3B", accent = "#BFE4D7";
const lastDaily = 5 + report["每日"].length;
const FONT = "Arial";
for (const sheet of [overview, payroll, slips, daily, rules, raw]) {
  sheet.showGridLines = false;
  sheet.getRange("A1:R100").format.font = {name: FONT, size: 10, color: ink};
}
overview.tabColor = navy;
slips.tabColor = blue;
rules.tabColor = "#708A9F";

function title(sheet, text, end = "H") {
  sheet.getRange("A2").values = [[text]];
  sheet.getRange("A2").format.font = {name: FONT, size: 14, bold: true, color: navy};
  sheet.getRange(`A3:${end}3`).format.borders = {bottom: {style: "thin", color: "#AABBC9"}};
  sheet.getRange("A2").format.rowHeight = 26;
}
function header(sheet, address) {
  const range = sheet.getRange(address);
  range.format.fill = navy;
  range.format.font = {name: FONT, size: 10, bold: true, color: "#FFFFFF"};
  range.format.rowHeight = 24;
  range.format.horizontalAlignment = "center";
  range.format.verticalAlignment = "center";
}
function widths(sheet, spec) {
  for (const [column, width] of Object.entries(spec)) sheet.getRange(`${column}1:${column}100`).format.columnWidth = width;
}
function band(sheet, start, end, lastCol) {
  for (let row = start; row <= end; row++) {
    if ((row - start) % 2) sheet.getRange(`A${row}:${lastCol}${row}`).format.fill = pale;
  }
}

// Source and control values sit to the right of the three reader views.
title(rules, "示範計算規則", "F");
rules.getRange("A3:B3").values = [["基本時薪（元）", 200]];
rules.getRange("A5:B11").values = [
  ["工時項目", "倍率"],
  ["一般服務", 1],
  ["平日延長前 2 小時", 1.25],
  ["平日延長後 2 小時", 1.5],
  ["休息日服務", 1.25],
  ["示範假日服務", 1.5],
  ["轉場", 1],
];
header(rules, "A5:B5");
rules.getRange("A13:B14").values = [["獎金門檻（小時）", 100], ["達標獎金（元）", 1000]];
rules.getRange("A16").values = [["類型1：週一至週五為一般工作日；類型2：週一至週六為一般工作日。"]];
rules.getRange("A17").values = [["週日及類型1週六為休息日；示範行事曆中的假日、補班日優先。"]];
rules.getRange("A18").values = [["取消紀錄不計入。地點改變記 15 分鐘轉場；獎金只看服務分鐘。"]];
rules.getRange("A20").values = [["全為虛構資料與作品自訂規則；非課程原始資料、實際薪資或法定加班算法。"]];
rules.getRange("A21").values = [["示範應發金額未包含保險、稅、代扣或其他正式薪資項目。"]];
rules.getRange("B3").format.fill = "#FFF0BF";
rules.getRange("B6:B11").format.fill = "#FFF0BF";
rules.getRange("B13:B14").format.fill = "#FFF0BF";
rules.getRange("B3").setNumberFormat("#,##0");
rules.getRange("B6:B11").setNumberFormat("0.00");
rules.getRange("B13:B14").setNumberFormat("#,##0");
widths(rules, {A: 79, B: 17});

title(raw, "虛構服務紀錄", "G");
raw.getRange("A3").values = [["來源：本作品自行產生的模擬資料 data/services.csv"]];
raw.getRange("A5:G5").values = [["紀錄編號", "員工代碼", "服務日期", "開始時間", "服務分鐘", "服務狀態", "地點代碼"]];
header(raw, "A5:G5");
const rawRows = services.map(r => [r["紀錄編號"], r["員工代碼"], new Date(`${r["服務日期"]}T00:00:00Z`), r["開始時間"], Number(r["服務分鐘"]), r["服務狀態"], r["地點代碼"]]);
raw.getRangeByIndexes(5, 0, rawRows.length, 7).values = rawRows;
raw.getRange(`C6:C${5+rawRows.length}`).setNumberFormat("yyyy-mm-dd");
raw.getRange(`E6:E${5+rawRows.length}`).setNumberFormat("#,##0");
band(raw, 6, 5+rawRows.length, "G");
widths(raw, {A: 17, B: 13, C: 16, D: 14, E: 15, F: 15, G: 15});
raw.freezePanes.freezeRows(5);

title(daily, "每日工時分類", "L");
daily.getRange("A3").values = [["2025 年 5 月；分鐘為單位，轉場另列，不併入服務分鐘。"]];
daily.getRange("A5:L5").values = [["員工代碼", "顯示名稱", "服務日期", "分類日別", "服務分鐘", "一般服務", "延長前2小時", "延長後2小時", "休息日", "示範假日", "轉場分鐘", "分類差額"]];
header(daily, "A5:L5");
const nameByCode = Object.fromEntries(employees.map(r => [r["員工代碼"], r["顯示名稱"]]));
const dailyRows = report["每日"].map(r => [r["員工代碼"], nameByCode[r["員工代碼"]], new Date(`${r["服務日期"]}T00:00:00Z`), r["分類日別"], r["服務分鐘"], r["一般服務分鐘"], r["平日延長前2小時分鐘"], r["平日延長後2小時分鐘"], r["休息日服務分鐘"], r["示範假日服務分鐘"], r["轉場分鐘"], null]);
daily.getRangeByIndexes(5, 0, dailyRows.length, 12).values = dailyRows;
const dailyChecks = dailyRows.map((_, i) => [`=E${i+6}-SUM(F${i+6}:J${i+6})`]);
daily.getRangeByIndexes(5, 11, dailyRows.length, 1).formulas = dailyChecks;
daily.getRange(`C6:C${lastDaily}`).setNumberFormat("yyyy-mm-dd");
daily.getRange(`E6:L${lastDaily}`).setNumberFormat("#,##0");
band(daily, 6, lastDaily, "L");
widths(daily, {A: 13, B: 17, C: 16, D: 17, E: 15, F: 15, G: 18, H: 18, I: 15, J: 15, K: 15, L: 14});
daily.freezePanes.freezeRows(5);

title(payroll, "示範薪資計算", "F");
payroll.getRange("A3").values = [["分項金額四捨五入至元後相加；規則可在「示範規則」查看。"]];
payroll.getRange("A5:F5").values = [["員工代碼", "顯示名稱", "項目", "分鐘", "倍率", "示範金額（元）"]];
header(payroll, "A5:F5");
const itemDefs = [
  ["一般服務", "F", 6], ["平日延長前2小時", "G", 7], ["平日延長後2小時", "H", 8],
  ["休息日服務", "I", 9], ["示範假日服務", "J", 10], ["轉場", "K", 11],
];
const payStart = [];
for (let i = 0; i < employees.length; i++) {
  const employee = employees[i];
  const start = 6 + i * 9;
  payStart.push(start);
  const inputRows = [...itemDefs.map(([label]) => [employee["員工代碼"], employee["顯示名稱"], label, null, null, null]), [employee["員工代碼"], employee["顯示名稱"], "示範獎金", null, null, null], [employee["員工代碼"], employee["顯示名稱"], "示範應發合計", null, null, null]];
  payroll.getRangeByIndexes(start-1, 0, inputRows.length, 6).values = inputRows;
  for (let j = 0; j < itemDefs.length; j++) {
    const row = start + j;
    const [, sourceCol, ruleRow] = itemDefs[j];
    payroll.getRange(`D${row}`).formulas = [[`=SUMIFS('每日工時'!$${sourceCol}$6:$${sourceCol}$${lastDaily},'每日工時'!$A$6:$A$${lastDaily},A${row})`]];
    payroll.getRange(`E${row}`).formulas = [[`='示範規則'!$B$${ruleRow}`]];
    payroll.getRange(`F${row}`).formulas = [[`=ROUND(D${row}/60*'示範規則'!$B$3*E${row},0)`]];
  }
  const bonusRow = start + 6;
  payroll.getRange(`D${bonusRow}`).formulas = [[`=SUMIFS('每日工時'!$E$6:$E$${lastDaily},'每日工時'!$A$6:$A$${lastDaily},A${bonusRow})`]];
  payroll.getRange(`F${bonusRow}`).formulas = [[`=IF(D${bonusRow}>='示範規則'!$B$13*60,'示範規則'!$B$14,0)`]];
  payroll.getRange(`F${start+7}`).formulas = [[`=SUM(F${start}:F${start+6})`]];
  payroll.getRange(`A${start+7}:F${start+7}`).format.fill = light;
  payroll.getRange(`A${start+7}:F${start+7}`).format.font = {name: FONT, size: 10, bold: true, color: navy};
}
payroll.getRange(`D6:D${payStart.at(-1)+7}`).setNumberFormat("#,##0");
payroll.getRange(`E6:E${payStart.at(-1)+7}`).setNumberFormat("0.00");
payroll.getRange(`F6:F${payStart.at(-1)+7}`).setNumberFormat("#,##0");
widths(payroll, {A: 14, B: 17, C: 25, D: 17, E: 14, F: 23});
payroll.freezePanes.freezeRows(5);

title(overview, "員工工時與示範薪資總覽", "H");
overview.getRange("A3").values = [["2025 年 5 月・5 位虛構員工；金額僅供作品示範。"]];
overview.getRange("A5:H5").values = [["員工代碼", "顯示名稱", "上班類型", "服務時數", "轉場分鐘", "示範獎金", "其他示範金額", "示範應發合計"]];
header(overview, "A5:H5");
overview.getRange("A6:C10").values = employees.map(e => [e["員工代碼"], e["顯示名稱"], e["上班類型"]]);
for (let i = 0; i < employees.length; i++) {
  const row = 6 + i;
  const pay = payStart[i];
  overview.getRange(`D${row}`).formulas = [[`=ROUND(SUMIFS('每日工時'!$E$6:$E$${lastDaily},'每日工時'!$A$6:$A$${lastDaily},A${row})/60,1)`]];
  overview.getRange(`E${row}`).formulas = [[`=SUMIFS('每日工時'!$K$6:$K$${lastDaily},'每日工時'!$A$6:$A$${lastDaily},A${row})`]];
  overview.getRange(`F${row}`).formulas = [[`='示範薪資計算'!F${pay+6}`]];
  overview.getRange(`G${row}`).formulas = [[`=H${row}-F${row}`]];
  overview.getRange(`H${row}`).formulas = [[`='示範薪資計算'!F${pay+7}`]];
}
overview.getRange("A11").values = [["合計"]];
for (const column of ["D", "E", "F", "G", "H"]) overview.getRange(`${column}11`).formulas = [[`=SUM(${column}6:${column}10)`]];
overview.getRange("A11:H11").format.fill = light;
overview.getRange("A11:H11").format.font = {name: FONT, size: 10, bold: true, color: navy};
band(overview, 6, 10, "H");
overview.getRange("D6:D11").setNumberFormat("0.0");
overview.getRange("E6:H11").setNumberFormat("#,##0");
widths(overview, {A: 14, B: 18, C: 15, D: 16, E: 17, F: 17, G: 21, H: 21});

title(slips, "示範薪資單", "D");
slips.getRange("A3").values = [["2025 年 5 月；以下金額沒有保險、稅或其他扣項，並非實際薪資單。"]];
for (let i = 0; i < employees.length; i++) {
  const start = 5 + i * 13;
  const pay = payStart[i];
  slips.getRange(`A${start}`).values = [[`員工 ${employees[i]["顯示名稱"]}（${employees[i]["員工代碼"]}）`]];
  slips.getRange(`A${start}:C${start}`).format.fill = blue;
  slips.getRange(`A${start}:C${start}`).format.font = {name: FONT, size: 10, bold: true, color: "#FFFFFF"};
  slips.getRange(`A${start+1}:C${start+1}`).values = [["項目", "分鐘", "金額（元）"]];
  header(slips, `A${start+1}:C${start+1}`);
  for (let j = 0; j < 7; j++) {
    const dest = start + 2 + j, source = pay + j;
    slips.getRange(`A${dest}`).formulas = [[`='示範薪資計算'!C${source}`]];
    if (j < 6) slips.getRange(`B${dest}`).formulas = [[`='示範薪資計算'!D${source}`]];
    slips.getRange(`C${dest}`).formulas = [[`='示範薪資計算'!F${source}`]];
  }
  const total = start + 9;
  slips.getRange(`A${total}`).values = [["示範應發合計"]];
  slips.getRange(`C${total}`).formulas = [[`='示範薪資計算'!F${pay+7}`]];
  slips.getRange(`A${total}:C${total}`).format.fill = light;
  slips.getRange(`A${total}:C${total}`).format.font = {name: FONT, size: 10, bold: true, color: navy};
  slips.getRange(`B${start+2}:C${total}`).setNumberFormat("#,##0");
}
widths(slips, {A: 31, B: 16, C: 20});

wb.recalculate();
const checks = [
  await wb.inspect({kind: "table", range: "每月總覽!A5:H11", include: "values,formulas", tableMaxRows: 7, tableMaxCols: 8}),
  await wb.inspect({kind: "table", range: "示範薪資計算!A5:F13", include: "values,formulas", tableMaxRows: 9, tableMaxCols: 6}),
  await wb.inspect({kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!", options: {useRegex: true, maxResults: 50}, summary: "formula errors"}),
];
for (const check of checks) console.log(check.ndjson);
const expected = Object.fromEntries(report["每月"].map(r => [r["員工代碼"], r["示範應發金額"]]));
const actual = overview.getRange("A6:H10").values;
for (const row of actual) {
  if (Number(row[7]) !== expected[row[0]]) throw new Error(`Excel 金額與 Python 計算不符：${row[0]} ${row[7]} vs ${expected[row[0]]}`);
}
const differences = daily.getRange(`L6:L${lastDaily}`).values.flat();
if (differences.some(value => Number(value) !== 0)) throw new Error("每日工時分類未對平");
rules.getRange("B3").values = [[210]];
wb.recalculate();
if (Number(overview.getRange("H6").values[0][0]) <= expected.E01) throw new Error("調整示範時薪後，總覽金額未更新");
rules.getRange("B3").values = [[200]];
rules.getRange("B13").values = [[101]];
wb.recalculate();
if (Number(overview.getRange("F6").values[0][0]) !== 0 || Number(overview.getRange("F10").values[0][0]) !== 1000) throw new Error("調整獎金門檻後，獎金未更新");
rules.getRange("B13").values = [[100]];
wb.recalculate();
if (Number(overview.getRange("H6").values[0][0]) !== expected.E01) throw new Error("還原示範規則後，總覽金額未恢復");

const previewDir = path.resolve("salary_previews");
await fs.mkdir(previewDir, {recursive: true});
for (const [sheetName, range, file] of [["每月總覽", "A1:H12", "overview.png"], ["示範薪資單", "A1:C15", "slip.png"], ["每日工時", "A1:L13", "daily.png"], ["示範規則", "A1:B21", "rules.png"], ["虛構服務紀錄", "A1:G12", "source.png"]]) {
  const preview = await wb.render({sheetName, range, scale: 1.5, format: "png"});
  await fs.writeFile(path.join(previewDir, file), new Uint8Array(await preview.arrayBuffer()));
}
const outputDir = path.join(project, "output");
await fs.mkdir(outputDir, {recursive: true});
const outputPath = path.join(outputDir, "示範員工工時與薪資報表.xlsx");
const output = await SpreadsheetFile.exportXlsx(wb);
await output.save(outputPath);
console.log(JSON.stringify({outputPath, expected, dayRows: dailyRows.length, records: rawRows.length}));
