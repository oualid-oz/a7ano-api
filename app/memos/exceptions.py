from app.core.exceptions import ResourceNotFoundException


class MemoNotFoundException(ResourceNotFoundException):
    code = "MEMO_NOT_FOUND"
    message = "Memo not found."


class MemoFolderNotFoundException(ResourceNotFoundException):
    code = "MEMO_FOLDER_NOT_FOUND"
    message = "Memo folder not found."


class MemoTagNotFoundException(ResourceNotFoundException):
    code = "MEMO_TAG_NOT_FOUND"
    message = "Memo tag not found."
