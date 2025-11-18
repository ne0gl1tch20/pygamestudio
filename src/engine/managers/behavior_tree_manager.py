# engine/managers/behavior_tree_manager.py
from enum import Enum
import json
import sys
import random

# Attempt to import core dependencies, use minimal mocks if they fail
try:
    from engine.core.engine_state import EngineState
    from engine.utils.file_utils import FileUtils
    from engine.utils.vector2 import Vector2
    from engine.utils.vector3 import Vector3
except ImportError as e:
    print(f"[BehaviorTreeManager Import Error] {e}. Using Internal Mocks.")
    class EngineState:
        def __init__(self): self.current_scene = self
        def get_object(self, uid): 
            # Mock object retrieval for conditions/tasks
            if uid == "P1001": 
                class MockPlayer:
                    def __init__(self): self.position = Vector2(50, 50)
                return MockPlayer()
            return None
    class FileUtils:
        @staticmethod
        def log_message(msg): print(f"[BTM-INFO] {msg}")
        @staticmethod
        def log_error(msg): print(f"[BTM-ERROR] {msg}", file=sys.stderr)
    class Vector2:
        def __init__(self, x=0, y=0): self.x, self.y = float(x), float(y)
        def __add__(self, other): return Vector2(self.x + other.x, self.y + other.y)
        def __sub__(self, other): return Vector2(self.x - other.x, self.y - other.y)
        def __mul__(self, scalar): return Vector2(self.x * scalar, self.y * scalar)
        @property
        def magnitude(self): return (self.x**2 + self.y**2)**0.5
        def normalized(self): return self * (1/self.magnitude if self.magnitude > 0 else 0)
        def distance_to(self, other): return (self - other).magnitude
    class Vector3:
        def __init__(self, x=0, y=0, z=0): self.x, self.y, self.z = float(x), float(y), float(z)


class NodeState(Enum):
    SUCCESS = 1
    FAILURE = 2
    RUNNING = 3

class BehaviorNode:
    """Base class for all behavior tree nodes."""
    def __init__(self, name="Node"):
        self.name = name
        self.children = []
        self.state = NodeState.FAILURE

    def add_child(self, child_node):
        self.children.append(child_node)

    def execute(self, game_object, dt):
        """Must be overridden by subclasses."""
        raise NotImplementedError

# --- Composite Nodes ---

class Selector(BehaviorNode):
    """
    Composite: Tries children in order. Returns SUCCESS as soon as a child succeeds. 
    Returns FAILURE if all children fail.
    """
    def execute(self, game_object, dt):
        for child in self.children:
            child_state = child.execute(game_object, dt)
            if child_state == NodeState.RUNNING or child_state == NodeState.SUCCESS:
                self.state = child_state
                return self.state
        
        self.state = NodeState.FAILURE
        return self.state

class Sequence(BehaviorNode):
    """
    Composite: Tries children in order. Returns FAILURE as soon as a child fails. 
    Returns SUCCESS if all children succeed.
    """
    def execute(self, game_object, dt):
        for child in self.children:
            child_state = child.execute(game_object, dt)
            if child_state == NodeState.RUNNING or child_state == NodeState.FAILURE:
                self.state = child_state
                return self.state
        
        self.state = NodeState.SUCCESS
        return self.state

# --- Leaf Nodes (Tasks and Conditions) ---

class Task(BehaviorNode):
    """
    Leaf Node: Performs a specific action.
    """
    def __init__(self, name, action_func):
        super().__init__(name)
        self.action_func = action_func

    def execute(self, game_object, dt):
        """Executes the action function, which must return NodeState."""
        try:
            self.state = self.action_func(game_object, dt)
        except Exception as e:
            FileUtils.log_error(f"Error in BT Task '{self.name}': {e}")
            self.state = NodeState.FAILURE
        return self.state

class Condition(BehaviorNode):
    """
    Leaf Node: Checks a specific condition.
    """
    def __init__(self, name, check_func, is_negated=False):
        super().__init__(name)
        self.check_func = check_func
        self.is_negated = is_negated

    def execute(self, game_object, dt):
        """Executes the check function, which must return a boolean."""
        try:
            result = self.check_func(game_object, dt)
            if self.is_negated: result = not result
            
            self.state = NodeState.SUCCESS if result else NodeState.FAILURE
        except Exception as e:
            FileUtils.log_error(f"Error in BT Condition '{self.name}': {e}")
            self.state = NodeState.FAILURE
            
        return self.state

class BehaviorTreeManager:
    """
    Manages the collection and execution of AI Behavior Trees.
    """
    def __init__(self, state: EngineState):
        self.state = state
        self.trees = {} # {tree_name: root_node}
        
        # Register default actions/conditions for templates
        self.available_actions = self._get_default_actions()
        self.available_conditions = self._get_default_conditions()
        self._load_default_tree()
        self._load_patrol_only_tree() # For dropdown demo

    # --- Default Action/Condition Definitions (for templates/editor dropdowns) ---

    def _get_default_actions(self):
        """Returns a dict of default, runnable Task functions."""
        
        def task_patrol(obj, dt):
            # Simple patrol: move left/right within a boundary
            speed = 50 * dt
            
            # Use an auxiliary component (simulated in obj.components) to store state
            bt_state_comp = obj.get_component("AIBTState")
            if not bt_state_comp:
                # Mock component if not found (assuming the game object has an add_component method)
                # NOTE: SceneObject must have a robust add_component/get_component
                initial_state = {"type": "AIBTState", "target_x": obj.position.x + 100, "move_dir": 1}
                # Assuming obj has an add_component method:
                # obj.add_component(initial_state) 
                
                # For safety in mocks, we just create a local state dict
                bt_state_comp = initial_state
                obj.components.append(bt_state_comp) # Assuming components is accessible

            move_dir = bt_state_comp.get("move_dir", 1)
            
            # Update position (assuming 2D for this simple demo)
            if isinstance(obj.position, Vector2):
                 obj.position.x += speed * move_dir
            
            # Flip direction if hitting a simple boundary (e.g., 200 units from origin)
            if obj.position.x > 200:
                bt_state_comp["move_dir"] = -1
            elif obj.position.x < -200:
                bt_state_comp["move_dir"] = 1
                
            return NodeState.RUNNING

        def task_chase_player(obj, dt):
            # Find the player object (mocking UID P1001)
            player_obj = self.state.get_object_by_uid("P1001") 
            if not player_obj: return NodeState.FAILURE
            
            # Simple chase logic
            direction = (player_obj.position - obj.position).normalized()
            speed = 80 * dt
            obj.position += direction * speed
            
            return NodeState.RUNNING

        def task_flee_player(obj, dt):
            # Find the player object
            player_obj = self.state.get_object_by_uid("P1001")
            if not player_obj: return NodeState.FAILURE
            
            # Simple flee logic (move opposite to player)
            direction = (obj.position - player_obj.position).normalized()
            speed = 50 * dt
            obj.position += direction * speed
            
            return NodeState.RUNNING

        def task_idle(obj, dt):
            # Do nothing
            return NodeState.RUNNING
            
        return {
            "Patrol": task_patrol,
            "ChasePlayer": task_chase_player,
            "FleePlayer": task_flee_player,
            "Idle": task_idle
        }

    def _get_default_conditions(self):
        """Returns a dict of default, runnable Condition functions."""
        
        def condition_is_player_near(obj, dt):
            # Find the player object (mocking)
            player_obj = self.state.get_object_by_uid("P1001")
            if not player_obj: return False
            
            # Check distance (e.g., less than 100 units)
            distance = player_obj.position.distance_to(obj.position)
            return distance < 100

        def condition_is_player_too_close(obj, dt):
            # Check if player is too close (e.g., less than 30 units)
            player_obj = self.state.get_object_by_uid("P1001")
            if not player_obj: return False
            distance = player_obj.position.distance_to(obj.position)
            return distance < 30

        return {
            "IsPlayerNear": condition_is_player_near,
            "IsPlayerTooClose": condition_is_player_too_close
        }
        
    # --- Tree Definitions ---

    def _load_default_tree(self):
        """
        Creates the 'DefaultAI' (Chase/Flee/Patrol) demo tree structure.
        """
        
        # 1. Root Selector (Highest Priority: Flee > Chase > Patrol)
        root = Selector("DefaultAI Root Selector")

        # 2. Flee Sequence (Highest Priority)
        flee_seq = Sequence("Flee Sequence")
        flee_seq.add_child(Condition("Is Player Too Close?", self.available_conditions["IsPlayerTooClose"]))
        flee_seq.add_child(Task("Flee", self.available_actions["FleePlayer"]))
        root.add_child(flee_seq)

        # 3. Chase Sequence
        chase_seq = Sequence("Chase Sequence")
        chase_seq.add_child(Condition("Is Player Near?", self.available_conditions["IsPlayerNear"]))
        chase_seq.add_child(Task("Chase", self.available_actions["ChasePlayer"]))
        root.add_child(chase_seq)
        
        # 4. Default Patrol Task
        root.add_child(Task("Patrol", self.available_actions["Patrol"]))
        
        self.trees["DefaultAI"] = root
        FileUtils.log_message("Loaded DefaultAI Behavior Tree.")

    def _load_patrol_only_tree(self):
        """
        Creates a simple tree for the dropdown demo.
        Root -> Task: Patrol
        """
        root = Sequence("PatrolOnly")
        root.add_child(Task("Patrol", self.available_actions["Patrol"]))
        self.trees["PatrolOnly"] = root
        FileUtils.log_message("Loaded PatrolOnly Behavior Tree.")

    # --- Runtime Execution ---

    def execute_tree(self, tree_name: str, game_object, dt: float):
        """
        Executes a specific behavior tree for a game object.
        """
        if tree_name not in self.trees:
            # Fallback/warning for missing tree
            if tree_name != "DefaultAI":
                FileUtils.log_warning(f"Behavior Tree '{tree_name}' not found. Falling back to DefaultAI.")
                tree_name = "DefaultAI"
            else:
                 return # Skip if even default is missing

        root_node = self.trees.get(tree_name)
        if root_node:
            try:
                # Execution starts at the root node
                root_node.execute(game_object, dt)
            except Exception as e:
                FileUtils.log_error(f"Critical error during BT execution for '{tree_name}': {e}")