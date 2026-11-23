# 動競 Taiwan Sports Hub

面向台灣運動迷的 Flask 賽事、球星與在地活動查詢網站。使用 Python 3.11+、Flask 3、requests、python-dotenv；前端以 Tailwind CSS CDN 載入，無須額外前端建置。

## 專案結構

```text
.
├── .env.example
├── .gitignore
├── README.md
├── requirements.txt
├── vercel.json
├── api/
│   └── index.py
├── data/
│   └── tw_activities.json
├── services/
│   ├── __init__.py
│   └── sports_api.py
└── templates/
    ├── 404.html
    ├── activities.html
    ├── base.html
    ├── index.html
    ├── players.html
    ├── schedule.html
    └── sports.html
```

## 本機啟動

```powershell
py -3.11 -m venv .venv
\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
# 編輯 .env 並填入 BALLDONTLIE_API_KEY（選填；未設定時會使用精選範例資料）
python -m flask --app api.index run --debug
```

開啟 `http://127.0.0.1:5000`。API 呼叫使用 8 秒 timeout，成功回應以程序內字典快取 900 秒。Serverless 執行個體重啟時快取會重設，屬於記憶體快取的預期行為。NBA API 缺少金鑰、發生錯誤或被限流時，球員與球隊頁面回傳精選資料並顯示提示。

## 推送至 GitHub

先在 GitHub 建立空白 repository（不要初始化 README、License 或 `.gitignore`），再於專案根目錄執行：

```powershell
git init
git add .
git commit -m "建立動競台灣運動資訊站"
git branch -M main
git remote add origin https://github.com/<你的帳號>/<repository 名稱>.git
git push -u origin main
```

`.env` 已列入 `.gitignore`；不要把 API 金鑰提交至 GitHub。

## 部署到 Vercel

1. 登入 Vercel，選 **Add New → Project**，匯入剛推送的 GitHub repository。
2. Framework Preset 選 **Other**；根目錄維持專案根目錄，Build Command 與 Output Directory 留空即可。`vercel.json` 會將所有路徑交由 `api/index.py` 的 Flask `app` 處理。
3. 在 Project Settings → Environment Variables 新增 `BALLDONTLIE_API_KEY`，值貼上 BALLDONTLIE API 金鑰，選擇要套用的環境（Production；需要時也勾選 Preview/Development）。
4. 儲存後重新部署。未設定金鑰也能部署，NBA 頁面會使用範例資料。

## 部署後確認

依序開啟部署網址的 `/`、`/sports`、`/schedule?sport=f1`、`/players`、`/players?type=f1`、`/activities`。確認頁面以繁體中文呈現、活動篩選可用、賽事時間標示台灣時間、NBA 無金鑰時有友善提示，且頁面在手機寬度可橫向操作賽程表。若已設定 API 金鑰，使用球員搜尋框輸入 Curry 或 LeBron；BALLDONTLIE 免費額度只有每分鐘 5 次，重複查詢會由 15 分鐘快取降低請求量。

## 資料來源與注意事項

- F1 賽程與車手：Jolpica F1 API，請求帶有 `TaiwanSportsHub/1.0` User-Agent。
- 運動百科：TheSportsDB 測試金鑰 `123`；圖片以 `/medium` 結尾載入。
- NBA 球隊與球員：BALLDONTLIE API，以 `Authorization` 標頭讀取環境變數金鑰。
- 台灣活動：`data/tw_activities.json` 中的展示資料，正式公開前請由主辦方確認與更新時間、費用及名額。
