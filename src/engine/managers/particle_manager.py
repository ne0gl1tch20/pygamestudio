# engine/managers/particle_manager.py
import pygame
import sys
import copy
import random
import math

# Attempt to import core dependencies, use minimal mocks if they fail
try:
    from engine.core.engine_state import EngineState
    from engine.managers.camera_manager import CameraObject
    from engine.utils.file_utils import FileUtils
    from engine.utils.vector2 import Vector2
    from engine.utils.color import Color
    from engine.utils.math_utils import MathUtils
except ImportError as e:
    print(f"[ParticleManager Import Error] {e}. Using Internal Mocks.")
    class EngineState: pass
    class FileUtils:
        @staticmethod
        def log_message(msg): print(f"[PM-INFO] {msg}")
    class Vector2:
        def __init__(self, x=0, y=0): self.x, self.y = x, y
        def __add__(self, other): return Vector2(self.x + other.x, self.y + other.y)
        def __mul__(self, scalar): return Vector2(self.x * scalar, self.y * scalar)
    class Color:
        @classmethod
        def red(cls): return Color(255, 0, 0)
        def to_rgb(self): return (self.r, self.g, self.b)
        def lerp(self, other, t): return (100, 100, 100) # Mock lerp
    class MathUtils:
        @staticmethod
        def clamp(val, min_v, max_v): return max(min_v, min(max_v, val))
        
    class CameraObject:
        def __init__(self): self.position = Vector2(0, 0); self.zoom = 1.0


# --- Particle Data Structures ---

class Particle:
    """Represents a single particle instance."""
    def __init__(self, start_pos: Vector2, template: dict):
        self.position = start_pos.copy()
        self.velocity = Vector2(*template.get('initial_velocity', [0, 0]))
        self.lifetime = template.get('lifetime', 1.0)
        self.time_alive = 0.0
        
        self.start_size = template.get('start_size', 5.0)
        self.end_size = template.get('end_size', 1.0)
        self.start_color = template.get('start_color', Color.red())
        self.end_color = template.get('end_color', Color.red())
        self.gravity_scale = template.get('gravity_scale', 1.0)
        self.texture = template.get('texture', None) # Asset name
        
        # Add random variations
        self.velocity.x += random.uniform(-template.get('rand_vel_x', 0), template.get('rand_vel_x', 0))
        self.velocity.y += random.uniform(-template.get('rand_vel_y', 0), template.get('rand_vel_y', 0))

class Emitter:
    """Represents a continuous or burst particle emitter."""
    def __init__(self, name: str, position: Vector2, template: dict):
        self.name = name
        self.position = position.copy()
        self.template = template
        self.particles = []
        self.is_active = template.get('is_looping', False)
        self.emission_rate = template.get('emission_rate', 10.0) # Particles per second
        self.emission_timer = 0.0
        self.max_particles = template.get('max_particles', 100)
        
        # Total duration for burst/non-looping
        self.duration = template.get('duration', 5.0)
        self.time_elapsed = 0.0
        
        # Cache the Color objects from the template data (assuming Color class is used)
        template['start_color'] = Color(*template.get('start_color', [255, 0, 0]))
        template['end_color'] = Color(*template.get('end_color', [255, 255, 0]))


# --- Particle Manager Core ---

class ParticleManager:
    """
    Manages all Emitter instances and updates/renders all active particles.
    """
    
    def __init__(self, state: EngineState):
        self.state = state
        self.state.particle_manager = self
        self.emitters = {} # {emitter_name: Emitter}
        self.global_gravity = Vector2(0, 980) # Follows 2D physics gravity for simplicity
        
        self._load_default_templates()
        FileUtils.log_message("ParticleManager initialized.")

    def _load_default_templates(self):
        """Creates basic particle templates for use in scripts/editor."""
        self.templates = {
            "Firework": {
                'lifetime': 1.5, 'initial_velocity': [0, -300], 'gravity_scale': 0.5,
                'start_size': 10.0, 'end_size': 0.5, 'start_color': [255, 200, 0], 'end_color': [255, 0, 0],
                'rand_vel_x': 100, 'rand_vel_y': 100, 'is_looping': False, 'max_particles': 500
            },
            "Steam": {
                'lifetime': 2.0, 'initial_velocity': [0, -50], 'gravity_scale': -0.1,
                'start_size': 2.0, 'end_size': 10.0, 'start_color': [200, 200, 200], 'end_color': [100, 100, 100],
                'rand_vel_x': 10, 'rand_vel_y': 10, 'is_looping': True, 'emission_rate': 20
            }
        }

    def create_emitter(self, name: str, position: Vector2, template_name: str, start_active: bool = False) -> Emitter:
        """Instantiates a new Emitter from a template."""
        if name in self.emitters:
            FileUtils.log_warning(f"Emitter '{name}' already exists. Skipping creation.")
            return self.emitters[name]
            
        template = self.templates.get(template_name)
        if not template:
            FileUtils.log_error(f"Particle template '{template_name}' not found.")
            return None
            
        emitter = Emitter(name, position, template)
        emitter.is_active = start_active
        self.emitters[name] = emitter
        return emitter

    def emit_burst(self, emitter_name: str, count: int):
        """Forces a single burst emission from an emitter."""
        emitter = self.emitters.get(emitter_name)
        if emitter:
            for _ in range(count):
                self._create_particle(emitter)
                
    def _create_particle(self, emitter: Emitter):
        """Creates and initializes a single particle from the emitter's template."""
        if len(emitter.particles) >= emitter.max_particles:
            # Simple max particle check: remove the oldest one
            emitter.particles.pop(0) 
            
        new_particle = Particle(emitter.position, emitter.template)
        emitter.particles.append(new_particle)

    # --- Main Loop Methods ---

    def update(self, dt: float):
        """Updates all active emitters and individual particles."""
        
        # Sync gravity with 2D physics system (if available)
        if self.state.physics_system_2d and self.state.current_scene and not self.state.current_scene.is_3d:
            self.global_gravity = self.state.physics_system_2d.gravity
        # NOTE: 3D particles would need Vector3 positions and a different gravity vector
            
        emitters_to_remove = []
        for name, emitter in self.emitters.items():
            
            # Emitter update
            if emitter.is_active:
                emitter.time_elapsed += dt
                
                # Continuous emission
                if emitter.template.get('is_looping', False):
                    emitter.emission_timer += dt
                    num_to_emit = int(emitter.emission_timer * emitter.emission_rate)
                    for _ in range(num_to_emit):
                        self._create_particle(emitter)
                    emitter.emission_timer -= num_to_emit / emitter.emission_rate
                
                # Stop if non-looping and duration elapsed
                if not emitter.template.get('is_looping', False) and emitter.time_elapsed > emitter.duration:
                    emitter.is_active = False # Stop emitting

            # Particle update
            particles_to_remove = []
            for particle in emitter.particles:
                particle.time_alive += dt
                
                if particle.time_alive >= particle.lifetime:
                    particles_to_remove.append(particle)
                    continue
                    
                # Apply physics (Simple Euler integration)
                # Apply gravity
                acceleration = self.global_gravity * particle.gravity_scale
                particle.velocity += acceleration * dt
                
                # Update position
                particle.position += particle.velocity * dt
                
            # Cleanup dead particles
            for p in particles_to_remove:
                emitter.particles.remove(p)
                
            # If emitter is inactive and has no particles left, mark for removal
            if not emitter.is_active and not emitter.particles:
                emitters_to_remove.append(name)
                
        # Cleanup inactive emitters
        for name in emitters_to_remove:
            del self.emitters[name]

    def render(self, surface: pygame.Surface, camera: CameraObject):
        """Renders all active particles onto the provided surface."""
        
        for emitter in self.emitters.values():
            for particle in emitter.particles:
                
                # --- Interpolate Properties ---
                t = MathUtils.clamp(particle.time_alive / particle.lifetime, 0.0, 1.0)
                
                # Color (linear interpolation)
                current_color_rgb = particle.start_color.lerp(particle.end_color, t).to_rgb()
                
                # Size (linear interpolation)
                current_size = MathUtils.lerp(particle.start_size, particle.end_size, t) * camera.zoom
                
                # --- World to Screen ---
                
                # Camera offset
                relative_pos = particle.position - camera.position
                
                # Apply zoom
                zoomed_pos_x = relative_pos.x * camera.zoom
                zoomed_pos_y = relative_pos.y * camera.zoom
                
                # Center on screen
                screen_x = int(zoomed_pos_x + surface.get_width() / 2)
                screen_y = int(zoomed_pos_y + surface.get_height() / 2)
                
                # --- Draw Particle ---
                
                # Only draw if on screen (simple bounds check)
                if 0 <= screen_x < surface.get_width() and 0 <= screen_y < surface.get_height():
                    
                    if particle.texture:
                        # Draw textured particle (Mock: Draw a scaled, rotated image)
                        # texture = self.state.asset_loader.get_asset('image', particle.texture)
                        # Draw a circle instead for simplicity
                        pygame.draw.circle(surface, current_color_rgb, (screen_x, screen_y), int(current_size))
                    else:
                        # Draw simple colored circle
                        pygame.draw.circle(surface, current_color_rgb, (screen_x, screen_y), int(current_size))