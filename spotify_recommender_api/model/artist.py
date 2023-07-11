from dataclasses import dataclass
from spotify_recommender_api.requests.api_handler import ArtistHandler

@dataclass
class Artist:
    id: str
    name: str
    genres: 'list[str]'


    @staticmethod
    def get_artist_genres(artist_id: str) -> 'list[str]':
        response = ArtistHandler.get_artist(artist_id).json()

        return response['genres']

