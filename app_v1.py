import streamlit as st
import os
import tempfile
import requests
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, APIC, error
from mutagen.mp3 import MP3

def search_deezer(query):
    url = f"https://api.deezer.com/search?q={query}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json().get('data', [])
    return []

def download_cover(url):
    response = requests.get(url)
    if response.status_code == 200:
        return response.content
    return None

def tag_mp3(file_bytes, title, artist, album, year, cover_data):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
        tmp_file.write(file_bytes.read())
        tmp_path = tmp_file.name

    audio = EasyID3(tmp_path)
    audio['title'] = title
    audio['artist'] = artist
    audio['album'] = album
    audio['date'] = str(year)
    audio.save()

    mp3 = MP3(tmp_path, ID3=ID3)
    try:
        mp3.add_tags()
    except error:
        pass

    if cover_data:
        mp3.tags.add(
            APIC(
                encoding=3,
                mime='image/jpeg',
                type=3,
                desc='Cover',
                data=cover_data
            )
        )
        mp3.save()

    return tmp_path

st.title("🎵 MP3 Tagger with Deezer")

uploaded_file = st.file_uploader("Upload an MP3 file", type="mp3")

if uploaded_file:
    filename = uploaded_file.name
    name_base = os.path.splitext(filename)[0]
    parts = name_base.split(" - ")

    if len(parts) == 2:
        artist_guess, title_guess = parts
    else:
        artist_guess, title_guess = "", name_base

    st.markdown(f"**Guessed Title:** `{title_guess}`  \n**Guessed Artist:** `{artist_guess}`")

    query = st.text_input("Edit Search Query", f"{artist_guess} {title_guess}")
    if st.button("🔍 Search Deezer"):
        results = search_deezer(query)
        if results:
            options = [
                f"{track['title']} by {track['artist']['name']} (Album: {track['album']['title']})"
                for track in results[:5]
            ]
            choice = st.radio("Select the correct track:", options)
            selected = results[options.index(choice)]

            st.session_state["selected_track"] = selected
        else:
            st.warning("No results found.")

if "selected_track" in st.session_state and uploaded_file:
    selected = st.session_state["selected_track"]
    if st.button("🎯 Tag MP3"):
        with st.spinner("Tagging file..."):
            cover_data = download_cover(selected['album']['cover_big'])
            tagged_path = tag_mp3(
                uploaded_file,
                title=selected['title'],
                artist=selected['artist']['name'],
                album=selected['album']['title'],
                year=selected.get('release_date', '2025')[:4],
                cover_data=cover_data
            )

            with open(tagged_path, "rb") as f:
                st.success("File tagged successfully!")
                st.download_button(
                    label="⬇️ Download Tagged MP3",
                    data=f.read(),
                    file_name=filename,
                    mime="audio/mpeg"
                )
            os.remove(tagged_path)
