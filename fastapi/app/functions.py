import os
import json
from datetime import datetime, timedelta
import httpx
from dotenv import load_dotenv
import google.generativeai as genai

# .env から環境変数読み込み
load_dotenv()
CLIENT_ID = os.getenv("FITBIT_CLIENT_ID")
CLIENT_SECRET = os.getenv("FITBIT_CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")
FITBIT_API_BASE = "https://api.fitbit.com"

# Gemini API のキープロセス
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

# Gemini モデルクライアント初期化
try:
    gemini_model = genai.GenerativeModel("gemini-1.5-flash")
except TypeError:
    # 旧バージョンではキーワード引数
    gemini_model = genai.GenerativeModel(model_name="gemini-1.5-flash")

async def get_access_token(code: str) -> dict:
    token_url = f"{FITBIT_API_BASE}/oauth2/token"
    auth = httpx.BasicAuth(CLIENT_ID, CLIENT_SECRET)
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "client_id": CLIENT_ID,
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI,
        "code": code
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(token_url, headers=headers, data=data, auth=auth)
        resp.raise_for_status()
        token_data = resp.json()
        # token.json に保存
        token_path = os.path.join(os.getcwd(), "token.json")
        with open(token_path, "w") as f:
            json.dump(token_data, f, indent=2)
        return token_data

async def fetch_fitbit_data(endpoint: str, token: str) -> dict:
    url = f"{FITBIT_API_BASE}{endpoint}"
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=headers)
        resp.raise_for_status()
        return resp.json()

# 各種データ取得
async def fetch_profile(token: str) -> dict:
    print("DEBUG:fetch_profile",token)
    return await fetch_fitbit_data("/1/user/-/profile.json", token)

async def fetch_heartrate(token: str, date: str) -> dict:
    print("DEBUG:fetch_heartrate",token)
    endpoint = f"/1/user/-/activities/heart/date/{date}/1d/1min.json"
    return await fetch_fitbit_data(endpoint, token)

async def fetch_sleep_date(token: str, date: str) -> dict:
    print("DEBUG:fetch_sleep_date",token)
    endpoint = f"/1.2/user/-/sleep/date/{date}.json"
    return await fetch_fitbit_data(endpoint, token)

async def fetch_sleep_list(token: str, start: str, end: str) -> dict:
    print("DEBUG:fetch_sleep_list",token)
    endpoint = f"/1.2/user/-/sleep/list.json?afterDate={start}&sort=desc&offset=0&limit=30"
    return await fetch_fitbit_data(endpoint, token)

async def fetch_activity_date(token: str, date: str) -> dict:
    print("DEBUG:fetch_activity_date",token)
    endpoint = f"/1/user/-/activities/date/{date}.json"
    return await fetch_fitbit_data(endpoint, token)

async def fetch_activity_heart_zones(token: str, date: str) -> dict:
    print("DEBUG:fetch_activity_heart_zones",token)
    endpoint = f"/1/user/-/activities/heart/date/{date}/1d.json"
    return await fetch_fitbit_data(endpoint, token)


# Gemini による診断
async def generate_llm_response(
    prompt: str
) -> str:
    """
    Gemini にプロンプトを渡し、生成されたテキストを返します。
    """
    # 引数は位置で渡す
    response = gemini_model.generate_content(prompt)
    return response.text

async def gemini_diagnose(data: dict) -> str:
    """
    集めた全データをまとめてプロンプト化し、Gemini で診断
    """
    # 三重引用符とf文字列でJSONを埋め込む
    prompt = f"""
以下はユーザーの健康データです。睡眠、運動、心拍数の情報から総合的に判断し、生活改善のためのアドバイスを挙げてください。
```json
{json.dumps(data, ensure_ascii=False, indent=2)}
```
"""
    return await generate_llm_response(prompt)

async def run_langgraph_analysis(token: str) -> str:
    """
    トークンを使って一連のFitbitデータを取得し、Gemini診断結果を返す
    """
    today = datetime.now().strftime("%Y-%m-%d")
    start_30_days_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

    # データ収集
    profile = await fetch_profile(token)
    sleep_today = await fetch_sleep_date(token, today)
    sleep_list = await fetch_sleep_list(token, start_30_days_ago, today)
    heartrate = await fetch_heartrate(token, today)
    activity = await fetch_activity_date(token, today)
    heart_zones = await fetch_activity_heart_zones(token, today)

    # まとめる
    data = {
        "profile": profile,
        "sleep_today": sleep_today,
        "sleep_list": sleep_list,
        "heartrate": heartrate,
        "activity": activity,
        "heart_zones": heart_zones,
    }

    # Gemini で診断
    result = await gemini_diagnose(data)
    return result
