# spotify-api

<img src='https://storage.googleapis.com/pr-newsroom-wp/1/2018/11/Spotify_Logo_CMYK_Green.png' width='60%'>

## Context
This script, in jupyter notebook format for organization purposes, applies the technique called K Nearest Neighbors to find the 50 closest songs to either one chosen or one of the users top 5(short term), all within a specific Spotify playlist, in order to maintain the most consistency in terms of the specific chosen style, and creates a new playlist with those songs in the user's library, using their genres, artists and overall popularity as metrics to determine indexes of comparison between songs

### Variations
There are also 2 variations from that, which consist of medium term favorites related top 100 and "short term top 5" related top 50 songs. They vary from OG model since the base song(s) is(are) not chosen by hand but statistically

## DISCLAIMER ##
Not fit for direct use since some information such as client id, client secret, both of which are, now, in a hidden script on .gitignore so that it is not made public, have to be informed in order for the Spotify Web API to work properly
And also, these scripts are deprecated, so they will not have any maintenance or overtime improvements
