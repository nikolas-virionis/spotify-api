import datetime
import functools

from typing import Any, Union
from dataclasses import dataclass, field
from spotify_recommender_api.model.artist import Artist
from spotify_recommender_api.requests.api_handler import APIHandler

@dataclass(frozen=True)
class Song:
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
    def get_song_genres(artists: 'list[Artist]'):
        genres = functools.reduce(lambda acc, artist: acc + artist.genres, artists, [])

        return list(set(genres))

    @staticmethod
    def query_audio_features(song_id: str) -> 'tuple[float, ...]':
        audio_features = APIHandler.query_audio_features(song_id).json()

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
                    genres=artist['genres']
                )
                for artist in song.get("artists", [])
            ],
            song.get('added_at', datetime.datetime.now()),
        )