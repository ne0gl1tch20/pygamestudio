# engine/gui/panel_assets.py
import pygame
import sys
import os
import random

# Attempt to import core dependencies, use minimal mocks if they fail
try:
    from engine.core.engine_state import EngineState
    from engine.core.asset_loader import AssetLoader
    from ..engine.utils.file_utils import FileUtils
    from ..engine.gui.gui_widgets import Window, Label, Scrollbar, TextInput, Button
    from engine.utils.color import Color
except ImportError as e:
    print(f"[PanelAssets Import Error] {e}. Using Internal Mocks.")
    class EngineState:
        def get_theme_color(self, k): return (40, 40, 40)
        def get_asset_loader(self): return self # Mock asset loader
        def get_icon(self, name): 
            s = pygame.Surface((24, 24)); s.fill((255, 255, 255)); return s
        @property
        def current_project_path(self): return os.path.join(os.getcwd(), 'projects', 'example_project')
    class AssetLoader:
        ASSET_DIRS = {'image': 'images', 'sound': 'sounds', 'mesh': 'meshes', 'script': 'scripts', 'material': 'materials'}
        def get_asset_path(self, type, name, is_engine_asset=False): 
             return os.path.join(EngineState().current_project_path, 'assets', self.ASSET_DIRS[type], name)
    class FileUtils:
        @staticmethod
        def log_message(msg): print(f"[PA-INFO] {msg}")
    class Window:
        def __init__(self, rect, title, **kwargs): self.rect = rect
        def draw(self, surface, theme): pass
        def handle_event(self, event): return False
        def get_content_rect(self): return self.rect
    class Label:
        def __init__(self, rect, text, **kwargs): self.rect = rect
        def draw(self, surface, theme): pass
    class Scrollbar:
        def __init__(self, rect, max_scroll): self.rect = rect; self.max_scroll = max_scroll
        def handle_event(self, event): return False
        def draw(self, surface, theme): pass
        def get_scroll_offset(self): return 0
    class TextInput:
        def __init__(self, rect, initial_text, **kwargs): self.rect = rect
        def handle_event(self, event): return False
        def draw(self, surface, theme): pass
    class Button:
        def __init__(self, rect, text, icon=None, **kwargs): self.rect = rect; self.text = text
        def handle_event(self, event): return False
        def draw(self, surface, theme): pass
    class Color:
        @staticmethod
        def white(): return (255, 255, 255)
        @staticmethod
        def black(): return (0, 0, 0)
        @staticmethod
        def yellow(): return (255, 255, 0)
        @staticmethod
        def blue(): return (0, 0, 255)


class PanelAssets:
    """
    Displays the asset browser, allowing users to view, filter, and select 
    assets within the current project's asset directories.
    """
    
    ITEM_SIZE = 64 # Size of the asset preview/icon
    GRID_PADDING = 10
    
    ASSET_TYPES = ['all'] + list(AssetLoader.ASSET_DIRS.keys())
    
    def __init__(self, rect: pygame.Rect, state: EngineState, title: str):
        self.state = state
        self.title = title
        self.window = Window(rect, title, closable=False, movable=False, resizeable=False)
        self.rect = rect.copy()
        
        self.font = pygame.font.Font(None, 14)
        
        # State
        self.current_filter = 'all'
        self.current_dir = 'assets' # Relative path within project
        self.selected_asset = None
        
        # UI Elements
        self.search_input = TextInput(pygame.Rect(0, 0, 150, 24), "Search...")
        self.add_button = Button(pygame.Rect(0, 0, 30, 24), "➕", self.state.asset_loader.get_icon('plus'), action=self._add_asset_mock, show_text=False)
        self.filter_buttons = {} # {type: Button}
        self.scrollbar = None
        
        self._mock_asset_list = self._generate_mock_asset_list() # Mock file system
        self._update_ui_rects()

    def _generate_mock_asset_list(self):
        """Generates a stable mock list of assets for demonstration."""
        mock_list = []
        for type, subdir in AssetLoader.ASSET_DIRS.items():
            for i in range(random.randint(2, 6)):
                filename = f"{type}_asset_{i+1}.{subdir.split('/')[0][:3]}"
                mock_list.append({
                    "name": filename,
                    "type": type,
                    "path": os.path.join(self.state.current_project_path, self.current_dir, subdir, filename)
                })
        return mock_list

    def _update_ui_rects(self):
        """Updates the rects of internal UI elements based on window size."""
        self.window.rect = self.rect 
        self.content_rect = self.window.get_content_rect()
        
        # Calculate horizontal positions for top controls
        control_y = self.content_rect.y + self.PADDING
        x_offset = self.content_rect.x + self.PADDING
        
        # Search Input
        self.search_input.rect.topleft = (x_offset, control_y)
        x_offset += self.search_input.rect.width + self.PADDING
        
        # Add Button
        self.add_button.rect.topleft = (x_offset, control_y)
        x_offset += self.add_button.rect.width + self.PADDING
        
        # Filter Buttons
        for type_name in self.ASSET_TYPES:
            if type_name not in self.filter_buttons:
                # Create button with a size based on content
                btn_w = self.font.size(type_name.capitalize())[0] + 10
                self.filter_buttons[type_name] = Button(
                    pygame.Rect(x_offset, control_y, btn_w, 24),
                    type_name.capitalize(),
                    action=lambda t=type_name: self._set_filter(t)
                )
            self.filter_buttons[type_name].rect.topleft = (x_offset, control_y)
            x_offset += self.filter_buttons[type_name].rect.width + 5
            
        # Area below controls for asset grid
        self.grid_area_rect = self.content_rect.copy()
        self.grid_area_rect.y = control_y + 24 + self.PADDING
        self.grid_area_rect.height -= (self.grid_area_rect.y - self.content_rect.y) + self.PADDING
        
        # Scrollbar setup (max scroll calculated in draw loop)
        self.scrollbar = Scrollbar(pygame.Rect(self.grid_area_rect.right - 10, self.grid_area_rect.y, 10, self.grid_area_rect.height), 0)


    def _set_filter(self, filter_type: str):
        """Sets the active asset filter type."""
        self.current_filter = filter_type
        self.scrollbar.set_scroll_offset(0) # Reset scroll on filter change
        FileUtils.log_message(f"Asset filter set to: {filter_type}")
        
    def _add_asset_mock(self):
        """Mock: Triggers asset creation/import dialog."""
        FileUtils.log_message("Action: Open 'Add New Asset' Dialog (Mock).")
        # In a full system, this would open a sub-window for import/new creation
        pass


    def handle_event(self, event: pygame.event.Event) -> bool:
        """Handles user input for search, filters, and asset selection."""
        consumed = self.window.handle_event(event)
        
        if not self.window.rect.collidepoint(pygame.mouse.get_pos()):
            return consumed

        # Handle top controls
        if self.search_input.handle_event(event): consumed = True
        if self.add_button.handle_event(event): consumed = True
        for btn in self.filter_buttons.values():
            if btn.handle_event(event): consumed = True
            
        # Handle scrollbar
        if self.scrollbar.handle_event(event): consumed = True
        
        # Handle asset selection (inside the grid area)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.grid_area_rect.collidepoint(event.pos):
                return self._handle_asset_selection(event.pos)
                
        return consumed

    def _handle_asset_selection(self, mouse_pos: tuple[int, int]) -> bool:
        """Determines which asset item was clicked and updates selection."""
        scroll_offset = self.scrollbar.get_scroll_offset()
        
        # Grid layout calculation
        item_w = self.ITEM_SIZE + self.GRID_PADDING
        
        # Calculate max items per row
        items_per_row = max(1, (self.grid_area_rect.width - self.GRID_PADDING) // item_w)
        
        # Relative position within the grid area
        rel_x = mouse_pos[0] - self.grid_area_rect.x
        rel_y = mouse_pos[1] - self.grid_area_rect.y
        
        # Add scroll offset to Y
        logical_y = rel_y + scroll_offset
        
        # Determine row and column index
        col_index = rel_x // item_w
        row_index = logical_y // item_w

        clicked_index = row_index * items_per_row + col_index
        
        # Get the filtered list for accurate indexing
        filtered_assets = self._get_filtered_assets(self.search_input.get_text())
        
        if 0 <= clicked_index < len(filtered_assets):
            self.selected_asset = filtered_assets[clicked_index]
            FileUtils.log_message(f"Selected asset: {self.selected_asset['name']} ({self.selected_asset['type']})")
            return True
            
        self.selected_asset = None
        return True


    def _get_filtered_assets(self, search_text: str):
        """Filters the mock asset list based on current filter and search text."""
        filtered = []
        
        for asset in self._mock_asset_list:
            # Type filter
            if self.current_filter != 'all' and asset['type'] != self.current_filter:
                continue
            # Search filter
            if search_text != "Search..." and search_text.lower() not in asset['name'].lower():
                continue
                
            filtered.append(asset)
            
        return filtered

    def _get_asset_icon_surface(self, asset_type: str) -> pygame.Surface:
        """Returns a generic icon/placeholder for an asset type."""
        # This should eventually be delegated to AssetLoader with proper assets
        
        if asset_type == 'image':
            color = Color.blue().to_rgb()
            text = "IMG"
        elif asset_type == 'mesh':
            color = Color.yellow().to_rgb()
            text = "3D"
        elif asset_type == 'sound':
            color = (0, 255, 100)
            text = "AUD"
        elif asset_type == 'script':
            color = (255, 100, 0)
            text = "PY"
        else:
            color = Color.gray().to_rgb()
            text = "FILE"

        s = pygame.Surface((self.ITEM_SIZE, self.ITEM_SIZE))
        s.fill(color)
        
        text_surface = self.font.render(text, True, Color.black().to_rgb())
        s.blit(text_surface, text_surface.get_rect(center=(self.ITEM_SIZE // 2, self.ITEM_SIZE // 2)))
        
        return s


    def draw(self, surface: pygame.Surface, theme: str):
        """Draws the assets panel and its contents (controls and grid)."""
        
        # 1. Update Layout
        self.rect = self.window.rect 
        self._update_ui_rects()
        
        # 2. Draw Window Frame
        self.window.draw(surface, theme)
        
        # 3. Draw Controls
        self.search_input.draw(surface, theme)
        self.add_button.draw(surface, theme)
        for type_name, btn in self.filter_buttons.items():
            # Highlight active filter button
            btn.is_toggled = (type_name == self.current_filter)
            btn.draw(surface, theme)
            
        # 4. Asset Grid Drawing
        
        # Setup clipping for the scrollable grid area
        surface.set_clip(self.grid_area_rect)
        scroll_offset = self.scrollbar.get_scroll_offset()
        
        filtered_assets = self._get_filtered_assets(self.search_input.get_text())
        
        item_w = self.ITEM_SIZE + self.GRID_PADDING
        items_per_row = max(1, (self.grid_area_rect.width - self.GRID_PADDING) // item_w)
        
        current_x = self.grid_area_rect.x + self.GRID_PADDING
        current_y = self.grid_area_rect.y + self.GRID_PADDING - scroll_offset
        
        for i, asset in enumerate(filtered_assets):
            
            row = i // items_per_row
            col = i % items_per_row
            
            x = self.grid_area_rect.x + self.GRID_PADDING + col * item_w
            y = self.grid_area_rect.y + self.GRID_PADDING + row * item_w - scroll_offset
            
            # --- Draw Item Box ---
            item_rect = pygame.Rect(x, y, self.ITEM_SIZE, self.ITEM_SIZE)
            
            # Highlight if selected
            is_selected = self.selected_asset and self.selected_asset['name'] == asset['name']
            bg_color = self.state.get_theme_color('accent') if is_selected else self.state.get_theme_color('primary')
            
            pygame.draw.rect(surface, bg_color, item_rect)
            
            # Draw Item Icon/Preview
            icon = self._get_asset_icon_surface(asset['type'])
            surface.blit(icon, item_rect.topleft)
            
            # Draw Asset Name (Below the icon)
            name_text = self.font.render(asset['name'], True, self.state.get_theme_color('text'))
            surface.blit(name_text, (x, y + self.ITEM_SIZE + 2))
            
            # Update current_y for scrollbar height calculation
            current_y_end = y + self.ITEM_SIZE + self.ITEM_HEIGHT # Item + label height
            
        surface.set_clip(None)
        
        # 5. Update and Draw Scrollbar
        
        # Calculate total content height
        total_rows = (len(filtered_assets) + items_per_row - 1) // items_per_row
        total_height = total_rows * item_w + self.GRID_PADDING
        
        self.scrollbar.max_scroll = max(0, total_height - self.grid_area_rect.height)
        self.scrollbar.draw(surface, theme)