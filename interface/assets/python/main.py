import json

from pyscript import window, document


def start(event) -> None:
    checkbox_user_id = document.querySelector("#UserID")
    checkbox_liked_songs = document.querySelector("#LikedSongs")
    checkbox_playlist_id = document.querySelector("#PlaylistID")
    checkbox_playlist_url = document.querySelector("#PlaylistUrl")

    if not (
        checkbox_liked_songs.checked
        or checkbox_playlist_id.checked
        or checkbox_playlist_url.checked
    ) and not window.confirm("Confirm to start the api without any playlist or check any of the options"):
        return

    parameters = {}

    if checkbox_user_id.checked:
        text_user_id = document.querySelector("#UserIDText")
        if not text_user_id.value:
            window.alert("Please provide a User ID or Uncheck the User ID option")
            return
        parameters['user_id'] = document.querySelector("#UserIDText").value or None

    parameters['liked_songs'] = checkbox_liked_songs.checked

    if checkbox_playlist_id.checked:
        text_playlist_id = document.querySelector("#PlaylistIDText")
        if not text_playlist_id.value:
            window.alert("Please provide a Playlist ID or Uncheck the Playlist ID option")
            return
        parameters['playlist_id'] = text_playlist_id.value or None

    if checkbox_playlist_url.checked:
        text_playlist_url = document.querySelector("#UPlaylistUrlText")
        if not text_playlist_url.value:
            window.alert("Please provide a Playlist URL or Uncheck the Playlist URL option")
            return
        parameters['playlist_url'] = text_playlist_url.value or None

    window.localStorage.setItem('spotify-recommender-setup', json.dumps(parameters))

    if window.localStorage.getItem('spotify-recommender-token'):
        pass

    window.location.href = "features.html"
