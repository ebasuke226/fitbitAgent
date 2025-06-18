import os
import streamlit as st
import requests

# 認証はホスト、分析はコンテナ間でアクセス
HOST_URL = os.getenv("HOST_URL", "http://localhost:8080")
API_URL  = os.getenv("API_URL",  "http://fastapi:8080")

st.title("🏥 Fitbit Health AI Agent")

# JWTをクエリパラメータから取得して保存
query_params = st.experimental_get_query_params()
token = query_params.get("token", [None])[0]
if token:
    st.session_state["jwt_token"] = token

# トークン表示（デバッグ用）
jwt_token = st.session_state.get("jwt_token")
st.markdown("📦 **JWT Token**: " + (jwt_token if jwt_token else "なし"))

# 1. 認証リンク（別タブで表示）
if st.button("🔑 Login with Fitbit"):
    st.markdown(
        f'<a href="{HOST_URL}/login" target="_blank">▶ Fitbit 認証ページを開く</a>',
        unsafe_allow_html=True
    )

st.markdown("---")

# 2. ヘルス診断の実行
if st.button("🩺 Run Health Diagnosis"):
    if not jwt_token:
        st.error("JWTトークンが見つかりません。先にログインしてください。")
    else:
        with st.spinner("分析中..."):
            try:
                headers = {"Authorization": f"Bearer {jwt_token}"}
                resp = requests.post(f"{API_URL}/analyze", headers=headers, timeout=30)
                resp.raise_for_status()

                data = resp.json()
                advice = data.get("advice")

                if advice:
                    st.subheader("💡 Life Improvement Advice")
                    st.success(advice)
                else:
                    st.error("診断結果（advice）が取得できませんでした。")
            except requests.exceptions.RequestException as e:
                st.error(f"API呼び出しエラー: {e}")
            except Exception as e:
                st.error(f"予期しないエラー: {e}")
