import logging
import spotify_recommender_api.util as util

from typing import Union
from spotify_recommender_api.song import Song
from spotify_recommender_api.playlist.base_playlist import BasePlaylist
from spotify_recommender_api.requests.api_handler import PlaylistHandler

class LikedSongs(BasePlaylist):

    def __init__(self, user_id: str, retrieval_type: str) -> None:
        super().__init__(user_id, retrieval_type, f"{user_id} Liked Songs")
        self.user_id = user_id
        self.playlist_name = f"{user_id} Liked Songs"

    @staticmethod
    def get_song_count(playlist_id: Union[str, None] = None) -> int:
        return PlaylistHandler.get_liked_songs_count()

    @staticmethod
    def get_playlist_name(playlist_id: Union[str, None] = None) -> str:
        return playlist_id


    def get_playlist_from_web(self) -> 'list[Song]':
        songs = []
        total_song_count = self.get_song_count()

        logging.info('Retrieving Liked Songs.')
        for offset in range(0, total_song_count, 50):

            util.progress_bar(offset, total_song_count, suffix=f'{offset}/{total_song_count}', percentage_precision=1)
            playlist_songs = PlaylistHandler.liked_songs(limit=50, offset=offset)

            for song in playlist_songs.json()["items"]:
                song_id, name, popularity, artists, added_at = Song.song_data(song=song)

                song_genres = Song.get_song_genres(artists=artists)

                danceability, loudness, energy, instrumentalness, tempo, valence = Song.query_audio_features(song_id=song_id)

                vader_sentiment_analysis = Song.vader_sentiment_analysis(song_name=name, artist_name=artists[0].name)

                songs.append(
                    Song(
                        name=name,
                        id=song_id,
                        tempo=tempo,
                        energy=energy,
                        valence=valence,
                        added_at=added_at,
                        loudness=loudness,
                        genres=song_genres,
                        popularity=popularity,
                        danceability=danceability,
                        instrumentalness=instrumentalness,
                        lyrics=vader_sentiment_analysis['lyrics'],
                        artists=[artist.name for artist in artists],
                        vader_sentiment=vader_sentiment_analysis['vader_sentiment'],
                    )
                )

        util.progress_bar(total_song_count, total_song_count, suffix=f'{total_song_count}/{total_song_count}', percentage_precision=1)
        print()
        logging.info('Songs mapping complete')

        return songs
