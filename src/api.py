from requests import get, post, delete
import pandas as pd
from sensitive import *
from auth import get_auth
import operator
import json
from functools import reduce
import os


def playlist_url_to_id(url):
    uri = url.split('?')[0]
    id = uri.split('open.spotify.com/playlist/')[1]
    return id


class SpotifyAPI:
    """
    ### Spotify API is the Class that provides access to the playlists recommendations
    """

    def __get_total_song_count(self):
        """
        Function returns the total number of songs in the playlist
        """
        playlist_res = get(
            f'https://api.spotify.com/v1/playlists/{self.__playlist_id}', headers=self.__headers)
        return playlist_res.json()["tracks"]["total"]

    def __add_genres(self, list, genres):
        """
        Function represents a way to have only unique values for a given list while constantly appending new genre values

        ## Parameters
         - list: the overall, big, complete, list of genres
         - the possibly new genre values
        """
        for genre in genres:
            if genre not in list:
                list.append(genre)

        return list

    def __get_song_genres(self, song):
        """
        Function that gets all the genres for a given song

        ## Parameters
         - song: the song dictionary
        """
        genres = []
        song_artists = song["track"]["artists"] if 'track' in list(song.keys()) else song["artists"]
        for artist in song_artists:
            id = artist["id"]
            if id not in self.__artists:
                artist_genres_res = get(
                    f'https://api.spotify.com/v1/artists/{id}', headers=self.__headers)
                try:
                    artist_genres = artist_genres_res.json()["genres"]
                except Exception:
                    print(artist_genres_res.json())
                genres = self.__add_genres(genres, artist_genres)
                self.__artists[artist["name"]] = artist_genres
            else:
                genres = self.__add_genres(genres, self.__artists[id])

        return genres

    def __song_data(self, song):
        """
        Function that gets additional information about the song
        like its name, artists, id, popularity

        ## Parameters
         - song: the song raw dictionary
        """
        return song["track"]['id'], song["track"]['name'], song["track"]['popularity'], [artist["name"] for artist in song["track"]["artists"]]

    def __get_playlist_items(self):
        """
        Function that gets the items (songs) inside the playlist

        ## Note
        Ran automatically but can last as long as 2.5 seconds for each song (can be worse depending on the network connection) inside of te playlist, not because it is compute demanding but because it needs to do a up to a bunch of http requests per song, which can take a while

        """
        self.__all_genres = []
        for offset in range(0, self.__get_total_song_count(), 100):
            all_genres_res = get(
                f'https://api.spotify.com/v1/playlists/{self.__playlist_id}/tracks?limit=100&offset={offset}', headers=self.__headers)
            for song in all_genres_res.json()["items"]:
                (id, name, popularity, artist), song_genres = self.__song_data(
                    song), self.__get_song_genres(song)
                self.__songs.append({"id": id, "name": name, "artists": artist,
                                     "popularity": popularity, "genres": song_genres})
                self.__all_genres = self.__add_genres(
                    self.__all_genres, song_genres)

    def __playlist_adjustments(self):
        """
        Function that does a bunch of adjustments to the overall formatting of the playlist, before making it visible

        """
        songs = self.__songs[-self.__get_total_song_count():]
        self.__all_artists = list(self.__artists.keys())
        playlist = pd.DataFrame(data=songs, columns=[
            'id', 'name', 'artists', 'popularity', 'genres'])
        playlist["genres_indexed"] = [self.__genres_indexed(eval(playlist["genres"][x]) if type(
            playlist["genres"][x]) == 'str' else playlist["genres"][x]) for x in range(len(playlist["genres"]))]
        playlist["artists_indexed"] = [self.__artists_indexed(eval(playlist["artists"][x]) if type(
            playlist["artists"][x]) == 'str' else playlist["artists"][x]) for x in range(len(playlist["artists"]))]
        self.__playlist = playlist

    def __get_playlist_from_csv(self):
        """
        Function that creates the playlist variable from a CSV file previouusly created by this same API

        """
        df = pd.read_parquet('./.spotify-recommender-util/util.parquet')

        self.__artists, self.__songs, self.__all_genres = list(map(lambda arr: arr if type(
            arr) == 'str' else eval(arr), df['artists'][0], df['songs'][0], df['all_genres'][0]))

        self.__playlist = pd.read_csv('playlist.csv')

    def __get_playlist_from_parquet(self):
        """
        "Secret" dev function that creates the playlist variable from a parquet file, in a hidden folder, previouusly created by this same API, so that in dev it was not necessary to make the thousans of http requests al the times there was a test. Now the challenge is open for you to try to find the way to get thi playlist to run

        """
        df = pd.read_parquet('./.spotify-recommender-util/util.parquet')

        self.__artists, self.__songs, self.__all_genres = list(map(lambda arr: arr if type(
            arr) == 'str' else eval(arr), df['artists'][0], df['songs'][0], df['all_genres'][0]))

        self.__all_artists = list(self.__artists.keys())
        self.__playlist = pd.read_parquet(
            './.spotify-recommender-util/playlist.parquet')

    def __get_playlist(self):
        """
        General purpose function to get the playlist, either from CSV or web requests

        """
        answer = input(
            'Do you want to get the playlist data via CSV saved previously or read from spotify, *which will take a few minutes* depending on the playlist size (csv/web)? ')
        while answer.lower() not in ['csv', 'web', 'parquet']:
            answer = input("Please select a valid response: ")
        if answer.lower() == 'csv':
            self.__get_playlist_from_csv()
            return False
        if answer.lower() == 'parquet':
            self.__get_playlist_from_parquet()
            return False

        return True

    def __playlist_to_parquet(self):
        """
        Backup dev automatic function that saves the playlist as a parquet file inside a hidden directory

        """
        if not os.path.exists('./.spotify-recommender-util'):
            os.mkdir('./.spotify-recommender-util')

        df = pd.DataFrame(data=[{'artists': self.__artists, 'songs': self.__songs,
                          'all_genres': self.__all_genres}], columns=['artists', 'songs', 'all_genres'])

        df.to_parquet('./.spotify-recommender-util/util.parquet')

        self.__playlist[['id', 'name', 'artists', 'genres', 'popularity', 'genres_indexed', 'artists_indexed']].to_parquet('./.spotify-recommender-util/playlist.parquet')

    def __init__(self, auth_token, user_id, playlist_id=None, playlist_url=None):
        if not auth_token:
            raise ValueError('auth_token is required')
        self.__user_id = user_id
        self.__auth_token = auth_token
        self.__headers = {"Accept": "application/json",
                          "Content-Type": "application/json", "Authorization": self.__auth_token}
        self.__artists = {}
        self.__songs = []

        if self.__get_playlist():
            if playlist_id:
                self.__playlist_id = playlist_id
            else:
                if not playlist_url:
                    raise ValueError(
                        'Either the playlist url or its id must be specified')
                self.__playlist_id = playlist_url_to_id(playlist_url)
                self.__playlist_url = playlist_url

            self.__get_playlist_items()
            self.__playlist_adjustments()
            self.__playlist_to_parquet()

        self.__knn_prepared_data(self.__playlist)
        self.__prepare_favorites_playlist()

    def playlist_to_csv(self):
        if not os.path.exists('./.spotify-recommender-util'):
            os.mkdir('./.spotify-recommender-util')
        df = pd.DataFrame(data=[{'artists': self.__artists, 'songs': self.__songs,
                          'all_genres': self.__all_genres}], columns=['artists', 'songs', 'all_genres'])

        df.to_parquet('./.spotify-recommender-util/util.parquet')

        self.__playlist[['id', 'name', 'artists', 'genres', 'popularity']].drop_duplicates(
            keep='first').to_csv('playlist.csv', header=True, index=None)

    def __genres_indexed(self, genres):
        indexed = []
        for all_genres_x in self.__all_genres:

            continue_outer = False
            for genre in genres:
                index = all_genres_x == genre
                if index:
                    'clipboard'
            if continue_outer:
                continue

            indexed.append(int(False))

        return indexed

    def __artists_indexed(self, artists):
        indexed = []
        for all_artists_x in self.__all_artists:

            continue_outer = False
            for genre in artists:
                index = all_artists_x == genre
                if index:
                    continue_outer = True
                    indexed.append(int(True))
                    break

            if continue_outer:
                continue

            indexed.append(int(False))

        return indexed

    def __knn_prepared_data(self, df):
        data = df[['id', 'name', 'genres', 'artists',
                   'popularity', 'genres_indexed', 'artists_indexed']]
        list = []
        for index in range(len(data['id'])):
            list.append({'id': data['id'][index], 'name': data['name'][index], 'genres': data['genres'][index], 'artists': data['artists'][index],
                        'popularity': data['popularity'][index], 'genres_indexed': data['genres_indexed'][index], 'artists_indexed': data['artists_indexed'][index]})

        self.__song_dict = list

    def __list_distance(self, a, b):
        distance = 0
        for item_a, item_b in list(zip(a, b)):
            if item_a != item_b:
                if int(item_a) == 1:
                    distance += 0.4
                else:
                    distance += 0.2
            else:
                if int(item_a) == 1:
                    distance -= 0.4

        return distance

    def __compute_distance(self, a, b):
        genres_distance = self.__list_distance(
            a['genres_indexed'], b['genres_indexed'])
        artists_distance = self.__list_distance(
            a['artists_indexed'], b['artists_indexed'])
        popularity_distance = abs(a['popularity'] - b['popularity'])
        return genres_distance + artists_distance * 0.4 + (popularity_distance * 0.005)

    def __get_neighbors(self, song, K, song_dict):
        distances = []
        for song_index, song_value in enumerate(song_dict):
            if (song_index != song):
                dist = self.__compute_distance(song_dict[song], song_value)
                distances.append((song_index, dist))
        distances.sort(key=operator.itemgetter(1))
        neighbors = []
        for x in range(K):
            neighbors.append([*distances[x]])
        return neighbors

    def __get_index_for_song(self, song):
        if len(self.__playlist['name'][self.__playlist['name'] == song] == 0):
            raise ValueError(f'Playlist does not contain the song {song!r}')
        item = self.__playlist[[self.__playlist['name'][x] ==
                                song for x in range(len(self.__playlist['name']))]]
        index = item.index[0]
        return index

    def get_recommendations_for_song(self, song, K, with_distance: bool = False, generate_csv: bool = False, generate_parquet: bool = False):
        try:
            if K > 99:
                print('K limit exceded. Maximum value for K is 99')
                K = 99
            elif K < 1:
                raise ValueError('Value for K must be between 1 and 99')


            df = self.__get_recommendations('song', song, K)
            playlist_name = f'{song} Related'
            if generate_csv:
                df.to_csv(f'{playlist_name}.csv')
            if generate_parquet:
                df.to_parquet(f'{playlist_name}.parquet', compression='snappy')

            if with_distance:
                return df

            return df.drop(columns=['distance'])
        except ValueError as e:
            print(e)

    def __get_desired_dict_fields(self, index):
        dict = self.__song_dict[index]
        desired_fields = [dict['id'], dict['name'],
                          dict['artists'], dict['genres'], dict['popularity']]
        return desired_fields

    def __song_list_to_df(self, neighbors):
        data = list(
            map(lambda x: list(self.__get_desired_dict_fields(x[0]) + [x[1]]), neighbors))

        return pd.DataFrame(data=data, columns=['id', 'name', 'artists', 'genres', 'popularity', 'distance'])

    def __get_recommendations(self, type, info, K=50):
        index = 0
        if type == 'song':
            index = self.__get_index_for_song(info)
        elif type in ['medium', 'short']:
            index = len(info) - 1
        else:
            raise ValueError('Type does not correspond to a valid option')
        song_dict = self.__song_dict if type == 'song' else info
        neighbors = self.__get_neighbors(index, K, song_dict)
        return self.__song_list_to_df(neighbors)

    def playlist_exists(self, name):
        request = get('https://api.spotify.com/v1/me/playlists',
                      headers=self.__headers).json()

        playlists = list(map(lambda playlist: (
            playlist['id'], playlist['name']), request['items']))

        for playlist in playlists:
            if playlist[1] == name:
                return playlist[0]

        return False

    def __create_playlist(self, type):
        playlist_name = ''
        description = ''
        if type == 'song':
            playlist_name = f"{self.__song_name!r} Related"
            description = f"Songs related to {self.__song_name!r}"
        elif type in ['short', 'medium']:
            playlist_name = "Recent-ish Favorites" if type == 'medium' else "Latest Favorites"
            description = f"Songs related to your {type} term top 5"
        else:
            raise ValueError('type not valid')
        new_id = ""
        playlist_id_found = self.playlist_exists(playlist_name)
        if playlist_id_found:
            new_id = playlist_id_found

            playlist_tracks = list(map(lambda track: {'uri': track['track']['uri']}, get(
                f'https://api.spotify.com/v1/playlists/{new_id}/tracks', headers=self.__headers).json()['items']))

            delete_json = delete(f'https://api.spotify.com/v1/playlists/{new_id}/tracks',
                                 headers=self.__headers, data=json.dumps({"tracks": playlist_tracks})).json()
                                 
        else:
            data = {"name": playlist_name,
                    "description": description, "public": False}
            playlist_creation = post(
                f'https://api.spotify.com/v1/users/{self.__user_id}/playlists', headers=self.__headers, data=json.dumps(data))
            new_id = playlist_creation.json()['id']
        return new_id

    def build_playlist(self, type, additional_info, K):
        if K > 99:
            print('K limit exceded. Maximum value for K is 99')
            K = 99
        elif K < 1:
            raise ValueError('Value for K must be between 1 and 99')
        song_uris = ''
        if type == 'song':
            index = self.__get_index_for_song(additional_info)
            song_uris = f'spotify:track:{self.__song_dict[index]["id"]}'
            for neighbor in self.__get_recommendations('song', additional_info, K)['id']:
                song_uris += f',spotify:track:{self.__song_dict[neighbor]["id"]}'
        elif type in ['medium', 'short']:
            for neighbor in self[f'__{type}_fav']['id']:
                song_uris += f',spotify:track:{neighbor}'

            song_uris = song_uris[1:]
        else:
            raise ValueError('Invalid type')

        add_songs_req = post(
            f'https://api.spotify.com/v1/playlists/{self.__create_playlist(type)}/tracks?uris={song_uris}', headers=self.__headers, data=json.dumps({}))
        add_songs_req.json()

    def __get_genres(self, genres):
        try:
            all_genres = genres[0][:]
        except IndexError:
            raise ValueError('Playlist chosen does not correspond to any of the users favorite songs')

        for index in range(1, len(genres)):
            for i in range(0, len(all_genres)):
                all_genres[i] = all_genres[i] or genres[index][i]

        return all_genres

    def __get_artists(self, artists):
        all_artists = artists[0][:]

        for index in range(1, len(artists)):
            for i in range(0, len(all_artists)):
                all_artists[i] = all_artists[i] or artists[index][i]

        return all_artists

    def __get_top_5(self, time_range='medium'):
        if time_range not in ['medium', 'short']:
            raise ValueError(
                'time_range must be either medium_term or short_term')
        top_5 = get(
            f'https://api.spotify.com/v1/me/top/tracks?time_range={time_range}_term&limit=5', headers=self.__headers).json()
        top_5_songs = list(filter(lambda song: song['name'] in list(self.__playlist['name']), list(map(lambda song: {'name': song['name'], 'genres': self.__get_song_genres(
            song), 'artists': list(map(lambda artist: artist['name'], song['artists'])), 'popularity': song['popularity']}, top_5['items']))))

        return top_5_songs

    def __prepare_fav_data(self, term):
        top_5_songs = self.__get_top_5(term)
        
        temp_genres = list(reduce(lambda acc, x: acc +
                                  list(set(x['genres']) - set(acc)), top_5_songs, []))
        temp_artists = list(reduce(
            lambda acc, x: acc + list(set(x['artists']) - set(acc)), top_5_songs, []))
        latest_fav = {'id': "", 'name': "Recent-ish Favorites" if type ==
                      'medium' else "Latest Favorites", 'genres': temp_genres, 'artists': temp_artists}

        latest_fav['genres_indexed'] = self.__get_genres(
            list(map(lambda song: self.__genres_indexed(song['genres']), top_5_songs)))

        latest_fav['artists_indexed'] = self.__get_artists(
            list(map(lambda song: self.__artists_indexed(song['artists']), top_5_songs)))

        latest_fav['popularity'] = int(reduce(
            lambda acc, song: acc + int(song['popularity']), top_5_songs, 0) / len(top_5_songs))

        return latest_fav

    def __end_prepared_fav_data(self, type):
        song_dict = self.__song_dict[:]
        fav = self.__prepare_fav_data(type)
        song_dict.append(fav)
        return song_dict

    def get_playlist(self):
        return self.__playlist[['id', 'name', 'artists', 'genres', 'popularity']]

    def get_short_term_favorites_playlist(self, with_distance: bool = False, generate_csv: bool = False, generate_parquet: bool = False):
        df = self.__short_fav
        playlist_name = 'Latest Favorites'
        if generate_csv:
            df.to_csv(f'{playlist_name}.csv')
        if generate_parquet:
            df.to_parquet(f'{playlist_name}.parquet', compression='snappy')

        if with_distance:
            return df
        else:
            return df.drop(columns=['distance'])

    def get_medium_term_favorites_playlist(self, with_distance: bool = False, generate_csv: bool = False, generate_parquet: bool = False):
        df = self.__medium_fav
        playlist_name = 'Recent-ish Favorites'
        if generate_csv:
            df.to_csv(f'{playlist_name}.csv')
        if generate_parquet:
            df.to_parquet(f'{playlist_name}.parquet', compression='snappy')

        if with_distance:
            return df

        return df.drop(columns=['distance'])

    def __prepare_favorites_playlist(self):
        self.__short_fav = self.__get_recommendations(
            'short',  self.__end_prepared_fav_data('short'))
        self.__medium_fav = self.__get_recommendations(
            'medium',  self.__end_prepared_fav_data('medium'))


def start_api(user_id, playlist_url=None, playlist_id=None):
    """
    ### Function that prepares for and initializes the API
    
    ## Note: 
    Internet Connection is required
    
    
    # Parameters:
     - user_id: the id of user, present in the user account profile
     - playlist_url(optional): the url for the playlist, which is visible when trying to share it
     - playlist_id (optional): the id of the playlist, an unique big hash which identifies the playlist

    ## Note:
    Although both the playlist_url and playlist_id are optional, one of them is required, though the choice is up to you
    
    """
    if not playlist_url and not playlist_id:
        raise ValueError(
            'It is necessary to specify a playlist either with playlist id or playlist url')
    get_auth()
    auth_token = input('Paste here the auth token: ')
    while not auth_token:
        auth_token = input('Enter a valid auth token: ')

    auth_token = f'Bearer {auth_token}'

    return SpotifyAPI(auth_token=auth_token, playlist_id=playlist_id, user_id=user_id, playlist_url=playlist_url)
