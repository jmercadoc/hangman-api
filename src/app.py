import asyncio
from typing import Dict
from fastapi import Depends, FastAPI, HTTPException, Query, WebSocket
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import random

import inputs
import db
from utils import generate_game_code, generate_token, get_current_player


app = FastAPI()
active_connections: Dict[str, List[WebSocket]] = {}
origins = [
    "http://localhost:3000",  # React default
    "http://localhost:8080",  # Commonly used port
    "https://hangman.juan-antonio.xyz/",  # Commonly used port
    "http://hangman.juan-antonio.xyz/",  # Commonly used port
    # "https://your-deployed-react-app.com",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/create_game/")
def create_game(game: inputs.GameCreate):
    game_id = generate_game_code()
    token = generate_token(game.admin, game_id)
   
    game_data = {
        'game_id': game_id,
        'admin': game.admin,
        'words': [],
        'all_words': [],
        'current_word': '',
        'current_guess': '',
        'started': False,
        'finished': False,
    }
    db.create_game(game_data)
    return {"gameId": game_id, "token": token, "message": "Game created successfully!"}


@app.post("/add_words/{game_id}")
def add_word(game_id: str, words: inputs.WordsInput, current_player_game: tuple = Depends(get_current_player)):
    current_player, current_game_id = current_player_game
    if game_id != current_game_id:
        raise HTTPException(status_code=400, detail="Invalid game code for this admin.")
    
    game_data = db.get_game(game_id)

    if current_player != game_data['admin']:
        raise HTTPException(status_code=400, detail="Invalid admin for this game code.")
     
    if game_data['started']:
        raise HTTPException(status_code=400, detail="Game already started.")
    
    words_unique = []
    for word in words.words:
        w = word.lower()
        if not w in game_data['words']:
            words_unique.append(w)
    
    if words_unique:  
        game_data['words'].extend(words_unique)
        game_data['all_words'].extend(words_unique)
        
        
    db.save_game(game_data)
    
    return {"message": "Word added successfully!"}


@app.post("/start_game/{game_id}")
async def start_game(game_id: str, current_player_game: tuple = Depends(get_current_player)):
    current_player, current_game_id = current_player_game
    if game_id != current_game_id:
        raise HTTPException(status_code=400, detail="Invalid game code for this admin.")
    
    game_data = db.get_game(game_id)
    
    if current_player != game_data['admin']:
        raise HTTPException(status_code=400, detail="Invalid admin for this game code.")
    
    if game_data['started']:
        raise HTTPException(status_code=400, detail="Game already started.")
    
    if not game_data['words']:
        raise HTTPException(status_code=400, detail="No words added.")
    
    game_data['started'] = True
    game_data['current_word'] = random.choice(game_data['words'])
    game_data['words'].remove(game_data['current_word'])
    game_data['current_guess'] = '_' * len(game_data['current_word'])
    db.save_game(game_data)

    if game_id in active_connections:
        for player_socket in active_connections[game_id]:
            await player_socket.send_text(game_data['current_guess'])
    
    return {"message": "Game started successfully!"}


@app.post("/join_game/{game_id}")
def join_game(game_id: str, player: inputs.PlayerInput):
    game_data = db.get_game(game_id)
    
    if not game_data:
        raise HTTPException(status_code=404, detail="Invalid game code.")
    if game_data['started']:
        raise HTTPException(status_code=400, detail="Game already started.")
    
    token = generate_token(player.player_name, game_id)
    player_data = {
        'game_id': game_id,
        'player_name': player.player_name,
        'guesses': 0, 
        'guessed_words': [],
        'won': False,
    } 
    db.save_player(player_data)
    
    return {"token": token, "message": f"{player.player_name} joined the game!"}


def determine_winner(game_id: str):
    players = db.get_players(game_id)
    max_guesses = max([player['guesses'] for player in players])
    winners = [player['player_name'] for player in players if player['guesses'] == max_guesses]
    return winners


@app.post("/guess_letter/{game_id}")
async def guess_letter(game_id: str, letter_guess: inputs.LetterGuess, current_player_game: tuple = Depends(get_current_player)):
    player_name, current_game_id = current_player_game
    player_data = db.get_player(game_id, player_name)

    if player_data is None:
        raise HTTPException(status_code=404, detail="Invalid player name.")
    
    if game_id != current_game_id:
        raise HTTPException(status_code=400, detail="Invalid game code for this admin.")
    
    game_data = db.get_game(game_id)

    # Comprobar que el juego ha comenzado
    if not game_data['started']:
        raise HTTPException(status_code=400, detail="Game has not started.")
    
    
    # Actualizar la adivinanza
    current_word = game_data['current_word']
    letter = letter_guess.letter.lower() 
    updated_guess = ''.join([current_word[i] if current_word[i] == letter else game_data['current_guess'][i] for i in range(len(current_word))])
    game_data['current_guess'] = updated_guess
    db.save_game(game_data)
     
    if updated_guess == current_word:
        
        player_data = db.get_player(game_id, player_name)
        player_data['guesses'] += 1
        player_data['guessed_words'].append(current_word)
        
        db.save_player(player_data)
        
        await notify_all_players(game_id, "Word guessed! Waiting for the next word.")
        await asyncio.sleep(3)

        if not game_data['words']:
            game_data['finished'] = True
            db.save_game(game_data)
            
            winner = determine_winner(game_id)
            await notify_all_players(game_id, "No more words to guess. Game finished!")
            await notify_all_players(game_id, f"Congratulations! All words guessed. Winner: {winner}.")
            return {"message": f"Congratulations! All words guessed. Winner: {winner}."}
        
        game_data['current_word'] = random.choice(game_data['words'])
        game_data['words'].remove(game_data['current_word'])
        game_data['current_guess'] = '_' * len(game_data['current_word'])
        db.save_game(game_data)
        await notify_all_players(game_id, game_data['current_guess'])

    return {"message": "Guess received!", "current_guess": game_data['current_guess']}


async def notify_all_players(game_id: str, message: str):
    if game_id in active_connections:
        for player_socket in active_connections[game_id]:
            await player_socket.send_text(message)


@app.websocket("/ws/{game_id}/{player_name}")
async def game_updates(websocket: WebSocket, game_id: str, player_name: str):
    print("game_id", game_id, "player_name", player_name)
    await websocket.accept()
    
    # Agrega la conexión WebSocket a las conexiones activas.
    if game_id not in active_connections:
        active_connections[game_id] = []
    active_connections[game_id].append(websocket)
    
    try:
        while True:
            # Aquí podrías enviar/escuchar mensajes si lo necesitas.
            # Por ejemplo, para chat en el juego.
            data = await websocket.receive_text()
            # Procesa 'data' si es necesario...
            
    except Exception as e:
        # Manejar cualquier excepción que pueda surgir.
        pass
    finally:
        # Si un cliente se desconecta, asegúrate de eliminar su WebSocket de las conexiones activas.
        active_connections[game_id].remove(websocket)