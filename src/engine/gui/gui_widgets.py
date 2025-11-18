# engine/gui/gui_widgets.py
import pygame
import sys
from typing import Callable, Any, List

# --- MOCK DEPENDENCIES (for standalone testing) ---
try:
    from ..engine.utils.color import Color
    from ..engine.utils.math_utils import MathUtils
    from ..engine.utils.file_utils import FileUtils
except ImportError:
    class Color:
        def __init__(self, r, g, b, a=255): self.r, self.g, self.b, self.a = r, g, b, a
        def to_rgb(self): return (self.r, self.g, self.b)
        def to_rgba(self): return (self.r, self.g, self.b, self.a)
        @classmethod
        def black(cls): return cls(0, 0, 0)
        @classmethod
        def white(cls): return cls(255, 255, 255)
        @classmethod
        def red(cls): return cls(255, 0, 0)
        @classmethod
        def gray(cls): return cls(128, 128, 128)
    class MathUtils:
        @staticmethod
        def clamp(val, min_v, max_v): return max(min_v, min(max_v, val))
    class FileUtils:
        @staticmethod
        def log_message(msg): print(f"[GUI-INFO] {msg}")

# Initialize Pygame Font
try:
    pygame.font.init()
except pygame.error:
    pass # Already initialized in main.py


# --- Base Theme/Color Getter ---
def _get_theme_colors(theme: str):
    """Returns a dictionary of colors for the given theme."""
    if theme == 'dark':
        return {
            "background": Color(30, 30, 30).to_rgb(),
            "primary": Color(50, 50, 50).to_rgb(),        # Panel background
            "secondary": Color(70, 70, 70).to_rgb(),      # Button/Input background
            "hover": Color(90, 90, 90).to_rgb(),          # Hover state
            "accent": Color(50, 150, 255).to_rgb(),       # Highlight / Accent Blue
            "text": Color(200, 200, 200).to_rgb(),        # Standard text
            "text_disabled": Color(120, 120, 120).to_rgb(),
            "border": Color(35, 35, 35).to_rgb(),         # Thin border
            "accent_border": Color(255, 255, 0).to_rgb(), # Selection/Focus Yellow
        }
    else: # light theme
        return {
            "background": Color(200, 200, 200).to_rgb(),
            "primary": Color(230, 230, 230).to_rgb(),
            "secondary": Color(210, 210, 210).to_rgb(),
            "hover": Color(190, 190, 190).to_rgb(),
            "accent": Color(0, 100, 200).to_rgb(),
            "text": Color(50, 50, 50).to_rgb(),
            "text_disabled": Color(150, 150, 150).to_rgb(),
            "border": Color(220, 220, 220).to_rgb(),
            "accent_border": Color(255, 100, 0).to_rgb(),
        }

# --- Base Widget Class ---
class Widget:
    """Base class for all GUI elements."""
    def __init__(self, rect: pygame.Rect):
        self.rect = rect
        self.is_hovered = False
        self.is_focused = False
        self.is_disabled = False

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Handles Pygame events; returns True if the event was consumed."""
        mouse_pos = pygame.mouse.get_pos()
        self.is_hovered = self.rect.collidepoint(mouse_pos)
        
        # Simple click sets focus
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.is_hovered and not self.is_disabled:
            self.is_focused = True
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and not self.is_hovered:
            self.is_focused = False

        return False

    def draw(self, surface: pygame.Surface, theme: str):
        """Draws the widget onto the surface."""
        raise NotImplementedError

# --- 1. Window Widget (Container) ---

class Window(Widget):
    """A floating or docked panel container."""
    TITLE_BAR_HEIGHT = 20

    def __init__(self, rect: pygame.Rect, title: str, closable: bool = True, movable: bool = True, resizeable: bool = False):
        super().__init__(rect)
        self.title = title
        self.is_open_flag = True
        self.closable = closable
        self.movable = movable
        self.resizeable = resizeable
        
        self._is_dragging = False
        self._drag_offset = (0, 0)
        
        # Close Button (Mock)
        self.close_button_rect = pygame.Rect(self.rect.right - 18, self.rect.y + 2, 16, 16)

    def open(self):
        self.is_open_flag = True
    
    def close(self):
        self.is_open_flag = False
        
    def is_open(self):
        return self.is_open_flag
        
    def get_content_rect(self):
        """Returns the area inside the window for content rendering."""
        return pygame.Rect(
            self.rect.x + 1,
            self.rect.y + self.TITLE_BAR_HEIGHT + 1,
            self.rect.width - 2,
            self.rect.height - self.TITLE_BAR_HEIGHT - 2
        )

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.is_open_flag:
            return False
            
        mouse_pos = pygame.mouse.get_pos()
        title_bar_rect = pygame.Rect(self.rect.x, self.rect.y, self.rect.width, self.TITLE_BAR_HEIGHT)

        # 1. Close Button
        self.close_button_rect = pygame.Rect(self.rect.right - 18, self.rect.y + 2, 16, 16)
        if self.closable:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.close_button_rect.collidepoint(mouse_pos):
                self.close()
                return True
        
        # 2. Dragging/Moving
        if self.movable:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and title_bar_rect.collidepoint(mouse_pos):
                self._is_dragging = True
                self._drag_offset = (mouse_pos[0] - self.rect.x, mouse_pos[1] - self.rect.y)
                return True
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if self._is_dragging:
                    self._is_dragging = False
                    return True
            elif event.type == pygame.MOUSEMOTION and self._is_dragging:
                new_x = mouse_pos[0] - self._drag_offset[0]
                new_y = mouse_pos[1] - self._drag_offset[1]
                self.rect.topleft = (new_x, new_y)
                # Update close button rect
                self.close_button_rect = pygame.Rect(self.rect.right - 18, self.rect.y + 2, 16, 16)
                return True
                
        return False

    def draw(self, surface: pygame.Surface, theme: str):
        if not self.is_open_flag: return
        
        colors = _get_theme_colors(theme)
        
        # Draw main background
        pygame.draw.rect(surface, colors['primary'], self.rect, 0, 3)
        pygame.draw.rect(surface, colors['border'], self.rect, 1, 3)
        
        # Draw Title Bar
        title_bar_rect = pygame.Rect(self.rect.x + 1, self.rect.y + 1, self.rect.width - 2, self.TITLE_BAR_HEIGHT - 1)
        pygame.draw.rect(surface, colors['secondary'], title_bar_rect, 0, 3)
        
        # Draw Title Text
        font = pygame.font.Font(None, 16)
        text_surface = font.render(self.title, True, colors['text'])
        surface.blit(text_surface, (self.rect.x + 5, self.rect.y + 3))
        
        # Draw Close Button (X)
        if self.closable:
            pygame.draw.rect(surface, colors['text'], self.close_button_rect)
            pygame.draw.line(surface, colors['primary'], (self.close_button_rect.x + 3, self.close_button_rect.y + 3), (self.close_button_rect.right - 3, self.close_button_rect.bottom - 3), 2)
            pygame.draw.line(surface, colors['primary'], (self.close_button_rect.right - 3, self.close_button_rect.y + 3), (self.close_button_rect.x + 3, self.close_button_rect.bottom - 3), 2)


# --- 2. Button Widget ---

class Button(Widget):
    def __init__(self, rect: pygame.Rect, text: str, icon: pygame.Surface = None, action: Callable = None, show_text: bool = True, toggle_icon: pygame.Surface = None, is_toggled: bool = False):

        super().__init__(rect)
        self.text = text
        self.icon = icon
        self.action = action
        self.show_text = show_text
        self.is_toggled = is_toggled
        self.toggle_icon = toggle_icon

    def handle_event(self, event: pygame.event.Event) -> bool:
        if self.is_disabled: return False
        
        consumed = super().handle_event(event)
        
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.is_hovered:
            if self.action:
                self.action()
                return True
                
        return consumed

    def draw(self, surface: pygame.Surface, theme: str):
        colors = _get_theme_colors(theme)
        
        # Determine current color based on state
        color = colors['secondary']
        if self.is_disabled:
            color = colors['text_disabled']
        elif self.is_toggled:
            color = colors['accent']
        elif self.is_hovered:
            color = colors['hover']
            
        # Draw background
        pygame.draw.rect(surface, color, self.rect, 0, 3)
        pygame.draw.rect(surface, colors['border'], self.rect, 1, 3)
        
        # Draw Icon and Text
        content_x = self.rect.x + 5
        
        if self.is_toggled and self.toggle_icon:
             icon_to_draw = self.toggle_icon
        else:
             icon_to_draw = self.icon
        
        if icon_to_draw:
            icon_rect = icon_to_draw.get_rect(midleft=(content_x, self.rect.centery))
            surface.blit(icon_to_draw, icon_rect)
            content_x += icon_rect.width + 5
            
        if self.show_text:
            font = pygame.font.Font(None, 18)
            text_color = colors['text'] if not self.is_disabled else colors['primary']
            text_surface = font.render(self.text, True, text_color)
            text_rect = text_surface.get_rect(midleft=(content_x, self.rect.centery))
            surface.blit(text_surface, text_rect)


# --- 3. Label Widget ---

class Label(Widget):
    def __init__(self, rect: pygame.Rect, text: str, font: pygame.font.Font = None, text_color: tuple = None, alignment: str = "center"):
        super().__init__(rect)
        self.text = text
        self.font = font if font else pygame.font.Font(None, 18)
        self.text_color = text_color
        self.alignment = alignment

    def draw(self, surface: pygame.Surface, theme: str):
        colors = _get_theme_colors(theme)
        text_color = self.text_color if self.text_color else colors['text']
        
        text_surface = self.font.render(self.text, True, text_color)
        text_rect = text_surface.get_rect()
        
        # Apply alignment
        if self.alignment == "center":
            text_rect.center = self.rect.center
        elif self.alignment == "left":
            text_rect.midleft = (self.rect.x + 5, self.rect.centery)
        elif self.alignment == "right":
            text_rect.midright = (self.rect.right - 5, self.rect.centery)

        surface.blit(text_surface, text_rect)


# --- 4. TextInput Widget ---

class TextInput(Widget):
    def __init__(self, rect: pygame.Rect, initial_text: str = "", placeholder: str = "", is_numeric: bool = False, read_only: bool = False):
        super().__init__(rect)
        self.text = initial_text
        self.placeholder = placeholder
        self.is_numeric = is_numeric
        self.read_only = read_only
        self.cursor_pos = len(initial_text)
        self.font = pygame.font.Font(None, 18)
        self.clock = pygame.time.Clock() # For cursor blink
        self._last_cursor_toggle = 0
        self._show_cursor = True

    def handle_event(self, event: pygame.event.Event) -> bool:
        if self.read_only: 
            # Still check for hover/focus but consume no keyboard events
            return super().handle_event(event)

        consumed = super().handle_event(event)
        
        if self.is_focused:
            if event.type == pygame.KEYDOWN:
                self._show_cursor = True
                self._last_cursor_toggle = pygame.time.get_ticks()
                
                if event.key == pygame.K_BACKSPACE:
                    if self.cursor_pos > 0:
                        self.text = self.text[:self.cursor_pos - 1] + self.text[self.cursor_pos:]
                        self.cursor_pos = max(0, self.cursor_pos - 1)
                elif event.key == pygame.K_DELETE:
                    self.text = self.text[:self.cursor_pos] + self.text[self.cursor_pos + 1:]
                elif event.key == pygame.K_LEFT:
                    self.cursor_pos = max(0, self.cursor_pos - 1)
                elif event.key == pygame.K_RIGHT:
                    self.cursor_pos = min(len(self.text), self.cursor_pos + 1)
                elif event.key == pygame.K_HOME:
                    self.cursor_pos = 0
                elif event.key == pygame.K_END:
                    self.cursor_pos = len(self.text)
                elif event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER:
                    self.is_focused = False # Lose focus on Enter
                    return True
                elif event.unicode:
                    if self.is_numeric and not event.unicode.isdigit() and event.unicode not in ('-', '.'):
                        pass # Ignore non-numeric input
                    else:
                        # Insert character at cursor position
                        self.text = self.text[:self.cursor_pos] + event.unicode + self.text[self.cursor_pos:]
                        self.cursor_pos += 1
                consumed = True
            
            # Click inside box to move cursor
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.is_hovered:
                # Approximate cursor position based on mouse click (simplified)
                approx_x = event.pos[0] - self.rect.x - 5
                current_x = 0
                for i, char in enumerate(self.text):
                    char_w = self.font.size(char)[0]
                    if current_x + char_w / 2 > approx_x:
                        self.cursor_pos = i
                        break
                    current_x += char_w
                else:
                    self.cursor_pos = len(self.text)
                consumed = True

        return consumed

    def draw(self, surface: pygame.Surface, theme: str):
        colors = _get_theme_colors(theme)
        
        # Draw background
        bg_color = colors['secondary'] if not self.read_only else colors['primary']
        pygame.draw.rect(surface, bg_color, self.rect, 0, 3)
        
        # Draw border
        border_color = colors['accent_border'] if self.is_focused else colors['border']
        pygame.draw.rect(surface, border_color, self.rect, 1, 3)
        
        # Text/Placeholder
        display_text = self.text
        text_color = colors['text']
        
        if not display_text and not self.is_focused and self.placeholder:
            display_text = self.placeholder
            text_color = colors['text_disabled']
            
        text_surface = self.font.render(display_text, True, text_color)
        text_rect = text_surface.get_rect(midleft=(self.rect.x + 5, self.rect.centery))
        
        # Clipping to prevent text overflow
        clip_rect = self.rect.inflate(-2, -2)
        surface.set_clip(clip_rect)
        
        surface.blit(text_surface, text_rect)
        
        surface.set_clip(None) # Clear clip
        
        # Draw Cursor
        if self.is_focused and not self.read_only:
            # Blink logic
            if pygame.time.get_ticks() - self._last_cursor_toggle > 500:
                self._show_cursor = not self._show_cursor
                self._last_cursor_toggle = pygame.time.get_ticks()
            
            if self._show_cursor:
                # Calculate cursor x-position
                text_before_cursor = self.text[:self.cursor_pos]
                cursor_x = self.rect.x + 5 + self.font.size(text_before_cursor)[0]
                
                cursor_rect = pygame.Rect(cursor_x, self.rect.y + 3, 2, self.rect.height - 6)
                pygame.draw.rect(surface, colors['text'], cursor_rect)

    def get_text(self) -> str:
        return self.text
        
    def set_text(self, text: str):
        self.text = text
        self.cursor_pos = len(text)


# --- 5. Checkbox Widget ---

class Checkbox(Widget):
    def __init__(self, rect: pygame.Rect, is_checked: bool = False, label: str = None, disabled: bool = False):
        super().__init__(rect)
        self._is_checked = is_checked
        self.label = label
        self.is_disabled = disabled
        self.box_size = min(self.rect.height - 4, 16)
        
    def handle_event(self, event: pygame.event.Event) -> bool:
        if self.is_disabled: return False
        
        consumed = super().handle_event(event)
        
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.is_hovered:
            self._is_checked = not self._is_checked
            return True
            
        return consumed

    def draw(self, surface: pygame.Surface, theme: str):
        colors = _get_theme_colors(theme)
        
        # Box Rect (right aligned if label exists, otherwise centered)
        box_rect = pygame.Rect(0, 0, self.box_size, self.box_size)
        if self.label:
            box_rect.midright = (self.rect.right - 2, self.rect.centery)
        else:
            box_rect.center = self.rect.center
            
        # Draw box outline
        outline_color = colors['accent'] if self.is_checked else colors['border']
        if self.is_disabled: outline_color = colors['text_disabled']
        pygame.draw.rect(surface, outline_color, box_rect, 1)
        
        # Draw checkmark/fill
        if self._is_checked:
            fill_rect = box_rect.inflate(-4, -4)
            pygame.draw.rect(surface, colors['accent'], fill_rect)
            
        # Draw Label (if present)
        if self.label:
            Label(pygame.Rect(self.rect.x, self.rect.y, self.rect.width - box_rect.width, self.rect.height), 
                  self.label, alignment="left").draw(surface, theme)

    def get_value(self) -> bool:
        return self._is_checked


# --- 6. Slider Widget ---

class Slider(Widget):
    def __init__(self, rect: pygame.Rect, min_val: float = 0.0, max_val: float = 1.0, initial_val: float = 0.5, step: float = 0.01):
        super().__init__(rect)
        self.min_val = min_val
        self.max_val = max_val
        self.value = MathUtils.clamp(initial_val, min_val, max_val)
        self.step = step
        self._is_dragging = False

    def handle_event(self, event: pygame.event.Event) -> bool:
        if self.is_disabled: return False
        
        consumed = super().handle_event(event)
        
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.is_hovered:
            self._is_dragging = True
            consumed = True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._is_dragging = False
            
        if event.type == pygame.MOUSEMOTION and self._is_dragging:
            # Calculate new value based on mouse X position
            mouse_x = event.pos[0]
            slider_width = self.rect.width
            # Normalized position (0 to 1)
            norm_pos = MathUtils.clamp((mouse_x - self.rect.x) / slider_width, 0.0, 1.0)
            
            # Interpolate value
            raw_value = MathUtils.lerp(self.min_val, self.max_val, norm_pos)
            
            # Apply snapping (steps)
            self.value = round(raw_value / self.step) * self.step
            self.value = MathUtils.clamp(self.value, self.min_val, self.max_val)
            
            return True
            
        return consumed

    def draw(self, surface: pygame.Surface, theme: str):
        colors = _get_theme_colors(theme)
        
        # Draw track
        track_rect = pygame.Rect(self.rect.x, self.rect.centery - 2, self.rect.width, 4)
        pygame.draw.rect(surface, colors['secondary'], track_rect, 0, 2)
        
        # Calculate knob position
        range_val = self.max_val - self.min_val
        norm_val = (self.value - self.min_val) / range_val if range_val != 0 else 0.0
        knob_x = self.rect.x + int(self.rect.width * norm_val)
        
        # Draw knob
        knob_color = colors['accent'] if self._is_dragging else (colors['hover'] if self.is_hovered else colors['secondary'])
        pygame.draw.circle(surface, knob_color, (knob_x, self.rect.centery), 7)
        pygame.draw.circle(surface, colors['border'], (knob_x, self.rect.centery), 7, 1)

    def get_value(self) -> float:
        return self.value


# --- 7. Scrollbar Widget ---

class Scrollbar(Widget):
    """A vertical or horizontal scrollbar with a knob."""
    def __init__(self, rect: pygame.Rect, max_scroll: float, orientation: str = 'vertical'):
        super().__init__(rect)
        self.max_scroll = max_scroll # Total pixel height/width of content
        self.scroll_offset = 0.0     # Current scroll position (0 to max_scroll)
        self.orientation = orientation
        self._is_dragging = False
        self._drag_offset = 0
        self.thumb_min_size = 20 # Minimum size for the thumb/knob

    def get_content_size(self):
        """Returns the size of the visible scroll area (width or height)."""
        return self.rect.height if self.orientation == 'vertical' else self.rect.width
        
    def _calculate_thumb_params(self):
        """Calculates the size and position of the scrollbar thumb."""
        view_size = self.get_content_size()
        
        # Prevent division by zero and handle cases where content fits entirely
        if self.max_scroll <= 0 or view_size >= self.max_scroll + view_size:
            thumb_size = view_size
            thumb_pos = 0
            is_scrollable = False
        else:
            is_scrollable = True
            # Thumb size is proportional to the visible content
            thumb_size = view_size * (view_size / (self.max_scroll + view_size))
            thumb_size = MathUtils.clamp(thumb_size, self.thumb_min_size, view_size)
            
            # Max travel space for the thumb
            max_thumb_travel = view_size - thumb_size
            
            # Thumb position is proportional to scroll offset
            scroll_ratio = self.scroll_offset / self.max_scroll
            thumb_pos = max_thumb_travel * scroll_ratio
            
        return thumb_size, thumb_pos, is_scrollable

    def handle_event(self, event: pygame.event.Event) -> bool:
        consumed = super().handle_event(event)
        
        thumb_size, thumb_pos, is_scrollable = self._calculate_thumb_params()
        if not is_scrollable:
            return False

        mouse_pos = pygame.mouse.get_pos()
        
        # Calculate thumb rect
        if self.orientation == 'vertical':
            thumb_rect = pygame.Rect(self.rect.x, self.rect.y + thumb_pos, self.rect.width, thumb_size)
        else: # horizontal
            thumb_rect = pygame.Rect(self.rect.x + thumb_pos, self.rect.y, thumb_size, self.rect.height)
            
        # 1. Dragging
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and thumb_rect.collidepoint(mouse_pos):
            self._is_dragging = True
            if self.orientation == 'vertical':
                self._drag_offset = mouse_pos[1] - thumb_rect.y
            else:
                self._drag_offset = mouse_pos[0] - thumb_rect.x
            return True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._is_dragging = False
            
        if event.type == pygame.MOUSEMOTION and self._is_dragging:
            if self.orientation == 'vertical':
                new_y = mouse_pos[1] - self._drag_offset
                max_travel = self.rect.height - thumb_size
                norm_pos = MathUtils.clamp((new_y - self.rect.y) / max_travel, 0.0, 1.0)
            else:
                new_x = mouse_pos[0] - self._drag_offset
                max_travel = self.rect.width - thumb_size
                norm_pos = MathUtils.clamp((new_x - self.rect.x) / max_travel, 0.0, 1.0)
                
            self.scroll_offset = self.max_scroll * norm_pos
            return True
            
        # 2. Mouse Wheel Scrolling (Only if hovering over the scrollbar rect itself)
        if self.is_hovered:
            scroll_delta = 0
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 4: # Scroll up
                    scroll_delta = -self.LINE_HEIGHT * 3 # Scroll 3 lines worth
                elif event.button == 5: # Scroll down
                    scroll_delta = self.LINE_HEIGHT * 3
            
            if scroll_delta != 0:
                self.scroll_offset = MathUtils.clamp(self.scroll_offset + scroll_delta, 0.0, self.max_scroll)
                return True

        return consumed

    def draw(self, surface: pygame.Surface, theme: str):
        colors = _get_theme_colors(theme)
        
        # Draw track background
        pygame.draw.rect(surface, colors['primary'], self.rect, 0, 3)
        
        thumb_size, thumb_pos, is_scrollable = self._calculate_thumb_params()
        
        if is_scrollable:
            # Draw thumb
            if self.orientation == 'vertical':
                thumb_rect = pygame.Rect(self.rect.x + 1, self.rect.y + thumb_pos, self.rect.width - 2, thumb_size)
            else:
                thumb_rect = pygame.Rect(self.rect.x + thumb_pos, self.rect.y + 1, thumb_size, self.rect.height - 2)
                
            thumb_color = colors['accent'] if self._is_dragging else (colors['secondary'] if self.is_hovered else colors['hover'])
            pygame.draw.rect(surface, thumb_color, thumb_rect, 0, 3)

    def get_scroll_offset(self) -> float:
        return self.scroll_offset
        
    def set_scroll_offset(self, offset: float):
        """Manually sets the scroll offset."""
        self.scroll_offset = MathUtils.clamp(offset, 0.0, self.max_scroll)
        
    def scroll_to_bottom(self):
        """Sets the scroll offset to the maximum value."""
        self.scroll_offset = self.max_scroll


# --- 8. Dropdown Widget ---

class Dropdown(Widget):
    """A selectable list of options that appears when clicked."""
    def __init__(self, rect: pygame.Rect, options: List[str], initial_selection: str = None, action: Callable = None):
        super().__init__(rect)
        self.options = options
        self.selected_option = initial_selection if initial_selection in options else (options[0] if options else "")
        self.action = action
        self.is_open_list = False
        self.font = pygame.font.Font(None, 18)
        self.option_height = self.rect.height

    def handle_event(self, event: pygame.event.Event) -> bool:
        if self.is_disabled: return False
        
        consumed = super().handle_event(event)

        # Dropdown button click
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.is_hovered and not self.is_open_list:
            self.is_open_list = True
            return True
            
        # Click outside to close list
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.is_open_list:
            list_rect = self.get_list_rect()
            if not list_rect.collidepoint(event.pos):
                self.is_open_list = False
                return True
                
        # Handle list item selection
        if self.is_open_list and event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            list_rect = self.get_list_rect()
            if list_rect.collidepoint(event.pos):
                rel_y = event.pos[1] - list_rect.y
                clicked_index = rel_y // self.option_height
                
                if 0 <= clicked_index < len(self.options):
                    self.selected_option = self.options[clicked_index]
                    self.is_open_list = False
                    if self.action: self.action(self.selected_option)
                    return True
                    
        return consumed

    def get_list_rect(self) -> pygame.Rect:
        """Returns the rect for the floating options list."""
        return pygame.Rect(self.rect.x, self.rect.bottom, self.rect.width, len(self.options) * self.option_height)

    def draw(self, surface: pygame.Surface, theme: str):
        colors = _get_theme_colors(theme)
        
        # Draw button (closed state)
        pygame.draw.rect(surface, colors['secondary'], self.rect, 0, 3)
        pygame.draw.rect(surface, colors['border'], self.rect, 1, 3)
        
        # Draw selected option text
        text_surface = self.font.render(self.selected_option, True, colors['text'])
        surface.blit(text_surface, (self.rect.x + 5, self.rect.y + 3))
        
        # Draw arrow indicator (Mock triangle)
        arrow_x = self.rect.right - 10
        arrow_y = self.rect.centery
        pygame.draw.polygon(surface, colors['text'], 
                            [(arrow_x, arrow_y + 3), (arrow_x - 6, arrow_y + 3), (arrow_x - 3, arrow_y - 2)])
        
        # Draw open list
        if self.is_open_list:
            list_rect = self.get_list_rect()
            pygame.draw.rect(surface, colors['secondary'], list_rect, 0, 3)
            pygame.draw.rect(surface, colors['accent'], list_rect, 1, 3)
            
            for i, option in enumerate(self.options):
                option_rect = pygame.Rect(list_rect.x, list_rect.y + i * self.option_height, list_rect.width, self.option_height)
                
                # Highlight hovered option
                if option_rect.collidepoint(pygame.mouse.get_pos()):
                    pygame.draw.rect(surface, colors['hover'], option_rect, 0, 3)
                    
                # Highlight selected option
                if option == self.selected_option:
                    pygame.draw.rect(surface, colors['accent'], option_rect, 1, 3)
                    
                text_surface = self.font.render(option, True, colors['text'])
                surface.blit(text_surface, (option_rect.x + 5, option_rect.y + 3))

    def get_value(self) -> str:
        return self.selected_option