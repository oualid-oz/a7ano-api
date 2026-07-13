from app.core.exceptions import ResourceNotFoundException


class TaskNotFoundException(ResourceNotFoundException):
    code = "TASK_NOT_FOUND"
    message = "Task not found."
