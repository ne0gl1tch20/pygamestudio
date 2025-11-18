# engine/core/network_manager.py
import socket
import threading
import json
import time
import copy
import sys

# Attempt to import core dependencies, use minimal mocks if they fail
try:
    from engine.core.engine_state import EngineState
    from engine.utils.file_utils import FileUtils
    from engine.utils.vector2 import Vector2
    from engine.utils.vector3 import Vector3
except ImportError as e:
    print(f"[NetworkManager Import Error] {e}. Using Internal Mocks.")
    class EngineState: pass
    class FileUtils:
        @staticmethod
        def log_message(msg): print(f"[NM-INFO] {msg}")
        @staticmethod
        def log_error(msg): print(f"[NM-ERROR] {msg}", file=sys.stderr)
        @staticmethod
        def log_warning(msg): print(f"[NM-WARN] {msg}")
    class Vector2:
        def __init__(self, x=0, y=0): self.x, self.y = x, y
        def __str__(self): return f"({self.x}, {self.y})"
    class Vector3(Vector2):
        def __init__(self, x=0, y=0, z=0): super().__init__(x, y); self.z = z


# --- Constants ---
MAX_PACKET_SIZE = 4096
NETWORK_TICK_RATE = 20 # Times per second the server/client attempts to send data

# --- Network Modes ---
MODE_NONE = 0
MODE_HOST = 1
MODE_CLIENT = 2

# --- Network Packet Types (Simplified) ---
PACKET_PLAYER_INPUT = "P_INPUT" # Client to Server
PACKET_AUTHORITATIVE_STATE = "A_STATE" # Server to Client (Full scene sync)
PACKET_JOIN_REQUEST = "JOIN_REQ"
PACKET_JOIN_ACK = "JOIN_ACK"
PACKET_CHAT_MESSAGE = "CHAT"


class NetworkManager:
    """
    Handles multiplayer client/server connectivity and synchronization.
    Uses basic TCP sockets for reliable, authoritative server model.
    """
    
    def __init__(self, state: EngineState):
        self.state = state
        self.state.network_manager = self
        
        self.mode = MODE_NONE
        self.socket = None
        self.thread = None
        self.is_running = False
        
        self.host = self.state.config.network_settings.get("default_host")
        self.port = self.state.config.network_settings.get("default_port")
        self.max_connections = self.state.config.network_settings.get("max_connections", 10)

        # Server State
        self.clients = {} # {address: socket}
        self.player_states = {} # {client_id: {obj_uid: {pos: [x,y,z], ...}}} - Last received state/input
        self.client_id_counter = 100 # Simple ID assignment

        # Client State
        self.client_id = None
        self.latest_server_state = {} # Last authoritative state received from server
        
        self.network_timer = 0.0
        self.network_interval = 1.0 / NETWORK_TICK_RATE
        
    # --- Control Methods ---

    def start_host(self, host: str = None, port: int = None):
        """Starts the network manager as an authoritative server."""
        if self.is_running:
            self.stop()
        
        self.host = host if host else self.host
        self.port = port if port else self.port
        self.mode = MODE_HOST
        self.is_running = True
        self.clients.clear()
        self.player_states.clear()
        self.client_id_counter = 100
        
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind((self.host, self.port))
            self.socket.listen(self.max_connections)
            self.socket.settimeout(0.1) # Non-blocking accept in the thread loop
            
            self.thread = threading.Thread(target=self._server_loop, daemon=True)
            self.thread.start()
            
            FileUtils.log_message(f"Server started on {self.host}:{self.port}")
            return True
        except Exception as e:
            self.stop()
            FileUtils.log_error(f"Failed to start server: {e}")
            return False

    def start_client(self, host: str = None, port: int = None):
        """Starts the network manager as a client, connecting to a server."""
        if self.is_running:
            self.stop()

        self.host = host if host else self.host
        self.port = port if port else self.port
        self.mode = MODE_CLIENT
        self.is_running = True
        
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.socket.setblocking(False) # Use non-blocking for event loop
            
            self.thread = threading.Thread(target=self._client_loop, daemon=True)
            self.thread.start()
            
            # Send initial join request
            self._send_packet(PACKET_JOIN_REQUEST, {"username": "Player", "version": "V4.0.0"})
            
            FileUtils.log_message(f"Client connected to {self.host}:{self.port}")
            return True
        except Exception as e:
            self.stop()
            FileUtils.log_error(f"Failed to connect to server: {e}")
            return False

    def stop(self):
        """Shuts down the network manager, closing sockets and threads."""
        if not self.is_running:
            return
            
        self.is_running = False
        self.mode = MODE_NONE
        
        if self.socket:
            try:
                self.socket.shutdown(socket.SHUT_RDWR)
                self.socket.close()
            except:
                pass # Socket might already be closed

        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
            
        self.clients.clear()
        self.player_states.clear()
        self.latest_server_state.clear()
        FileUtils.log_message("Network Manager stopped.")
        
    def is_hosting(self):
        return self.mode == MODE_HOST
        
    def is_client(self):
        return self.mode == MODE_CLIENT

    # --- Core Loops (Run in a separate thread) ---

    def _server_loop(self):
        """Threaded loop for the server to accept connections and receive data."""
        while self.is_running and self.mode == MODE_HOST:
            # 1. Accept new connections
            try:
                client_socket, addr = self.socket.accept()
                if len(self.clients) >= self.max_connections:
                    client_socket.close()
                    FileUtils.log_warning(f"Connection rejected: Max connections reached.")
                    continue
                    
                client_socket.setblocking(False)
                client_id = self.client_id_counter
                self.client_id_counter += 1
                
                self.clients[client_id] = client_socket
                FileUtils.log_message(f"New client connected: ID {client_id} from {addr[0]}:{addr[1]}")
                
                # Send join acknowledgement with assigned ID
                self._send_packet_to(client_socket, PACKET_JOIN_ACK, {"client_id": client_id})

            except socket.timeout:
                pass # Expected timeout on accept()
            except Exception as e:
                # print(f"Server accept error: {e}") # Suppress frequent minor errors
                pass

            # 2. Receive data from all clients
            self._server_receive_data()
            
            # 3. Prevent 100% CPU utilization
            time.sleep(0.01)


    def _client_loop(self):
        """Threaded loop for the client to receive authoritative data."""
        while self.is_running and self.mode == MODE_CLIENT:
            try:
                data = self.socket.recv(MAX_PACKET_SIZE)
                if data:
                    self._process_received_data(data)
                else:
                    # Server closed the connection
                    FileUtils.log_warning("Server disconnected.")
                    self.stop()
                    break
            except BlockingIOError:
                pass # Expected when no data is available
            except ConnectionResetError:
                FileUtils.log_error("Connection lost to server (Reset).")
                self.stop()
                break
            except Exception as e:
                # print(f"Client receive error: {e}") # Suppress frequent minor errors
                pass
            
            time.sleep(0.01) # Prevent 100% CPU utilization

    # --- Data Transmission/Receiving ---

    def _send_packet(self, type: str, payload: dict, target_socket: socket.socket = None):
        """Encodes and sends a packet over the network."""
        packet = json.dumps({"type": type, "payload": payload})
        try:
            if target_socket:
                target_socket.sendall(packet.encode('utf-8') + b'\n') # Use newline delimiter
            elif self.socket and self.mode == MODE_CLIENT:
                self.socket.sendall(packet.encode('utf-8') + b'\n')
        except Exception as e:
            # Handle socket errors (e.g., disconnection)
            FileUtils.log_error(f"Error sending packet: {e}")
            if target_socket:
                self._server_disconnect_client(target_socket)
            elif self.mode == MODE_CLIENT:
                self.stop()

    def _send_packet_to(self, client_socket: socket.socket, type: str, payload: dict):
        """Server helper to send a packet to a specific client socket."""
        self._send_packet(type, payload, client_socket)
        
    def _broadcast_packet(self, type: str, payload: dict, exclude_client_id: int = None):
        """Server helper to broadcast a packet to all connected clients."""
        packet = json.dumps({"type": type, "payload": payload})
        encoded_packet = packet.encode('utf-8') + b'\n'
        
        client_ids_to_remove = []
        
        for client_id, client_socket in self.clients.items():
            if client_id == exclude_client_id:
                continue
            try:
                client_socket.sendall(encoded_packet)
            except Exception:
                client_ids_to_remove.append(client_id)
        
        # Clean up disconnected clients
        for client_id in client_ids_to_remove:
            self._server_disconnect_client(self.clients.get(client_id), client_id)

    def _server_disconnect_client(self, client_socket: socket.socket, client_id: int = None):
        """Handles server-side cleanup for a disconnected client."""
        if not client_id:
            # Find client_id by socket (less efficient, but necessary if ID is unknown)
            for cid, sock in self.clients.items():
                if sock == client_socket:
                    client_id = cid
                    break
        
        if client_id in self.clients:
            del self.clients[client_id]
            if client_id in self.player_states:
                del self.player_states[client_id]
            FileUtils.log_message(f"Client ID {client_id} disconnected.")
            
    def _server_receive_data(self):
        """Server attempts to receive data from all clients."""
        client_ids_to_remove = []
        for client_id, client_socket in self.clients.items():
            try:
                # Non-blocking receive
                data = client_socket.recv(MAX_PACKET_SIZE)
                if data:
                    self._process_received_data(data, client_id)
                else:
                    # Client disconnected gracefully
                    client_ids_to_remove.append(client_id)
            except BlockingIOError:
                pass # No data available
            except ConnectionResetError:
                client_ids_to_remove.append(client_id)
            except Exception:
                client_ids_to_remove.append(client_id)

        # Cleanup disconnected clients outside the iteration loop
        for client_id in client_ids_to_remove:
            self._server_disconnect_client(self.clients.get(client_id), client_id)

    def _process_received_data(self, data: bytes, source_client_id: int = None):
        """Decodes received network data and processes packets."""
        # TCP stream usually requires handling fragmented packets
        # For simplicity, we assume one packet per received chunk (separated by \n)
        messages = data.decode('utf-8').split('\n')
        
        for msg in messages:
            if not msg.strip(): continue
            try:
                packet = json.loads(msg)
                if packet['type'] == PACKET_PLAYER_INPUT and self.mode == MODE_HOST:
                    self._server_handle_player_input(source_client_id, packet['payload'])
                elif packet['type'] == PACKET_AUTHORITATIVE_STATE and self.mode == MODE_CLIENT:
                    self._client_handle_authoritative_state(packet['payload'])
                elif packet['type'] == PACKET_JOIN_ACK and self.mode == MODE_CLIENT:
                    self.client_id = packet['payload']['client_id']
                    FileUtils.log_message(f"Received JOIN_ACK. Assigned Client ID: {self.client_id}")
                elif packet['type'] == PACKET_CHAT_MESSAGE:
                    FileUtils.log_message(f"[CHAT] Client {source_client_id if source_client_id else 'Server'}: {packet['payload']['message']}")
            except json.JSONDecodeError as e:
                FileUtils.log_error(f"JSON decode error in network data: {e} | Raw: {msg[:100]}...")
            except Exception as e:
                FileUtils.log_error(f"Error processing packet: {e}")

    # --- Server Side Handlers ---

    def _server_handle_player_input(self, client_id: int, payload: dict):
        """
        Processes a client's input (e.g., WASD key state) and updates 
        the server's representation of that player's state.
        """
        # Store the last received input/state from this client
        self.player_states[client_id] = payload
        
        # NOTE: Authoritative movement logic should happen in the GameRuntime/Physics system
        # The GameRuntime's update loop will use the latest self.player_states to move the 
        # corresponding SceneObject (e.g., P1001_clientid) and then call self.update(dt)

    # --- Client Side Handlers ---
    
    def _client_handle_authoritative_state(self, payload: dict):
        """
        Processes the authoritative game state received from the server.
        This state is then applied to local game objects in the next frame update.
        """
        # Store the authoritative state
        self.latest_server_state = payload
        
        # Apply state to scene objects (simplified interpolation)
        scene = self.state.current_scene
        if scene:
            for uid, state_data in payload.items():
                obj = scene.get_object(uid)
                if obj and 'position' in state_data:
                    # Simple application, no interpolation for this demo
                    pos = state_data['position']
                    if obj.is_3d and len(pos) == 3:
                        obj.position = Vector3(*pos)
                    elif not obj.is_3d and len(pos) == 2:
                        obj.position = Vector2(*pos)


    # --- Main Update Loop (Called by EngineRuntime/EditorMain every frame) ---

    def update(self, dt: float):
        """
        Performs network-related tasks like state synchronization.
        This runs in the main thread (or the thread calling EngineRuntime.update).
        """
        if self.mode == MODE_NONE:
            return

        self.network_timer += dt
        if self.network_timer >= self.network_interval:
            self.network_timer = 0.0
            
            if self.mode == MODE_HOST:
                self._server_synchronize_state()
            elif self.mode == MODE_CLIENT:
                self._client_send_input(dt)
        
    def _server_synchronize_state(self):
        """The server collects the current state and broadcasts it to clients."""
        if not self.state.current_scene:
            return
            
        scene = self.state.current_scene
        authoritative_state = {}
        
        # Collect positions of all networked objects (e.g., those with a Rigidbody)
        # Note: We assume networked objects are tagged or have a specific component.
        for obj in scene.get_all_objects():
            # Mock check: Only objects with "P" prefix and Rigidbody are networked
            if obj.uid.startswith('P') and obj.get_component("Rigidbody2D") or obj.get_component("Rigidbody3D"):
                
                # Check for networked component for owner/client ID
                net_comp = obj.get_component("Networked")
                # If a networked component exists, we serialize its relevant state
                
                state_data = {
                    "position": list(obj.position) if obj.is_3d else obj.position.to_tuple(),
                    "rotation": list(obj.rotation) if obj.is_3d else obj.rotation,
                    # Add more state data (velocity, health, etc.)
                }
                authoritative_state[obj.uid] = state_data
                
        # Broadcast the complete state snapshot
        self._broadcast_packet(PACKET_AUTHORITATIVE_STATE, authoritative_state)

    def _client_send_input(self, dt: float):
        """The client collects and sends its input state to the server."""
        input_manager = self.state.input_manager
        
        # Simplified input packet (WASD and Mouse buttons)
        input_data = {
            "keys": {
                'w': input_manager.get_key('w'), 'a': input_manager.get_key('a'),
                's': input_manager.get_key('s'), 'd': input_manager.get_key('d'),
                'space': input_manager.get_key('space')
            },
            "mouse": {
                'lmb': input_manager.get_mouse_button(1),
                'rmb': input_manager.get_mouse_button(3)
            },
            "dt": dt
        }
        
        # Also include the client's current object position for simple client-side prediction/reconciliation
        # Find the player object associated with this client ID
        player_obj = self.state.current_scene.get_object(f"P1001") # Mocking the player UID for the client
        if player_obj:
            input_data['local_pos'] = list(player_obj.position) if player_obj.is_3d else player_obj.position.to_tuple()
            
        self._send_packet(PACKET_PLAYER_INPUT, input_data)
        
    def send_chat_message(self, message: str):
        """Sends a simple chat message."""
        if self.mode != MODE_NONE:
            self._send_packet(PACKET_CHAT_MESSAGE, {"message": message})
        else:
            FileUtils.log_message(f"[LOCAL CHAT] {message}")