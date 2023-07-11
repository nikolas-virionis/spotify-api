import requests

from typing import Any, Union
from spotify_recommender_api.requests.request_handler import RequestHandler, BASE_URL


class PlaylistHandler:

    @staticmethod
    def playlist_details(playlist_id: str) -> requests.Response:
        return RequestHandler.get_request(url=f'{BASE_URL}/playlists/{playlist_id}')

    @staticmethod
    def insert_songs_in_playlist(playlist_id: str, uris: str) -> requests.Response:
        return RequestHandler.post_request(url=f'{BASE_URL}/playlists/{playlist_id}/tracks?{uris=!s}')

    @staticmethod
    def update_playlist_details(playlist_id: str, data: 'dict[str, Any]') -> requests.Response:
        return RequestHandler.put_request(url=f'{BASE_URL}/playlists/{playlist_id}', data=data)

    @classmethod
    def get_liked_songs_count(cls) -> int:
        response = cls.liked_songs(limit=1)

        return response.json()['total']

    @classmethod
    def get_playlist_total_song_count(cls, playlist_id: str) -> int:
        response = cls.playlist_songs(playlist_id=playlist_id, limit=1)

        return response.json()['tracks']['total']

    @staticmethod
    def delete_playlist_songs(playlist_id: str, playlist_tracks: 'list[dict[str, str]]') -> requests.Response:
        return RequestHandler.delete_request(
            data={"tracks": playlist_tracks},
            url=f'{BASE_URL}/playlists/{playlist_id}/tracks',
        )

    @staticmethod
    def playlist_songs(playlist_id: str, limit: int = 100, offset: Union[int, None] = None) -> requests.Response:
        if limit > 100 or limit < 1:
            raise ValueError('Limit must be between 1 and 100')

        url = f'{BASE_URL}/playlists/{playlist_id}/tracks?{limit=!s}'

        if offset is not None:
            url += f'&{offset=!s}'

        return RequestHandler.get_request(url=url)

    @staticmethod
    def liked_songs(limit: int = 50, offset: Union[int, None] = None) -> requests.Response:
        if limit > 50 or limit < 1:
            raise ValueError('Limit must be between 1 and 50')


        url = f'{BASE_URL}/me/tracks?{limit=!s}'

        if offset is not None:
            url += f'&{offset=!s}'

        return RequestHandler.get_request(url=url)


class LibraryHandler:

    @staticmethod
    def create_playlist(user_id: str, data: 'dict[str, Any]') -> requests.Response:
        return RequestHandler.post_request(url=f'{BASE_URL}/users/{user_id}/playlists', data=data)

    @classmethod
    def get_total_playlist_count(cls) -> int:
        response = cls.library_playlists(limit=1)

        return response.json()['total']

    @staticmethod
    def library_playlists(limit: int = 50, offset: Union[int, None] = None) -> requests.Response:
        if limit > 50 or limit < 1:
            raise ValueError('Limit must be between 1 and 50')


        url = f'{BASE_URL}/me/playlists?{limit=!s}'

        if offset is not None:
            url += f'&{offset=!s}'

        return RequestHandler.get_request(url=url)


class SongHandler:

    @staticmethod
    def query_audio_features(song_id: str) -> requests.Response:
        return RequestHandler.get_request(url=f'{BASE_URL}/audio-features/{song_id}')


class UserHandler:

    @staticmethod
    def search(search_type: str, query: str, limit: int = 1) -> requests.Response:
        if search_type not in {'track', 'artist'}:
            raise ValueError('search type must be either track or artist')

        return RequestHandler.get_request(url=f'{BASE_URL}/search?q={query}&type={search_type}&{limit=!s}')

    @staticmethod
    def top_tracks(time_range: str = 'short_term', limit: int = 1) -> requests.Response:
        if time_range not in {'long_term', 'medium_term', 'short_term'}:
            raise ValueError("Time range must be one of 'long_term', 'medium_term', 'short_term'")

        return RequestHandler.get_request(url=f'{BASE_URL}/me/top/tracks?{time_range=!s}&{limit=!s}')

    @staticmethod
    def top_artists(time_range: str = 'short_term', limit: int = 1) -> requests.Response:
        if time_range not in {'long_term', 'medium_term', 'short_term'}:
            raise ValueError("Time range must be one of 'long_term', 'medium_term', 'short_term'")

        return RequestHandler.get_request(url=f'{BASE_URL}/me/top/artists?{time_range=!s}&{limit=!s}')

class ArtistHandler:

    @staticmethod
    def get_artist(artist_id: str) -> requests.Response:
        return RequestHandler.get_request(url=f'{BASE_URL}/artists/{artist_id}')
