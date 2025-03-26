"""
User interface module for Prospector client
"""
import curses
import time

class GameUI:
    """Handles the curses-based user interface"""
    
    def __init__(self, student_id1, student_id2):
        """Initialize the UI"""
        self.screen = None
        self.height = 0
        self.width = 0
        self.student_id1 = student_id1
        self.student_id2 = student_id2
        self.messages = []
        self.cursor_x = 0
        self.cursor_y = 0
        self.selected_orientation = "north"  # Default orientation
        self.input_mode = False
        self.input_buffer = ""
        self.input_prompt = ""
        self.input_callback = None
    
    def initialize(self):
        """Initialize curses and set up the screen"""
        # Initialize curses
        self.screen = curses.initscr()
        curses.start_color()
        curses.curs_set(0)  # Hide cursor by default
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
        
        return True
    
    def cleanup(self):
        """Clean up curses settings"""
        if self.screen:
            # Reset terminal settings
            curses.nocbreak()
            self.screen.keypad(False)
            curses.echo()
            curses.endwin()
    
    def clear(self):
        """Clear the screen"""
        self.screen.clear()
    
    def refresh(self):
        """Refresh the screen"""
        self.screen.refresh()
    
    def add_message(self, message, color=1):
        """Add a message to the message queue"""
        self.messages.append((message, color))
        if len(self.messages) > 5:  # Keep only the most recent messages
            self.messages.pop(0)
    
    def display_header(self):
        """Display the game header"""
        # Title
        title = "PROSPECTOR"
        self.screen.addstr(1, (self.width - len(title)) // 2, title, curses.A_BOLD)
        
        # Student IDs
        subtitle = f"Produced by {self.student_id1} and {self.student_id2} for assessment 2 of CS5003"
        self.screen.addstr(2, (self.width - len(subtitle)) // 2, subtitle)
        
        # Divider
        self.screen.addstr(3, 0, "-" * self.width)
    
    def display_messages(self):
        """Display the message queue"""
        message_y = self.height - 7
        self.screen.addstr(message_y - 1, 1, "Messages:")
        
        for i, (msg, color) in enumerate(self.messages):
            try:
                self.screen.addstr(message_y + i, 1, msg, curses.color_pair(color))
            except curses.error:
                # Handle edge case if message is too long or position is out of bounds
                pass
    
    def display_menu(self, current_option=0, options=None):
        """Display a menu with options"""
        if options is None:
            options = ["Create a new game", "Join a game", "Quit"]
        
        menu_y = 5
        self.screen.addstr(menu_y, 2, "Main Menu:")
        
        for i, option in enumerate(options):
            try:
                if i == current_option:
                    self.screen.addstr(menu_y + i + 2, 4, f"> {option}", curses.color_pair(6) | curses.A_BOLD)
                else:
                    self.screen.addstr(menu_y + i + 2, 4, f"  {option}")
            except curses.error:
                # Handle edge case if screen size is too small
                pass
        
        try:
            self.screen.addstr(menu_y + len(options) + 3, 2, "Use arrow keys to navigate, Enter to select")
        except curses.error:
            # Handle edge case if screen size is too small
            pass
        
        return current_option
    
    def display_game(self, game_state):
        """Display the current game state"""
        if not game_state:
            return
        
        # Game info
        game_info_y = 5
        try:
            self.screen.addstr(game_info_y, 2, f"Game ID: {game_state['game_id']}")
        except curses.error:
            pass
        
        # Player information
        player_info_y = game_info_y + 2
        try:
            self.screen.addstr(player_info_y, 2, "Players:")
        except curses.error:
            pass
        
        for i, player in enumerate(game_state['players']):
            color = 4 if i == 0 else 5  # First player cyan, second yellow
            try:
                self.screen.addstr(player_info_y + i + 1, 4, 
                                  f"{player['name']} - Score: {player['score']}", 
                                  curses.color_pair(color))
            except curses.error:
                pass
        
        # Current player
        current_player = game_state['players'][game_state['current_player_index']]
        current_player_y = player_info_y + len(game_state['players']) + 2
        try:
            self.screen.addstr(current_player_y, 2, f"Current turn: {current_player['name']}")
        except curses.error:
            pass
        
        # Draw the game grid
        grid_y = current_player_y + 2
        grid_x = 10
        self._draw_grid(grid_y, grid_x, game_state['grid'], game_state['grid_size'])
        
        # Game status
        status_y = grid_y + game_state['grid_size'] * 2 + 2
        if game_state['game_over']:
            try:
                if game_state['winner'] == 'draw':
                    self.screen.addstr(status_y, 2, "Game Over - It's a draw!", curses.color_pair(6))
                else:
                    winner = next((p['name'] for p in game_state['players'] if p['id'] == game_state['winner']), "Unknown")
                    self.screen.addstr(status_y, 2, f"Game Over - Winner: {winner}", curses.color_pair(2))
            except curses.error:
                pass
        
        # Controls hint
        controls_y = status_y + 2
        try:
            self.screen.addstr(controls_y, 2, "Controls: Arrow keys to move, Space to change orientation, Enter to place fence")
            self.screen.addstr(controls_y + 1, 2, f"Selected orientation: {self.selected_orientation}")
        except curses.error:
            pass
    
    def _draw_grid(self, start_y, start_x, grid, grid_size):
        """Draw the game grid"""
        cell_width = 4  # Width of each cell in characters
        
        # Safety check to ensure grid has the right dimensions
        if not grid or len(grid) != grid_size:
            return
        
        for y in range(grid_size):
            if y >= len(grid):
                continue
                
            for x in range(grid_size):
                if x >= len(grid[y]):
                    continue
                    
                cell = grid[y][x]
                cell_y = start_y + y * 2
                cell_x = start_x + x * cell_width
                
                # Check if we're within screen bounds
                if cell_y >= self.height - 1 or cell_x >= self.width - 3:
                    continue
                
                # Draw north fence (or space)
                north_char = '---' if cell.get('north', False) else '   '
                try:
                    if self.cursor_y == y and self.cursor_x == x and self.selected_orientation == 'north':
                        self.screen.addstr(cell_y, cell_x, north_char, curses.color_pair(6) | curses.A_BOLD)
                    else:
                        self.screen.addstr(cell_y, cell_x, north_char)
                except curses.error:
                    pass
                
                # Draw west fence (or space)
                west_char = '|' if cell.get('west', False) else ' '
                try:
                    if self.cursor_y == y and self.cursor_x == x and self.selected_orientation == 'west':
                        self.screen.addstr(cell_y + 1, cell_x - 1, west_char, curses.color_pair(6) | curses.A_BOLD)
                    else:
                        self.screen.addstr(cell_y + 1, cell_x - 1, west_char)
                except curses.error:
                    pass
                
                # Draw cell content (owner indicator)
                cell_content = ' '
                cell_color = 1  # Default color
                
                if cell.get('owner') is not None:
                    # Find owner in players list to determine color
                    player_index = 0
                    for i, player in enumerate(grid):
                        if isinstance(player, dict) and player.get('id') == cell.get('owner'):
                            player_index = i
                            break
                    
                    cell_color = 4 if player_index == 0 else 5
                    cell_content = 'A' if player_index == 0 else 'B'
                
                try:
                    self.screen.addstr(cell_y + 1, cell_x + 1, cell_content, curses.color_pair(cell_color))
                except curses.error:
                    pass
                
                # Draw east fence (or space)
                east_char = '|' if cell.get('east', False) else ' '
                try:
                    if self.cursor_y == y and self.cursor_x == x and self.selected_orientation == 'east':
                        self.screen.addstr(cell_y + 1, cell_x + 3, east_char, curses.color_pair(6) | curses.A_BOLD)
                    else:
                        self.screen.addstr(cell_y + 1, cell_x + 3, east_char)
                except curses.error:
                    pass
                
                # Draw south fence (or space)
                south_char = '---' if cell.get('south', False) else '   '
                try:
                    if self.cursor_y == y and self.cursor_x == x and self.selected_orientation == 'south':
                        self.screen.addstr(cell_y + 2, cell_x, south_char, curses.color_pair(6) | curses.A_BOLD)
                    else:
                        self.screen.addstr(cell_y + 2, cell_x, south_char)
                except curses.error:
                    pass
    
    def handle_input(self, game_state=None):
        """Handle keyboard input"""
        if self.input_mode:
            return self._handle_input_mode()
        
        key = self.screen.getch()
        
        # If in a game
        if game_state:
            grid_size = game_state.get('grid_size', 5)
            
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
                # Return fence placement info
                return {
                    'action': 'place_fence',
                    'position': {'x': self.cursor_x, 'y': self.cursor_y},
                    'orientation': self.selected_orientation
                }
            elif key == ord('q'):
                return {'action': 'quit'}
        
        # If in menu
        else:
            return key
        
        return None
    
    def prompt_input(self, prompt, callback):
        """Show a prompt for user input"""
        self.input_mode = True
        self.input_prompt = prompt
        self.input_buffer = ""
        self.input_callback = callback
        curses.curs_set(1)  # Show cursor
    
    def _handle_input_mode(self):
        """Handle input in text input mode"""
        key = self.screen.getch()
        
        if key == 10:  # Enter key
            result = self.input_buffer
            self.input_mode = False
            self.input_buffer = ""
            curses.curs_set(0)  # Hide cursor
            
            if self.input_callback:
                self.input_callback(result)
                self.input_callback = None
        elif key == 27:  # Escape key
            self.input_mode = False
            self.input_buffer = ""
            curses.curs_set(0)  # Hide cursor
            
            if self.input_callback:
                self.input_callback(None)
                self.input_callback = None
        elif key == curses.KEY_BACKSPACE or key == 127 or key == 8:
            # Handle backspace (multiple possible key codes)
            self.input_buffer = self.input_buffer[:-1]
        elif 32 <= key <= 126:  # Printable characters
            self.input_buffer += chr(key)
        
        # Display the prompt and input
        try:
            self.screen.addstr(self.height - 3, 1, self.input_prompt + " " * (self.width - len(self.input_prompt) - 2))
            self.screen.addstr(self.height - 2, 1, self.input_buffer + " " * (self.width - len(self.input_buffer) - 2))
            self.screen.move(self.height - 2, 1 + len(self.input_buffer))  # Move cursor to end of input
        except curses.error:
            # Handle edge case if screen size is too small
            pass
        
        return None

    def highlight_game_id(self, game_id):
        """Display game ID prominently"""
        try:
            # Draw a box around the game ID to make it more visible
            box_y = 5
            box_x = 2
            game_id_text = f"GAME ID: {game_id}"
            
            # Draw horizontal lines
            self.screen.addstr(box_y, box_x, "+" + "-" * (len(game_id_text) + 2) + "+", curses.A_BOLD)
            self.screen.addstr(box_y + 2, box_x, "+" + "-" * (len(game_id_text) + 2) + "+", curses.A_BOLD)
            
            # Draw vertical lines and content
            self.screen.addstr(box_y + 1, box_x, "|", curses.A_BOLD)
            self.screen.addstr(box_y + 1, box_x + len(game_id_text) + 3, "|", curses.A_BOLD)
            
            # Draw the game ID in bright color
            self.screen.addstr(box_y + 1, box_x + 2, game_id_text, curses.color_pair(2) | curses.A_BOLD)
            
            # Add instruction
            self.screen.addstr(box_y + 3, box_x, "Copy this ID to join from another client", curses.color_pair(6))
            
        except curses.error:
            # Handle edge case if screen size is too small
            self.add_message(f"GAME ID: {game_id} (copy this to join)", 2)

    # Update the display_game method to call highlight_game_id
    def display_game(self, game_state):
        """Display the current game state"""
        if not game_state:
            return
        
        # Game info with highlighted ID
        self.highlight_game_id(game_state['game_id'])
        
        # Rest of method remains the same...
        # Player information
        player_info_y = 10  # Adjusted to make room for highlighted game ID
        try:
            self.screen.addstr(player_info_y, 2, "Players:")
        except curses.error:
            pass
        
    def handle_server_message(self, message):
        """Handle a message from the server with improved UI integration"""
        status = message.get('status')
        
        if status == 'error':
            print(f"Error: {message.get('message')}")
            self.add_message(f"Error: {message.get('message')}", 3)
        elif status == 'success':
            if 'game_state' in message:
                self.game_state = message['game_state']
                self.game_id = message['game_state']['game_id']
                
                # Add game ID to console for backup
                print(f"\n=== GAME ID: {self.game_id} ===\n")
                
                # Make sure game ID is visible in messages too
                self.add_message(f"GAME ID: {self.game_id} (copy this)", 2)
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