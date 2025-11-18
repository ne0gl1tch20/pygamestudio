# tools/build_scripts.py
import os
import sys
import json
import zipfile
import shutil
import subprocess
from typing import Dict, Any, List

# Attempt to import core dependencies, use minimal mocks if they fail
try:
    from engine.utils.file_utils import FileUtils
    from engine.core.export_manager import ExportManager
except ImportError as e:
    print(f"[BuildScripts Import Error] {e}. Using Internal Mocks.")
    class FileUtils:
        @staticmethod
        def log_message(msg): print(f"[BDS-INFO] {msg}")
        @staticmethod
        def log_error(msg): print(f"[BDS-ERROR] {msg}", file=sys.stderr)
        @staticmethod
        def create_dirs_if_not_exist(path): os.makedirs(path, exist_ok=True)
        @staticmethod
        def get_engine_root_path(): return os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    class ExportManager:
        ENGINE_RUNTIME_FILES = ['main.py', 'startup.py']


class BuildScripts:
    """
    Contains helper functions and final executable wrappers used by the 
    ExportManager for creating runnable game builds.
    """
    
    def __init__(self):
        self.engine_root = FileUtils.get_engine_root_path()
        self.export_manager = ExportManager(None) # Mock manager

    def _copy_engine_runtime(self, target_path: str):
        """Copies essential core engine files to the build directory."""
        FileUtils.log_message("Copying core engine runtime files...")
        
        # Define all engine folders to copy (simplified for mock)
        core_folders = ['engine/core', 'engine/utils', 'engine/managers', 'engine/rendering', 'engine/physics', 'engine/scripting']
        
        for folder_rel in core_folders:
            src = os.path.join(self.engine_root, folder_rel)
            dst = os.path.join(target_path, folder_rel)
            if os.path.isdir(src):
                shutil.copytree(src, dst, dirs_exist_ok=True)
                
        # Copy root files (main.py, startup.py)
        for filename in self.export_manager.ENGINE_RUNTIME_FILES:
            shutil.copy2(os.path.join(self.engine_root, filename), os.path.join(target_path, filename))

    def create_desktop_runner(self, project_name: str, target_build_path: str, platform: str):
        """
        Creates a mock final executable/runner script for desktop builds.
        This would invoke tools like PyInstaller in a real deployment system.
        """
        FileUtils.log_message(f"Creating {platform} desktop runner...")

        # 1. Copy full engine runtime
        self._copy_engine_runtime(target_build_path)
        
        # 2. Copy project files (already done by ExportManager mock, but needed for completeness)
        
        # 3. Create the final execution script (main.py modification)
        
        # We create a new entry point that loads the project's main.py
        runner_content = f"""
# {project_name}_runner_exe_entry.py

import sys
import os
import pygame
# Ensure all modules are accessible (the build includes the engine/ directory)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Mock minimal EngineRuntime/GameManager to launch the project

# --- MOCKING ENGINE STARTUP FOR BUILD ---
class MockGameManager:
    def __init__(self): self.project_data = {{"main_scene": "main_scene.json"}} # Mock

def launch_game():
    try:
        # 1. Load project's main script module
        project_main_path = os.path.join("{project_name}", "main.py")
        import importlib.util
        spec = importlib.util.spec_from_file_location("game_main", project_main_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # 2. Mock Engine Initialization and Runtime Execution
        # This is where the actual EngineRuntime would be created and run.
        
        # Mock the project's start_game hook
        mock_game_manager = MockGameManager()
        if hasattr(module, 'start_game'):
             scene_data = module.start_game(mock_game_manager) 
             print(f"Project '{project_name}' start_game hook executed. Scene data received: {{'name': scene_data.get('name', 'N/A')}}")

        print("--- RUNTIME MOCK: Game Loop Started ---")
        # In a real scenario, EngineRuntime.run() would block here.
        # We just print a confirmation.

    except Exception as e:
        print(f"CRITICAL GAME LAUNCH ERROR: {{e}}")
        import traceback
        traceback.print_exc()
    
    input("Press Enter to exit build runner...") # Keep console open for debug

if __name__ == '__main__':
    launch_game()
"""
        runner_path = os.path.join(target_build_path, f"run_{project_name}.py")
        FileUtils.write_text(runner_path, runner_content)
        
        # 4. Mock Compilation/Packaging
        FileUtils.log_warning(f"Mock Packaging: A real build would use PyInstaller/etc. to package {runner_path} into an executable.")
        FileUtils.log_message(f"Desktop build files placed in {target_build_path}. Run 'run_{project_name}.py' to launch mock game.")
        
        return True


# --- Command Line Interface ---
if __name__ == '__main__':
    build_scripts = BuildScripts()
    
    if len(sys.argv) > 4:
        command = sys.argv[1].lower()
        project_name = sys.argv[2]
        target_path = sys.argv[3]
        platform = sys.argv[4]
        
        if command == 'createdesktop':
            build_scripts.create_desktop_runner(project_name, target_path, platform)
        else:
            FileUtils.log_error(f"Unknown build script command: {command}")
    else:
        FileUtils.log_message("BuildScripts CLI: Usage: python build_scripts.py [createdesktop] <project_name> <target_path> <platform>")

