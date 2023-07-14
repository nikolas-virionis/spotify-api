import datetime
import functools

from typing import Any
from dataclasses import dataclass, field
from spotify_recommender_api.artist import Artist
from spotify_recommender_api.requests.api_handler import SongHandler

@dataclass(frozen=True)
class Song:
    """Represents a song with its attributes and data."""

    id: str
    name: str
    popularity: int
    danceability: float
    loudness: float
    energy: float
    instrumentalness: float
    tempo: float
    valence: float
    genres: 'list[str]' = field(default_factory=list)
    artists: 'list[str]' = field(default_factory=list)
    added_at: datetime.datetime = datetime.datetime.now()
    genres_indexed: 'list[int]' = field(default_factory=list, repr=False)
    artists_indexed: 'list[int]' = field(default_factory=list, repr=False)


    @staticmethod
    def get_song_genres(artists: 'list[Artist]') -> 'list[str]':
        """Get the unique genres from a list of artists.

        Args:
            artists (list[Artist]): List of artists.

        Returns:
            list[str]: List of unique genres.
        """
        genres = functools.reduce(lambda acc, artist: acc + artist.genres, artists, [])

        return list(set(genres))

    @staticmethod
    def query_audio_features(song_id: str) -> 'tuple[float, ...]':
        """Query the audio features of a song.

        Args:
            song_id (str): ID of the song.

        Returns:
            tuple[float, ...]: Tuple of audio features.
        """
        audio_features = SongHandler.query_audio_features(song_id).json()

        return (
            audio_features['danceability'],
            audio_features['loudness'] / -60,
            audio_features['energy'],
            audio_features['instrumentalness'],
            audio_features['tempo'],
            audio_features['valence']
        )

    @staticmethod
    def song_data(song: 'dict[str, Any]') -> 'tuple[str, str, int, list[Artist], datetime.datetime]':
        """Extract relevant data from a song dictionary.

        Args:
            song (dict[str, Any]): Song data dictionary.

        Returns:
            tuple[str, str, int, list[Artist], datetime.datetime]: Tuple of song data.
        """
        if "track" in song:
            song = song['track']

        return (
            song['id'],
            song['name'],
            song['popularity'],
            [
                Artist(
                    id=artist['id'],
                    name=artist['name'],
                    genres=Artist.get_artist_genres(artist['id'])
                )
                for artist in song.get("artists", [])
            ],
            song.get('added_at', datetime.datetime.now()),
        )

