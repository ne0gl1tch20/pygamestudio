# engine/utils/timer.py
import time
import sys

# Attempt to import core dependencies, use minimal mocks if they fail
try:
    from engine.utils.file_utils import FileUtils
except ImportError:
    class FileUtils:
        @staticmethod
        def log_message(msg): print(f"[TIMER-INFO] {msg}")


class Timer:
    """
    A simple utility class for measuring elapsed time, controlling intervals, 
    and timing code execution blocks.
    """
    
    def __init__(self, duration: float = 1.0, is_looping: bool = False):
        self.duration = duration    # The target duration in seconds
        self.is_looping = is_looping # True if the timer automatically resets
        self.start_time = time.time()
        self.is_running = True
        self.is_finished = False
        self._elapsed_time = 0.0

    def start(self):
        """Starts or resets the timer."""
        self.start_time = time.time()
        self.is_running = True
        self.is_finished = False
        self._elapsed_time = 0.0

    def pause(self):
        """Pauses the timer, preserving the elapsed time."""
        if self.is_running:
            self._elapsed_time += time.time() - self.start_time
            self.is_running = False

    def unpause(self):
        """Resumes the timer from where it was paused."""
        if not self.is_running and not self.is_finished:
            self.start_time = time.time()
            self.is_running = True

    def reset(self):
        """Resets the timer to 0.0 elapsed time."""
        self.start_time = time.time()
        self.is_running = False
        self.is_finished = False
        self._elapsed_time = 0.0
        
    def check(self) -> bool:
        """
        Updates the timer and checks if the duration has been reached. 
        Auto-resets if is_looping is True.
        """
        if not self.is_running:
            return False

        current_time = time.time()
        self._elapsed_time = (current_time - self.start_time)

        if self.get_elapsed_time() >= self.duration:
            self.is_finished = True
            if self.is_looping:
                # Reset the start time by subtracting the duration (for frame accuracy)
                self.start_time += self.duration
                self.is_finished = False # Ready for next loop
            else:
                self.is_running = False # Stop non-looping timer
            return True
            
        return False

    def get_elapsed_time(self) -> float:
        """Returns the total elapsed time in seconds."""
        if self.is_running:
            return self._elapsed_time + (time.time() - self.start_time)
        return self._elapsed_time
        
    def get_time_ratio(self) -> float:
        """Returns the elapsed time as a ratio of the total duration (0.0 to 1.0)."""
        if self.duration == 0: return 0.0
        return min(1.0, self.get_elapsed_time() / self.duration)
        
    @staticmethod
    def measure_execution(func: callable, *args, **kwargs) -> tuple[float, any]:
        """
        Static method to measure the execution time of a function.
        Returns (time_in_seconds, function_return_value).
        """
        start = time.time()
        try:
            result = func(*args, **kwargs)
            end = time.time()
            duration = end - start
            FileUtils.log_message(f"Function '{func.__name__}' executed in {duration:.4f}s.")
            return duration, result
        except Exception as e:
            FileUtils.log_error(f"Error during timed execution of '{func.__name__}': {e}")
            return -1.0, None