import spotify_recommender_api.util as util

from spotify_recommender_api.song.song import Song


class SongUtil:
    """Class for utility methods regarding song operations"""

    @staticmethod
    def _build_song_objects(recommendations: dict, dict_key: str = 'tracks') -> 'list[Song]':
        """Builds a list of Song objects from the recommendations data.

        Args:
            recommendations (dict): Recommendations data.
            dict_key (str, optional): Key to access the song data in the recommendations dictionary. Defaults to 'tracks'.

        Returns:
            list[Song]: List of Song objects.
        """
        songs = []

        for songs_chunk in util.chunk_list(recommendations[dict_key], 50):

            song_batch = []
            for song in songs_chunk:
                song_id, name, popularity, artists, _, genres = Song.song_data_batch(song=song)

                vader_sentiment_analysis = Song.vader_sentiment_analysis(song_name=name, artist_name=artists[0])

                song_batch.append({
                    'name': name,
                    'id': song_id,
                    'genres': genres,
                    'popularity': popularity,
                    'lyrics': vader_sentiment_analysis['lyrics'],
                    'artists': [artist for artist in artists],
                    'vader_sentiment': vader_sentiment_analysis['vader_sentiment'],
                })

            songs_ids = [song['id'] for song in songs_chunk]

            songs_audio_features = Song.batch_query_audio_features(songs_ids)

            for song, song_audio_features in zip(song_batch, songs_audio_features):
                song.update(song_audio_features)

            songs += song_batch


        return songs
