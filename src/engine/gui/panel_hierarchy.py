# engine/gui/panel_hierarchy.py
import pygame
import sys
import copy

# Attempt to import core dependencies, use minimal mocks if they fail
try:
    from ..engine.core.engine_state import EngineState
    from ..engine.core.scene_manager import Scene, SceneObject
    from ..engine.utils.file_utils import FileUtils
    from ..engine.gui.gui_widgets import Window, Button, Label, Scrollbar
    from ..engine.utils.color import Color
except ImportError as e:
    print(f"[PanelHierarchy Import Error] {e}. Using Internal Mocks.")
    class EngineState:
        def get_theme_color(self, k): return (40, 40, 40)
        def get_object_by_uid(self, uid): return None
        selected_object_uid = None
        def __init__(self): self.current_scene = self
        def get_icon(self, name): 
            s = pygame.Surface((24, 24)); s.fill((255, 255, 255)); return s
    class Scene:
        def get_all_objects(self): return []
    class SceneObject:
        def __init__(self, uid, name): self.uid = uid; self.name = name
    class FileUtils:
        @staticmethod
        def log_message(msg): print(f"[PH-INFO] {msg}")
    class Window:
        def __init__(self, rect, title, **kwargs): self.rect = rect
        def draw(self, surface, theme): pass
        def handle_event(self, event): return False
        def get_content_rect(self): return self.rect
    class Button:
        def __init__(self, rect, text, icon=None, **kwargs): self.rect = rect
        def handle_event(self, event): return False
        def draw(self, surface, theme): pass
    class Label:
        def __init__(self, rect, text, **kwargs): self.rect = rect
        def draw(self, surface, theme): pass
    class Scrollbar:
        def __init__(self, rect, max_scroll): self.rect = rect; self.max_scroll = max_scroll
        def handle_event(self, event): return False
        def draw(self, surface, theme): pass
        def get_scroll_offset(self): return 0
    class Color:
        @staticmethod
        def white(): return (255, 255, 255)
        @staticmethod
        def black(): return (0, 0, 0)
        @staticmethod
        def yellow(): return (255, 255, 0)


class PanelHierarchy:
    """
    Displays the hierarchy (tree structure) of all SceneObjects in the current scene.
    Allows for selection, renaming, and basic object manipulation (add/delete).
    """
    
    ITEM_HEIGHT = 24
    
    def __init__(self, rect: pygame.Rect, state: EngineState, title: str):
        self.state = state
        self.title = title
        self.window = Window(rect, title, closable=False, movable=False, resizeable=False)
        
        self.font = pygame.font.Font(None, 18)
        
        # UI Elements
        self.scrollbar = None
        self.content_rect = self.window.get_content_rect() # Initial value
        self.add_button = Button(pygame.Rect(0, 0, 24, 24), "+", self.state.asset_loader.get_icon('plus'), action=self._add_object)
        self.delete_button = Button(pygame.Rect(0, 0, 24, 24), "🗑️", self.state.asset_loader.get_icon('delete'), action=self._delete_object)
        
        self._update_ui_rects()
        
    def _update_ui_rects(self):
        """Updates the rects of internal UI elements based on window size."""
        self.window.rect = self.rect # The manager sets the window's rect directly
        self.content_rect = self.window.get_content_rect()
        
        # Position control buttons at the top right of the content area
        btn_y = self.content_rect.y + 2
        btn_del_x = self.content_rect.right - 2 - 24
        btn_add_x = btn_del_x - 24 - 2
        
        self.delete_button.rect.topleft = (btn_del_x, btn_y)
        self.add_button.rect.topleft = (btn_add_x, btn_y)
        
        # Scrollbar setup
        max_scroll = max(0, len(self.state.current_scene.get_all_objects()) * self.ITEM_HEIGHT - self.content_rect.height + 30)
        scroll_rect = pygame.Rect(self.content_rect.right - 10, self.content_rect.y, 10, self.content_rect.height)
        self.scrollbar = Scrollbar(scroll_rect, max_scroll)


    def handle_event(self, event: pygame.event.Event) -> bool:
        """Handles user input for selection and manipulation."""
        consumed = self.window.handle_event(event)
        
        if not self.window.rect.collidepoint(pygame.mouse.get_pos()):
            return consumed # Ignore clicks outside panel

        # Pass event to scrollbar
        if self.scrollbar.handle_event(event):
            return True

        # Pass event to top buttons
        if self.add_button.handle_event(event) or self.delete_button.handle_event(event):
            return True
            
        # Handle object selection
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = event.pos
            content_area = self.content_rect.copy()
            # Reduce content area to account for buttons at the top
            content_area.y += self.ITEM_HEIGHT 
            content_area.height -= self.ITEM_HEIGHT
            
            if content_area.collidepoint(mouse_pos):
                return self._handle_selection_click(mouse_pos)
                
        return consumed

    def _handle_selection_click(self, mouse_pos: tuple[int, int]) -> bool:
        """Determines which object was clicked and updates selection."""
        scroll_offset = self.scrollbar.get_scroll_offset()
        
        # Calculate index of clicked item
        # Subtract the offset of the first item below the buttons
        relative_y = mouse_pos[1] - self.content_rect.y - self.ITEM_HEIGHT 
        
        # Add scroll offset to find the logical y position
        logical_y = relative_y + scroll_offset
        
        # Calculate index
        clicked_index = int(logical_y / self.ITEM_HEIGHT)
        
        scene_objects = self.state.current_scene.get_all_objects()
        
        if 0 <= clicked_index < len(scene_objects):
            selected_obj = scene_objects[clicked_index]
            self.state.selected_object_uid = selected_obj.uid
            FileUtils.log_message(f"Selected object: {selected_obj.name} ({selected_obj.uid})")
            return True
        
        # Clicked in the hierarchy area but not on an item
        self.state.selected_object_uid = None
        return True

    def _add_object(self):
        """Action: Adds a new SceneObject to the scene."""
        if self.state.current_scene:
            is_3d = self.state.current_scene.is_3d
            
            # Create minimal data for a new object
            new_uid = str(hash(self.state.current_scene.name + str(len(self.state.current_scene.get_all_objects())) + str(pygame.time.get_ticks())))
            new_name = f"NewObject_{len(self.state.current_scene.get_all_objects())}"
            
            # Use the core SceneObject definition
            from engine.core.scene_manager import SceneObject, Vector2, Vector3
            
            initial_pos = [0, 0, 0] if is_3d else [0, 0]
            initial_scale = [1, 1, 1] if is_3d else [1, 1]
            
            new_obj_data = {
                "uid": new_uid, 
                "name": new_name, 
                "position": initial_pos,
                "scale": initial_scale,
                "components": [] # Start empty
            }
            new_obj = SceneObject(new_obj_data, is_3d)
            self.state.current_scene.add_object(new_obj)
            self.state.selected_object_uid = new_uid # Select the new object
            
            self._update_ui_rects() # Recalculate scrollbar max
            FileUtils.log_message(f"Added new object: {new_name}")

    def _delete_object(self):
        """Action: Deletes the currently selected object."""
        if self.state.selected_object_uid and self.state.current_scene:
            name = self.state.get_object_by_uid(self.state.selected_object_uid).name
            if self.state.current_scene.remove_object(self.state.selected_object_uid):
                FileUtils.log_message(f"Deleted object: {name}")
                self.state.selected_object_uid = None
                self._update_ui_rects() # Recalculate scrollbar max

    def draw(self, surface: pygame.Surface, theme: str):
        """Draws the hierarchy panel and its contents."""
        
        # 1. Update Layout (Handles window resizing implicitly)
        self.rect = self.window.rect # Ensure the panel's rect is set by the manager
        self._update_ui_rects()
        
        # 2. Draw Window Frame
        self.window.draw(surface, theme)
        content_rect = self.content_rect
        
        # 3. Draw Control Buttons
        self.add_button.draw(surface, theme)
        self.delete_button.draw(surface, theme)
        
        # 4. Draw Scrollbar
        self.scrollbar.draw(surface, theme)
        scroll_offset = self.scrollbar.get_scroll_offset()
        
        # 5. Draw Object List
        scene_objects = self.state.current_scene.get_all_objects() if self.state.current_scene else []
        
        # Clip rendering to the content area (below the buttons)
        clip_rect = content_rect.copy()
        clip_rect.y += self.ITEM_HEIGHT # Start drawing below buttons
        clip_rect.height -= self.ITEM_HEIGHT
        
        surface.set_clip(clip_rect)
        
        item_y = content_rect.y + self.ITEM_HEIGHT - scroll_offset
        
        for obj in scene_objects:
            item_rect = pygame.Rect(content_rect.x + 2, item_y, content_rect.width - 4 - self.scrollbar.rect.width, self.ITEM_HEIGHT)
            
            # Background color (Highlight if selected)
            bg_color = self.state.get_theme_color('secondary')
            text_color = self.state.get_theme_color('text')
            
            if obj.uid == self.state.selected_object_uid:
                bg_color = self.state.get_theme_color('accent')
                text_color = Color.white().to_rgb() # White text on accent background
            
            pygame.draw.rect(surface, bg_color, item_rect)
            
            # Draw Object Name
            text_surface = self.font.render(obj.name, True, text_color)
            surface.blit(text_surface, (item_rect.x + 5, item_rect.y + (self.ITEM_HEIGHT - self.font.get_height()) // 2))
            
            item_y += self.ITEM_HEIGHT
            
            # Stop rendering if beyond the visible area
            if item_y > content_rect.bottom:
                break
                
        # Clear clipping
        surface.set_clip(None)