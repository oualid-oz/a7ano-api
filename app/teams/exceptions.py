from app.core.exceptions import ResourceNotFoundException


class TeamNotFoundException(ResourceNotFoundException):
    code = "TEAM_NOT_FOUND"
    message = "Team not found."


class TeamMemberNotFoundException(ResourceNotFoundException):
    code = "TEAM_MEMBER_NOT_FOUND"
    message = "Team member not found."
