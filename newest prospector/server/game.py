"""
Game logic for Prospector
"""
import uuid
import time
from datetime import datetime
import threading

class Game:
    """Represents a Prospector game instance"""
    
    def __init__(self, grid_size=5, num_players=2):
        """Initialize a new game with the given grid size and player count"""
        self.game_id = str(uuid.uuid4())
        self.grid_size = grid_size
        self.num_players = num_players
        self.players = []
        self.current_player_index = 0
        self.grid = self._initialize_grid(grid_size)
        self.game_over = False
        self.winner = None
        self.created_at = datetime.now().isoformat()
        self.last_activity = time.time()
        self.land_types = self._initialize_land_types(grid_size)
        self.turn_time_limit = 60  # 60 seconds per turn
        self.turn_start_time = time.time()
        self.timer_thread = None
        self.timer_active = False
    
    def _initialize_grid(self, size):
        """Initialize an empty grid of the specified size"""
        grid = []
        for y in range(size):
            row = []
            for x in range(size):
                cell = {
                    "north": False,  # North fence
                    "east": False,   # East fence
                    "south": False,  # South fence
                    "west": False,   # West fence
                    "owner": None,   # Player who claimed this land
                    "type": "regular"  # Type of land
                }
                row.append(cell)
            grid.append(row)
        return grid
    
    def _initialize_land_types(self, size):
        """Initialize land types (all regular by default)"""
        return "regular"
    
    def add_player(self, player_id, player_name):
        """Add a player to the game"""
        if len(self.players) >= self.num_players:
            return False
        
        # Check if player is already in the game
        if any(p["id"] == player_id for p in self.players):
            return False
        
        self.players.append({
            "id": player_id,
            "name": player_name,
            "score": 0
        })
        
        self.last_activity = time.time()
        return True
    
    def place_fence(self, player_id, x, y, orientation):
        """Place a fence at the specified position and orientation"""
        # Check if it's the player's turn
        if self.players[self.current_player_index]["id"] != player_id:
            return {"status": "error", "message": "Not your turn"}
        
        # Check if the game is over
        if self.game_over:
            return {"status": "error", "message": "Game is over"}
        
        # Validate position
        if x < 0 or x >= self.grid_size or y < 0 or y >= self.grid_size:
            return {"status": "error", "message": "Position out of bounds"}
        
        # Validate orientation
        if orientation not in ["north", "east", "south", "west"]:
            return {"status": "error", "message": "Invalid orientation"}
        
        # Check if fence already exists
        cell = self.grid[y][x]
        if cell[orientation]:
            return {"status": "error", "message": "Fence already exists"}
        
        # Place the fence
        cell[orientation] = True
        
        # Also update the adjacent cell's corresponding fence
        if orientation == "north" and y > 0:
            self.grid[y-1][x]["south"] = True
        elif orientation == "east" and x < self.grid_size - 1:
            self.grid[y][x+1]["west"] = True
        elif orientation == "south" and y < self.grid_size - 1:
            self.grid[y+1][x]["north"] = True
        elif orientation == "west" and x > 0:
            self.grid[y][x-1]["east"] = True
        
        # Check if land is claimed
        land_claimed = False
        if self._check_land_enclosed(x, y):
            # Update owner and score
            current_player = self.players[self.current_player_index]
            cell["owner"] = current_player["id"]
            
            # Add points based on land type
            points = 1 if cell["type"] == "regular" else 2
            current_player["score"] += points
            
            land_claimed = True
        
        # Update last activity
        self.last_activity = time.time()
        
        # Update current player if no land was claimed
        if not land_claimed:
            self.current_player_index = (self.current_player_index + 1) % len(self.players)
        
        # Check if the game is over
        if self._check_game_over():
            self._end_game()
        
        return {
            "status": "success",
            "land_claimed": land_claimed
        }
    
    def _check_land_enclosed(self, x, y):
        """Check if a piece of land is completely enclosed by fences"""
        cell = self.grid[y][x]
        return (cell["north"] and cell["east"] and cell["south"] and 
                cell["west"] and cell["owner"] is None)
    
    def _check_game_over(self):
        """Check if the game is over (all land claimed)"""
        for row in self.grid:
            for cell in row:
                # If all fences are present but no owner, it should have been claimed
                if (cell["north"] and cell["east"] and cell["south"] and 
                    cell["west"] and cell["owner"] is None):
                    return False
                
                # If not all fences are present, game is not over
                if not (cell["north"] and cell["east"] and cell["south"] and cell["west"]):
                    return False
        
        return True
    
    def _end_game(self):
        """Handle game end conditions"""
        self.game_over = True
        
        # Find the winner(s)
        max_score = max(p["score"] for p in self.players)
        winners = [p["id"] for p in self.players if p["score"] == max_score]
        
        # If there's only one winner
        if len(winners) == 1:
            self.winner = winners[0]
        else:
            # It's a draw
            self.winner = "draw"
    
    def remove_player(self, player_id):
        """Handle a player leaving the game"""
        # Find player in the game
        player_index = next((i for i, p in enumerate(self.players) if p["id"] == player_id), None)
        if player_index is None:
            return False
        
        # If game hasn't started or only one player, game ends
        if len(self.players) <= 1:
            return "remove_game"
        
        # Remove player from game
        self.players.pop(player_index)
        
        # Adjust current player index if needed
        if self.current_player_index >= len(self.players):
            self.current_player_index = 0
        
        # Mark game as over if only one player remains
        if len(self.players) == 1:
            self.game_over = True
            self.winner = self.players[0]["id"]
        
        return True
    
    def to_dict(self):
        """Convert game state to a dictionary for JSON serialization"""
        return {
            "game_id": self.game_id,
            "grid_size": self.grid_size,
            "num_players": self.num_players,
            "players": self.players,
            "current_player_index": self.current_player_index,
            "grid": self.grid,
            "game_over": self.game_over,
            "winner": self.winner,
            "created_at": self.created_at,
            "last_activity": self.last_activity
        }

    def start_turn_timer(self, on_timeout):
        """Start a timer for the current player's turn"""
        self.turn_start_time = time.time()
        self.timer_active = True
        
        if self.timer_thread and self.timer_thread.is_alive():
            self.timer_thread.cancel()
        
        self.timer_thread = threading.Timer(self.turn_time_limit, on_timeout)
        self.timer_thread.daemon = True
        self.timer_thread.start()

    def cancel_turn_timer(self):
        """Cancel the current turn timer"""
        self.timer_active = False
        if self.timer_thread and self.timer_thread.is_alive():
            self.timer_thread.cancel()

    def get_remaining_time(self):
        """Get the remaining time for the current turn"""
        elapsed = time.time() - self.turn_start_time
        remaining = max(0, self.turn_time_limit - elapsed)
        return int(remaining)