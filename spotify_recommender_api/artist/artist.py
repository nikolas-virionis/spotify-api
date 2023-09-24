from dataclasses import dataclass
from spotify_recommender_api.requests.api_handler import ArtistHandler

@dataclass
class Artist:
    """Dataclass to standardize artist handling"""

    id: str
    name: str
    genres: 'list[str]'


    @staticmethod
    def get_artist_genres(artist_id: str) -> 'list[str]':
        """Function to return an artist list of genres

        Args:
            artist_id (str): The artist id

        Returns:
            list[str]: The list of genres attached to the artist
        """
        response = ArtistHandler.get_artist(artist_id).json()

        return response['genres']



    @staticmethod
    def get_artists_genres(artists_id: 'list[str]') -> 'list[str]':
        """Function to return an artist list of genres

        Args:
            artist_id (str): The artist id

        Returns:
            list[str]: The list of genres attached to the artist
        """
        response = ArtistHandler.batch_get_artist(artists_id).json()

        genres = []
        for artist in response['artists']:
            genres += artist['genres']

        return list(set(genres))

