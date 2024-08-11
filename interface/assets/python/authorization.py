import json
import requests

from pyscript import window, document

query_params = {
    k: v
    for k, v in [
        i.split('=')
        for i in window.location.href.split('?')[1].split('&')
    ]
}


auth_code = query_params.get('code')

with open('../security/spotify.json', 'r') as f:
    spotify_credentials = json.load(f)

    client_id = spotify_credentials['client_id']
    redirect_uri = spotify_credentials['redirect_uri']
    client_secret = spotify_credentials['client_secret']
    if "localhost" in window.location.href or "127.0.0" in window.location.href:
        redirect_uri = "http://127.0.0.1:5500/spotify-api/interface/authorization.html"

    auth_req = requests.post(
        auth=(client_id, client_secret),
        url="https://accounts.spotify.com/api/token",
        data={
            "code": auth_code,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        },
    ).json()

    auth_token = auth_req['access_token']
    refresh_token = auth_req['refresh_token']

    window.localStorage.setItem('spotify-recommender-token', auth_token)
    window.localStorage.setItem('spotify-recommender-refresh-token', refresh_token)

    window.close()

