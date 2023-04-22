
import time
import uvicorn
import threading
import webbrowser
import contextlib
from fastapi import FastAPI, status
from fastapi.responses import HTMLResponse
from spotify_recommender_api.sensitive import *
from spotify_recommender_api.request_handler import *
app = FastAPI()

redirect_uri = 'http://localhost:8000/callback'
scope = ["playlist-modify-private", "playlist-read-private", "user-library-read", "user-library-modify", "user-top-read"]

class Server(uvicorn.Server):
    """Subclass of uvicorn.Server so that the run and shutdown methods can be done while running in a separate thread

    """
    def install_signal_handlers(self):
        pass

    @contextlib.contextmanager
    def run_in_thread(self):
        """Method to run the server in a separate thread using the context manager
        """
        thread = threading.Thread(target=self.run)
        thread.start()
        try:
            while not self.started:
                time.sleep(1e-3)
            yield
        finally:
            self.should_exit = True
            thread.join()


def up_server():
    """Function to start the fastapi server and wait for the callback request from spotify to complete, to get the access token the shutdown the server
    """
    config = uvicorn.Config(app=app, host="127.0.0.1", port=8000)
    server = Server(config=config)

    with server.run_in_thread():
        webbrowser.open_new_tab('http://localhost:8000/')
        while True:
            try:
                with open('./.spotify-recommender-util/execution-status.txt', 'r') as f:
                    auth_status = f.readline()
            except Exception as e:
                pass
            else:
                break

def get_access_token(auth_code: str) -> str:
    """Funciton to request for the access token request

    Args:
        auth_code (str): Temporary code to have access to the access token

    Returns:
        str: Access token
    """
    response = post_request_with_auth(
        "https://accounts.spotify.com/api/token",
        auth=(CLIENT_ID, CLIENT_SECRET),
        data={
            "grant_type": "authorization_code",
            "code": auth_code,
            "redirect_uri": redirect_uri,
        },
    )

    return response.json()["access_token"]

@app.get("/", status_code=status.HTTP_200_OK)
async def auth():
    """Primary function to request for the auth code to get the token later on

    Returns:
        fastapi.responses.HTMLResponse: HTML page to trigger the authentication
    """
    auth_url = f"https://accounts.spotify.com/authorize?response_type=code&client_id={CLIENT_ID}&redirect_uri={redirect_uri}&scope={' '.join(scope)}"
    return HTMLResponse(content=f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Spotify Recommender</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {{
                    background-color: #191414;
                    font-family: 'Helvetica Neue', sans-serif;
                    color: white;
                    margin: 0;
                    padding: 0;
                }}

                .header {{
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    padding: 1rem;
                    background-color: #282828;
                    height: 4rem;
                }}

                .header h1 {{
                    font-size: 2rem;
                    margin: auto;
                    padding: auto;
                }}

                a {{
                    display: block;
                    background-color: #1DB954;
                    color: white;
                    padding: 1.5rem 4rem;
                    text-align: center;
                    text-decoration: none;
                    border-radius: 2rem;
                    margin: 4rem auto 0;
                    max-width: 25rem;
                    font-size: 1.5rem;
                    font-weight: bold;
                }}

                a:hover {{
                    background-color: #1ED760;
                    cursor: pointer;
                }}
            </style>
        </head>
        <body>
            <header class="header">
                <h1>Spotify</h1>
            </header>
            <a href="{auth_url}">Authorize</a>
        </body>
        </html>
    ''')


@app.get("/callback", status_code=status.HTTP_200_OK)
async def callback(code: str):
    """Callback endpoint to get the access token and store it in a temporary file for later use

    Args:
        code (str): Auth code to have access to the access token

    Returns:
        fastapi.responses.HTMLResponse: HTML page to close the web page after the retrieval of the access token
    """

    token = get_access_token(code)

    with open('./.spotify-recommender-util/execution.txt', 'w') as f:
        f.write(token)

    with open('./.spotify-recommender-util/execution-status.txt', 'w') as f:
        f.write('SUCEDDED')

    return HTMLResponse(content='''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Spotify Recommender</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {
                    background-color: #191414;
                    font-family: 'Helvetica Neue', sans-serif;
                    color: white;
                    margin: 0;
                    padding: 0;
                }

                .header {
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    padding: 1rem;
                    background-color: #282828;
                    height: 4rem;
                }

                .header h1 {
                    font-size: 2rem;
                    margin: auto;
                    padding: auto;
                }

                .message {
                    position: absolute;
                    top: 50%;
                    left: 50%;
                    transform: translate(-50%, -50%);
                    font-size: 1.5rem;
                    text-align: center;
                    color: white;
                }
            </style>
        </head>
        <body>
            <header class="header">
                <h1>Spotify</h1>
            </header>
            <div class="message">
                <p>You may close this window now and return to your script</p>
            </div>
        </body>
        </html>
    ''')

