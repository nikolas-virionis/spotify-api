import datetime
import functools

from typing import Any, Union
from dataclasses import dataclass, field
from spotify_recommender_api.artist import Artist
from spotify_recommender_api.requests.api_handler import SongHandler

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


    @staticmethod
    def _build_song_objects(recommendations: dict, dict_key: str = 'tracks') -> 'list[Song]':
        """Builds a list of Song objects from the recommendations data.

        Args:
            recommendations (dict): Recommendations data.

        Returns:
            List[Song]: List of Song objects.
        """
        songs = []

        for song in recommendations[dict_key]:
            song_id, name, popularity, artists, _ = Song.song_data(song=song)
            song_genres = Song.get_song_genres(artists=artists)

            danceability, loudness, energy, instrumentalness, tempo, valence = Song.query_audio_features(song_id=song_id)

            songs.append(
                Song(
                    name=name,
                    id=song_id,
                    tempo=tempo,
                    energy=energy,
                    valence=valence,
                    loudness=loudness,
                    genres=song_genres,
                    popularity=popularity,
                    danceability=danceability,
                    instrumentalness=instrumentalness,
                    artists=[artist.name for artist in artists],
                )
            )

        return songs
