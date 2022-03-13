from requests import get, post, delete
import pandas as pd
from spotify_recommender_api.sensitive import *
from spotify_recommender_api.authentication import get_auth
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
        song_artists = song["track"]["artists"] if 'track' in list(
            song.keys()) else song["artists"]
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
        playlist = pd.DataFrame(data=list(songs))
        # , columns=['id', 'name', 'artists', 'popularity', 'genres']
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
        # print(list(map(lambda arr: arr if type(
        #     arr) != 'str' else eval(arr), [df['artists'][0], df['songs'][0], df['all_genres'][0]])))
        self.__artists, self.__songs, self.__all_genres = list(map(lambda arr: arr if type(
            arr) != 'str' else eval(arr), [df['artists'][0], df['songs'][0], df['all_genres'][0]]))

        self.__playlist = pd.read_csv('playlist.csv')

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

        return True

    def __init__(self, auth_token, user_id, playlist_id=None, playlist_url=None):
        """
        #### Spotify API is the Class that provides access to the playlists recommendations

        ## Parameters
         - auth_token: The authentication token for the Spotify API, base64 encoded string that allows the use of the API's functionalities
         - playlist_id: The playlist ID hash in Spotify
         - playlist_url: The url used while sharing the playlist
         - user_id: The user ID, visible in the Spotify profile account settings

        #### It will trigger most of the API functions and can take a good while to complete
        """
        if not auth_token:
            raise ValueError('auth_token is required')
        self.__user_id = user_id
        self.__auth_token = auth_token
        self.__headers = {"Accept": "application/json",
                          "Content-Type": "application/json", "Authorization": self.__auth_token}
        self.__artists = {}
        self.__songs = []
        self.__deny_favorites = False

        if playlist_id:
            self.__playlist_id = playlist_id
        else:
            if not playlist_url:
                raise ValueError(
                    'Either the playlist url or its id must be specified')
            self.__playlist_id = playlist_url_to_id(playlist_url)
            self.__playlist_url = playlist_url

        if self.__get_playlist():
            self.__get_playlist_items()

        self.__playlist_adjustments()
        self.__knn_prepared_data(self.__playlist)
        self.__prepare_favorites_playlist()

    def playlist_to_csv(self):
        """
        #### Function to convert playlist to CSV format
        #### Really useful if the package is being used in a .py file since it is not worth it to use it directly through web requests everytime even more when the playlist has not changed since last package usage
        """
        if not os.path.exists('./.spotify-recommender-util'):
            os.mkdir('./.spotify-recommender-util')
        df = pd.DataFrame(data=[{'artists': self.__artists, 'songs': self.__songs,
                          'all_genres': self.__all_genres}], columns=['artists', 'songs', 'all_genres'])

        df.to_parquet('./.spotify-recommender-util/util.parquet')

        playlist = self.__playlist[['id', 'name',
                                    'artists', 'genres', 'popularity']]

        playlist.to_csv('playlist.csv')

    def __genres_indexed(self, genres):
        """
        #### Function that returns the list of genres, mapped to the overall list of genres, in a binary format
        ##### Useful for the overall execution of the algorithm which determines the distance between each song

        ### Parameters
         - genres: list of genres for a given song
        """
        indexed = []
        for all_genres_x in self.__all_genres:

            continue_outer = False
            for genre in genres:
                index = all_genres_x == genre
                if index:
                    continue_outer = True
                    indexed.append(int(True))
                    break

            if continue_outer:
                continue

            indexed.append(int(False))

        return indexed

    def __artists_indexed(self, artists):
        """
        #### Function that returns the list of artists, mapped to the overall list of artists, in a binary format
        ##### Useful for the overall execution of the algorithm which determines the distance between each song

        ### Parameters
         - artists: list of artists for a given song
        """
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
        """
        Function to prepare the data for the algorithm which calculates the distances between the songs

        ### Parameters
         - df: the playlist DataFrame


        ### Note
        It will make a copy of the playlist to a list, to avoid changing the original DataFrame playlist
        And also leave it in an easier to iterate over format
        """
        data = df[['id', 'name', 'genres', 'artists',
                   'popularity', 'genres_indexed', 'artists_indexed']]
        list = []
        for index in range(len(data['id'])):
            list.append({'id': data['id'][index], 'name': data['name'][index], 'genres': data['genres'][index], 'artists': data['artists'][index],
                        'popularity': data['popularity'][index], 'genres_indexed': data['genres_indexed'][index], 'artists_indexed': data['artists_indexed'][index]})

        self.__song_dict = list

    def __list_distance(self, a, b):
        """
        The weighted algorithm that calculates the distance between two songs according to either the distance between each song list of genres or the distance between each song list of artists


        ### Note
        The "distance" is a mathematical value that represents how different two songs are considering some parameter such as their genres or artists


        ### Parameters
         - a: one song's list of genres or artists
         - b: counterpart song's list of genres or artists

        ### Note
        For obvious reasons although both the parameters have two value options (genres, artists), when one of the parameters is specified as one of those, the other follows
        """
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
        """
        The portion of the algorithm that calculates the overall distance between two songs regarding the following:
         - genres: the difference between the two song's genres, using the __list_distance function above
         - artists: the difference between the two song's artists, using the __list_distance function above
         - popularity: the difference between the two song's popularity, considering it a basic absolute value from the actual difference between the values

        At the end there is a weighted multiplication of all the factors that implies two things:
         - They are in really different scales.drop_duplicates(subset='id', keep='first')
         - They have different importance levels to the final result of the calculation


        ### Parameters
         - a: the song a, having all it's caracteristics
         - b: the song b, having all it's caracteristics
        """
        genres_distance = self.__list_distance(
            a['genres_indexed'], b['genres_indexed'])
        artists_distance = self.__list_distance(
            a['artists_indexed'], b['artists_indexed'])
        popularity_distance = abs(a['popularity'] - b['popularity'])
        return genres_distance + artists_distance * 0.38 + popularity_distance * 0.03

    def __get_neighbors(self, song, K, song_dict):
        """
        Function thats using the distance calculated above, returns the K nearest neighbors for a given song


        ### Parameters
         - song: song's index in the songs list
         - K: desired number K of neighbors to be returned
         - song_dict: the list of songs
        """
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
        """
        Function that returns the index of a given song in the list of songs

        ### Parameters
         - song: song name
        """
        if song not in list(self.__playlist['name']):
            # print(self.__playlist['name'])
            raise ValueError(f'Playlist does not contain the song {song!r}')
        item = self.__playlist[[self.__playlist['name'][x] ==
                                song for x in range(len(self.__playlist['name']))]]
        index = item.index[0]
        return index

    def __playlist_exists(self, name):
        """
        Function used to check if a playlist exists inside the user's library

        Used before the creation of a new playlist, related to a song or some term favorites

        ### Parameters
         - name: name of the playlist being created, which could easily be bypassed, if the playlist names were not made automatically
        """
        request = get('https://api.spotify.com/v1/me/playlists',
                      headers=self.__headers).json()

        playlists = list(map(lambda playlist: (
            playlist['id'], playlist['name']), request['items']))

        for playlist in playlists:
            if playlist[1] == name:
                return playlist[0]

        return False

    def __create_playlist(self, type):
        """
        Function that will return the empty playlist id, to be filled in later by the recommender songs

        This playlist may be a new one just created or a playlist that was previously created and now had all its songs removed

        ## Note:
        This function will change the user's library either making a new playlist or making a playlist empty

        ### Parameters
         - type: the type of the playlist being created ('song', 'short', 'medium'), meaning:
            --- 'song': a playlist related to a song
            --- 'short': a playlist related to the short term favorites for that given user
            --- 'medium': a playlist related to the medium term favorites for that given user
        """
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
        playlist_id_found = self.__playlist_exists(playlist_name)
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

    def __build_playlist(self, type, K, additional_info=None):
        """
        Function that fills the new playlist with the recommendations for the given type 
        type: the type of the playlist being created ('song', 'short', 'medium'):
         - 'song': a playlist related to a song
         - 'short': a playlist related to the short term favorites for that given user
         - 'medium': a playlist related to the medium term favorites for that given user

        ## Note:
        This function will change the user's library by filling the previously created empty playlist

        ### Parameters
         - type: the type of the playlist being created 
         - K: desired number K of neighbors to be returned
         - additional_info (optional): the song name when the type is 'song'


        """
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
                song_uris += f',spotify:track:{neighbor}'
        elif type in ['medium', 'short']:
            ids = self.__medium_fav['id'] if type == 'medium' else self.__short_fav['id']
            for neighbor in ids:
                song_uris += f',spotify:track:{neighbor}'

            song_uris = song_uris[1:]
        else:
            raise ValueError('Invalid type')

        add_songs_req = post(
            f'https://api.spotify.com/v1/playlists/{self.__create_playlist(type)}/tracks?uris={song_uris}', headers=self.__headers, data=json.dumps({}))
        add_songs_req.json()

    def get_recommendations_for_song(self, song, K, with_distance: bool = False, generate_csv: bool = False, generate_parquet: bool = False, build_playlist: bool = False, print_base_caracteristics: bool = False):
        """
        Playlist which centralises the actions for a recommendation made for a given song

        ## Parameters
         - song: The desired song name
         - K: desired number K of neighbors to be returned
         - with_distance (bool): Whether to allow the distance column to the DataFrame returned, which will have no actual value for most use cases, since  it does not obey any actual unit, it is just a mathematical value to determine the coset songs
         - generate_csv (bool): Whether to generate a CSV file containing the recommended playlist
         - generate_parquet (bool): Whether to generate a parquet file containing the recommended playlist
         - build_playlist (bool): Whether to build the playlist to the user's library
         - print_base_caracteristics (bool): Whether to print the base / informed song information, in order to check why such predictions were made by the algorithm

        ## Note
        The build_playlist option when set to True will change the user's library

        """
        try:
            if K > 99:
                print('K limit exceded. Maximum value for K is 99')
                K = 99
            elif K < 1:
                raise ValueError('Value for K must be between 1 and 99')

            self.__song_name = song
            df = self.__get_recommendations('song', song, K)
            playlist_name = f'{song} Related'

            if print_base_caracteristics:
                index = self.__get_index_for_song(song)
                caracteristics = self.__song_dict[index]
                name, genres, artists, popularity = list(
                    caracteristics.values())[1:5]
                print(f'{name = }\n{artists = }\n{genres = }\n{popularity = }')

            if generate_csv:
                df.to_csv(f'{playlist_name}.csv')

            if generate_parquet:
                df.to_parquet(f'{playlist_name}.parquet', compression='snappy')

            if build_playlist:
                self.__build_playlist('song', K, additional_info=song)

            if with_distance:
                return df

            return df.drop(columns=['distance'])
        except ValueError as e:
            print(e)

    def __get_desired_dict_fields(self, index):
        """
        Function that returns the usual fields for a given song

        ### Parameters
         - index: The index of the song inside the song list

        """
        dict = self.__song_dict[index]
        desired_fields = [dict['id'], dict['name'],
                          dict['artists'], dict['genres'], dict['popularity']]
        return desired_fields

    def __song_list_to_df(self, neighbors):
        """
        Function that returns DataFrame representation of the list of neighbor songs

        ### Parameters
         - neighbors: list of a given song's neighbors

        """
        data = list(
            map(lambda x: list(self.__get_desired_dict_fields(x[0]) + [x[1]]), neighbors))

        return pd.DataFrame(data=data, columns=['id', 'name', 'artists', 'genres', 'popularity', 'distance'])

    def __get_recommendations(self, type, info, K=51):
        """
        General purpose function to get recommendations for any type supported by the package

        ### Parameters
         - info: the changed song_dict list if the type is short or medium or else it is the name of the song to get recommendations from
         - K: desired number K of neighbors to be returned
         - type: the type of the playlist being created ('song', 'short', 'medium'), meaning:

            --- 'song': a playlist related to a song

            --- 'short': a playlist related to the short term favorites for that given user

            --- 'medium': a playlist related to the medium term favorites for that given user

        """
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

    def __get_genres(self, genres):
        """
        Function to unite all the genres from different songs into one list of genres


        ### Parameters
         - genres: the list of lists of genres from the different songs
        """
        try:
            all_genres = genres[0][:]
        except IndexError:
            self.__deny_favorites = True
            raise ValueError(
                'Playlist chosen does not correspond to any of the users favorite songs')

        for index in range(1, len(genres)):
            for i in range(0, len(all_genres)):
                all_genres[i] = all_genres[i] or genres[index][i]

        return all_genres

    def __get_artists(self, artists):
        """
        Function to unite all the artists from different songs into one list of artists


        ### Parameters
         - artists: the list of lists of artists from the different songs
        """
        try:
            all_artists = artists[0][:]
        except IndexError:
            raise ValueError(
                'Playlist chosen does not correspond to any of the users favorite songs')

        for index in range(1, len(artists)):
            for i in range(0, len(all_artists)):
                all_artists[i] = all_artists[i] or artists[index][i]

        return all_artists

    def __get_top_5(self, time_range='medium'):
        """
        Function that gets and initially formats the top 5 songs in a given time_range

        ### Parameters
         - time_range: The time range to get the top 5 songs from ('medium', 'short')
        """
        if time_range not in ['medium', 'short']:
            raise ValueError(
                'time_range must be either medium_term or short_term')
        top_5 = get(
            f'https://api.spotify.com/v1/me/top/tracks?time_range={time_range}_term&limit=5', headers=self.__headers).json()
        top_5_songs = list(filter(lambda song: song['name'] in list(self.__playlist['name']), list(map(lambda song: {'name': song['name'], 'genres': self.__get_song_genres(
            song), 'artists': list(map(lambda artist: artist['name'], song['artists'])), 'popularity': song['popularity']}, top_5['items']))))

        return top_5_songs

    def __prepare_fav_data(self, term):
        """
        Function that expands on the formatting of the top_5 some time_range favorites

        ### Parameters
         - time_range: The time range to get the top 5 songs from ('medium', 'short')
        """
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
        """
        Final preparation for favorite data before getting visible

        """
        song_dict = self.__song_dict[:]
        fav = self.__prepare_fav_data(type)
        song_dict.append(fav)
        return song_dict

    def get_playlist(self):
        """
        Function that returns the playlist as pandas DataFrame with the needed human readable columns
        """
        return self.__playlist[['id', 'name', 'artists', 'genres', 'popularity']]

    def get_short_term_favorites_playlist(self, with_distance: bool = False, generate_csv: bool = False, generate_parquet: bool = False, build_playlist: bool = False):
        """
        Playlist which centralises the actions for a recommendation made for top 5 songs short term

        ## Parameters
         - with_distance (bool): Whether to allow the distance column to the DataFrame returned, which will have no actual value for most use cases, since  it does not obey any actual unit, it is just a mathematical value to determine the coset songs
         - generate_csv (bool): Whether to generate a CSV file containing the recommended playlist
         - generate_parquet (bool): Whether to generate a parquet file containing the recommended playlist
         - build_playlist (bool): Whether to build the playlist to the user's library

        ## Note
        The build_playlist option when set to True will change the user's library

        """
        if self.__deny_favorites:
            print("The chosen playlist does not contain the user's favorite songs")
            return
        df = self.__short_fav
        playlist_name = 'Latest Favorites'
        if generate_csv:
            df.to_csv(f'{playlist_name}.csv')
        if generate_parquet:
            df.to_parquet(f'{playlist_name}.parquet', compression='snappy')

        if build_playlist:
            self.__build_playlist('short', 51)

        if with_distance:
            return df

        return df.drop(columns=['distance'])

    def get_medium_term_favorites_playlist(self, with_distance: bool = False, generate_csv: bool = False, generate_parquet: bool = False, build_playlist: bool = False):
        """
        Playlist which centralises the actions for a recommendation made for top 5 songs medium term

        ## Parameters
         - with_distance (bool): Whether to allow the distance column to the DataFrame returned, which will have no actual value for most use cases, since  it does not obey any actual unit, it is just a mathematical value to determine the coset songs
         - generate_csv (bool): Whether to generate a CSV file containing the recommended playlist
         - generate_parquet (bool): Whether to generate a parquet file containing the recommended playlist
         - build_playlist (bool): Whether to build the playlist to the user's library

        ## Note
        The build_playlist option when set to True will change the user's library

        """
        if self.__deny_favorites:
            print("The chosen playlist does not contain the user's favorite songs")
            return
        df = self.__medium_fav
        playlist_name = 'Recent-ish Favorites'
        if generate_csv:
            df.to_csv(f'{playlist_name}.csv')
        if generate_parquet:
            df.to_parquet(f'{playlist_name}.parquet', compression='snappy')

        if build_playlist:
            self.__build_playlist('medium', 51)

        if with_distance:
            return df

        return df.drop(columns=['distance'])

    def __prepare_favorites_playlist(self):
        """
        Automatic creation of both the favorites related recommendations
        """
        try:
            self.__short_fav = self.__get_recommendations(
                'short',  self.__end_prepared_fav_data('short'))
            self.__medium_fav = self.__get_recommendations(
                'medium',  self.__end_prepared_fav_data('medium'))
        except ValueError:
            return


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
    if playlist_url and not playlist_id:
        playlist_id = False
    if playlist_id and not playlist_url:
        playlist_url = False

    get_auth()
    auth_token = input('Paste here the auth token: ')
    while not auth_token:
        auth_token = input('Enter a valid auth token: ')

    auth_token = f'Bearer {auth_token}'

    return SpotifyAPI(auth_token=auth_token, playlist_id=playlist_id, user_id=user_id, playlist_url=playlist_url)
