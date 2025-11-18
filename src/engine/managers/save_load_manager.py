# engine/managers/save_load_manager.py
import pygame
import sys
import os
import json
import time
import shutil
import copy

# Attempt to import core dependencies, use minimal mocks if they fail
try:
    from engine.core.engine_state import EngineState
    from engine.core.engine_config import EngineConfig
    from engine.utils.file_utils import FileUtils
    from engine.core.scene_manager import SceneManager # Used for scene loading/saving
except ImportError as e:
    print(f"[SaveLoadManager Import Error] {e}. Using Internal Mocks.")
    class EngineState:
        def __init__(self): 
            self.config = self
            self.editor_settings = {"autosave_interval_minutes": 5}
            self.current_project_path = os.path.join(os.getcwd(), 'projects', 'example_project')
            self.current_scene = self
            self.scene_manager = self
            self.game_manager = self
        def get_setting(self, *args): return 5
    class EngineConfig:
        def save_config(self): FileUtils.log_message("Mock Config Save")
        def set_setting(self, *args): pass
    class FileUtils:
        @staticmethod
        def log_message(msg): print(f"[SLM-INFO] {msg}")
        @staticmethod
        def log_error(msg): print(f"[SLM-ERROR] {msg}", file=sys.stderr)
        @staticmethod
        def create_dirs_if_not_exist(path): os.makedirs(path, exist_ok=True)
        @staticmethod
        def write_json(path, data): pass
        @staticmethod
        def read_json(path): return {}
    class SceneManager:
        def __init__(self, state): pass
        def save_scene(self): return True
        def load_scene(self, path): return True
        @property
        def current_scene_file(self): return "main_scene.json"


class SaveLoadManager:
    """
    Handles persistence of the entire project state: scene, project.json, 
    and editor settings. Supports Save, Load, Save As, and Autosave.
    """
    
    # Filenames (relative to project root)
    PROJECT_CONFIG_FILE = 'project.json'
    AUTOSAVE_DIR = 'autosave'
    BACKUP_DIR = 'backups'
    
    def __init__(self, state: EngineState):
        self.state = state
        self.state.save_load_manager = self
        self.last_save_time = time.time()
        self.autosave_interval = self.state.config.get_setting('editor_settings', 'autosave_interval_minutes', 5) * 60 # seconds
        
        FileUtils.log_message("SaveLoadManager initialized.")

    # --- Core Saving Logic ---

    def save_full_project(self, target_path: str, is_save_as: bool = False, is_autosave: bool = False) -> bool:
        """
        Saves all relevant project state files (project.json, current scene).
        """
        if not target_path:
            FileUtils.log_error("Cannot save: Project path is undefined.")
            return False

        # 1. Handle 'Save As' (Create/Move project structure)
        if is_save_as:
            old_path = self.state.current_project_path
            
            # If the new path is different, create the new folder structure
            if old_path != target_path:
                try:
                    FileUtils.create_dirs_if_not_exist(target_path)
                    # Copy essential sub-directories if they exist in old project
                    for subdir in ['assets', 'scripts', 'docs']:
                        old_subdir = os.path.join(old_path, subdir)
                        if os.path.isdir(old_subdir):
                            shutil.copytree(old_subdir, os.path.join(target_path, subdir), dirs_exist_ok=True)
                    
                    self.state.current_project_path = target_path
                    self.state.config.set_setting('editor_settings', 'last_opened_project', target_path)
                    self.state.config.save_config()
                    FileUtils.log_message(f"Project path updated to: {target_path}")
                except Exception as e:
                    FileUtils.log_error(f"Failed to create new project structure at {target_path}: {e}")
                    return False

        # 2. Save Project Configuration (project.json)
        if not self._save_project_config(target_path):
            return False

        # 3. Save Current Scene
        scene_manager = self.state.scene_manager
        if scene_manager and scene_manager.current_scene_file:
            # Re-save to the same scene file in the (potentially new) project path
            scene_file_name = os.path.basename(scene_manager.current_scene_file)
            scene_relative_path = self.state.game_manager.project_data.get('main_scene', 'main_scene.json') # Use the path from project.json
            
            # Full path relative to the new project path
            full_scene_path = os.path.join(target_path, scene_relative_path) 
            
            # Ensure the scene's subdirectory exists
            FileUtils.create_dirs_if_not_exist(os.path.dirname(full_scene_path))
            
            # The SceneManager expects a path relative to the project root, so we pass it the full path here.
            # However, since SceneManager.save_scene handles relative paths implicitly, we just need to ensure 
            # the current_scene_file is correctly set. For a Save As, we temporarily override it.
            
            original_scene_file = scene_manager.current_scene_file
            scene_manager.current_scene_file = full_scene_path 
            
            scene_saved = scene_manager.save_scene(full_scene_path)
            
            # Restore original scene file path if it was a temporary Save As path
            if is_save_as:
                scene_manager.current_scene_file = original_scene_file # Keep original name for future quick-save

            if not scene_saved:
                FileUtils.log_error("Failed to save current scene.")
                return False
        
        # 4. Finalize
        self.last_save_time = time.time()
        
        if not is_autosave:
            # Create a backup on successful manual save (Versioning)
            self._create_project_backup(target_path)
            
        log_msg = "Autosave" if is_autosave else ("Project Saved As" if is_save_as else "Project Saved")
        FileUtils.log_message(f"{log_msg} successfully to {target_path}")
        return True


    def _save_project_config(self, target_path: str) -> bool:
        """Saves the project.json file with current settings."""
        config_path = os.path.join(target_path, self.PROJECT_CONFIG_FILE)
        
        # Build the current project data dictionary
        proj_data = self.state.game_manager.project_data.copy()
        
        # Update settings block with current runtime settings from EngineConfig
        proj_data['settings'] = self.state.config.project_settings
        
        # Ensure main_scene path is relative
        if self.state.scene_manager and self.state.scene_manager.current_scene_file:
            # Assuming current_scene_file is a full path for safety, make it relative
            try:
                main_scene_file = os.path.relpath(self.state.scene_manager.current_scene_file, target_path)
            except ValueError:
                 # If paths are on different drives, use the basename as a fallback
                 main_scene_file = os.path.basename(self.state.scene_manager.current_scene_file)
            
            proj_data['main_scene'] = main_scene_file
            
        try:
            FileUtils.write_json(config_path, proj_data)
            return True
        except Exception as e:
            FileUtils.log_error(f"Failed to save project config to {config_path}: {e}")
            return False

    # --- Loading Logic (Delegates to GameManager) ---
    
    def load_project(self, project_path: str) -> bool:
        """Loads a project via the GameManager."""
        if self.state.game_manager:
            return self.state.game_manager.load_project(project_path)
        FileUtils.log_error("GameManager not initialized. Cannot load project.")
        return False
        
    # --- Autosave and Backup ---

    def autosave_check(self):
        """Checks if it's time for an autosave and performs it."""
        if self.state.is_editor_mode and self.state.current_project_path:
            current_time = time.time()
            if current_time - self.last_save_time >= self.autosave_interval:
                FileUtils.log_message("Autosave triggered...")
                # Autosave always goes to the dedicated autosave directory
                autosave_path = os.path.join(self.state.current_project_path, self.AUTOSAVE_DIR)
                FileUtils.create_dirs_if_not_exist(autosave_path)
                
                # NOTE: Autosave typically just saves the scene/config to a specific file, not the full project folder
                # We mock a save to the scene file inside the autosave dir for simplicity.
                
                # 1. Save Scene to Autosave/main_scene_autosave.json
                scene_manager = self.state.scene_manager
                if scene_manager and self.state.current_scene:
                    autosave_scene_path = os.path.join(autosave_path, "main_scene_autosave.json")
                    
                    original_scene_file = scene_manager.current_scene_file
                    scene_manager.current_scene_file = autosave_scene_path # Set temporary path
                    
                    if scene_manager.save_scene(autosave_scene_path):
                         FileUtils.log_message(f"Autosave scene saved to {autosave_scene_path}")
                    
                    scene_manager.current_scene_file = original_scene_file # Restore original path

                # 2. Save Config to Autosave/project_autosave.json (Mocked, often not needed)
                self.last_save_time = current_time # Reset timer even if save failed
                
                FileUtils.log_message("Autosave complete.")
                
    def _create_project_backup(self, project_path: str):
        """Creates a timestamped backup of the project's scene/config files."""
        backup_root = os.path.join(project_path, self.BACKUP_DIR)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        backup_dir = os.path.join(backup_root, timestamp)
        
        FileUtils.create_dirs_if_not_exist(backup_dir)
        
        # Files to backup (config and current scene)
        files_to_copy = [self.PROJECT_CONFIG_FILE]
        scene_path_rel = self.state.game_manager.project_data.get('main_scene', 'main_scene.json')
        files_to_copy.append(scene_path_rel)
        
        try:
            for rel_path in files_to_copy:
                source_path = os.path.join(project_path, rel_path)
                target_path = os.path.join(backup_dir, os.path.basename(rel_path)) # Only copy base file name
                
                if os.path.exists(source_path):
                    shutil.copy2(source_path, target_path)
            
            FileUtils.log_message(f"Created project backup at {backup_dir}")
        except Exception as e:
            FileUtils.log_error(f"Failed to create project backup: {e}")
            
    def get_available_backups(self, project_path: str) -> list[str]:
        """Returns a list of available backup timestamps."""
        backup_root = os.path.join(project_path, self.BACKUP_DIR)
        if not os.path.isdir(backup_root):
            return []
        # Return sorted list of sub-directories (timestamps)
        return sorted([d for d in os.listdir(backup_root) if os.path.isdir(os.path.join(backup_root, d))], reverse=True)