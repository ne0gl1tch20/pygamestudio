# engine/core/workshop_manager.py
import os
import sys
import json
import zipfile
import shutil
import time
import copy

# Attempt to import core dependencies, use minimal mocks if they fail
try:
    from engine.core.engine_state import EngineState
    from engine.utils.file_utils import FileUtils
    from engine.utils.math_utils import MathUtils # Used for random ratings
except ImportError as e:
    print(f"[WorkshopManager Import Error] {e}. Using Internal Mocks.")
    class EngineState: pass
    class FileUtils:
        @staticmethod
        def log_message(msg): print(f"[WM-INFO] {msg}")
        @staticmethod
        def log_error(msg): print(f"[WM-ERROR] {msg}", file=sys.stderr)
        @staticmethod
        def log_warning(msg): print(f"[WM-WARN] {msg}")
        @staticmethod
        def create_dirs_if_not_exist(path): os.makedirs(path, exist_ok=True)
        @staticmethod
        def get_engine_root_path(): return os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    class MathUtils:
        @staticmethod
        def clamp(val, min_v, max_v): return max(min_v, min(max_v, val))
        @staticmethod
        def lerp(a, b, t): return a + (b - a) * t
        @staticmethod
        def random(): return time.time() % 1 # Simple mock random float 0.0-1.0

class WorkshopManager:
    """
    Manages the mocked Steam-like Workshop system for uploading, downloading,
    and browsing project/asset packages.
    
    The 'server' is a local directory (workshop_server/) for demonstration.
    """
    
    WORKSHOP_ROOT = os.path.join(FileUtils.get_engine_root_path(), 'workshop_server')
    METADATA_FILE = 'workshop_metadata.json'
    PROJECTS_DIR = os.path.join(FileUtils.get_engine_root_path(), 'projects')

    def __init__(self, state: EngineState):
        self.state = state
        self.state.workshop_manager = self
        self.available_items = {} # {id: metadata}
        FileUtils.create_dirs_if_not_exist(self.WORKSHOP_ROOT)
        self.scan_workshop()

    def scan_workshop(self):
        """
        Scans the local workshop_server directory for packaged items (.zip)
        and extracts/loads their metadata.
        """
        self.available_items.clear()
        
        for item_dir in os.listdir(self.WORKSHOP_ROOT):
            full_dir_path = os.path.join(self.WORKSHOP_ROOT, item_dir)
            if os.path.isdir(full_dir_path):
                metadata_path = os.path.join(full_dir_path, self.METADATA_FILE)
                if os.path.exists(metadata_path):
                    try:
                        with open(metadata_path, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                            # Mock in some dynamic data
                            item_id = metadata.get('id', item_dir)
                            metadata['id'] = item_id
                            metadata['path'] = full_dir_path
                            metadata['rating'] = self._mock_rating(item_id)
                            metadata['download_count'] = metadata.get('download_count', 0)
                            self.available_items[item_id] = metadata
                    except Exception as e:
                        FileUtils.log_error(f"Failed to read metadata for {item_dir}: {e}")
                        
        FileUtils.log_message(f"Workshop scanned. Found {len(self.available_items)} items.")

    def _mock_rating(self, item_id: str):
        """Generates a pseudo-random rating based on the item ID for realism."""
        # Simple hash function based on ID to make the rating stable
        seed = sum(ord(c) for c in item_id)
        rating = MathUtils.clamp((seed % 50) / 10 + 2.5 + (MathUtils.random() - 0.5) * 0.5, 1.0, 5.0)
        return round(rating, 2)
        
    # --- Upload (Package) System ---

    def upload_project(self, project_path: str, tags: list[str], description: str):
        """
        Packages the current project into a zip file with metadata and 
        places it in the mock workshop server directory.
        """
        project_name = os.path.basename(project_path)
        workshop_item_id = project_name.lower().replace(' ', '_') + "_" + str(int(time.time()))
        
        # 1. Prepare Metadata
        metadata = {
            "id": workshop_item_id,
            "name": project_name,
            "author": "Engine User", # Mock author
            "version": self.state.config.project_settings.get("engine_version", "V4.0.0"),
            "is_3d": self.state.config.project_settings.get("is_3d_mode", False),
            "description": description,
            "tags": tags,
            "date_uploaded": time.strftime("%Y-%m-%d %H:%M:%S"),
            "download_count": 0,
            "project_root": project_name # Name of the folder inside the zip
        }
        
        # 2. Create Workshop Item Directory
        item_dir = os.path.join(self.WORKSHOP_ROOT, workshop_item_id)
        FileUtils.create_dirs_if_not_exist(item_dir)
        
        # 3. Write Metadata
        metadata_path = os.path.join(item_dir, self.METADATA_FILE)
        try:
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=4)
        except Exception as e:
            FileUtils.log_error(f"Failed to write workshop metadata: {e}")
            shutil.rmtree(item_dir, ignore_errors=True)
            return False

        # 4. Create Project Zip Package (Simplified inclusion of *all* project files)
        zip_path = os.path.join(item_dir, f"{workshop_item_id}.zip")
        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for root, _, files in os.walk(project_path):
                    for file in files:
                        full_file_path = os.path.join(root, file)
                        # Create archive path relative to the project_path but inside a root folder (project_name)
                        rel_path = os.path.relpath(full_file_path, project_path)
                        archive_path = os.path.join(project_name, rel_path)
                        zf.write(full_file_path, archive_path)
                        
            FileUtils.log_message(f"Project '{project_name}' uploaded to workshop as '{workshop_item_id}'.")
            self.scan_workshop() # Refresh list
            return True

        except Exception as e:
            FileUtils.log_error(f"Failed to create project zip for upload: {e}")
            shutil.rmtree(item_dir, ignore_errors=True)
            return False

    # --- Download (Import) System ---

    def download_and_import(self, item_id: str, import_name: str = None):
        """
        Downloads the item package from the workshop server and imports 
        it into the local projects directory.
        """
        item_data = self.available_items.get(item_id)
        if not item_data:
            FileUtils.log_error(f"Workshop item ID '{item_id}' not found.")
            return False
            
        project_name = import_name if import_name else item_data['name'].replace(' ', '_')
        target_path = os.path.join(self.PROJECTS_DIR, project_name)
        
        if os.path.exists(target_path):
            FileUtils.log_error(f"Project directory '{project_name}' already exists. Import aborted.")
            return False
            
        zip_path = os.path.join(item_data['path'], f"{item_id}.zip")
        
        if not os.path.exists(zip_path):
            FileUtils.log_error(f"Workshop zip file not found for item ID '{item_id}'.")
            return False
            
        try:
            # 1. Unzip to a temporary location
            temp_extract_path = os.path.join(self.WORKSHOP_ROOT, 'temp_import')
            FileUtils.create_dirs_if_not_exist(temp_extract_path)
            
            with zipfile.ZipFile(zip_path, 'r') as zf:
                zf.extractall(temp_extract_path)

            # 2. Find the root project folder inside the zip (from metadata)
            zip_root_name = item_data.get('project_root', os.path.basename(item_data['path']))
            source_path = os.path.join(temp_extract_path, zip_root_name)

            if not os.path.isdir(source_path):
                # Fallback: check all subdirs
                subdirs = [d for d in os.listdir(temp_extract_path) if os.path.isdir(os.path.join(temp_extract_path, d))]
                if subdirs:
                    source_path = os.path.join(temp_extract_path, subdirs[0])
                else:
                    FileUtils.log_error(f"Could not find project root inside the downloaded zip for '{item_id}'.")
                    return False
            
            # 3. Move to final projects directory
            shutil.move(source_path, target_path)

            # 4. Cleanup temp
            shutil.rmtree(temp_extract_path)
            
            # 5. Update metadata (mock download count)
            item_data['download_count'] = item_data.get('download_count', 0) + 1
            self._save_metadata(item_id, item_data)

            FileUtils.log_message(f"Workshop item '{item_data['name']}' imported as project '{project_name}'.")
            return True

        except Exception as e:
            FileUtils.log_error(f"Error importing workshop item '{item_id}': {e}")
            shutil.rmtree(temp_extract_path, ignore_errors=True)
            return False
            
    # --- Metadata/Rating Mock ---
    
    def submit_rating(self, item_id: str, rating: float):
        """Mock function to simulate rating submission and update local metadata."""
        if item_id not in self.available_items:
            FileUtils.log_error(f"Cannot rate: Item ID '{item_id}' not found.")
            return False
            
        rating = MathUtils.clamp(rating, 1.0, 5.0)
        item_data = self.available_items[item_id]
        
        # Simple averaging mock (actual rating is re-calculated on scan, this is just for feedback)
        current_rating = item_data.get('rating', 3.0)
        current_downloads = item_data.get('download_count', 1) # Treat downloads as votes
        
        new_rating = (current_rating * current_downloads + rating) / (current_downloads + 1)
        item_data['rating'] = round(new_rating, 2)
        item_data['download_count'] = current_downloads + 1
        
        self._save_metadata(item_id, item_data)
        FileUtils.log_message(f"Submitted rating of {rating} for '{item_data['name']}'. New average: {item_data['rating']}")
        return True

    def _save_metadata(self, item_id: str, metadata: dict):
        """Saves the updated metadata file to the workshop server directory."""
        metadata_path = os.path.join(self.available_items[item_id]['path'], self.METADATA_FILE)
        
        # Remove dynamic keys before saving
        save_metadata = copy.deepcopy(metadata)
        save_metadata.pop('path', None) 
        save_metadata.pop('rating', None) 
        
        try:
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(save_metadata, f, indent=4)
        except Exception as e:
            FileUtils.log_error(f"Failed to save updated metadata for {item_id}: {e}")