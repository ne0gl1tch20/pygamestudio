# engine/physics/physics2d.py
import pygame
import sys
import math

# Attempt to import core dependencies, use minimal mocks if they fail
try:
    from engine.core.engine_state import EngineState
    from engine.core.scene_manager import Scene
    from engine.utils.file_utils import FileUtils
    from engine.utils.vector2 import Vector2
    from engine.physics.rigidbody2d import Rigidbody2D
    from engine.physics.collision2d import Collision2D
except ImportError as e:
    print(f"[Physics2D Import Error] {e}. Using Internal Mocks.")
    class EngineState: pass
    class Scene: 
        def __init__(self): self.scene_properties = {"gravity": [0, 980]}
        def get_all_objects(self): return []
    class FileUtils:
        @staticmethod
        def log_message(msg): print(f"[P2D-INFO] {msg}")
        @staticmethod
        def log_error(msg): print(f"[P2D-ERROR] {msg}", file=sys.stderr)
    class Vector2:
        def __init__(self, x=0, y=0): self.x, self.y = x, y
        def __add__(self, other): return Vector2(self.x + other.x, self.y + other.y)
        def __mul__(self, scalar): return Vector2(self.x * scalar, self.y * scalar)
    class Rigidbody2D: pass
    class Collision2D:
        @staticmethod
        def is_colliding(obj_a, obj_b): return False
        @staticmethod
        def resolve_collision(obj_a, obj_b): return None


class Physics2D:
    """
    The main 2D physics simulation loop and integrator.
    Applies forces (like gravity), integrates motion, and manages collision detection/resolution.
    """
    
    def __init__(self, state: EngineState):
        self.state = state
        self.state.physics_system_2d = self
        self.collision_system = Collision2D()
        self.gravity = Vector2(0, 980.0) # Default gravity in pixels/sec^2 (y-down)
        self.rigidbody_map = {} # {SceneObject: Rigidbody2D instance}
        
        FileUtils.log_message("Physics2D system initialized.")
        
    def _ensure_rigidbody_instance(self, game_object):
        """
        Ensures a Rigidbody2D instance exists for the game object's component data.
        If the object has a 'Rigidbody2D' component, create or retrieve its state object.
        """
        if game_object not in self.rigidbody_map:
            rb_comp_data = game_object.get_component("Rigidbody2D")
            if rb_comp_data:
                # Initialize Rigidbody2D state object
                rb = Rigidbody2D.from_component(rb_comp_data, game_object.position)
                self.rigidbody_map[game_object] = rb
                
    def update(self, dt: float, scene: Scene):
        """
        The main physics update step, called once per frame.
        1. Apply forces/gravity.
        2. Integrate motion (update position/velocity).
        3. Detect and resolve collisions.
        """
        
        # 0. Update gravity from scene properties
        gravity_vec = scene.scene_properties.get("gravity", [0, 980])
        if isinstance(gravity_vec, (list, tuple)) and len(gravity_vec) >= 2:
            self.gravity = Vector2(*gravity_vec[:2])
            
        # 1. First Pass: Apply forces and semi-implicit Euler integration
        for obj in scene.get_all_objects():
            if obj.is_3d: continue # Skip 3D objects
            self._ensure_rigidbody_instance(obj)
            
            rb = self.rigidbody_map.get(obj)
            if rb:
                # Apply gravity (Force = mass * acceleration)
                gravity_force = self.gravity * rb.mass
                rb.add_force(gravity_force)
                
                # Apply damping (e.g., air resistance/friction)
                rb.velocity *= (1.0 - rb.linear_damping * dt)
                
                # Integrate linear motion (Semi-Implicit Euler)
                # v(t+dt) = v(t) + F/m * dt
                # x(t+dt) = x(t) + v(t+dt) * dt
                
                # Update velocity
                if rb.mass > 0:
                    acceleration = rb.force_accumulator * (1.0 / rb.mass)
                    rb.velocity += acceleration * dt
                
                # Update position (The actual game object's position)
                obj.position += rb.velocity * dt
                
                # Clear forces for next frame
                rb.force_accumulator = Vector2(0, 0)
                
        # 2. Second Pass: Collision Detection and Resolution
        
        # Collect all objects with a Rigidbody and Collider (or just Collider for static)
        dynamic_objects = [obj for obj in scene.get_all_objects() if obj.get_component("Rigidbody2D")]
        
        # Simple N^2 broad-phase check (inefficient, but simple for demo)
        for i in range(len(dynamic_objects)):
            obj_a = dynamic_objects[i]
            rb_a = self.rigidbody_map.get(obj_a)

            # Check dynamic vs dynamic
            for j in range(i + 1, len(dynamic_objects)):
                obj_b = dynamic_objects[j]
                rb_b = self.rigidbody_map.get(obj_b)
                
                self._check_and_resolve(obj_a, rb_a, obj_b, rb_b)

            # Check dynamic vs static objects (Mock static objects: objects with only a Collider)
            # NOTE: For this demo, we mock a static floor/wall
            
            # Mock Static Floor (Hardcoded at Y = 300)
            floor_y = 300.0
            
            # Simple boundary check against floor
            collider_a = obj_a.get_component("BoxCollider2D")
            if collider_a and obj_a.position.y > floor_y:
                # Assume a fixed height for the object (size property of collider/sprite)
                half_height = collider_a.get("height", 32) / 2.0 
                
                # Simple position correction (penetration resolution)
                penetration = (obj_a.position.y - half_height) - floor_y
                if penetration > 0:
                    # Move object up
                    obj_a.position.y -= penetration
                    
                    # Apply collision response (simple velocity reflection/stop)
                    if rb_a.velocity.y > 0:
                        rb_a.velocity.y *= -rb_a.restitution # Bounce
                        # Stop if velocity is near zero to prevent jittering
                        if abs(rb_a.velocity.y) < 5.0:
                            rb_a.velocity.y = 0
                    
                    # Store the collision event for game scripts
                    rb_a.is_grounded = True # Simple flag for game logic (e.g., jumping)
                    
            # Update the rigidbody's position back to the object (redundant here, but good practice)
            rb.position = obj.position.copy()

    def _check_and_resolve(self, obj_a, rb_a, obj_b, rb_b):
        """Checks for collision between two objects and resolves them if found."""
        
        # A full system would check for collider components (Box, Circle, Polygon)
        collider_a = obj_a.get_component("BoxCollider2D")
        collider_b = obj_b.get_component("BoxCollider2D")
        
        if collider_a and collider_b:
            # Simple AABB check (Mock)
            # In a full system, Collision2D.is_colliding would perform GJK/SAT.
            
            # Mock collision check: check if positions are very close (not accurate)
            distance = (obj_a.position - obj_b.position).magnitude
            min_distance = 50 # Mock value based on default sizes
            
            if distance < min_distance:
                # Collision detected (Mock)
                
                # Resolution: Separate the objects (Simple vector separation)
                mtv = (obj_a.position - obj_b.position).normalize() * (min_distance - distance)
                obj_a.position += mtv * 0.5
                obj_b.position -= mtv * 0.5
                
                # Resolution: Apply impulse (Simple velocity swap/damping mock)
                if rb_a and rb_b:
                    v_rel = rb_b.velocity - rb_a.velocity
                    impulse_scalar = -(1.0 + rb_a.restitution) * (v_rel.dot(mtv.normalize()))
                    
                    # Apply impulse (ignoring mass for simplicity)
                    rb_a.velocity -= mtv.normalize() * impulse_scalar
                    rb_b.velocity += mtv.normalize() * impulse_scalar

                # Store collision event
                # obj_a.colliding_with.append(obj_b)
                # obj_b.colliding_with.append(obj_a)
                
                # Log a message for the console
                if self.state.is_editor_mode:
                    FileUtils.log_message(f"Collision between {obj_a.name} and {obj_b.name}")