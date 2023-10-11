import logging
import datetime
import functools
import lyricsgenius

from typing import Any
from dataclasses import dataclass, field
from spotify_recommender_api.artist import Artist
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from spotify_recommender_api.requests.api_handler import SongHandler
from spotify_recommender_api.server.sensitive import GENIUS_ACCESS_TOKEN

vader_sentiment_analyser = SentimentIntensityAnalyzer()
genius = lyricsgenius.Genius(
    retries=5,
    sleep_time=0,
    verbose=False,
    remove_section_headers=True,
    access_token=GENIUS_ACCESS_TOKEN,
)


@dataclass(frozen=True)
class Song:
    """Represents a song with its attributes and data."""

    id: str
    name: str
    popularity: int
    danceability: float = 0
    loudness: float = 0
    energy: float = 0
    instrumentalness: float = 0
    tempo: float = 0
    valence: float = 0
    lyrics: str = ''
    vader_sentiment: float = 0
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
    def batch_query_audio_features(song_ids: 'list[str]') -> 'list[dict[str, float | int]]':
        """Query the audio features of a song.

        Args:
            song_ids (list[str]): IDs of the songs.

        Returns:
            tuple[float, ...]: Tuple of audio features.
        """
        response = SongHandler.batch_query_audio_features(song_ids).json()

        return [
            {
                'danceability': audio_features['danceability'],
                'loudness': audio_features['loudness'] / -60,
                'energy': audio_features['energy'],
                'instrumentalness': audio_features['instrumentalness'],
                'tempo': audio_features['tempo'],
                'valence': audio_features['valence']
            }
            for audio_features in response['audio_features']
        ]

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

    @staticmethod
    def song_data_batch(song: 'dict[str, Any]') -> 'tuple[str, str, int, list[Artist], datetime.datetime]':
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
                artist['name']
                for artist in song.get("artists", [])
            ],
            song.get('added_at', datetime.datetime.now()),
            Artist.get_artists_genres([artist['id'] for artist in song.get("artists", [])])
        )

    @staticmethod
    def vader_sentiment_analysis(song_name: str, artist_name: str) -> 'tuple[str, float]':
        genius_song = None

        for _ in range(5):
            if genius_song is not None:
                break
            try:
                genius_song = genius.search_song(song_name, artist_name, get_full_info=False)
            except Exception as e:
                logging.warning(f'Error while searching for song lyrics on genius: {e}')
                genius_song = None

        if genius_song is None:
            return {
                'lyrics': '',
                'vader_sentiment': 0
            }

        lyrics = '\n'.join(genius_song.lyrics.split('\n')[1:])

        vader_analysis = vader_sentiment_analyser.polarity_scores(lyrics)

        return {
            'lyrics': lyrics,
            'vader_sentiment': vader_analysis['compound']
        }