from abc import ABC, abstractmethod


class BaseTask(ABC):
    """Base interface for all autonomous game mode tasks."""

    def __init__(self, name: str, priority: int, target_screen: str):
        self.name = name
        self.priority = priority
        self.target_screen = target_screen

    @abstractmethod
    def can_run(self) -> bool:
        """Return True if this task is eligible to run (e.g., has attempts left, not yet done today)."""
        pass

    @abstractmethod
    def execute(self) -> bool:
        """Run the task loop. Returns True on success, False on error/timeout."""
        pass

    def on_complete(self):
        """Hook called when task completes successfully."""
        print(f"[Task] ภารกิจ '{self.name}' เสร็จสิ้นสมบูรณ์")

    def on_error(self, error_msg: str):
        """Hook called when task encounters an unrecoverable error."""
        print(f"[Task] ภารกิจ '{self.name}' เกิดข้อผิดพลาด: {error_msg}")
