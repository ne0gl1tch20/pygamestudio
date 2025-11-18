# Pygame Studio

**Pygame Studio** is a modular game engine built on top of Python's `pygame` library. It allows you to create 2D (and basic 3D) games with an easy-to-use runtime, project management, and scripting system. This engine is designed to make game development accessible, structured, and flexible.

---

## Features

- **2D & 3D Game Support**
  - Native 2D rendering with Pygame
  - Optional 3D rendering and physics placeholders for future expansion
- **Project Management**
  - Easy-to-create projects with default templates
  - Asset management: images, sounds, music, shaders, tilesets, and more
- **Runtime & Core Systems**
  - Game loop with delta time management
  - Physics system, scripting engine, audio, particles, cutscenes, and camera
  - Behavior trees and AI support
- **Scripting**
  - Python-based script system for game objects
  - Example scripts included (`player_movement.py`)
- **Editor Ready**
  - Can be extended into a full editor using PySide6 (planned)
- **Configuration**
  - Default and user config system (`settings.json`)
  - Auto-generated project folders and example projects

---

## Links

[API Reference](https://github.com/ne0gl1tch20/pygamestudio/blob/main/docs/api_reference.md)

---

## Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/pygame-studio.git
cd pygame-studio
````

2. Install dependencies:

```bash
pip install pygame
```

> Future versions may require PySide6 for editor integration.

---

## Getting Started

1. Run the startup script to initialize the engine environment:

```bash
python startup.py
```

2. Open `projects/example_project/main.py` to see how the game entry point is structured.

3. Modify or add scripts in `projects/example_project/scripts/` to customize behavior.

---

## Folder Structure

```
pygame-studio/
│
├─ assets/             # Global engine assets
│  ├─ images/
│  ├─ sounds/
│  └─ ...
├─ projects/           # All user projects
│  └─ example_project/
│      ├─ assets/
│      ├─ scripts/
│      ├─ main.py
│      └─ project.json
├─ plugins/            # Optional runtime plugins
├─ logs/               # Engine logs
├─ config/             # settings.json
├─ engine/             # Core engine code
└─ startup.py          # Initialize engine environment
```

---

## Example Usage

```python
from projects.example_project import main as game_main
import pygame
from engine.core.engine_runtime import EngineRuntime
from engine.core.engine_state import EngineState

pygame.init()
screen = pygame.display.set_mode((800, 600))
state = EngineState()
runtime = EngineRuntime(screen, state)

runtime.run(game_main_module=game_main)
```

---

## Contributing

Contributions are welcome! Feel free to open issues, submit pull requests, or help extend the engine with new systems like:

* Full 3D rendering
* PySide6 editor interface
* Additional minigames or templates

---

## License

MIT License
© 2025 Your Name or Organization

---

## Notes

* Some modules are currently **mocked** for sequential generation, but they can be replaced with real implementations as the engine grows.
* The engine is designed to be fully offline and extensible, with JSON-based project saving/loading.