"""
Common protocol definitions for Prospector game
"""
import json

# Message types (actions)
CREATE_GAME = "create_game"
JOIN_GAME = "join_game"
PLACE_FENCE = "place_fence"
LEAVE_GAME = "leave_game"
GET_STATS = "get_stats"

# Response statuses
SUCCESS = "success"
ERROR = "error"
UPDATE = "update"

def create_message(action, **kwargs):
    """Create a protocol message with the given action and parameters"""
    message = {"action": action}
    message.update(kwargs)
    return message

def encode_message(message):
    """Encode a message to JSON string"""
    return json.dumps(message).encode('utf-8')

def decode_message(data):
    """Decode a JSON string to a message dictionary"""
    return json.loads(data.decode('utf-8'))

# Client to Server message creation helpers
def create_game_message(player_name, grid_size=5, num_players=2):
    """Create a message to create a new game"""
    return create_message(
        CREATE_GAME,
        player_name=player_name,
        grid_size=grid_size,
        num_players=num_players
    )

def join_game_message(game_id, player_name):
    """Create a message to join an existing game"""
    return create_message(
        JOIN_GAME,
        game_id=game_id,
        player_name=player_name
    )

def place_fence_message(game_id, x, y, orientation):
    """Create a message to place a fence"""
    return create_message(
        PLACE_FENCE,
        game_id=game_id,
        position={"x": x, "y": y},
        orientation=orientation
    )

def leave_game_message(game_id):
    """Create a message to leave a game"""
    return create_message(
        LEAVE_GAME,
        game_id=game_id
    )

def get_stats_message(player_id=None):
    """Create a message to get player statistics"""
    return create_message(
        GET_STATS,
        player_id=player_id
    )