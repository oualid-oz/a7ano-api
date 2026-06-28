from typing import Any

DEFAULT_PERMISSIONS = [
    ("organization:create", "organization", "create"),
    ("organization:read", "organization", "read"),
    ("organization:update", "organization", "update"),
    ("organization:delete", "organization", "delete"),
    ("team:create", "team", "create"),
    ("team:read", "team", "read"),
    ("team:update", "team", "update"),
    ("team:delete", "team", "delete"),
    ("project:create", "project", "create"),
    ("project:read", "project", "read"),
    ("project:update", "project", "update"),
    ("project:delete", "project", "delete"),
    ("memo:create", "memo", "create"),
    ("memo:read", "memo", "read"),
    ("memo:update", "memo", "update"),
    ("memo:delete", "memo", "delete"),
    ("vault:create", "vault", "create"),
    ("vault:read", "vault", "read"),
    ("vault:update", "vault", "update"),
    ("vault:delete", "vault", "delete"),
    ("user:manage", "user", "manage"),
    ("role:manage", "role", "manage"),
]

DEFAULT_ROLES: dict[str, dict[str, Any]] = {
    "super_admin": {
        "description": "Full platform access",
        "permissions": [name for name, _, _ in DEFAULT_PERMISSIONS],
    },
    "organization_admin": {
        "description": "Manage an organization",
        "permissions": [
            "organization:*",
            "team:*",
            "project:*",
            "user:manage",
            "memo:*",
            "vault:*",
        ],
    },
    "team_admin": {
        "description": "Manage a team",
        "permissions": [
            "team:read",
            "team:update",
            "project:*",
            "memo:*",
            "vault:*",
        ],
    },
    "project_manager": {
        "description": "Manage projects",
        "permissions": [
            "project:*",
            "team:read",
            "memo:*",
            "vault:read",
            "vault:update",
        ],
    },
    "member": {
        "description": "Regular organization member",
        "permissions": [
            "organization:read",
            "team:read",
            "project:read",
            "project:update",
            "memo:*",
            "vault:read",
        ],
    },
    "guest": {
        "description": "Read-only guest",
        "permissions": [
            "organization:read",
            "team:read",
            "project:read",
            "memo:read",
            "vault:read",
        ],
    },
}
