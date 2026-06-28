from app.core.exceptions import ResourceNotFoundException


class ProjectNotFoundException(ResourceNotFoundException):
    code = "PROJECT_NOT_FOUND"
    message = "Project not found."


class ProjectTagNotFoundException(ResourceNotFoundException):
    code = "PROJECT_TAG_NOT_FOUND"
    message = "Project tag not found."


class ProjectAssigneeNotFoundException(ResourceNotFoundException):
    code = "PROJECT_ASSIGNEE_NOT_FOUND"
    message = "Project assignee not found."
