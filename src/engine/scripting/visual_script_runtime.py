# engine/scripting/visual_script_runtime.py
import json
import sys
from typing import Dict, Any, List, Tuple, Callable

# Attempt to import core dependencies, use minimal mocks if they fail
try:
    from engine.core.engine_state import EngineState
    from engine.core.scene_manager import SceneObject
    from engine.utils.file_utils import FileUtils
    from engine.utils.vector2 import Vector2
    from engine.utils.vector3 import Vector3
    from engine.utils.math_utils import MathUtils
except ImportError as e:
    print(f"[VisualScriptRuntime Import Error] {e}. Using Internal Mocks.")
    class EngineState: pass
    class FileUtils:
        @staticmethod
        def log_message(msg): print(f"[VSR-INFO] {msg}")
        @staticmethod
        def log_error(msg): print(f"[VSR-ERROR] {msg}", file=sys.stderr)
    class Vector2:
        def __init__(self, x, y): self.x, self.y = x, y
    class Vector3:
        def __init__(self, x, y, z): self.x, self.y, self.z = x, y, z
    class MathUtils:
        @staticmethod
        def clamp(v, a, b): return max(a, min(b, v))
    class SceneObject:
        def __init__(self, uid): self.uid = uid; self.position = Vector2(0, 0)
        def get_component(self, type): return None


# --- Node Definition Registry ---

class NodeRegistry:
    """Stores the logic for all available visual script nodes."""
    
    # Execution function signature: func(node_data, runtime_context, execution_input) -> (output_value, next_exec_node_id)
    # Value function signature: func(node_data, runtime_context) -> output_value

    REGISTRY: Dict[str, Dict[str, Any]] = {}

    @staticmethod
    def register_node(type: str, exec_func: Callable = None, value_func: Callable = None, metadata: Dict = None):
        """Registers a new node type."""
        NodeRegistry.REGISTRY[type] = {
            "exec_func": exec_func,
            "value_func": value_func,
            "metadata": metadata if metadata else {"category": "Logic"}
        }

# --- Default Node Implementations ---

def exec_start_event(node, context, exec_input):
    """Execution Node: Entry point for the script (like `init`)."""
    # Simply passes execution flow to the 'Out' connection
    return None, node['outputs']['Out']['connections'][0]['target_node'] if node['outputs']['Out']['connections'] else None
    
def exec_update_event(node, context, exec_input):
    """Execution Node: Frame update point (like `update(dt)`)."""
    # Simply passes execution flow to the 'Out' connection
    return None, node['outputs']['Out']['connections'][0]['target_node'] if node['outputs']['Out']['connections'] else None

def exec_branch(node, context, exec_input):
    """Execution Node: If/Else conditional branch."""
    condition_input_id = node['inputs']['Condition']['connections'][0]['target_node']
    condition_value = context.evaluate_value_node(condition_input_id)
    
    if condition_value:
        # Branch is True
        return None, node['outputs']['True']['connections'][0]['target_node'] if node['outputs']['True']['connections'] else None
    else:
        # Branch is False
        return None, node['outputs']['False']['connections'][0]['target_node'] if node['outputs']['False']['connections'] else None

def exec_set_position(node, context, exec_input):
    """Execution Node: Sets the position of the owning object."""
    # Evaluate the input value nodes
    new_pos_input_id = node['inputs']['Position']['connections'][0]['target_node']
    new_pos = context.evaluate_value_node(new_pos_input_id)
    
    # Apply to the owner object
    if new_pos and isinstance(context.owner_object.position, (Vector2, Vector3)):
        context.owner_object.position = new_pos
        
    # Pass execution
    return None, node['outputs']['Out']['connections'][0]['target_node'] if node['outputs']['Out']['connections'] else None

def value_get_position(node, context):
    """Value Node: Returns the current position of the owning object."""
    return context.owner_object.position

def value_add_float(node, context):
    """Value Node: Adds two float values."""
    # Get values from input connections or default properties
    val_a_id = node['inputs']['A']['connections'][0]['target_node']
    val_b_id = node['inputs']['B']['connections'][0]['target_node']
    
    val_a = context.evaluate_value_node(val_a_id)
    val_b = context.evaluate_value_node(val_b_id)
    
    # Ensure they are numbers before adding
    try:
        return float(val_a) + float(val_b)
    except:
        return 0.0

# Register default nodes
NodeRegistry.register_node("StartEvent", exec_func=exec_start_event, metadata={"category": "Events"})
NodeRegistry.register_node("UpdateEvent", exec_func=exec_update_event, metadata={"category": "Events"})
NodeRegistry.register_node("Branch", exec_func=exec_branch, metadata={"category": "Flow"})
NodeRegistry.register_node("SetPosition", exec_func=exec_set_position, metadata={"category": "Transform"})
NodeRegistry.register_node("GetPosition", value_func=value_get_position, metadata={"category": "Transform"})
NodeRegistry.register_node("AddFloat", value_func=value_add_float, metadata={"category": "Math"})
NodeRegistry.register_node("FloatConstant", value_func=lambda n, c: n['properties']['Value'], metadata={"category": "Math"})


# --- Visual Script Runtime Context ---

class RuntimeContext:
    """
    Holds the runtime state for a single executing visual script instance.
    Includes the object it is attached to and a reference to the engine state.
    """
    def __init__(self, script_graph: Dict, owner_object: SceneObject, state: EngineState):
        self.script_graph = script_graph
        self.owner_object = owner_object
        self.state = state
        self._node_states = {} # For persistent node data (e.g., flip-flop)

    def get_node(self, node_id: str) -> Dict | None:
        """Retrieves a node dictionary by its ID."""
        return self.script_graph.get("nodes", {}).get(node_id)

    def evaluate_value_node(self, node_id: str) -> Any:
        """
        Recursively evaluates a value node (non-execution flow) and returns its output.
        Handles caching of evaluation results within the current frame (optional optimization).
        """
        node = self.get_node(node_id)
        if not node: return None

        node_type = node['type']
        node_def = NodeRegistry.REGISTRY.get(node_type)
        
        if node_def and node_def.get('value_func'):
            try:
                # Call the registered value function
                return node_def['value_func'](node, self)
            except Exception as e:
                FileUtils.log_error(f"Error evaluating value node {node_type} ({node_id}): {e}")
                return None
        
        # If it's not a value node, but an execution node, it cannot be evaluated for a value
        return None

# --- Visual Script Runtime Manager ---

class VisualScriptRuntime:
    """
    Manages the execution of all active visual script graphs attached to SceneObjects.
    """
    
    def __init__(self, state: EngineState):
        self.state = state
        self.state.visual_script_runtime = self
        self.active_scripts: Dict[str, RuntimeContext] = {} # {obj_uid: RuntimeContext}
        
        FileUtils.log_message(f"VisualScriptRuntime initialized with {len(NodeRegistry.REGISTRY)} node types.")

    def initialize_script(self, obj: SceneObject, graph_data: Dict):
        """Creates a runtime context for a single visual script graph."""
        if obj.uid in self.active_scripts:
            # Cleanup old instance if present
            del self.active_scripts[obj.uid]
            
        context = RuntimeContext(graph_data, obj, self.state)
        self.active_scripts[obj.uid] = context
        
        # Immediately run the 'StartEvent' node chain
        self._execute_event_chain("StartEvent", context)

    def update_scripts(self, dt: float):
        """Triggers the 'UpdateEvent' chain for all active scripts."""
        for context in self.active_scripts.values():
            # Pass dt as execution input (useful for nodes that need frame time)
            self._execute_event_chain("UpdateEvent", context, execution_input={'dt': dt})

    def _execute_event_chain(self, event_type: str, context: RuntimeContext, execution_input: Any = None):
        """
        Finds all nodes of the given event_type and starts their execution chain.
        """
        # Simple graph traversal via execution flow
        
        # Find all nodes that match the event type
        start_nodes = [n for n_id, n in context.script_graph.get("nodes", {}).items() if n['type'] == event_type]
        
        for start_node in start_nodes:
            current_node_id = start_node['id']
            next_exec_node_id = current_node_id # Start at the event node itself

            # Iterative traversal loop (prevents infinite recursion for long chains)
            while next_exec_node_id:
                node = context.get_node(next_exec_node_id)
                if not node: break
                
                node_type = node['type']
                node_def = NodeRegistry.REGISTRY.get(node_type)
                
                if not node_def or not node_def.get('exec_func'):
                    FileUtils.log_error(f"Node '{node_type}' ({next_exec_node_id}) is not an executable node.")
                    break
                
                try:
                    # Execute the node's logic
                    output_value, next_exec_node_id = node_def['exec_func'](node, context, execution_input)
                    
                    # If the node has multiple execution outputs (like Branch), the exec_func decides the next ID.
                    # If the node has a single output (like most functions), the exec_func should retrieve the target.

                except Exception as e:
                    FileUtils.log_error(f"Runtime error in node {node_type} ({next_exec_node_id}) for {context.owner_object.name}: {e}")
                    # Stop execution chain on error
                    break