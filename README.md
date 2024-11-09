# JBox

JBox is a web application for managing file storage and organization. It allows users to create folders, upload files, and manage them through a web interface. The application also integrates with Discord for file chunk storage and progress updates.

## Features

- Create and delete folders
- Upload and delete files
- List files in a folder
- Download files
- Real-time upload progress updates via WebSocket
- Discord integration for file chunk storage

## Project Structure

markdown
## Project Structure

```
JBox/
├── .gitignore
├── Dockerfile
├── README.md
├── requirements.txt
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── database.py
│   ├── discord_bot.py
│   ├── main.py
│   ├── models.py
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── files.py
│   │   ├── folders.py
│   │   ├── root.py
│   │   ├── status.py
│   │   ├── test_db.py
│   ├── templates/
│   │   ├── folder.html
│   │   ├── index.html
│   ├── websocket_manager.py
│   └── utils.py
```

## Installation

1. Clone the repository:
    ```sh
    git clone https://github.com/yourusername/JBox.git
    cd JBox
    ```

2. Create and activate a virtual environment:
    ```sh
    python -m venv env
    source env/bin/activate  # On Windows use `env\Scripts\activate`
    ```

3. Install the dependencies:
    ```sh
    pip install -r requirements.txt
    ```

4. Set up the environment variables:
    - Copy the `.env.example` file to `.env` in the `app/` directory:
        ```sh
        cp app/.env.example app/.env
        ```
    - Edit the [.env](http://_vscodecontentref_/2) file to include your Discord token and channel ID:
        ```
        DISCORD_TOKEN=Your-Discord-Token
        CHANNEL_ID=Your-Discord-Channel-ID
        ```

5. Run the application:
    ```sh
    uvicorn app.main:app --reload
    ```

## Usage

- Open your browser and navigate to `http://localhost:8000`.
- Use the interface to create folders, upload files, and manage your storage.

## Deployment

**Note:** This application will not work on Vercel due to its limitations with WebSocket and long-running processes. It is recommended to deploy this application on platforms like [Railway](https://railway.app/) which support these features.

## API Endpoints

### Folders

- **Create Folder**
    - `POST /create_folder/?name={folder_name}`
    - Creates a new folder with the specified name.

- **Delete Folder**
    - `DELETE /folders/{folder_name}`
    - Deletes the specified folder and all its files.

- **List Folders**
    - `GET /folders/`
    - Lists all folders.

### Files

- **Upload File**
    - `POST /upload/?folder_id={folder_id}`
    - Uploads a file to the specified folder.

- **Delete File**
    - `DELETE /files/{file_name}?folder_name={folder_id}`
    - Deletes the specified file from the folder.

- **List Files**
    - `GET /files/{folder_id}`
    - Lists all files in the specified folder.

- **Download File**
    - `GET /download/{filename}`
    - Downloads the specified file.

### Status

- **Get Status**
    - `GET /status/`
    - Returns the status of the Discord bot and channel connection.

### WebSocket

- **Progress Updates**
    - `ws://localhost:8000/ws/progress`
    - WebSocket endpoint for real-time upload progress updates.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.