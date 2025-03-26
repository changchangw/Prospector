"""
Network communication module for Prospector client
"""
import socket
import threading
from common.protocol import encode_message, decode_message

class NetworkClient:
    """Handles network communication with the game server"""
    
    def __init__(self, host='127.0.0.1', port=5555):
        """Initialize with server host and port"""
        self.host = host
        self.port = port
        self.socket = None
        self.connected = False
        self.callback = None
        self.receiver_thread = None
    
    def connect(self):
        """Connect to the server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.connected = True
            
            # Start receiver thread
            self.receiver_thread = threading.Thread(target=self._receive_messages)
            self.receiver_thread.daemon = True
            self.receiver_thread.start()
            
            return True
        except Exception as e:
            print(f"Connection error: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from the server"""
        self.connected = False
        if self.socket:
            self.socket.close()
            self.socket = None
    
    def send_message(self, message):
        """Send a message to the server"""
        if not self.connected or not self.socket:
            return False
        
        try:
            self.socket.send(encode_message(message))
            return True
        except Exception as e:
            print(f"Send error: {e}")
            self.connected = False
            return False
    
    def set_callback(self, callback):
        """Set callback function for received messages"""
        self.callback = callback
    
    def _receive_messages(self):
        """Continuously receive and process messages from the server"""
        while self.connected and self.socket:
            try:
                data = self.socket.recv(4096)
                if not data:
                    break
                
                message = decode_message(data)
                
                # Call the callback if set
                if self.callback:
                    self.callback(message)
                
            except Exception as e:
                print(f"Receive error: {e}")
                break
        
        self.connected = False