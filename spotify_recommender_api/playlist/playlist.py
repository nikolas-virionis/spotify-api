import logging
import spotify_recommender_api.util as util

from spotify_recommender_api.song import Song
from spotify_recommender_api.requests import PlaylistHandler
from spotify_recommender_api.playlist.base_playlist import BasePlaylist

class Playlist(BasePlaylist):

    def __init__(self, user_id: str, retrieval_type: str, playlist_id: str) -> None:
        super().__init__(user_id, retrieval_type, playlist_id)

    @staticmethod
    def get_song_count(playlist_id: str) -> int:
        return PlaylistHandler.get_playlist_total_song_count(playlist_id=playlist_id)

    @staticmethod
    def get_playlist_name(playlist_id: str) -> str:
        return util.get_base_playlist_name(playlist_id=playlist_id)

    def get_playlist_from_web(self) -> 'list[Song]':
        songs = []
        total_song_count = self.get_song_count(playlist_id=self.playlist_id)

        logging.info('Retrieving playlist songs.')
        for offset in range(0, total_song_count, 100):
            util.progress_bar(offset, total_song_count, suffix=f'{offset}/{total_song_count}', percentage_precision=1)

            song_batch = []

            playlist_songs = PlaylistHandler.playlist_songs(playlist_id=self.playlist_id, limit=100, offset=offset)

            for song in playlist_songs.json()["items"]:
                song_id, name, popularity, artists, added_at, genres = Song.song_data_batch(song)

                song_batch.append({
                    'name': name,
                    'id': song_id,
                    'genres': genres,
                    'added_at': added_at,
                    'popularity': popularity,
                    'artists': list(artists),
                })

            songs_ids = [song['track']['id'] for song in playlist_songs.json()["items"]]

            songs_audio_features = Song.batch_query_audio_features(songs_ids[:len(songs_ids)//2]) + Song.batch_query_audio_features(songs_ids[len(songs_ids)//2:])

            for song, song_audio_features in zip(song_batch, songs_audio_features):
                song.update(song_audio_features)

            songs += song_batch

        util.progress_bar(total_song_count, total_song_count, suffix=f'{total_song_count}/{total_song_count}', percentage_precision=1)
        print()
        logging.info('Songs mapping complete')

        return songs

