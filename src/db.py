import boto3

# Configura boto3 para conectarse a DynamoDB
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
game_table = dynamodb.Table('GameRooms')
player_table = dynamodb.Table('Players')

# game tabla pk = game_id
def create_game(game_data):
    game_table.put_item(Item=game_data)

def get_game(game_id):
    return game_table.get_item(Key={'game_id': game_id}).get('Item')


def save_game(game_data):
    game_table.put_item(Item=game_data)    


# player tabla pk = game_id, sk = player_name
def create_player(player_data):
    player_table.put_item(Item=player_data)

def get_player(game_id, player_name):
    return player_table.get_item(Key={'game_id': game_id, 'player_name': player_name}).get('Item')

def save_player(player_data):
    player_table.put_item(Item=player_data)

def get_players(game_id):
    players = player_table.query(
        KeyConditionExpression='game_id = :game_id',
        ExpressionAttributeValues={
            ':game_id': game_id
        }
    )
    return players.get('Items')    
