# General Error Messages
INTERNAL_SERVER_ERROR = "An internal server error occurred"
NOT_FOUND = "Entity you are looking for is not found on this server"
INVALID_REQUEST = "Invalid request parameters"
UNAUTHORIZED = "Unauthorized access"
FORBIDDEN = "Access forbidden"

# Database Error Messages
DATABASE_ERROR = "Database operation failed"
DATABASE_CONNECTION_ERROR = "Database connection error"
DATABASE_QUERY_ERROR = "Database query execution failed"

# File Operation Error Messages
FILE_OPERATION_ERROR = "File operation failed"
FILE_NOT_FOUND = "File not found"
FILE_UPLOAD_ERROR = "Error uploading file"
FILE_DOWNLOAD_ERROR = "Error downloading file"
FILE_DELETE_ERROR = "Error deleting file"
FILE_CHUNK_ERROR = "Error processing file chunk"

# Discord Bot Error Messages
DISCORD_BOT_ERROR = "Discord bot operation failed"
DISCORD_CHANNEL_ERROR = "Discord channel not available"
DISCORD_MESSAGE_ERROR = "Error processing Discord message"
DISCORD_CHUNK_ERROR = "Error processing Discord chunk"

# Folder Error Messages
FOLDER_NOT_FOUND = "Folder not found"
FOLDER_CREATE_ERROR = "Error creating folder"
FOLDER_DELETE_ERROR = "Error deleting folder"
FOLDER_LIST_ERROR = "Error fetching folder list"

# Validation Error Messages
VALIDATION_ERROR = "Validation failed"
EMPTY_FOLDER_NAME = "Folder name cannot be empty"
INVALID_FILE_TYPE = "Invalid file type"
INVALID_FILE_SIZE = "Invalid file size"

# Response Messages
SUCCESS_RESPONSE = {"status": True, "message": "Operation completed successfully"}
ERROR_RESPONSE = {"status": False, "message": "Operation failed"}