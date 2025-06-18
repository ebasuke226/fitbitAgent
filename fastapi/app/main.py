import os
import json
import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from urllib.parse import urlencode
from dotenv import load_dotenv
from datetime import datetime, timedelta
from .functions import (
    get_access_token,
    fetch_profile, fetch_heartrate, fetch_sleep_date, fetch_sleep_list,
    fetch_activity_date, fetch_activity_heart_zones,
    fetch_eda, fetch_spo2, fetch_skin_temp,
    gemini_diagnose
)
from langgraph.graph import StateGraph, END

# ロギング設定
type_logging = logging.getLogger("fitbit_ai")
logging.basicConfig(level=logging.DEBUG)

env_path = os.getcwd()
load_dotenv()

# Fitbit OAuth 設定
CLIENT_ID = os.getenv("FITBIT_CLIENT_ID")
CLIENT_SECRET = os.getenv("FITBIT_CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")

app = FastAPI()
BASE_DIR = os.getcwd()
TOKEN_PATH = os.path.join(BASE_DIR, "token.json")

type_logging.debug(f"WORKDIR={BASE_DIR}, token path={TOKEN_PATH}")

# 1. 認証エンドポイント
@app.get("/")
def authorize():
    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": "activity heartrate sleep temperature weight location nutrition profile",
        "expires_in": "604800"
    }
    url = f"https://www.fitbit.com/oauth2/authorize?{urlencode(params)}"
    type_logging.debug(f"Redirecting to Fitbit auth: {url}")
    return RedirectResponse(url)

# 2. コールバック
@app.get("/callback")
async def callback(request: Request):
    code = request.query_params.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="認可コードがありません")
    type_logging.debug(f"Callback code={code}")
    token_data = await get_access_token(code)
    type_logging.debug(f"Obtained tokens: {list(token_data.keys())}")
    return JSONResponse({"message": "トークン取得成功", "token_data": token_data})

# LangGraph スキーマ定義
from typing import TypedDict
class FitbitData(TypedDict):
    token: str
    date: str
    start_date: str
    profile: dict
    sleep_today: dict
    sleep_list: dict
    heartrate: dict
    activity: dict
    heart_zones: dict
    eda: dict
    advice: str

# ノード実装を再利用
async def n_profile(state): return {"profile": await fetch_profile(state["token"]) }
async def n_sleep_today(state): return {"sleep_today": await fetch_sleep_date(state["token"], state["date"]) }
async def n_sleep_list(state): return {"sleep_list": await fetch_sleep_list(state["token"], state["start_date"], state["date"]) }
async def n_heartrate(state): return {"heartrate": await fetch_heartrate(state["token"], state["date"]) }
async def n_activity(state):
    return {
        "activity": await fetch_activity_date(state["token"], state["date"]),
        "heart_zones": await fetch_activity_heart_zones(state["token"], state["date"]) }
async def n_skin_temp(state): return {"skin_temp": await fetch_skin_temp(state["token"], state["date"]) }
async def n_advice(state):
    data = state
    return {"advice": await gemini_diagnose(data)}

# フロー構築

def build_graph():
    graph = StateGraph(FitbitData)
    graph.add_node("fetch_profile", n_profile)
    graph.add_node("fetch_sleep_today", n_sleep_today)
    graph.add_node("fetch_sleep_list", n_sleep_list)
    graph.add_node("fetch_heartrate", n_heartrate)
    graph.add_node("fetch_activity", n_activity)
    graph.add_node("generate_advice", n_advice)
    graph.set_entry_point("fetch_profile")
    graph.add_edge("fetch_profile", "fetch_sleep_today")
    graph.add_edge("fetch_sleep_today", "fetch_sleep_list")
    graph.add_edge("fetch_sleep_list", "fetch_heartrate")
    graph.add_edge("fetch_heartrate", "fetch_activity")
    graph.add_edge("fetch_activity", "generate_advice")
    graph.add_edge("generate_advice", END)
    return graph.compile()

# Agent 初期化
agent = build_graph()

# 3. 診断エンドポイント
@app.get("/analyze")
async def analyze():
    logging.debug("/analyze called")
    if not os.path.exists(TOKEN_PATH):
        return JSONResponse(400, {"error": "トークンがありません。まず /callback を実行してください。"})
    with open(TOKEN_PATH) as f:
        token = json.load(f)["access_token"]
    today = datetime.now().strftime("%Y-%m-%d")
    start = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    state = {"token": token, "date": today, "start_date": start}
    # 非同期ノード実行
    result = await agent.ainvoke(state)
    logging.debug(f"Agent result: {result}")
    return result