# tools/data_migration.py
import os
import sys
import json
import shutil
from typing import Dict, Any, Callable

# Attempt to import core dependencies, use minimal mocks if they fail
try:
    from engine.utils.file_utils import FileUtils
    from engine.utils.json_schema import JsonSchema
except ImportError as e:
    print(f"[DataMigration Import Error] {e}. Using Internal Mocks.")
    class FileUtils:
        @staticmethod
        def log_message(msg): print(f"[DM-INFO] {msg}")
        @staticmethod
        def log_error(msg): print(f"[DM-ERROR] {msg}", file=sys.stderr)
        @staticmethod
        def log_warning(msg): print(f"[DM-WARN] {msg}")
        @staticmethod
        def read_json(path): return {}
        @staticmethod
        def write_json(path, data): pass
        @staticmethod
        def get_engine_root_path(): return os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    class JsonSchema:
        @staticmethod
        def validate_schema(data, schema): return []


class DataMigration:
    """
    Utility class for migrating project data (scenes, components, config) 
    between different versions of the engine (e.g., V3 to V4).
    """
    
    def __init__(self):
        self.migration_map: Dict[str, Callable] = self._get_migration_map()

    def _get_migration_map(self) -> Dict[str, Callable]:
        """Defines the available migration functions by version string."""
        return {
            "v3.0.0_to_v4.0.0": self._migrate_v3_to_v4,
            # Add future migrations here: "v4.0.0_to_v4.1.0": self._migrate_v4_to_v4_1,
        }

    def _migrate_v3_to_v4(self, project_path: str) -> bool:
        """
        Migration logic from mock V3 format to V4 format.
        Mock changes: Renaming 'game_object_2d' to 'sprite' and 'position' from list to object format (in code).
        """
        FileUtils.log_message(f"Starting migration V3.0.0 -> V4.0.0 for {project_path}...")
        
        proj_json_path = os.path.join(project_path, 'project.json')
        proj_data = FileUtils.read_json(proj_json_path)
        
        if not proj_data:
            FileUtils.log_error("Could not load project.json for migration.")
            return False

        # 1. Update Engine Version Tag
        proj_data['engine_version'] = "V4.0.0"
        
        # 2. Migrate Main Scene File
        main_scene_path = os.path.join(project_path, proj_data.get('main_scene', 'main_scene.json'))
        scene_data = FileUtils.read_json(main_scene_path)
        
        if not scene_data:
            FileUtils.log_error("Could not load main scene file for migration.")
            return False

        # Apply object-level migrations
        for obj in scene_data.get('objects', []):
            # Migration 2.1: Rename old 'game_object_2d' type to 'sprite'
            if obj.get('type') == 'game_object_2d':
                obj['type'] = 'sprite'
                FileUtils.log_message(f"  - Renamed object '{obj.get('name')}' type to 'sprite'.")
                
            # Migration 2.2: Rename old 'RenderComponent' to 'SpriteRenderer' if 2D
            for comp in obj.get('components', []):
                if comp.get('type') == 'RenderComponent' and not scene_data.get('is_3d'):
                    comp['type'] = 'SpriteRenderer'
                    FileUtils.log_message(f"  - Renamed component to 'SpriteRenderer' on {obj.get('name')}.")
                    
        # 3. Write migrated files (overwriting old ones, assume user has backups)
        FileUtils.write_json(main_scene_path, scene_data)
        FileUtils.write_json(proj_json_path, proj_data)
        
        FileUtils.log_message(f"Migration V3.0.0 -> V4.0.0 successful for {project_path}.")
        return True

    def run_migration(self, project_path: str, target_version: str) -> bool:
        """
        Executes the necessary migration steps to bring a project to the target version.
        """
        
        # Determine current project version (Mock: always assume V3 for this demo)
        current_version = "v3.0.0"
        migration_key = f"{current_version}_to_{target_version}".lower().replace('.', '_')

        if migration_key not in self.migration_map:
            FileUtils.log_error(f"No direct migration path found from {current_version} to {target_version}.")
            return False

        migration_func = self.migration_map[migration_key]
        
        # Create a backup before starting the migration
        backup_path = f"{project_path}_pre_{target_version.replace('.', '_')}_backup"
        try:
            shutil.copytree(project_path, backup_path)
            FileUtils.log_warning(f"Created pre-migration backup at: {backup_path}")
        except Exception as e:
            FileUtils.log_error(f"Failed to create pre-migration backup: {e}")
            return False # Stop if backup fails

        # Execute migration
        return migration_func(project_path)


# --- Command Line Interface ---
if __name__ == '__main__':
    data_migration = DataMigration()
    
    if len(sys.argv) > 2:
        command = sys.argv.lower()
        project = sys.argv
        target_version = sys.argv if len(sys.argv) > 3 else "V4.0.0"
        
        if command == 'migrate':
            data_migration.run_migration(project, target_version)
        else:
            FileUtils.log_error(f"Unknown data migration command: {command}")
    else:
        FileUtils.log_message("DataMigration CLI: Usage: python data_migration.py [migrate] <project_path> <target_version>")
