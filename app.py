from flask import Flask, redirect, request, session, url_for, render_template, jsonify
import requests
from openai import OpenAI
import os
import json
from urllib.parse import quote
from dotenv import load_dotenv

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Use a secure secret key

client = OpenAI()
# Spotify OAuth settings

load_dotenv()

CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
REDIRECT_URI = os.getenv('REDIRECT_URI')
AUTH_URL = 'https://accounts.spotify.com/authorize'
TOKEN_URL = 'https://accounts.spotify.com/api/token'


def filter_json(json_data):
    session['track_names'] = []
    filtered_data = {}
    # Add only necessary fields to the new dictionary
    filtered_data['items'] = []
    for item in json_data['items']:
        if 'name' not in item:
            filtered_item = {}
            session['track_names'].append(
                (item['track']['name'], item['track']['id']))
            filtered_item['name'] = item['track']['name']
            filtered_item['artists'] = ", ".join(
                [artist['name'] for artist in item['track']['artists']])
            filtered_item['popularity'] = item['track']['popularity']
            filtered_data['items'].append(filtered_item)
            continue
        filtered_item = {}
        filtered_item['name'] = item['name']
        session['track_names'].append((item['name'], item['id']))
        filtered_item['artists'] = ", ".join(
            [artist['name'] for artist in item['artists']])
        filtered_item['popularity'] = item['popularity']
        # Add any other fields you need here...

        filtered_data['items'].append(filtered_item)
    return filtered_data


def fetch_user_data():
    access_token = session['access_token']  # Get access token from the session
    if access_token is None:
        session.clear()
        return redirect(url_for('index'))
    headers = {
        'Authorization': f'Bearer {access_token}',
    }

    # Fetch user's top tracks
    time_ranges = ['short_term', 'medium_term', 'long_term']
    top_tracks = {}
    for time_range in time_ranges:
        top_tracks_response = requests.get(
            f'https://api.spotify.com/v1/me/top/tracks?limit=20&time_range={time_range}', headers=headers)
        top_tracks[time_range] = filter_json(top_tracks_response.json())

    # Fetch user's recently played tracks
    recently_played_response = requests.get(
        'https://api.spotify.com/v1/me/player/recently-played?limit=20', headers=headers)
    recently_played = filter_json(recently_played_response.json())

    # Format the data into a string
    user_data = "My top tracks for the last month are: " + \
        json.dumps(top_tracks['short_term'])
    user_data += "My top track from the last 6 months are: " + \
        json.dumps(top_tracks['medium_term'])
    user_data += "My top track from the last year are: " + \
        json.dumps(top_tracks['long_term'])
    user_data += ". My recently played tracks are: " + \
        json.dumps(recently_played)

    return user_data


@app.route('/')
def index():
    session.pop('previous_messages', None)
    session.pop('init_user_data', None)
    if 'access_token' in session:
        return render_template('chat.html')
    return render_template('index.html')


@app.route('/login')
def login():
    scope = 'user-top-read user-read-recently-played'
    auth_query = {
        'response_type': 'code',
        'redirect_uri': REDIRECT_URI,
        'client_id': CLIENT_ID,
        'scope': scope,
        'show_dialog': 'true',
    }
    query_params = "&".join(
        [f"{key}={quote(str(val))}" for key, val in auth_query.items()])
    return redirect(f"{AUTH_URL}?{query_params}")


@app.route('/callback')
def callback():
    code = request.args.get('code')
    auth_payload = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': REDIRECT_URI,
        'client_id': CLIENT_ID,
        # You need the client secret to get the access token
        'client_secret': CLIENT_SECRET,
    }
    response = requests.post(
        'https://accounts.spotify.com/api/token', data=auth_payload)
    response_data = response.json()
    session['access_token'] = response_data['access_token']
    return redirect(url_for('index'))


@app.route('/send_message', methods=['POST'])
def send_message():

    if session.get('init_user_data') is None:
        session['init_user_data'] = fetch_user_data()
    message = request.json.get('message')

    # Get the previous messages from the session
    previous_messages = session.get('previous_messages', [])

    # Add the new user message to the previous messages
    previous_messages.append({"role": "user", "content": message})
    init_user_data = session['init_user_data']
    # Generate a response
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are here to review the user's music taste, but you are grumpy and harsh. You answer responses one thing at a time, brief and sharp and snarky with puns, and are informal with text message responses that use aave and informal grammar, oftentimes not even capitalizing. provide examples and review tracks so you can make the user feel bad. you are slightly inclined towards more meaningful, message driven, soulful songs and lyrical rap. never end the conversation"},
            {"role": "assistant", "content": init_user_data},
            *previous_messages,
        ],
        max_tokens=100
    )

    # Store the assistant's response in the session
    previous_messages.append(
        {"role": "assistant", "content": response.choices[0].message.content})

    # Keep only the last 50 messages
    previous_messages = previous_messages[-50:]

    session['previous_messages'] = previous_messages
    return jsonify(response=response.choices[0].message.content)


@app.route('/tracks')
def tracks():
    global track_names
    return jsonify(track_names)


@app.route('/get_song_embed', methods=['POST'])
def get_song_embed():
    data = request.json
    message = data.get('message')
    if not message:
        return jsonify({'song_embed_url': None})

    song_artist_pairs = identify_song_titles_and_artists(message)
    print(song_artist_pairs)
    if song_artist_pairs == []:
        return jsonify({'song_embed_url': None})
    song_title, artist = song_artist_pairs[0]
    song_title = song_title.strip()
    artist = artist.strip()

    # Check if the song title is in track_names
    for track in track_names:
        if track[0].lower() == song_title.lower():
            return jsonify({'song_embed_url': f'https://open.spotify.com/embed/track/{track[1]}'})

    headers = {'Authorization': 'Bearer ' + session['access_token']}
    params = {'q': f'track:{song_title} artist:{
        artist}', 'type': 'track', 'limit': 1}
    response = requests.get(
        'https://api.spotify.com/v1/search', headers=headers, params=params)
    response.raise_for_status()
    tracks = response.json()['tracks']['items']
    if tracks:
        song_id = tracks[0]['id']
        return jsonify({'song_embed_url': f'https://open.spotify.com/embed/track/{song_id}'})
    else:
        return jsonify({'song_embed_url': None})


def identify_song_titles_and_artists(message):
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system",
                "content": "You are a helpful assistant. What song titles and their artists are mentioned in this text? Be concise and clear, list the first song title and artists. Split by commas for songs, like 'Song by Artist, Song2 by Artist2' ignore features If there are no songs, just try you best. be concise, not sentences"},
            {"role": "user", "content": message},
        ],
        max_tokens=100
    )
    print(response.choices[0].message.content)
    song_artist_pairs = response.choices[0].message.content.split(',')
    song_artist_pairs = [(pair.split(' by ')[0].strip(), ' by '.join(pair.split(
        ' by ')[1:]).strip()) for pair in song_artist_pairs if ' by ' in pair]
    return song_artist_pairs

# sign out route that clears the session


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True)
