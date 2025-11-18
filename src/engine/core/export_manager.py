# engine/core/export_manager.py
import os
import sys
import json
import zipfile
import shutil
import time

# Attempt to import core dependencies, use minimal mocks if they fail
try:
    from engine.core.engine_state import EngineState
    from engine.utils.file_utils import FileUtils
    from engine.utils.math_utils import MathUtils
except ImportError as e:
    print(f"[ExportManager Import Error] {e}. Using Internal Mocks.")
    class EngineState: pass
    class FileUtils:
        @staticmethod
        def log_message(msg): print(f"[EM-INFO] {msg}")
        @staticmethod
        def log_error(msg): print(f"[EM-ERROR] {msg}", file=sys.stderr)
        @staticmethod
        def create_dirs_if_not_exist(path): os.makedirs(path, exist_ok=True)
        @staticmethod
        def get_engine_root_path(): return os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    class MathUtils:
        @staticmethod
        def clamp(val, min_v, max_v): return max(min_v, min(max_v, val))


class ExportManager:
    """
    Manages the process of exporting a project into a runnable build 
    for various platforms (Desktop, Web/HTML5 stub).
    """

    EXPORT_TYPES = {
        "desktop_win": "Windows (.exe - Mock)",
        "desktop_linux": "Linux (.bin - Mock)",
        "web_html5": "Web (.zip/HTML5 Stub)"
    }
    
    ENGINE_BUILD_SCRIPTS_DIR = os.path.join(FileUtils.get_engine_root_path(), 'tools')
    ENGINE_RUNTIME_FILES = [
        'main.py', 'startup.py', 'engine/__init__.py', 'engine/core/engine_runtime.py',
        # ... and all other core engine files (for full build)
    ]

    def __init__(self, state: EngineState):
        self.state = state
        self.state.export_manager = self
        
        # Default export directory is in the engine root
        self.default_export_path = os.path.join(FileUtils.get_engine_root_path(), 'builds')
        FileUtils.create_dirs_if_not_exist(self.default_export_path)

    def export_project(self, export_type: str, export_path: str = None, project_path: str = None):
        """
        Main function to initiate the export process.
        """
        if export_type not in self.EXPORT_TYPES:
            FileUtils.log_error(f"Unknown export type: {export_type}")
            return False

        proj_path = project_path if project_path else self.state.current_project_path
        if not proj_path or not os.path.isdir(proj_path):
            FileUtils.log_error("No valid project path specified for export.")
            return False

        export_dir = export_path if export_path else self.default_export_path
        FileUtils.create_dirs_if_not_exist(export_dir)
        
        project_name = os.path.basename(proj_path)
        build_name = f"{project_name}_{export_type}_{time.strftime('%Y%m%d_%H%M%S')}"
        target_build_path = os.path.join(export_dir, build_name)
        FileUtils.create_dirs_if_not_exist(target_build_path)
        
        FileUtils.log_message(f"Starting export '{export_type}' for project '{project_name}' to {target_build_path}")

        try:
            if export_type == "web_html5":
                success = self._export_web_html5(proj_path, target_build_path, project_name)
            elif export_type.startswith("desktop"):
                success = self._export_desktop_mock(proj_path, target_build_path, project_name)
            else:
                success = False

            if success:
                FileUtils.log_message(f"Export '{export_type}' completed successfully to {target_build_path}")
            else:
                # Cleanup on failure
                shutil.rmtree(target_build_path, ignore_errors=True)
                FileUtils.log_error(f"Export '{export_type}' failed. Build folder removed.")
            
            return success

        except Exception as e:
            FileUtils.log_error(f"Critical error during export: {e}")
            shutil.rmtree(target_build_path, ignore_errors=True)
            return False

    # --- Export Implementations ---

    def _export_desktop_mock(self, project_path: str, target_build_path: str, project_name: str):
        """
        Mocks a full desktop build by copying project files and a simple runner.
        In a real scenario, this would invoke pyinstaller/Nuitka/etc.
        """
        FileUtils.log_message("Desktop mock export: Copying project files and assets...")
        
        # 1. Copy Project Files and Assets
        shutil.copytree(project_path, os.path.join(target_build_path, project_name))
        
        # 2. Mock Runtime Entry Point (A minimal script that mimics the engine run)
        mock_runner_content = f"""
# {project_name}_runner.py - Mock executable entry point

# Mock implementation of a runtime environment setup
import sys, os, importlib.util
sys.path.append(os.path.abspath('.'))

def run_game():
    print(f"--- Running Game: {{project_name}} ---")
    print("This is a mock build. A real build would include all engine dependencies.")
    
    # Mock loading the project's main script
    try:
        main_script_path = os.path.join("{project_name}", "main.py")
        spec = importlib.util.spec_from_file_location("game_main", main_script_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        if hasattr(module, 'start_game'):
            print("Running project's start_game hook...")
            # module.start_game(mock_game_manager) # Mock call to project startup
            
    except Exception as e:
        print(f"Error loading project script: {{e}}")
        
    print("Game finished. Exiting in 5 seconds...")
    import time
    time.sleep(5)
    
if __name__ == '__main__':
    run_game()
"""
        with open(os.path.join(target_build_path, f"{project_name}_runner.py"), 'w') as f:
            f.write(mock_runner_content)
            
        FileUtils.log_message("Desktop mock export completed. Run the '_runner.py' file to test.")
        return True

    def _export_web_html5(self, project_path: str, target_build_path: str, project_name: str):
        """
        Creates a web-friendly package (zip) with an index.html runner stub.
        Relies on the user having a system like Pygbag/pyscript for actual runtime.
        """
        FileUtils.log_message("Web/HTML5 export: Creating zip package and index.html stub...")
        
        # 1. Create the project archive (e.g., my_game.zip)
        archive_name = f"{project_name}_web_data.zip"
        archive_path = os.path.join(target_build_path, archive_name)
        
        try:
            # Create a zip containing the project's main folder
            with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                # Add project files and assets
                for root, _, files in os.walk(project_path):
                    for file in files:
                        full_file_path = os.path.join(root, file)
                        # Archive path should be relative to the project_path (no root folder in zip)
                        rel_path = os.path.relpath(full_file_path, project_path)
                        zf.write(full_file_path, rel_path)
                        
                # Add the necessary runner file (e.g., the project's main.py needs to be at the root of the virtual file system)
                # The assumption is that the web runtime executes the main.py script
                zf.write(os.path.join(project_path, 'main.py'), 'main.py')
        except Exception as e:
            FileUtils.log_error(f"Failed to create web data zip: {e}")
            return False

        # 2. Create index.html runner stub
        html_content = self._generate_html_stub(project_name, archive_name)
        with open(os.path.join(target_build_path, 'index.html'), 'w') as f:
            f.write(html_content)
            
        FileUtils.log_message("Web export completed. Place the contents on a web server or use a tool like Pygbag.")
        return True
        
    def _generate_html_stub(self, project_name: str, archive_name: str) -> str:
        """Generates a minimal index.html file with instructions for web runtime."""
        
        # NOTE: This uses generic Python web runner assumptions (like Pygbag's requirements)
        # It tells the runner which script to execute and what data to load.
        
        title = self.state.config.project_settings.get('game_title', project_name)
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <style>
        body {{ margin: 0; overflow: hidden; background: #000; }}
        canvas {{ display: block; margin: auto; background: #000; }}
    </style>
</head>
<body>

<!--
    PYGAME STUDIO ENGINE V4 WEB EXPORT STUB
    
    This HTML file is a placeholder for a Python-to-Web runtime (e.g., Pygbag, pyscript).
    
    The '{archive_name}' ZIP file contains the game's code and assets.
    
    The web runner must:
    1. Download and mount '{archive_name}' into a virtual file system.
    2. Execute the 'main.py' script inside the virtual file system (which is the project's main.py).
-->

<h1>{title}</h1>
<p>
    Web Game Loading... Please ensure a compatible Python-to-Web runtime 
    (like Pygbag/pyscript) is integrated here. 
</p>
<p>
    File to load: <strong>{archive_name}</strong><br>
    Entry script: <strong>main.py</strong> (inside the zip)
</p>

<!-- Placeholder for a web runner script, e.g., Pygbag's boot.js -->
<script>
    console.log("Web Export Initialized: Waiting for Pygame-Web runtime environment.");
    // Example: window.pygbag.run_game('{archive_name}', 'main.py');
</script>

</body>
</html>
"""
        return html