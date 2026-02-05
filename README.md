# CTK 焊口主控表建檔工具 (MVP)

這是一個使用 **Python + CustomTkinter** 的桌面工具，用於建立焊口主控表的初始資料，支援 DWG 清單匯入、DWG 解析、焊口批量建立/貼上、以及 Excel 匯出。

## 安裝

```bash
pip install -r requirements.txt
```

## 啟動

```bash
python app.py
```

## 使用流程

1. 匯入 DWG 清單（貼上或讀取 TXT）。
2. 若需調整候選規則，可在「Spec Rules 管理」頁籤維護 `class -> 材質候選 / DN厚度候選 / 預設焊接型式`。
3. 選擇 DWG 後建立焊口明細（批量生成/貼上，必要時套用 defaults）。
4. 匯出 Excel（輸出於 `output/`）。

## 設定檔

- `config/parser_profiles.json`：DWG NO 解析規則設定
- `config/spec_rules.json`：Class + DN 對應材質/厚度候選規則
