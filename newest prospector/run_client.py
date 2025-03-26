#!/usr/bin/env python3
"""
Client implementation for Prospector game
"""
import sys
import curses
import socket
import json
import threading
import time

# Protocol functions
def encode_message(message):
    """Encode a message to JSON string"""
    return json.dumps(message).encode('utf-8')

def decode_message(data):
    """Decode a JSON string to a message dictionary"""
    return json.loads(data.decode('utf-8'))

class ProspectorClient:
    """Client for Prospector game"""
    
    def __init__(self, student_id1, student_id2, host='127.0.0.1', port=5555):
        """Initialize the client"""
        # Student IDs
        self.student_id1 = 240009696
        self.student_id2 = 240000636
        
        # Network settings
        self.host = host
        self.port = port
        self.socket = None
        
        # Game state
        self.player_name = None
        self.game_id = None
        self.game_state = None
        self.running = False
        
        # Authentication
        self.logged_in = False
        self.username = None
        
        # UI variables
        self.screen = None
        self.height = 0
        self.width = 0
        self.messages = []
        self.cursor_x = 0
        self.cursor_y = 0
        self.selected_orientation = "north"
        self.menu_position = 0
        self.menu_options = [
            "Create a new game", 
            "Join a game", 
            "View statistics", 
            "Replay a game",
            "Register/Login", 
            "Quit"
        ]
        
        # Input handling
        self.input_mode = False
        self.input_buffer = ""
        self.input_prompt = ""
        self.input_callback = None
        
        # Replay mode variables
        self.replay_mode = False
        self.replay_state = None
        self.replay_index = 0
        self.replay_paused = False
        self.recordings = []
        self.recording_position = 0
    
    def connect(self):
        """Connect to the server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            print(f"Connected to server at {self.host}:{self.port}")
            
            # Start receiver thread
            self.receiver_thread = threading.Thread(target=self.receive_messages)
            self.receiver_thread.daemon = True
            self.receiver_thread.start()
            
            return True
        except Exception as e:
            print(f"Connection error: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from the server"""
        if self.socket:
            self.socket.close()
            self.socket = None
    
    def send_message(self, message):
        """Send a message to the server"""
        if not self.socket:
            print("Not connected to server")
            return False
        
        try:
            print(f"Sending: {message}")
            self.socket.send(encode_message(message))
            return True
        except Exception as e:
            print(f"Send error: {e}")
            return False
    
    def receive_messages(self):
        """Receive messages from the server"""
        while self.running and self.socket:
            try:
                data = self.socket.recv(4096)
                if not data:
                    print("Disconnected from server")
                    self.add_message("Disconnected from server", 3)
                    break
                
                message = decode_message(data)
                print(f"Received: {message}")
                self.handle_server_message(message)
                
            except Exception as e:
                print(f"Receive error: {e}")
                break
    
    def handle_server_message(self, message):
        """Handle a message from the server"""
        status = message.get('status')
        
        if status == 'error':
            print(f"Error: {message.get('message')}")
            self.add_message(f"Error: {message.get('message')}", 3)
        elif status == 'success':
            if 'game_state' in message:
                self.game_state = message['game_state']
                self.game_id = message['game_state']['game_id']
                self.add_message(message.get('message', 'Game updated'), 2)
            elif 'username' in message:
                self.logged_in = True
                self.username = message['username']
                self.add_message(f"Successfully logged in as {self.username}", 2)
            elif 'stats' in message:
                stats = message['stats']
                self.add_message(f"Player: {stats['name']}", 2)
                self.add_message(f"Wins: {stats['wins']}, Losses: {stats['losses']}, Draws: {stats['draws']}", 2)
            elif 'recordings' in message:
                self.recordings = message['recordings']
                self.display_recordings()
            elif 'recording' in message:
                self.start_replay(message['recording'])
            else:
                self.add_message(message.get('message', 'Success'), 2)
    
    def initialize_ui(self):
        """Initialize the curses UI"""
        self.screen = curses.initscr()
        curses.start_color()
        curses.curs_set(0)  # Hide cursor
        curses.noecho()
        curses.cbreak()
        self.screen.keypad(True)
        
        # Get screen dimensions
        self.height, self.width = self.screen.getmaxyx()
        
        # Initialize color pairs
        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)  # Default
        curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)  # Success
        curses.init_pair(3, curses.COLOR_RED, curses.COLOR_BLACK)    # Error
        curses.init_pair(4, curses.COLOR_CYAN, curses.COLOR_BLACK)   # Player 1
        curses.init_pair(5, curses.COLOR_YELLOW, curses.COLOR_BLACK) # Player 2
        curses.init_pair(6, curses.COLOR_BLUE, curses.COLOR_BLACK)   # Highlight
        curses.init_pair(7, curses.COLOR_MAGENTA, curses.COLOR_BLACK) # Gold land
        curses.init_pair(8, curses.COLOR_RED, curses.COLOR_BLACK)    # Copper land
    
    def cleanup_ui(self):
        """Clean up the curses UI"""
        if self.screen:
            curses.nocbreak()
            self.screen.keypad(False)
            curses.echo()
            curses.endwin()
    
    def add_message(self, message, color=1):
        """Add a message to the message queue"""
        self.messages.append((message, color))
        if len(self.messages) > 5:
            self.messages.pop(0)
    
    def start(self):
        """Start the client"""
        try:
            # Connect to server
            if not self.connect():
                print("Failed to connect to server")
                return
            
            # Set running flag
            self.running = True
            
            # Initialize UI
            self.initialize_ui()
            
            # Get player name
            self.prompt_input("Enter your name:", self.set_player_name)
            
            # Main loop
            while self.running:
                try:
                    # Clear screen
                    self.screen.clear()
                    
                    # Display header
                    self.display_header()
                    
                    # Handle different UI states
                    if self.input_mode:
                        self.handle_input_mode()
                    elif self.replay_mode:
                        self.display_replay()
                        self.handle_replay_input()
                    elif self.game_state:
                        self.display_game()
                        self.handle_game_input()
                    else:
                        self.display_menu()
                        self.handle_menu_input()
                    
                    # Display messages
                    self.display_messages()
                    
                    # Refresh screen
                    self.screen.refresh()
                    
                    # Small delay
                    time.sleep(0.05)
                
                except curses.error:
                    # Handle curses errors (usually from drawing outside the window)
                    pass
                except Exception as e:
                    print(f"Error in main loop: {e}")
                    self.add_message(f"Error: {e}", 3)
            
        except Exception as e:
            print(f"Error: {e}")
        finally:
            # Clean up
            if self.game_id:
                self.send_message({
                    "action": "leave_game",
                    "game_id": self.game_id
                })
            
            if self.socket:
                self.socket.close()
            
            self.cleanup_ui()
    
    def display_header(self):
        """Display the game header"""
        title = "PROSPECTOR"
        self.screen.addstr(1, (self.width - len(title)) // 2, title, curses.A_BOLD)
        
        subtitle = f"Produced by {self.student_id1} and {self.student_id2} for assessment 2 of CS5003"
        self.screen.addstr(2, (self.width - len(subtitle)) // 2, subtitle)
        
        self.screen.addstr(3, 0, "-" * self.width)
    
    def display_messages(self):
        """Display the message queue"""
        message_y = self.height - 7
        self.screen.addstr(message_y - 1, 1, "Messages:")
        
        for i, (msg, color) in enumerate(self.messages):
            self.screen.addstr(message_y + i, 1, msg[:self.width-2], curses.color_pair(color))
    
    def display_menu(self):
        """Display the main menu"""
        # Update menu items based on login status
        if self.logged_in:
            self.menu_options[4] = f"Logout ({self.username})"
        else:
            self.menu_options[4] = "Register/Login"
        
        menu_y = 5
        self.screen.addstr(menu_y, 2, "Main Menu:")
        
        for i, option in enumerate(self.menu_options):
            if i == self.menu_position:
                self.screen.addstr(menu_y + i + 2, 4, f"> {option}", curses.color_pair(6) | curses.A_BOLD)
            else:
                self.screen.addstr(menu_y + i + 2, 4, f"  {option}")
        
        self.screen.addstr(menu_y + len(self.menu_options) + 3, 2, "Use arrow keys to navigate, Enter to select")
    
    def display_game(self):
        """Display the current game state"""
        if not self.game_state:
            return
        
        # Game info
        game_info_y = 5
        self.screen.addstr(game_info_y, 2, f"Game ID: {self.game_state['game_id']}")
        
        # Player information
        player_info_y = game_info_y + 2
        self.screen.addstr(player_info_y, 2, "Players:")
        
        for i, player in enumerate(self.game_state['players']):
            color = 4 if i == 0 else 5  # Player colors
            self.screen.addstr(player_info_y + i + 1, 4, 
                             f"{player['name']} - Score: {player['score']}", 
                             curses.color_pair(color))
        
        # Current player
        if 'current_player_index' in self.game_state and len(self.game_state['players']) > 0:
            current_index = self.game_state['current_player_index']
            if current_index < len(self.game_state['players']):
                current_player = self.game_state['players'][current_index]
                current_y = player_info_y + len(self.game_state['players']) + 2
                self.screen.addstr(current_y, 2, f"Current turn: {current_player['name']}")
                
                # Display timer
                if not self.game_state['game_over']:
                    current_time = time.time()
                    turn_start_time = self.game_state.get('turn_start_time', current_time)
                    turn_time_limit = self.game_state.get('turn_time_limit', 60)
                    
                    elapsed = current_time - turn_start_time
                    remaining = max(0, turn_time_limit - elapsed)
                    
                    timer_y = current_y + 1
                    timer_color = 3 if remaining < 10 else 1  # Red if less than 10 seconds
                    self.screen.addstr(timer_y, 2, f"Time remaining: {int(remaining)} seconds", 
                                     curses.color_pair(timer_color))
        
        # Draw grid
        grid_y = player_info_y + len(self.game_state['players']) + 6
        grid_x = 10
        self.draw_grid(grid_y, grid_x)
        
        # Game status
        status_y = grid_y + self.game_state['grid_size'] * 2 + 2
        if self.game_state['game_over']:
            if self.game_state['winner'] == 'draw':
                self.screen.addstr(status_y, 2, "Game Over - It's a draw!", curses.color_pair(6))
            else:
                winner = next((p['name'] for p in self.game_state['players'] if p['id'] == self.game_state['winner']), "Unknown")
                self.screen.addstr(status_y, 2, f"Game Over - Winner: {winner}", curses.color_pair(2))
        
        # Controls
        controls_y = status_y + 2
        self.screen.addstr(controls_y, 2, "Controls: Arrow keys to move, Space to change orientation, Enter to place fence, Q to quit")
        self.screen.addstr(controls_y + 1, 2, f"Selected orientation: {self.selected_orientation}")
        
        # Land types legend
        legend_y = controls_y + 3
        self.screen.addstr(legend_y, 2, "Land Types: Regular=1pt, C=Copper (2pts), G=Gold (3pts)", curses.color_pair(1))
    
    def draw_grid(self, start_y, start_x):
        """Draw the game grid"""
        if not self.game_state or 'grid' not in self.game_state:
            return
        
        grid = self.game_state['grid']
        grid_size = self.game_state['grid_size']
        cell_width = 4
        
        # Land type indicators and colors
        land_type_chars = {
            "regular": " ",
            "copper": "C",
            "gold": "G"
        }
        
        land_type_colors = {
            "regular": 1,
            "copper": 8,
            "gold": 7
        }
        
        for y in range(grid_size):
            for x in range(grid_size):
                cell = grid[y][x]
                cell_y = start_y + y * 2
                cell_x = start_x + x * cell_width
                
                # Draw north fence
                north_char = '---' if cell.get('north', False) else '   '
                if y == self.cursor_y and x == self.cursor_x and self.selected_orientation == 'north':
                    self.screen.addstr(cell_y, cell_x, north_char, curses.color_pair(6) | curses.A_BOLD)
                else:
                    self.screen.addstr(cell_y, cell_x, north_char)
                
                # Draw west fence
                west_char = '|' if cell.get('west', False) else ' '
                if y == self.cursor_y and x == self.cursor_x and self.selected_orientation == 'west':
                    self.screen.addstr(cell_y + 1, cell_x - 1, west_char, curses.color_pair(6) | curses.A_BOLD)
                else:
                    self.screen.addstr(cell_y + 1, cell_x - 1, west_char)
                
                # Draw cell content (owner indicator or land type)
                land_type = cell.get('type', 'regular')
                cell_content = land_type_chars.get(land_type, ' ')
                cell_color = land_type_colors.get(land_type, 1)
                
                if cell.get('owner') is not None:
                    # Find owner in players list
                    for i, player in enumerate(self.game_state['players']):
                        if player['id'] == cell['owner']:
                            cell_color = 4 if i == 0 else 5
                            cell_content = 'A' if i == 0 else 'B'
                            break
                
                self.screen.addstr(cell_y + 1, cell_x + 1, cell_content, curses.color_pair(cell_color))
                
                # Draw east fence
                east_char = '|' if cell.get('east', False) else ' '
                if y == self.cursor_y and x == self.cursor_x and self.selected_orientation == 'east':
                    self.screen.addstr(cell_y + 1, cell_x + 3, east_char, curses.color_pair(6) | curses.A_BOLD)
                else:
                    self.screen.addstr(cell_y + 1, cell_x + 3, east_char)
                
                # Draw south fence
                south_char = '---' if cell.get('south', False) else '   '
                if y == self.cursor_y and x == self.cursor_x and self.selected_orientation == 'south':
                    self.screen.addstr(cell_y + 2, cell_x, south_char, curses.color_pair(6) | curses.A_BOLD)
                else:
                    self.screen.addstr(cell_y + 2, cell_x, south_char)
    
    def display_recordings(self):
        """Display the list of available recordings"""
        self.screen.clear()
        self.display_header()
        
        if not self.recordings:
            self.screen.addstr(5, 2, "No recordings available")
            self.screen.addstr(7, 2, "Press any key to return to the menu")
            self.screen.refresh()
            self.screen.getch()
            return
        
        recording_y = 5
        self.screen.addstr(recording_y, 2, "Available Game Recordings:")
        
        for i, recording in enumerate(self.recordings):
            players_str = ", ".join(recording.get("players", []))
            created_at = recording.get("created_at", "Unknown")
            
            if i == self.recording_position:
                self.screen.addstr(recording_y + i + 2, 4, 
                                 f"> Game {i+1}: {players_str} - {created_at}", 
                                 curses.color_pair(6) | curses.A_BOLD)
            else:
                self.screen.addstr(recording_y + i + 2, 4, 
                                 f"  Game {i+1}: {players_str} - {created_at}")
        
        self.screen.addstr(recording_y + len(self.recordings) + 3, 2, 
                         "Use arrow keys to navigate, Enter to select, Q to return to menu")
        
        # Handle input
        self.screen.refresh()
        while True:
            key = self.screen.getch()
            
            if key == curses.KEY_UP:
                self.recording_position = max(0, self.recording_position - 1)
            elif key == curses.KEY_DOWN:
                self.recording_position = min(len(self.recordings) - 1, self.recording_position + 1)
            elif key == 10:  # Enter key
                # Get selected recording
                if 0 <= self.recording_position < len(self.recordings):
                    game_id = self.recordings[self.recording_position]["game_id"]
                    self.send_message({
                        "action": "get_game_recording",
                        "game_id": game_id
                    })
                    return
            elif key == ord('q') or key == ord('Q'):
                return
            
            # Update display
            self.screen.clear()
            self.display_header()
            self.screen.addstr(recording_y, 2, "Available Game Recordings:")
            
            for i, recording in enumerate(self.recordings):
                players_str = ", ".join(recording.get("players", []))
                created_at = recording.get("created_at", "Unknown")
                
                if i == self.recording_position:
                    self.screen.addstr(recording_y + i + 2, 4, 
                                     f"> Game {i+1}: {players_str} - {created_at}", 
                                     curses.color_pair(6) | curses.A_BOLD)
                else:
                    self.screen.addstr(recording_y + i + 2, 4, 
                                     f"  Game {i+1}: {players_str} - {created_at}")
            
            self.screen.addstr(recording_y + len(self.recordings) + 3, 2, 
                             "Use arrow keys to navigate, Enter to select, Q to return to menu")
            
            self.screen.refresh()
    
    def start_replay(self, recording):
        """Start replaying a recorded game"""
        if not recording:
            self.add_message("No moves in recording", 3)
            return
        
        # Initialize replay state
        self.replay_mode = True
        self.replay_index = 0
        self.replay_paused = False
        self.replay_recording = recording
        
        # Initialize grid based on first move
        if len(recording) > 0:
            first_move = recording[0]
            grid_size = 5  # Default
            
            # Create a blank grid
            grid = []
            for y in range(grid_size):
                row = []
                for x in range(grid_size):
                    cell = {
                        "north": False,
                        "east": False,
                        "south": False,
                        "west": False,
                        "owner": None,
                        "type": "regular",
                        "value": 1
                    }
                    row.append(cell)
                grid.append(row)
            
            self.replay_grid = grid
            self.replay_scores = {}
            
            self.add_message("Starting replay. Space to pause/resume, Q to quit", 2)
        else:
            self.add_message("Empty recording", 3)
            self.replay_mode = False
    
    def display_replay(self):
        """Display the replay"""
        if not self.replay_mode or not hasattr(self, 'replay_recording'):
            return
        
        # Display replay header
        self.screen.addstr(5, 2, "GAME REPLAY", curses.A_BOLD)
        
        if self.replay_paused:
            self.screen.addstr(6, 2, "PAUSED", curses.color_pair(3))
        
        # Display current move
        move_y = 8
        if self.replay_index < len(self.replay_recording):
            move = self.replay_recording[self.replay_index]
            player_name = move.get("player_name", "Unknown")
            position = move.get("position", {})
            orientation = move.get("orientation", "unknown")
            land_claimed = move.get("land_claimed", False)
            
            self.screen.addstr(move_y, 2, f"Move {self.replay_index + 1}/{len(self.replay_recording)}")
            self.screen.addstr(move_y + 1, 2, f"Player: {player_name}")
            self.screen.addstr(move_y + 2, 2, f"Position: ({position.get('x', '?')}, {position.get('y', '?')})")
            self.screen.addstr(move_y + 3, 2, f"Orientation: {orientation}")
            self.screen.addstr(move_y + 4, 2, f"Land claimed: {'Yes' if land_claimed else 'No'}")
        
        # Display player scores
        score_y = move_y + 6
        self.screen.addstr(score_y, 2, "Scores:")
        
        score_row = 1
        for player_id, score in self.replay_scores.items():
            # Find player name
            player_name = next((move.get("player_name") for move in self.replay_recording 
                             if move.get("player_id") == player_id), "Unknown")
            
            self.screen.addstr(score_y + score_row, 4, f"{player_name}: {score}")
            score_row += 1
        
        # Draw grid
        grid_y = score_y + score_row + 2
        grid_x = 10
        self.draw_replay_grid(grid_y, grid_x)
        
        # Controls
        controls_y = grid_y + 12
        self.screen.addstr(controls_y, 2, "Controls: Space to pause/resume, Q to quit")
        
        # Apply current move
        if not self.replay_paused and self.replay_index < len(self.replay_recording):
            time.sleep(0.5)  # Delay between moves
            self.apply_replay_move()
    
    def draw_replay_grid(self, start_y, start_x):
        """Draw the replay grid"""
        if not hasattr(self, 'replay_grid'):
            return
        
        grid = self.replay_grid
        grid_size = len(grid)
        cell_width = 4
        
        for y in range(grid_size):
            for x in range(grid_size):
                cell = grid[y][x]
                cell_y = start_y + y * 2
                cell_x = start_x + x * cell_width
                
                # Draw north fence
                north_char = '---' if cell.get('north', False) else '   '
                self.screen.addstr(cell_y, cell_x, north_char)
                
                # Draw west fence
                west_char = '|' if cell.get('west', False) else ' '
                self.screen.addstr(cell_y + 1, cell_x - 1, west_char)
                
                # Draw cell content (owner)
                cell_content = ' '
                cell_color = 1
                
                if cell.get('owner') is not None:
                    # In replay we don't have player objects, so use simple A/B
                    player_index = 0
                    for i, player_id in enumerate(self.replay_scores.keys()):
                        if player_id == cell.get('owner'):
                            player_index = i
                            break
                    
                    cell_content = chr(65 + player_index)  # A, B, C, etc.
                    cell_color = 4 if player_index == 0 else 5
                
                self.screen.addstr(cell_y + 1, cell_x + 1, cell_content, curses.color_pair(cell_color))
                
                # Draw east fence
                east_char = '|' if cell.get('east', False) else ' '
                self.screen.addstr(cell_y + 1, cell_x + 3, east_char)
                
                # Draw south fence
                south_char = '---' if cell.get('south', False) else '   '
                self.screen.addstr(cell_y + 2, cell_x, south_char)
    
    def apply_replay_move(self):
        """Apply the current move in the replay"""
        if self.replay_index >= len(self.replay_recording):
            return
        
        move = self.replay_recording[self.replay_index]
        position = move.get("position", {})
        orientation = move.get("orientation")
        player_id = move.get("player_id")
        land_claimed = move.get("land_claimed", False)
        
        x = position.get('x')
        y = position.get('y')
        
        if x is None or y is None or orientation is None:
            self.replay_index += 1
            return
        
        # Place fence
        cell = self.replay_grid[y][x]
        cell[orientation] = True
        
        # Update adjacent cell
        if orientation == "north" and y > 0:
            self.replay_grid[y-1][x]["south"] = True
        elif orientation == "east" and x < len(self.replay_grid) - 1:
            self.replay_grid[y][x+1]["west"] = True
        elif orientation == "south" and y < len(self.replay_grid) - 1:
            self.replay_grid[y+1][x]["north"] = True
        elif orientation == "west" and x > 0:
            self.replay_grid[y][x-1]["east"] = True
        
        # If land claimed, update owner
        if land_claimed:
            cell["owner"] = player_id
            
            # Update score
            if player_id not in self.replay_scores:
                self.replay_scores[player_id] = 0
            
            self.replay_scores[player_id] += 1
        
        # Move to next move
        self.replay_index += 1
        
        # If at end, show completion message
        if self.replay_index >= len(self.replay_recording):
            self.add_message("Replay complete", 2)
    
    def handle_replay_input(self):
        """Handle input during replay"""
        key = self.screen.getch()
        
        if key == ord(' '):
            # Toggle pause/resume
            self.replay_paused = not self.replay_paused
            status = "paused" if self.replay_paused else "resumed"
            self.add_message(f"Replay {status}", 2)
        elif key == ord('q') or key == ord('Q'):
            # Quit replay mode
            self.replay_mode = False
            self.add_message("Replay ended", 2)
    
    def handle_menu_input(self):
        """Handle input in menu mode"""
        key = self.screen.getch()
        
        if key == curses.KEY_UP:
            self.menu_position = max(0, self.menu_position - 1)
        elif key == curses.KEY_DOWN:
            self.menu_position = min(len(self.menu_options) - 1, self.menu_position + 1)
        elif key == 10:  # Enter key
            self.handle_menu_selection()
        elif key == ord('q') or key == ord('Q'):
            self.running = False
    
    def handle_game_input(self):
        """Handle input in game mode"""
        key = self.screen.getch()
        grid_size = self.game_state.get('grid_size', 5)
        
        if key == curses.KEY_UP:
            self.cursor_y = max(0, self.cursor_y - 1)
        elif key == curses.KEY_DOWN:
            self.cursor_y = min(grid_size - 1, self.cursor_y + 1)
        elif key == curses.KEY_LEFT:
            self.cursor_x = max(0, self.cursor_x - 1)
        elif key == curses.KEY_RIGHT:
            self.cursor_x = min(grid_size - 1, self.cursor_x + 1)
        elif key == ord(' '):
            # Cycle through orientations
            orientations = ['north', 'east', 'south', 'west']
            current_index = orientations.index(self.selected_orientation)
            self.selected_orientation = orientations[(current_index + 1) % 4]
        elif key == 10:  # Enter key
            # Place fence
            self.send_message({
                'action': 'place_fence',
                'game_id': self.game_id,
                'position': {'x': self.cursor_x, 'y': self.cursor_y},
                'orientation': self.selected_orientation
            })
        elif key == ord('q') or key == ord('Q'):
            # Quit game
            if self.game_id:
                self.send_message({
                    'action': 'leave_game',
                    'game_id': self.game_id
                })
            self.game_id = None
            self.game_state = None
    
    def prompt_input(self, prompt, callback):
        """Show a prompt for user input"""
        self.input_mode = True
        self.input_prompt = prompt
        self.input_buffer = ""
        self.input_callback = callback
        curses.curs_set(1)  # Show cursor
    
    def handle_input_mode(self):
        """Handle input in text input mode"""
        # Display the prompt and current input
        self.screen.addstr(self.height - 3, 1, self.input_prompt + " " * 40)
        self.screen.addstr(self.height - 2, 1, self.input_buffer + "_" + " " * 40)
        self.screen.move(self.height - 2, 1 + len(self.input_buffer))
        
        key = self.screen.getch()
        
        if key == 10:  # Enter key
            result = self.input_buffer
            self.input_mode = False
            self.input_buffer = ""
            curses.curs_set(0)  # Hide cursor
            
            if self.input_callback:
                callback = self.input_callback
                self.input_callback = None
                callback(result)
        elif key == 27:  # Escape key
            self.input_mode = False
            self.input_buffer = ""
            curses.curs_set(0)  # Hide cursor
            
            if self.input_callback:
                callback = self.input_callback
                self.input_callback = None
                callback(None)
        elif key == curses.KEY_BACKSPACE or key == 127 or key == 8:
            # Handle backspace
            self.input_buffer = self.input_buffer[:-1]
        elif 32 <= key <= 126:  # Printable characters
            self.input_buffer += chr(key)
    
    def handle_menu_selection(self):
        """Handle menu option selection"""
        if self.menu_position == 0:  # Create a new game
            self.prompt_input("Grid size (2-10):", self.on_grid_size)
        elif self.menu_position == 1:  # Join a game
            self.prompt_input("Enter Game ID:", self.on_game_id)
        elif self.menu_position == 2:  # View statistics
            self.send_message({"action": "get_stats"})
        elif self.menu_position == 3:  # Replay a game
            self.send_message({"action": "list_recordings"})
        elif self.menu_position == 4:  # Register/Login
            if self.logged_in:
                self.send_message({"action": "logout_user"})
                self.logged_in = False
                self.username = None
                self.add_message("Logged out successfully", 2)
            else:
                self.show_login_menu()
        elif self.menu_position == 5:  # Quit
            self.running = False
    
    def show_login_menu(self):
        """Show the login/register menu"""
        login_menu = ["Login", "Register", "Back"]
        login_pos = 0
        
        while True:
            self.screen.clear()
            self.display_header()
            
            menu_y = 5
            self.screen.addstr(menu_y, 2, "User Authentication:")
            
            for i, option in enumerate(login_menu):
                if i == login_pos:
                    self.screen.addstr(menu_y + i + 2, 4, f"> {option}", curses.color_pair(6) | curses.A_BOLD)
                else:
                    self.screen.addstr(menu_y + i + 2, 4, f"  {option}")
            
            self.display_messages()
            self.screen.refresh()
            
            key = self.screen.getch()
            
            if key == curses.KEY_UP:
                login_pos = max(0, login_pos - 1)
            elif key == curses.KEY_DOWN:
                login_pos = min(len(login_menu) - 1, login_pos + 1)
            elif key == 10:  # Enter key
                if login_pos == 0:  # Login
                    self.prompt_login()
                    return
                elif login_pos == 1:  # Register
                    self.prompt_register()
                    return
                elif login_pos == 2:  # Back
                    return
            elif key == ord('q') or key == ord('Q'):
                return
    
    def prompt_login(self):
        """Prompt for login credentials"""
        self.prompt_input("Username:", self.on_login_username)
    
    def on_login_username(self, username):
        """Handle username input for login"""
        if username:
            self.temp_username = username
            self.prompt_input("Password:", self.on_login_password)
        else:
            self.add_message("Login cancelled", 3)
    
    def on_login_password(self, password):
        """Handle password input for login"""
        if password:
            self.send_message({
                "action": "login_user",
                "username": self.temp_username,
                "password": password
            })
            self.temp_username = None
        else:
            self.add_message("Login cancelled", 3)
    
    def prompt_register(self):
        """Prompt for registration credentials"""
        self.prompt_input("Choose a username:", self.on_register_username)
    
    def on_register_username(self, username):
        """Handle username input for registration"""
        if username:
            self.temp_username = username
            self.prompt_input("Choose a password:", self.on_register_password)
        else:
            self.add_message("Registration cancelled", 3)
    
    def on_register_password(self, password):
        """Handle password input for registration"""
        if password:
            self.send_message({
                "action": "register_user",
                "username": self.temp_username,
                "password": password
            })
            self.temp_username = None
        else:
            self.add_message("Registration cancelled", 3)
    
    def set_player_name(self, name):
        """Set the player name"""
        if name:
            self.player_name = name
            self.add_message(f"Welcome, {name}!", 2)
        else:
            self.player_name = "Anonymous"
            self.add_message("Using default name: Anonymous", 3)
    
    def on_grid_size(self, size_str):
        """Handle grid size input"""
        grid_size = 5  # Default
        if size_str and size_str.isdigit():
            size = int(size_str)
            if 2 <= size <= 10:
                grid_size = size
            else:
                self.add_message("Invalid grid size. Using default (5).", 3)
        else:
            self.add_message("Invalid input. Using default grid size (5).", 3)
        
        # Ask for number of players
        self.prompt_input("Number of players (2-4):", lambda num_str: self.on_num_players(num_str, grid_size))
    
    def on_num_players(self, num_str, grid_size):
        """Handle number of players input"""
        num_players = 2  # Default
        if num_str and num_str.isdigit():
            num = int(num_str)
            if 2 <= num <= 4:
                num_players = num
            else:
                self.add_message("Invalid number of players. Using default (2).", 3)
        else:
            self.add_message("Invalid input. Using default (2).", 3)
        
        # Create game
        self.send_message({
            "action": "create_game",
            "player_name": self.player_name,
            "grid_size": grid_size,
            "num_players": num_players
        })
    
    def on_game_id(self, game_id):
        """Handle game ID input"""
        if game_id:
            self.send_message({
                "action": "join_game",
                "game_id": game_id,
                "player_name": self.player_name
            })
        else:
            self.add_message("Join game cancelled.", 3)

def main():
    """Main function to start the client"""
    # Replace with your actual student IDs
    student_id1 = "XXXXXXXXX"
    student_id2 = "YYYYYYYYY"
    
    # Server address
    host = '127.0.0.1'
    port = 5555
    
    # Parse command line arguments
    if len(sys.argv) > 1 and sys.argv[1] != "[host]":
        host = sys.argv[1]
    if len(sys.argv) > 2 and sys.argv[2] != "[port]":
        port = int(sys.argv[2])
    
    print(f"Connecting to Prospector server at {host}:{port}")
    client = ProspectorClient(student_id1, student_id2, host, port)
    client.start()

if __name__ == "__main__":
    main()