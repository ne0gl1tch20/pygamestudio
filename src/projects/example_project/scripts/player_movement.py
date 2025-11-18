# Example player movement script
def init(self):
    self.speed = 150
    self.is_jumping = False

def update(self, dt):
    input_manager = getattr(self.state, 'input_manager', None)
    if input_manager:
        velocity = getattr(self.state.utils, 'Vector2', lambda x, y: [0,0])(0,0)
        # WASD controls (mock)
        if input_manager.get_key('w'): velocity[1] -= 1
        if input_manager.get_key('s'): velocity[1] += 1
        if input_manager.get_key('a'): velocity[0] -= 1
        if input_manager.get_key('d'): velocity[0] += 1
