from requests import post
import base64

def get_auth(client_id, client_secret):
    headers = {
        'Authorization': f'Basic {base64.b64encode(f"{client_id}:{client_secret}".encode("ascii")).decode("ascii")}'}

    response = post(url='https://accounts.spotify.com/api/token', headers=headers, data={'grant_type': 'client_credentials'})
    return f"Bearer {response.json()['access_token']}"

    
