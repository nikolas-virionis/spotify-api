import requests

from typing import Any, Union
from spotify_recommender_api.requests.request_handler import RequestHandler, BASE_URL


class PlaylistHandler:
    """Class for handling Spotify playlist-related API requests."""

    @staticmethod
    def playlist_details(playlist_id: str) -> requests.Response:
        """
        Get details of a playlist.

        Args:
            playlist_id (str): The ID of the playlist.

        Returns:
            requests.Response: The response object containing playlist details.
        """
        return RequestHandler.get_request(url=f'{BASE_URL}/playlists/{playlist_id}')

    @staticmethod
    def insert_songs_in_playlist(playlist_id: str, uris: str) -> requests.Response:
        """
        Insert songs into a playlist.

        Args:
            playlist_id (str): The ID of the playlist.
            uris (str): The string containing the URIs of the songs.

        Returns:
            requests.Response: The response object indicating the success of the request.
        """
        return RequestHandler.post_request(url=f'{BASE_URL}/playlists/{playlist_id}/tracks?{uris=!s}')

    @staticmethod
    def update_playlist_details(playlist_id: str, data: 'dict[str, Any]') -> requests.Response:
        """
        Update the details of a playlist.

        Args:
            playlist_id (str): The ID of the playlist.
            data (dict[str, Any]): The updated data for the playlist.

        Returns:
            requests.Response: The response object indicating the success of the request.
        """
        return RequestHandler.put_request(url=f'{BASE_URL}/playlists/{playlist_id}', data=data)

    @classmethod
    def get_liked_songs_count(cls) -> int:
        """
        Get the total count of liked songs.

        Returns:
            int: The total count of liked songs.
        """
        response = cls.liked_songs(limit=1)
        return response.json()['total']

    @classmethod
    def get_playlist_total_song_count(cls, playlist_id: str) -> int:
        """
        Get the total count of songs in a playlist.

        Args:
            playlist_id (str): The ID of the playlist.

        Returns:
            int: The total count of songs in the playlist.
        """
        response = cls.playlist_songs(playlist_id=playlist_id, limit=1)
        return response.json()['total']

    @staticmethod
    def delete_playlist_songs(playlist_id: str, playlist_tracks: 'list[dict[str, str]]') -> requests.Response:
        """
        Delete songs from a playlist.

        Args:
            playlist_id (str): The ID of the playlist.
            playlist_tracks (list[dict[str, str]]): The list of tracks to be deleted.

        Returns:
            requests.Response: The response object indicating the success of the request.
        """
        return RequestHandler.delete_request(
            data={"tracks": playlist_tracks},
            url=f'{BASE_URL}/playlists/{playlist_id}/tracks',
        )

    @staticmethod
    def playlist_songs(playlist_id: str, limit: int = 100, offset: Union[int, None] = None) -> requests.Response:
        """
        Get the songs in a playlist.

        Args:
            playlist_id (str): The ID of the playlist.
            limit (int): The maximum number of songs to retrieve. Default is 100.
            offset (Union[int, None]): The offset value for pagination. Default is None.

        Returns:
            requests.Response: The response object containing the playlist songs.
        """
        if limit > 100 or limit < 1:
            raise ValueError('Limit must be between 1 and 100')

        url = f'{BASE_URL}/playlists/{playlist_id}/tracks?{limit=!s}'

        if offset is not None:
            url += f'&{offset=!s}'

        return RequestHandler.get_request(url=url)

    @staticmethod
    def liked_songs(limit: int = 50, offset: Union[int, None] = None) -> requests.Response:
        """
        Get the liked songs of the user.

        Args:
            limit (int): The maximum number of songs to retrieve. Default is 50.
            offset (Union[int, None]): The offset value for pagination. Default is None.

        Returns:
            requests.Response: The response object containing the liked songs.
        """
        if limit > 50 or limit < 1:
            raise ValueError('Limit must be between 1 and 50')

        url = f'{BASE_URL}/me/tracks?{limit=!s}'

        if offset is not None:
            url += f'&{offset=!s}'

        return RequestHandler.get_request(url=url)


class LibraryHandler:
    """Class for handling Spotify library-related API requests."""

    @staticmethod
    def create_playlist(user_id: str, data: 'dict[str, Any]') -> requests.Response:
        """
        Create a new playlist.

        Args:
            user_id (str): The ID of the user.
            data (dict[str, Any]): The data for creating the playlist.

        Returns:
            requests.Response: The response object containing the newly created playlist.
        """
        return RequestHandler.post_request(url=f'{BASE_URL}/users/{user_id}/playlists', data=data)

    @classmethod
    def get_total_playlist_count(cls) -> int:
        """
        Get the total count of playlists in the user's library.

        Returns:
            int: The total count of playlists.
        """
        response = cls.library_playlists(limit=1)
        return response.json()['total']

    @staticmethod
    def library_playlists(limit: int = 50, offset: Union[int, None] = None) -> requests.Response:
        """
        Get the playlists in the user's library.

        Args:
            limit (int): The maximum number of playlists to retrieve. Default is 50.
            offset (Union[int, None]): The offset value for pagination. Default is None.

        Returns:
            requests.Response: The response object containing the library playlists.
        """
        if limit > 50 or limit < 1:
            raise ValueError('Limit must be between 1 and 50')

        url = f'{BASE_URL}/me/playlists?{limit=!s}'

        if offset is not None:
            url += f'&{offset=!s}'

        return RequestHandler.get_request(url=url)


class SongHandler:
    """Class for handling Spotify song-related API requests."""

    @staticmethod
    def query_audio_features(song_id: str) -> requests.Response:
        """
        Query audio features of a song.

        Args:
            song_id (str): The ID of the song.

        Returns:
            requests.Response: The response object containing the audio features of the song.
        """
        return RequestHandler.get_request(url=f'{BASE_URL}/audio-features/{song_id}')

    @staticmethod
    def batch_query_audio_features(song_ids: 'list[str]') -> requests.Response:
        """
        Query audio features of a song.

        Args:
            song_ids (list[str]): The ID of the song.

        Returns:
            requests.Response: The response object containing the audio features of the song.
        """
        if len(song_ids) > 100:
            raise ValueError('song_ids must be a list with at most 100 items')

        ids = ','.join(song_ids)

        return RequestHandler.get_request(url=f'{BASE_URL}/audio-features?{ids=!s}')


class UserHandler:
    """Class for handling Spotify user-related API requests."""

    @staticmethod
    def search(search_type: str, query: str, limit: int = 1) -> requests.Response:
        """
        Search for tracks or artists.

        Args:
            search_type (str): The type of search. Must be either 'track' or 'artist'.
            query (str): The search query.
            limit (int): The maximum number of results to retrieve. Default is 1.

        Returns:
            requests.Response: The response object containing the search results.
        """
        if search_type not in {'track', 'artist'}:
            raise ValueError('search type must be either track or artist')

        return RequestHandler.get_request(url=f'{BASE_URL}/search?q={query}&type={search_type}&{limit=!s}')

    @staticmethod
    def top_tracks(time_range: str = 'short_term', limit: int = 1) -> requests.Response:
        """
        Get the user's top tracks.

        Args:
            time_range (str): The time range for the top tracks. Must be one of 'long_term', 'medium_term', 'short_term'.
                Default is 'short_term'.
            limit (int): The maximum number of tracks to retrieve. Default is 1.

        Returns:
            requests.Response: The response object containing the user's top tracks.
        """
        if time_range not in {'long_term', 'medium_term', 'short_term'}:
            raise ValueError("Time range must be one of 'long_term', 'medium_term', 'short_term'")

        return RequestHandler.get_request(url=f'{BASE_URL}/me/top/tracks?{time_range=!s}&{limit=!s}')

    @staticmethod
    def top_artists(time_range: str = 'short_term', limit: int = 1) -> requests.Response:
        """
        Get the user's top artists.

        Args:
            time_range (str): The time range for the top artists. Must be one of 'long_term', 'medium_term', 'short_term'.
                Default is 'short_term'.
            limit (int): The maximum number of artists to retrieve. Default is 1.

        Returns:
            requests.Response: The response object containing the user's top artists.
        """
        if time_range not in {'long_term', 'medium_term', 'short_term'}:
            raise ValueError("Time range must be one of 'long_term', 'medium_term', 'short_term'")

        return RequestHandler.get_request(url=f'{BASE_URL}/me/top/artists?{time_range=!s}&{limit=!s}')


class ArtistHandler:
    """Class for handling Spotify artist-related API requests."""

    @staticmethod
    def get_artist(artist_id: str) -> requests.Response:
        """
        Get details of an artist.

        Args:
            artist_id (str): The ID of the artist.

        Returns:
            requests.Response: The response object containing artist details.
        """
        return RequestHandler.get_request(url=f'{BASE_URL}/artists/{artist_id}')

    @staticmethod
    def batch_get_artist(artist_ids: 'list[str]') -> requests.Response:
        """
        Get details of an artist.

        Args:
            artist_ids (list[str]): The ID of the artist.

        Returns:
            requests.Response: The response object containing artist details.
        """
        if len(artist_ids) > 50:
            raise ValueError('artist_ids must be a list with at most 50 items')

        ids = ','.join(artist_ids)

        return RequestHandler.get_request(url=f'{BASE_URL}/artists?{ids=!s}')
