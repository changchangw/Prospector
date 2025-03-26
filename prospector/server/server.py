#!/usr/bin/env python3
"""
Server implementation for Prospector game
"""
import socket
import json
import threading
import uuid
import time
import random
from datetime import datetime

# Protocol functions
def encode_message(message):
    """Encode a message to JSON string"""
    return json.dumps(message).encode('utf-8')

def decode_message(data):
    """Decode a JSON string to a message dictionary"""
    return json.loads(data.decode('utf-8'))

class GameServer:
    """Main server class for Prospector game"""
    
    def __init__(self, host='127.0.0.1', port=5555):
        """Initialize the server"""
        self.host = host
        self.port = port
        self.server_socket = None
        self.games = {}  # Dictionary to store active games
        self.players = {}  # Dictionary to store player stats
        self.recordings = {}  # Store game recordings
        self.users = {}  # Store registered users
        self.lock = threading.Lock()  # Lock for thread-safe operations
        self.running = False
    
    def start(self):
        """Start the server"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.running = True
            print(f"Server started on {self.host}:{self.port}")
            
            # Start inactivity checker
            checker_thread = threading.Thread(target=self.check_inactivity)
            checker_thread.daemon = True
            checker_thread.start()
            
            while self.running:
                try:
                    client_socket, address = self.server_socket.accept()
                    print(f"Connection from {address}")
                    
                    # Create a new thread to handle the client
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, address)
                    )
                    client_thread.daemon = True
                    client_thread.start()
                    
                except Exception as e:
                    if self.running:
                        print(f"Error accepting connection: {e}")
            
        except Exception as e:
            print(f"Server error: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """Stop the server"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
            print("Server stopped")
    
    def handle_client(self, client_socket, address):
        """Handle a client connection"""
        player_id = str(uuid.uuid4())
        player_name = None
        game_id = None
        
        try:
            while self.running:
                # Receive data from client
                data = client_socket.recv(4096)
                if not data:
                    break
                
                # Parse JSON message
                try:
                    message = decode_message(data)
                    print(f"Received from {address}: {message}")
                    
                    # Process message
                    response = self.process_message(message, player_id)
                    
                    # Update player_name and game_id if applicable
                    if 'player_name' in message:
                        player_name = message['player_name']
                    if 'game_id' in response and response['game_id']:
                        game_id = response['game_id']
                    
                    # Send response
                    client_socket.send(encode_message(response))
                except json.JSONDecodeError:
                    print(f"Invalid JSON from {address}")
                    client_socket.send(encode_message({
                        "status": "error",
                        "message": "Invalid JSON format"
                    }))
                
        except Exception as e:
            print(f"Error handling client {address}: {e}")
        finally:
            # Clean up when client disconnects
            print(f"Client {address} disconnected")
            if game_id and game_id in self.games:
                self.handle_player_disconnect(player_id, game_id)
            client_socket.close()
    
    def process_message(self, message, player_id):
        """Process a message from a client"""
        action = message.get('action', '')
        print(f"Processing action: {action}")
        
        if action == 'create_game':
            return self.create_game(message, player_id)
        elif action == 'join_game':
            return self.join_game(message, player_id)
        elif action == 'place_fence':
            return self.place_fence(message, player_id)
        elif action == 'leave_game':
            return self.leave_game(message, player_id)
        elif action == 'get_stats':
            return self.get_stats(message, player_id)
        elif action == 'register_user':
            return self.register_user(message, player_id)
        elif action == 'login_user':
            return self.login_user(message, player_id)
        elif action == 'list_recordings':
            return self.list_recordings(message, player_id)
        elif action == 'get_game_recording':
            return self.get_game_recording(message, player_id)
        elif action == 'logout_user':
            return self.logout_user(message, player_id)
        else:
            return {"status": "error", "message": "Unknown action"}
    
    def create_game(self, message, player_id):
        """Create a new game"""
        with self.lock:
            player_name = message.get('player_name', f"Player_{player_id[:8]}")
            grid_size = message.get('grid_size', 5)
            num_players = message.get('num_players', 2)
            
            # Validate inputs
            if grid_size < 2 or grid_size > 10:
                return {"status": "error", "message": "Invalid grid size (2-10)"}
            if num_players < 2 or num_players > 4:
                return {"status": "error", "message": "Invalid number of players (2-4)"}
            
            # Create game ID
            game_id = str(uuid.uuid4())
            
            # Initialize game state
            game_state = {
                "game_id": game_id,
                "grid_size": grid_size,
                "num_players": num_players,
                "players": [{
                    "id": player_id,
                    "name": player_name,
                    "score": 0
                }],
                "current_player_index": 0,
                "grid": self.initialize_grid(grid_size),
                "game_over": False,
                "winner": None,
                "created_at": datetime.now().isoformat(),
                "last_activity": time.time(),
                "turn_start_time": time.time(),
                "turn_time_limit": 60  # 60 seconds per turn
            }
            
            # Store game state
            self.games[game_id] = game_state
            
            # Initialize player stats
            if player_id not in self.players:
                self.players[player_id] = {
                    "name": player_name,
                    "wins": 0,
                    "losses": 0,
                    "draws": 0
                }
            
            # Initialize recordings for this game
            self.recordings[game_id] = []
            
            return {
                "status": "success",
                "message": "Game created successfully",
                "game_id": game_id,
                "game_state": game_state
            }
    
    def join_game(self, message, player_id):
        """Join an existing game"""
        with self.lock:
            game_id = message.get('game_id')
            player_name = message.get('player_name', f"Player_{player_id[:8]}")
            
            if not game_id or game_id not in self.games:
                return {"status": "error", "message": "Invalid game ID"}
            
            game = self.games[game_id]
            
            # Check if game is full
            if len(game["players"]) >= game.get("num_players", 2):
                return {"status": "error", "message": "Game is full"}
            
            # Check if player is already in the game
            if any(p["id"] == player_id for p in game["players"]):
                return {"status": "error", "message": "Player already in game"}
            
            # Add player to game
            game["players"].append({
                "id": player_id,
                "name": player_name,
                "score": 0
            })
            
            # Update last activity
            game["last_activity"] = time.time()
            
            # Initialize player stats
            if player_id not in self.players:
                self.players[player_id] = {
                    "name": player_name,
                    "wins": 0,
                    "losses": 0,
                    "draws": 0
                }
            
            return {
                "status": "success",
                "message": "Game joined successfully",
                "game_id": game_id,
                "game_state": game
            }

    def place_fence(self, message, player_id):
        """Place a fence"""
        with self.lock:
            game_id = message.get('game_id')
            position = message.get('position', {})
            orientation = message.get('orientation')
            
            if not game_id or game_id not in self.games:
                return {"status": "error", "message": "Invalid game ID"}
            
            game = self.games[game_id]
            
            # Check if it's the player's turn
            current_player = game["players"][game["current_player_index"]]
            if current_player["id"] != player_id:
                return {"status": "error", "message": "Not your turn"}
            
            # Check if the game is over
            if game["game_over"]:
                return {"status": "error", "message": "Game is over"}
            
            # Validate and place the fence
            x = position.get('x')
            y = position.get('y')
            
            # Validate position
            if x is None or y is None:
                return {"status": "error", "message": "Invalid position"}
            
            if x < 0 or x >= game["grid_size"] or y < 0 or y >= game["grid_size"]:
                return {"status": "error", "message": "Position out of bounds"}
            
            # Validate orientation
            if orientation not in ["north", "east", "south", "west"]:
                return {"status": "error", "message": "Invalid orientation"}
            
            # Check if fence already exists
            grid = game["grid"]
            cell = grid[y][x]
            if cell[orientation]:
                return {"status": "error", "message": "Fence already exists"}
            
            # Place the fence
            cell[orientation] = True
            
            # Update adjacent cell's fence
            if orientation == "north" and y > 0:
                grid[y-1][x]["south"] = True
            elif orientation == "east" and x < game["grid_size"] - 1:
                grid[y][x+1]["west"] = True
            elif orientation == "south" and y < game["grid_size"] - 1:
                grid[y+1][x]["north"] = True
            elif orientation == "west" and x > 0:
                grid[y][x-1]["east"] = True
            
            # Check if land is claimed
            land_claimed = False
            if self.check_land_enclosed(grid, x, y):
                # Update owner and score
                cell["owner"] = current_player["id"]
                # Add score based on land type
                land_value = cell.get("value", 1)  # Default to 1 if no value specified
                current_player["score"] += land_value
                land_claimed = True
            
            # Update last activity
            game["last_activity"] = time.time()
            
            # Update current player if no land was claimed
            if not land_claimed:
                game["current_player_index"] = (game["current_player_index"] + 1) % len(game["players"])
            
            # Reset turn timer
            game["turn_start_time"] = time.time()
            
            # Record the move
            if game_id not in self.recordings:
                self.recordings[game_id] = []

            self.recordings[game_id].append({
                "timestamp": time.time(),
                "player_id": player_id,
                "player_name": current_player["name"],
                "position": {"x": x, "y": y},
                "orientation": orientation,
                "land_claimed": land_claimed
            })
            
            # Check if the game is over
            if self.check_game_over(game):
                self.end_game(game)
            
            return {
                "status": "success",
                "message": "Fence placed successfully",
                "game_state": game,
                "land_claimed": land_claimed
            }
    
    def leave_game(self, message, player_id):
        """Leave a game"""
        with self.lock:
            game_id = message.get('game_id')
            
            if not game_id or game_id not in self.games:
                return {"status": "error", "message": "Invalid game ID"}
            
            game = self.games[game_id]
            
            return self.handle_player_disconnect(player_id, game_id)
    
    def get_stats(self, message, player_id):
        """Get player statistics"""
        with self.lock:
            if player_id not in self.players:
                return {"status": "error", "message": "Player not found"}
            
            return {
                "status": "success",
                "message": "Player statistics",
                "stats": self.players[player_id]
            }
    
    def handle_player_disconnect(self, player_id, game_id):
        """Handle a player disconnecting"""
        with self.lock:
            if game_id not in self.games:
                return {"status": "error", "message": "Game not found"}
            
            game = self.games[game_id]
            
            # Find player in the game
            player_index = None
            for i, player in enumerate(game["players"]):
                if player["id"] == player_id:
                    player_index = i
                    break
            
            if player_index is None:
                return {"status": "error", "message": "Player not in game"}
            
            # If game hasn't started or only one player, remove the game
            if len(game["players"]) <= 1:
                del self.games[game_id]
                return {"status": "success", "message": "Game removed"}
            
            # Otherwise, handle as player leaving
            player = game["players"][player_index]
            
            # Update remaining players' stats (they win)
            for p in game["players"]:
                if p["id"] != player_id:
                    if p["id"] in self.players:
                        self.players[p["id"]]["wins"] += 1
            
            # Update leaving player's stats (they lose)
            if player_id in self.players:
                self.players[player_id]["losses"] += 1
            
            # Remove player from game
            game["players"].pop(player_index)
            
            # Adjust current player index if needed
            if game["current_player_index"] >= len(game["players"]):
                game["current_player_index"] = 0
            
            # Mark game as over if only one player remains
            if len(game["players"]) == 1:
                game["game_over"] = True
                game["winner"] = game["players"][0]["id"]
            
            return {
                "status": "success",
                "message": "Player left game",
                "game_state": game
            }
    
    def initialize_grid(self, size):
        """Initialize an empty grid with different land types"""
        grid = []
        for y in range(size):
            row = []
            for x in range(size):
                # Randomly determine land type
                land_type = random.choices(
                    ["regular", "copper", "gold"],
                    weights=[0.7, 0.2, 0.1],  # 70% regular, 20% copper, 10% gold
                    k=1
                )[0]
                
                # Assign value based on land type
                land_value = 1
                if land_type == "copper":
                    land_value = 2
                elif land_type == "gold":
                    land_value = 3
                
                cell = {
                    "north": False,
                    "east": False,
                    "south": False,
                    "west": False,
                    "owner": None,
                    "type": land_type,
                    "value": land_value
                }
                row.append(cell)
            grid.append(row)
        return grid
    
    def check_land_enclosed(self, grid, x, y):
        """Check if a piece of land is completely enclosed by fences"""
        cell = grid[y][x]
        return (cell["north"] and cell["east"] and cell["south"] and 
                cell["west"] and cell["owner"] is None)
    
    def check_game_over(self, game):
        """Check if the game is over (all land claimed)"""
        grid = game["grid"]
        for row in grid:
            for cell in row:
                if not (cell["north"] and cell["east"] and cell["south"] and cell["west"]):
                    return False
        return True
    
    def end_game(self, game):
        """Handle game end conditions"""
        game["game_over"] = True
        
        # Find the winner(s)
        max_score = max(p["score"] for p in game["players"])
        winners = [p["id"] for p in game["players"] if p["score"] == max_score]
        
        # If there's only one winner
        if len(winners) == 1:
            winner_id = winners[0]
            game["winner"] = winner_id
            
            # Update player stats
            for player in game["players"]:
                player_id = player["id"]
                if player_id in self.players:
                    if player_id == winner_id:
                        self.players[player_id]["wins"] += 1
                    else:
                        self.players[player_id]["losses"] += 1
        else:
            # It's a draw
            game["winner"] = "draw"
            
            # Update player stats
            for player in game["players"]:
                player_id = player["id"]
                if player_id in self.players:
                    self.players[player_id]["draws"] += 1
    
    def check_inactivity(self):
        """Periodically check for inactive players"""
        inactivity_timeout = 60  # 60 seconds
        
        while self.running:
            time.sleep(10)  # Check every 10 seconds
            
            current_time = time.time()
            
            with self.lock:
                for game_id, game in list(self.games.items()):
                    if game["game_over"]:
                        continue
                    
                    # Check if current player has been inactive
                    turn_start_time = game.get("turn_start_time", current_time)
                    if current_time - turn_start_time > inactivity_timeout:
                        current_player_index = game["current_player_index"]
                        current_player = game["players"][current_player_index]
                        
                        print(f"Player {current_player['name']} timed out in game {game_id}")
                        
                        # Move to next player
                        game["current_player_index"] = (current_player_index + 1) % len(game["players"])
                        game["turn_start_time"] = current_time
                        game["last_activity"] = current_time
    
    def register_user(self, message, player_id):
        """Register a new user"""
        username = message.get('username')
        password = message.get('password')
        
        if not username or not password:
            return {"status": "error", "message": "Username and password required"}
        
        with self.lock:
            if username in self.users:
                return {"status": "error", "message": "Username already exists"}
            
            # Create user
            self.users[username] = {
                "password": password,
                "player_id": player_id,
                "stats": {
                    "wins": 0,
                    "losses": 0,
                    "draws": 0
                }
            }
            
            return {
                "status": "success",
                "message": f"User {username} registered successfully",
                "username": username
            }

    def login_user(self, message, player_id):
        """Login an existing user"""
        username = message.get('username')
        password = message.get('password')
        
        if not username or not password:
            return {"status": "error", "message": "Username and password required"}
        
        with self.lock:
            if username not in self.users:
                return {"status": "error", "message": "Username not found"}
            
            if self.users[username]["password"] != password:
                return {"status": "error", "message": "Incorrect password"}
            
            # Update player ID
            old_player_id = self.users[username]["player_id"]
            self.users[username]["player_id"] = player_id
            
            # Copy stats from old player ID if it exists
            if old_player_id in self.players:
                self.players[player_id] = self.players[old_player_id]
                self.players[player_id]["name"] = username
            else:
                # Initialize player stats
                self.players[player_id] = {
                    "name": username,
                    "wins": self.users[username]["stats"]["wins"],
                    "losses": self.users[username]["stats"]["losses"],
                    "draws": self.users[username]["stats"]["draws"]
                }
            
            return {
                "status": "success",
                "message": f"Logged in as {username}",
                "username": username
            }
    
    def logout_user(self, message, player_id):
        """Logout the current user"""
        # No actual server-side action needed for logout
        return {
            "status": "success",
            "message": "Logged out successfully"
        }
    
    def list_recordings(self, message, player_id):
        """List available game recordings"""
        recordings_list = []
        
        for game_id in self.recordings:
            if game_id in self.games:
                game = self.games[game_id]
                recordings_list.append({
                    "game_id": game_id,
                    "created_at": game.get("created_at", "Unknown"),
                    "players": [p["name"] for p in game.get("players", [])]
                })
        
        return {
            "status": "success",
            "message": "Recordings list retrieved",
            "recordings": recordings_list
        }
    
    def get_game_recording(self, message, player_id):
        """Get a recording of a game"""
        game_id = message.get('game_id')
        
        if not game_id or game_id not in self.recordings:
            return {"status": "error", "message": "Recording not found"}
        
        return {
            "status": "success",
            "message": "Game recording retrieved",
            "recording": self.recordings[game_id]
        }

def main():
    """Main function to start the server"""
    import sys
    
    host = '127.0.0.1'
    port = 5555
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        host = sys.argv[1]
    if len(sys.argv) > 2:
        port = int(sys.argv[2])
    
    print(f"Starting Prospector server on {host}:{port}")
    server = GameServer(host, port)
    
    try:
        server.start()
    except KeyboardInterrupt:
        print("Server shutdown requested...")
        server.stop()

if __name__ == "__main__":
    main()