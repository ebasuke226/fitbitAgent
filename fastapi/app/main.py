import httpx
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
    gemini_diagnose
)
from langgraph.graph import StateGraph, END

from .auth import create_jwt_token, decode_jwt_token
from .functions import run_langgraph_analysis


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

@app.get("/")
def root():
    return {"message": "FastAPI is running."}

@app.get("/login")
async def login():
    return RedirectResponse(
        url=f"https://www.fitbit.com/oauth2/authorize?response_type=code&client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&scope=profile%20activity%20sleep%20heartrate%20temperature"
    )

@app.get("/callback")
async def callback(code: str):
    auth = (CLIENT_ID, CLIENT_SECRET)  # ← タプルで渡す
    headers = {
    "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {
        "client_id": CLIENT_ID,
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI,
        "code": code,
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.fitbit.com/oauth2/token",
            headers=headers,
            data=data,
            auth=auth  # ← ここで渡す
        )

    if resp.status_code != 200:
        raise HTTPException(status_code=500, detail=f"認証失敗: {resp.text}")

    token_data = resp.json()

    # JWTを作成
    jwt_payload = {
        "access_token": token_data["access_token"],
        "refresh_token": token_data["refresh_token"],
        "user_id": token_data["user_id"]
    }
    jwt_token = create_jwt_token(jwt_payload)

    # ✅ Streamlit 側にリダイレクト（←絶対これ）
    return RedirectResponse(url=f"http://localhost:8501/?token={jwt_token}")




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
@app.post("/analyze")
async def analyze(request: Request):
    # JWTからアクセストークン取り出して診断実行（例）
    auth_header = request.headers.get("Authorization")
    print("✅ Authorization Header:", auth_header)


    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    
    token = auth_header.split(" ")[1]
    user_data = decode_jwt_token(token)
    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    result = await run_langgraph_analysis(user_data["access_token"])
    return {"advice": result}

