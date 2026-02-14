"""Exception hierarchy for kanban tracker."""


class KanbanError(Exception):
    """Base exception for all kanban errors. Exit code 1."""

    pass


# --- Not Found Errors ---


class NotFoundError(KanbanError):
    """Base for entity not found errors."""

    pass


class PlanNotFoundError(NotFoundError):
    """Plan with given ID does not exist."""

    def __init__(self, plan_id: int):
        self.plan_id = plan_id
        super().__init__(f"Plan {plan_id} not found")


class TaskNotFoundError(NotFoundError):
    """Task with given ID does not exist."""

    def __init__(self, task_id: int):
        self.task_id = task_id
        super().__init__(f"Task {task_id} not found")


class NoteNotFoundError(NotFoundError):
    """Note with given ID does not exist."""

    def __init__(self, note_id: int):
        self.note_id = note_id
        super().__init__(f"Note {note_id} not found")


class DocNotFoundError(NotFoundError):
    """LinkedDoc with given ID does not exist."""

    def __init__(self, doc_id: int):
        self.doc_id = doc_id
        super().__init__(f"Doc {doc_id} not found")


# --- Validation Errors ---


class ValidationError(KanbanError):
    """Base for validation errors."""

    pass


class InvalidStatusError(ValidationError):
    """Invalid status value provided."""

    def __init__(self, value: str, allowed: list[str]):
        self.value = value
        self.allowed = allowed
        super().__init__(f"Invalid status '{value}'. Must be: {', '.join(allowed)}")


class OrphanTaskError(ValidationError):
    """Task without a valid plan."""

    def __init__(self):
        super().__init__("Task must belong to a plan")


class DuplicateDocError(ValidationError):
    """Document already linked."""

    def __init__(self, path: str):
        self.path = path
        super().__init__(f"Document already linked: {path}")


# --- File Errors ---


class FileError(KanbanError):
    """Base for file-related errors."""

    pass


class FileNotFoundError(FileError):
    """File does not exist at path."""

    def __init__(self, path: str):
        self.path = path
        super().__init__(f"File not found: {path}")


class FileUnreadableError(FileError):
    """File exists but cannot be read."""

    def __init__(self, path: str, reason: str):
        self.path = path
        self.reason = reason
        super().__init__(f"Cannot read file {path}: {reason}")


class FileTooLargeError(FileError):
    """File exceeds size limit."""

    def __init__(self, path: str, size: int, max_size: int):
        self.path = path
        self.size = size
        self.max_size = max_size
        size_mb = size / (1024 * 1024)
        max_mb = max_size / (1024 * 1024)
        super().__init__(f"File {path} is {size_mb:.1f}MB, max is {max_mb:.1f}MB")
