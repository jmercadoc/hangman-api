from pydantic import BaseModel
from typing import List


class GameCreate(BaseModel):
    admin: str


class WordsInput(BaseModel):
    words: List[str]


class PlayerInput(BaseModel):
    player_name: str


class LetterGuess(BaseModel):
    letter: str
