from app.core.exceptions import AuthorizationException, ResourceNotFoundException


class VaultEntryNotFoundException(ResourceNotFoundException):
    code = "VAULT_ENTRY_NOT_FOUND"
    message = "Vault entry not found."


class VaultCategoryNotFoundException(ResourceNotFoundException):
    code = "VAULT_CATEGORY_NOT_FOUND"
    message = "Vault category not found."


class VaultShareNotFoundException(ResourceNotFoundException):
    code = "VAULT_SHARE_NOT_FOUND"
    message = "Vault share not found."


class VaultAccessDeniedException(AuthorizationException):
    code = "VAULT_ACCESS_DENIED"
    message = "You do not have permission to access this vault entry."
