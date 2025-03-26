#!/usr/bin/env python3
"""
Test script for Prospector game
"""
import sys
import os
import time
import threading
import json

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from server.server import GameServer
from common.protocol import (
    encode_message, decode_message,
    create_game_message, join_game_message,
    place_fence_message, leave_game_message
)

def start_server():
    """Start the game server in a separate thread"""
    server = GameServer('127.0.0.1', 5556)
    server_thread = threading.Thread(target=server.start)
    server_thread.daemon = True
    server_thread.start()
    return server

def simulate_client(actions, delay=0.5):
    """Simulate a client with a series of actions"""
    import socket
    
    # Connect to server
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect(('127.0.0.1', 5556))
    
    results = []
    
    try:
        for action in actions:
            # Send action
            client_socket.send(encode_message(action))
            
            # Receive response
            data = client_socket.recv(4096)
            response = decode_message(data)
            results.append(response)
            
            print(f"Action: {action}")
            print(f"Response: {json.dumps(response, indent=2)}")
            print("-" * 40)
            
            time.sleep(delay)
    finally:
        client_socket.close()
    
    return results

def test_basic_game():
    """Test a basic game flow"""
    print("Testing basic game flow...")
    
    # Start server
    server = start_server()
    time.sleep(1)  # Wait for server to start
    
    # Define player actions
    player1_actions = [
        create_game_message("Player1", 3, 2),
        # Place fences
        place_fence_message("game_id", 0, 0, "north"),
        place_fence_message("game_id", 1, 1, "east"),
        # ... more fence placements
    ]
    
    player2_actions = [
        join_game_message("game_id", "Player2"),
        # Place fences
        place_fence_message("game_id", 0, 1, "west"),
        place_fence_message("game_id", 2, 2, "south"),
        # ... more fence placements
    ]
    
    # Replace game_id with actual game ID from first response
    player1_results = simulate_client(player1_actions)
    game_id = player1_results[0].get("game_id")
    
    for i in range(1, len(player1_actions)):
        player1_actions[i]["game_id"] = game_id
    
    for action in player2_actions:
        action["game_id"] = game_id
    
    # Continue simulation with correct game ID
    player1_thread = threading.Thread(
        target=simulate_client, 
        args=(player1_actions[1:],)
    )
    player2_thread = threading.Thread(
        target=simulate_client, 
        args=(player2_actions,)
    )
    
    player1_thread.start()
    time.sleep(0.5)
    player2_thread.start()
    
    player1_thread.join()
    player2_thread.join()
    
    print("Basic game test completed.")

if __name__ == "__main__":
    test_basic_game()