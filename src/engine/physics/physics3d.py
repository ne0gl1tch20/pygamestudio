# engine/physics/physics3d.py
import pygame
import sys
import math

# Attempt to import core dependencies, use minimal mocks if they fail
try:
    from engine.core.engine_state import EngineState
    from engine.core.scene_manager import Scene
    from engine.utils.file_utils import FileUtils
    from engine.utils.vector3 import Vector3
    from engine.physics.rigidbody3d import Rigidbody3D
    from engine.physics.collision3d import Collision3D
except ImportError as e:
    print(f"[Physics3D Import Error] {e}. Using Internal Mocks.")
    class EngineState: pass
    class Scene: 
        def __init__(self): self.scene_properties = {"gravity": [0, -9.8, 0]}
        def get_all_objects(self): return []
    class FileUtils:
        @staticmethod
        def log_message(msg): print(f"[P3D-INFO] {msg}")
        @staticmethod
        def log_error(msg): print(f"[P3D-ERROR] {msg}", file=sys.stderr)
    class Vector3:
        def __init__(self, x=0, y=0, z=0): self.x, self.y, self.z = x, y, z
        def __add__(self, other): return Vector3(self.x + other.x, self.y + other.y, self.z + other.z)
        def __mul__(self, scalar): return Vector3(self.x * scalar, self.y * scalar, self.z * scalar)
    class Rigidbody3D: pass
    class Collision3D:
        @staticmethod
        def check_collision(obj_a, obj_b): return None


class Physics3D:
    """
    The main 3D physics simulation loop and integrator.
    Applies forces (like gravity), integrates motion, and manages collision detection/resolution.
    Uses a minimal implementation due to lack of standard 3D physics library.
    """
    
    def __init__(self, state: EngineState):
        self.state = state
        self.state.physics_system_3d = self
        self.gravity = Vector3(0, -9.8, 0) # Default gravity in meters/sec^2 (y-up)
        self.rigidbody_map = {} # {SceneObject: Rigidbody3D instance}
        
        # A full system would use an actual 3D collision engine like Bullet or ODE wrapper
        # We use a mock system.
        self.collision_system = Collision3D() 
        
        FileUtils.log_message("Physics3D system initialized.")
        
    def _ensure_rigidbody_instance(self, game_object):
        """
        Ensures a Rigidbody3D instance exists for the game object's component data.
        """
        if game_object not in self.rigidbody_map:
            rb_comp_data = game_object.get_component("Rigidbody3D")
            if rb_comp_data:
                # Initialize Rigidbody3D state object
                rb = Rigidbody3D.from_component(rb_comp_data, game_object.position, game_object.rotation)
                self.rigidbody_map[game_object] = rb
                
    def update(self, dt: float, scene: Scene):
        """
        The main physics update step, called once per frame.
        1. Apply forces/gravity and torques.
        2. Integrate motion (update position/velocity) and rotation/angular velocity.
        3. Detect and resolve collisions.
        """
        if not scene.is_3d: 
            return # Skip if scene is 2D
        
        # 0. Update gravity from scene properties
        gravity_vec = scene.scene_properties.get("gravity", [0, -9.8, 0])
        if isinstance(gravity_vec, (list, tuple)) and len(gravity_vec) >= 3:
            self.gravity = Vector3(*gravity_vec)
            
        # 1. First Pass: Integration (Verlet/Euler)
        for obj in scene.get_all_objects():
            if not obj.is_3d: continue
            self._ensure_rigidbody_instance(obj)
            
            rb = self.rigidbody_map.get(obj)
            if rb and rb.is_dynamic:
                
                # --- Linear Motion ---
                
                # Apply gravity
                gravity_force = self.gravity * rb.mass
                rb.add_force(gravity_force)
                
                # Apply linear damping
                rb.velocity *= (1.0 - rb.linear_damping * dt)

                # Integrate velocity (Semi-Implicit Euler)
                if rb.mass > 0:
                    acceleration = rb.force_accumulator * (1.0 / rb.mass)
                    rb.velocity += acceleration * dt
                
                # Update position (The actual game object's position)
                obj.position += rb.velocity * dt
                
                # --- Rotational Motion (Simplified Mock) ---
                
                # Apply angular damping
                rb.angular_velocity *= (1.0 - rb.angular_damping * dt)
                
                # Integrate angular velocity (Simple Euler)
                # rb.angular_velocity += rb.torque_accumulator * dt # Requires Inverse Tensor calculation
                
                # Update rotation (Euler angle accumulation - generally unstable)
                obj.rotation += rb.angular_velocity * dt 
                
                # Clear accumulators for next frame
                rb.force_accumulator = Vector3(0, 0, 0)
                rb.torque_accumulator = Vector3(0, 0, 0)
                
        # 2. Second Pass: Collision Detection and Resolution (Mock)
        
        dynamic_objects = [obj for obj in scene.get_all_objects() if obj.is_3d and obj.get_component("Rigidbody3D")]
        
        # N^2 collision check (Mock)
        for i in range(len(dynamic_objects)):
            obj_a = dynamic_objects[i]
            rb_a = self.rigidbody_map.get(obj_a)

            # Check dynamic vs dynamic
            for j in range(i + 1, len(dynamic_objects)):
                obj_b = dynamic_objects[j]
                rb_b = self.rigidbody_map.get(obj_b)
                
                self._check_and_resolve(obj_a, rb_a, obj_b, rb_b)

            # Check dynamic vs static plane (Mock Static Floor at Y=0)
            if obj_a.position.y < 0 and rb_a.velocity.y < 0:
                self._resolve_floor_collision(obj_a, rb_a)
                
        # 3. Final step: Update rigidbodies' internal positions
        for obj in dynamic_objects:
            rb = self.rigidbody_map.get(obj)
            if rb:
                rb.position = obj.position.copy()
                rb.rotation = obj.rotation.copy()


    def _check_and_resolve(self, obj_a, rb_a, obj_b, rb_b):
        """Checks for collision between two 3D objects and resolves them if found (Mock)."""
        
        # Check for collider components (BoxCollider3D assumed)
        collider_a = obj_a.get_component("BoxCollider3D")
        collider_b = obj_b.get_component("BoxCollider3D")
        
        if collider_a and collider_b:
            # Full implementation would call a sophisticated collision check (GJK/SAT in 3D)
            # contact_info = self.collision_system.check_collision(obj_a, obj_b)
            
            # Simple Sphere-Sphere distance check mock
            distance = (obj_a.position - obj_b.position).magnitude
            min_distance = 1.0 # Mock radius sum
            
            if distance < min_distance:
                # Collision detected (Mock)
                
                # Resolution: Separate objects (MTV mock)
                mtv = (obj_a.position - obj_b.position).normalize() * (min_distance - distance)
                obj_a.position += mtv * 0.5
                obj_b.position -= mtv * 0.5
                
                # Resolution: Apply impulse (Simple velocity swap/damping mock)
                if rb_a and rb_b:
                    v_rel = rb_b.velocity - rb_a.velocity
                    normal = mtv.normalize()
                    
                    # Simple impulse calculation
                    j = -(1.0 + rb_a.restitution) * v_rel.dot(normal)
                    
                    # Apply impulse
                    rb_a.velocity -= normal * j * rb_a.inv_mass
                    rb_b.velocity += normal * j * rb_b.inv_mass

                FileUtils.log_message(f"3D Collision between {obj_a.name} and {obj_b.name}")


    def _resolve_floor_collision(self, obj, rb):
        """Resolves collision with a mock static floor at Y=0."""
        
        # Simple position correction
        obj.position.y = 0.0 # Snap to zero
        
        # Simple velocity reflection/stop
        if rb.velocity.y < 0:
            rb.velocity.y *= -rb.restitution # Bounce up
            # Stop if velocity is near zero
            if abs(rb.velocity.y) < 0.1:
                rb.velocity.y = 0
                
        rb.is_grounded = True # Simple flag for game logic