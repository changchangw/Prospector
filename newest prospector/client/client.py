#!/usr/bin/env python3
"""
Main client application for Prospector game
"""
import curses
import sys
import time
from client.ui import GameUI
from client.network import NetworkClient
from common.protocol import (
    create_game_message, join_game_message, 
    place_fence_message, leave_game_message, get_stats_message
)

class ProspectorClient:
    """Main client class for Prospector game"""
    
    def __init__(self, student_id1, student_id2, host='127.0.0.1', port=5555):
        """Initialize the client application"""
        self.student_id1 = student_id1
        self.student_id2 = student_id2
        self.ui = GameUI(student_id1, student_id2)
        self.network = NetworkClient(host, port)
        self.player_name = None
        self.game_id = None
        self.game_state = None
        self.running = False
        self.menu_position = 0
        self.menu_options = ["Create a new game", "Join a game", "View statistics", "Quit"]
    
    def start(self):
        """Start the client application"""
        try:
            # Initialize UI
            self.ui.initialize()
            
            # Connect to server
            if not self.network.connect():
                self.ui.add_message("Failed to connect to server", 3)
                time.sleep(2)
                return
            
            # Set message callback
            self.network.set_callback(self.handle_server_message)
            
            # Get player name
            self.ui.prompt_input("Enter your name:", self.set_player_name)
            
            # Main game loop
            self.running = True
            while self.running:
                self.ui.clear()
                self.ui.display_header()
                
                if self.game_state:
                    self.ui.display_game(self.game_state)
                    action = self.ui.handle_input(self.game_state)
                    
                    if action:
                        if action['action'] == 'quit':
                            if self.game_id:
                                self.network.send_message(leave_game_message(self.game_id))
                                self.game_id = None
                                self.game_state = None
                        elif action['action'] == 'place_fence':
                            if self.game_id:
                                action['game_id'] = self.game_id
                                self.network.send_message(action)
                else:
                    # Display menu
                    self.menu_position = self.ui.display_menu(self.menu_position, self.menu_options)
                    key = self.ui.handle_input()
                    
                    if key == curses.KEY_UP:
                        self.menu_position = max(0, self.menu_position - 1)
                    elif key == curses.KEY_DOWN:
                        self.menu_position = min(len(self.menu_options) - 1, self.menu_position + 1)
                    elif key == 10:  # Enter key
                        self.handle_menu_selection(self.menu_position)
                
                self.ui.display_messages()
                self.ui.refresh()
                
                time.sleep(0.05)  # Small delay to reduce CPU usage
                
        except Exception as e:
            self.ui.add_message(f"Error: {e}", 3)
            time.sleep(2)
        finally:
            # Clean up
            if self.game_id:
                self.network.send_message(leave_game_message(self.game_id))
            self.network.disconnect()
            self.ui.cleanup()
    
    def set_player_name(self, name):
        """Set the player name"""
        if name:
            self.player_name = name
            self.ui.add_message(f"Welcome, {name}!", 2)
        else:
            self.player_name = "Anonymous"
            self.ui.add_message("Using default name: Anonymous", 3)
    
    def handle_menu_selection(self, selection):
        """Handle menu selection"""
        if selection == 0:  # Create a new game
            self.prompt_create_game()
        elif selection == 1:  # Join a game
            self.prompt_join_game()
        elif selection == 2:  # View statistics
            self.network.send_message(get_stats_message())
        elif selection == 3:  # Quit
            self.running = False
    
    def prompt_create_game(self):
        """Prompt for game creation settings"""
        def on_grid_size(size):
            if size and size.isdigit():
                grid_size = int(size)
                if 2 <= grid_size <= 10:
                    self.ui.prompt_input("Number of players (2-4):", on_num_players)
                else:
                    self.ui.add_message("Invalid grid size. Please enter a number between 2 and 10.", 3)
            else:
                self.ui.add_message("Invalid input. Using default grid size (5).", 3)
                self.ui.prompt_input("Number of players (2-4):", on_num_players)
        
        def on_num_players(num):
            if num and num.isdigit():
                num_players = int(num)
                if 2 <= num_players <= 4:
                    # Create game with specified settings
                    grid_size = int(size) if size and size.isdigit() else 5
                    msg = create_game_message(self.player_name, grid_size, num_players)
                    self.network.send_message(msg)
                else:
                    self.ui.add_message("Invalid number of players. Please enter a number between 2 and 4.", 3)
            else:
                self.ui.add_message("Invalid input. Using default (2 players).", 3)
                # Create game with default settings
                grid_size = int(size) if size and size.isdigit() else 5
                msg = create_game_message(self.player_name, grid_size, 2)
                self.network.send_message(msg)
        
        self.ui.prompt_input("Grid size (2-10):", on_grid_size)
    
    def prompt_join_game(self):
        """Prompt for game ID to join"""
        def on_game_id(game_id):
            if game_id:
                msg = join_game_message(game_id, self.player_name)
                self.network.send_message(msg)
            else:
                self.ui.add_message("Join game cancelled.", 3)
        
        self.ui.prompt_input("Enter Game ID:", on_game_id)
    
    def handle_server_message(self, message):
        """Handle messages received from the server"""
        status = message.get('status')
        
        if status == 'error':
            self.ui.add_message(f"Error: {message.get('message')}", 3)
        elif status == 'success':
            if 'game_state' in message:
                self.game_state = message['game_state']
                self.game_id = message['game_state']['game_id']
                self.ui.add_message(message.get('message', 'Game updated'), 2)
            elif 'stats' in message:
                stats = message['stats']
                self.ui.add_message(f"Player: {stats['name']}", 2)
                self.ui.add_message(f"Wins: {stats['wins']}, Losses: {stats['losses']}, Draws: {stats['draws']}", 2)
            else:
                self.ui.add_message(message.get('message', 'Success'), 2)

    def draw_grid(self, start_y, start_x):
        """Draw the game grid"""
        if not self.game_state or 'grid' not in self.game_state:
            return
        
        grid = self.game_state['grid']
        grid_size = self.game_state['grid_size']
        cell_width = 4
        
        # Define colors for land types
        land_type_colors = {
            "regular": 1,  # White
            "copper": 3,   # Red (or another color)
            "gold": 5      # Yellow
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
                cell_content = ' '
                cell_color = land_type_colors.get(cell.get('type', 'regular'), 1)
                
                if cell.get('owner') is not None:
                    # Find owner in players list
                    for i, player in enumerate(self.game_state['players']):
                        if player['id'] == cell['owner']:
                            cell_color = 4 if i == 0 else 5
                            cell_content = 'A' if i == 0 else 'B'
                            break
                else:
                    # Show land type indicator if not owned
                    if cell.get('type') == 'copper':
                        cell_content = 'C'
                    elif cell.get('type') == 'gold':
                        cell_content = 'G'
                
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

if __name__ == "__main__":
    # Replace with your actual student IDs
    student_id1 = "XXXXXXXXX"
    student_id2 = "YYYYYYYYY"
    
    # Server address
    host = '127.0.0.1'
    port = 5555
    
    # Parse command-line arguments
    if len(sys.argv) > 1:
        host = sys.argv[1]
    if len(sys.argv) > 2:
        port = int(sys.argv[2])
    
    client = ProspectorClient(student_id1, student_id2, host, port)
    client.start()