=== docs/api_reference.md ===
```markdown
# Pygame Studio Engine V4 - GODMODE PLUS API Reference

## I. Engine Architecture and Core State

The engine operates on a highly decoupled component-based architecture orchestrated by the global `EngineState`. All major systems (Physics, Rendering, Input) and user scripts communicate primarily through this central object.

### The EngineState Object (`self.state` in scripts/managers)
The central source of truth for the engine's entire state.

| Property | Type | Description |
| :--- | :--- | :--- |
| **`config`** | `EngineConfig` | Access to persistent editor and project settings (read-only access). |
| **`is_editor_mode`** | `bool` | `True` if running in the Editor, `False` if in the standalone game runtime. |
| **`current_scene`** | `Scene` | The currently loaded Scene object (root of the scene graph). |
| **`selected_object_uid`** | `str` | UID of the object currently selected in the Editor Hierarchy. |
| **`input_manager`** | `InputManager` | The core input system for querying keyboard/mouse/joystick status. |
| **`game_manager`** | `GameManager` | Handles project saving, loading, and initiating the runtime loop. |
| **`scene_manager`** | `SceneManager` | Manages scene loading, saving, and object lifecycle. |
| **`camera_manager`** | `CameraManager` | Manages all `CameraObject`s and the currently active camera view. |
| **`audio_manager`** | `AudioManager` | Controls sound playback, volume, and waveform generation. |
| **`network_manager`** | `NetworkManager` | Manages multiplayer hosting and client connection status. |
| **`utils`** | `dict` | **The sanctioned way to access all core utility classes** (`Vector2`, `Timer`, `MathUtils`, etc.) within scripts. |
| **`renderer_2d` / `renderer_3d`** | `Renderer2D`/`Renderer3D` | Access to the active rendering system. |
| **`script_engine`** | `ScriptEngine` | Manages script module loading and execution sandboxes. |

---

## II. Scene and Game Object Scripting (The Sandbox)

User scripts are executed within a special `ScriptSandbox` instance (`self`), providing controlled, high-level access to the hosting `SceneObject`.

### The Script Sandbox (`self` in `init/update/cleanup`)

| Property | Type | Description |
| :--- | :--- | :--- |
| **`uid`, `name`, `is_3d`** | `str`, `str`, `bool` | Read-only access to the object's identity. |
| **`position`, `rotation`, `scale`** | `Vector2`/`Vector3` | **Read/Write access** to the object's world-space transform. Mutating these updates the object directly. |
| **`components`** | `list[dict]` | The full list of component dictionaries attached to the object. **Use `get_component()` for safer access.** |

| Method | Signature | Description |
| :--- | :--- | :--- |
| **`get_component`** | `get_component(type: str) -> dict \| None` | Returns the component dictionary for the given type (e.g., "Rigidbody2D"). **Mutating this dictionary is how script modifies component properties.** |
| **`find_object`** | `find_object(name_or_uid: str) -> ScriptSandbox \| None` | Searches the current scene by name or UID and returns a sandbox instance for the found object. |

### Example Script Implementation

```python
# scripts/my_player_script.py

# Access utility classes via self.utils
# NOTE: No explicit imports required for engine/utils classes!

def init(self):
    # Initialize script-local variables
    self.move_vector = self.utils.Vector2.zero()
    self.initial_position = self.position.copy() # Use .copy() to prevent reference issues
    self.thrust_timer = self.utils.Timer(duration=2.0, is_looping=True)
    self.thrust_timer.start()
    
    # Get component properties
    rb_comp = self.get_component("Rigidbody2D")
    if rb_comp:
        print(f"Initial Mass: {rb_comp.get('mass')}")

def update(self, dt):
    # --- Input Handling Example ---
    if self.input_manager.get_key('d'):
        self.move_vector = self.utils.Vector2.right() * 100 * dt
        self.position += self.move_vector
        
    # --- Timer Check Example ---
    if self.thrust_timer.check():
        self.audio_manager.play_sound("thrust_sound") # Use audio manager
        
    # --- Component Modification Example (Physics) ---
    rb_comp = self.get_component("Rigidbody2D")
    if rb_comp and self.input_manager.get_key_down('space'):
        # Toggle dynamic state
        rb_comp['is_dynamic'] = not rb_comp['is_dynamic']
        self.state.audio_manager.play_sound("click_ui_sound") # Access via self.state

def cleanup(self):
    print(f"{self.name} script finished.")
```

---

## III. Utility Class Reference (`self.utils.*`)

These utility classes contain essential functions for game development. They are exposed directly through the `self.utils` dictionary in scripts.

| Class | Method / Property | Signature / Description |
| :--- | :--- | :--- |
| **`Vector2`** | `Vector2(x, y)` | Constructor. |
| | `magnitude` | `float`: The length of the vector. |
| | `normalize()` | `Vector2`: Returns a new unit vector. |
| | `dot(other) -> float` | Calculates the dot product. |
| | `lerp(other, t) -> Vector2` | Linear interpolation to another vector. |
| **`Vector3`** | `Vector3(x, y, z)` | Constructor. |
| | `cross(other) -> Vector3` | Calculates the cross product. |
| | `forward()`, `up()`, `right()` | Static methods returning common unit vectors. |
| **`Color`** | `Color(r, g, b, a)` | Constructor (0-255). |
| | `from_hex(hex_str)` | `Color`: Creates color from `#RRGGBB` or `#RRGGBBAA`. |
| | `lerp(other, t) -> Color` | Interpolates smoothly between two colors. |
| | `red()`, `white()` | Static methods returning common preset colors. |
| **`MathUtils`** | `clamp(v, min, max) -> float` | Clamps a value between a minimum and maximum. |
| | `lerp(a, b, t) -> float` | Linear interpolation between two floats. |
| | `perlin_noise_3d(x, y, z) -> float` | Generates Perlin noise in the range [-1.0, 1.0]. |
| **`Timer`** | `Timer(duration, is_looping)` | Constructor. |
| | `start()`, `pause()`, `reset()` | Control methods for the timer state. |
| | `check() -> bool` | Updates and returns `True` if duration is reached. Automatically loops if set. |
| | `get_time_ratio() -> float` | Returns elapsed time as a ratio of duration (0.0 to 1.0). |
| **`FileUtils`** | `log_message(msg, level='INFO')` | Writes a timestamped message to the console and log file. |

---

## IV. Core Manager API Details

### `NetworkManager` (`self.state.network_manager`)

| Method | Signature | Description |
| :--- | :--- | :--- |
| **`start_host`** | `start_host(host: str, port: int) -> bool` | Attempts to start the local game as an authoritative server on the specified IP/Port. |
| **`start_client`** | `start_client(host: str, port: int) -> bool` | Attempts to connect the local game as a client to the specified server. |
| **`stop`** | `stop()` | Shuts down the network connection (server or client). |
| **`send_chat_message`**| `send_chat_message(message: str)` | Sends a simple chat message packet (demo functionality). |
| **`player_states`** | `dict` | (Server Only) Dictionary of the latest input/state received from all connected clients. |

### `CutsceneManager` (`self.state.cutscene_manager`)

| Method | Signature | Description |
| :--- | :--- | :--- |
| **`play`** | `play()` | Starts playback of the `active_cutscene` from the current `playback_time`. |
| **`pause`** | `pause()` | Pauses cutscene playback. |
| **`stop`** | `stop()` | Stops playback and resets `playback_time` to 0.0. |
| **`set_playback_time`**| `set_playback_time(time: float)` | Jumps to a specific point in the timeline (triggers immediate state update). |
| **`active_cutscene`** | `Cutscene` | The currently loaded `Cutscene` object, including all its `tracks`. |

---

## V. Component Schemas and Runtime Effect

Components define data that affects the engine's core systems. Understanding their properties is key to modifying an object's behavior.

### Physics Components

| Component Type | Schema Property | Type | Runtime Effect |
| :--- | :--- | :--- | :--- |
| **`Rigidbody2D/3D`** | `mass` | `float` | Determines inertia and acceleration under force. Must be > 0 for dynamic objects. |
| | `is_dynamic` | `bool` | If `True`, is affected by gravity, forces, and is checked for collisions. |
| | `restitution` | `float` (0.0 - 1.0) | Bounciness after collision. 0.0 = no bounce, 1.0 = perfect reflection. |
| | `linear_damping` | `float` (0.0 - 1.0) | Slows down linear velocity over time (air resistance/friction). |
| **`BoxCollider2D`** | `width`, `height` | `float` | Dimensions of the unrotated rectangular collision box. |
| **`BoxCollider3D`** | `half_extents` | `vector3` | Half the length of the box along X, Y, and Z axes from the object's center. |

### AI and Scripting Components

| Component Type | Schema Property | Type | Runtime Effect |
| :--- | :--- | :--- | :--- |
| **`Script`** | `file` | `asset_selector` (script) | Path to the Python file defining the `init/update/cleanup` hooks. |
| | `enabled` | `bool` | Toggles execution of the script's `update` function. |
| **`BehaviorTree`**| `tree_name` | `dropdown` | Name of the behavior tree to execute for this NPC (e.g., "DefaultAI"). |
| **`AIBTState`** | *N/A* (Internal) | `dict` | Used by the `BehaviorTreeManager` to store persistent state data (e.g., "patrol direction," "last known player position") between task executions. |

### Rendering Components

| Component Type | Schema Property | Type | Runtime Effect |
| :--- | :--- | :--- | :--- |
| **`SpriteRenderer`** | `asset` | `asset_selector` (image) | The texture/sprite asset to be drawn. |
| | `layer` | `int` | Determines the drawing order (higher layers are drawn on top). |
| **`MeshRenderer`** | `mesh_asset` | `asset_selector` (mesh) | Reference to the loaded 3D mesh (e.g., from an OBJ or CSG export). |
| | `material_asset`| `asset_selector` (material) | Reference to the material definition defining color, roughness, and shader. |
```