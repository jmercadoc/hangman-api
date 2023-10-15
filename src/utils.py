import random
import string
import jwt
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

SECRET_KEY = "hangman_secret_key"
ALGORITHM = "HS256"

def generate_token(user_name: str, game_id: str):
        expiration_time = datetime.utcnow() + timedelta(days=1)

        return jwt.encode(
            {"sub": user_name, "game_id": game_id, "exp": expiration_time},
            SECRET_KEY,
            algorithm=ALGORITHM
        )

def get_current_player(token: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
    try:
        payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        player = payload.get("sub")
        game_id = payload.get("game_id")
        if player is None or game_id is None:
            raise HTTPException(status_code=401, detail="Invalid JWT token")
        return player, game_id
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="JWT token has expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid JWT token")



def generate_game_code():
    chars = ''.join(random.choice(string.ascii_uppercase) for _ in range(3))
    nums = ''.join(random.choice(string.digits) for _ in range(3))
    return f"{chars}-{nums}"