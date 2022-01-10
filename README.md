# spotify-api

<img src='https://storage.googleapis.com/pr-newsroom-wp/1/2018/11/Spotify_Logo_CMYK_Green.png' width='60%'>

## Context
This script, in jupyter notebook format for organization purposes, applies the technique called K Nearest Neighbors to find the 50 closest songs to either one chosen or one of the users top 5(short term), all within a specific Spotify playlist, in order to maintain the most consistency in terms of the specific chosen style, and creates a new playlist with those songs in the user's library, using their genres, artists and overall popularity as metrics to determine indexes of comparison between songs

## DISCLAIMER ##
Not fit for direct use since some information such as client id, client secret, auth token (which changes each hour or so) with the right scopes (about 10 among 20, chosen by hand), playlist id and user id, all of which are, now, in a .env so that it is not made public, have to be informed in order for the Spotify Web API to work properly
