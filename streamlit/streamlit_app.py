import os
import streamlit as st
import requests

# 認証はホスト、分析はコンテナ間
HOST_URL = os.getenv("HOST_URL", "http://localhost:8080")
API_URL  = os.getenv("API_URL",  "http://fastapi:8080")

st.title("Fitbit Health AI Agent")

# 1. 認証（リンク表示のみ）
if st.button("Login with Fitbit"):
    st.markdown(
        f'<a href="{HOST_URL}/" target="_blank">▶ Fitbit 認証ページを開く</a>',
        unsafe_allow_html=True
    )

st.markdown("---")

# 2. 診断実行（LLM応答のみ表示）
if st.button("Run Health Diagnosis"):
    with st.spinner("Analyzing..."):
        try:
            resp = requests.get(f"{API_URL}/analyze", timeout=30)
            resp.raise_for_status()
            data = resp.json()
            advice = None

            # FastAPI の /analyze が返す JSON の中の advice フィールドを取り出す
            if isinstance(data, dict):
                advice = data.get("advice")

            if advice:
                st.subheader("💡 Life Improvement Advice")
                st.write(advice)
            else:
                st.error("診断結果（advice）が取得できませんでした。")
        except Exception as e:
            st.error(f"Error calling /analyze: {e}")