import jwt
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# デバッグ用途としてハードコーディング
JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = "HS256"
JWT_EXP_DELTA_SECONDS = 3600  # 1時間

def create_jwt_token(data: dict):
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(seconds=JWT_EXP_DELTA_SECONDS)
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_jwt_token(token: str):
    try:
        # PyJWT ≥ 2.0 では decode() の戻り値は dict
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        print("❌ JWT expired")
        return None
    except jwt.InvalidTokenError as e:
        print(f"❌ JWT invalid: {e}")
        return None
