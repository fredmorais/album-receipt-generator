import requests
import urllib.parse
import urllib.request
import json
import math
import io
import os
import sys
import base64
from datetime import datetime
from PIL import Image, ImageFilter, ImageFont, ImageDraw




# If config file does not exist, prompt the indications to complete the configuration
if not os.path.exists("config.txt"):
    print("\nIt looks like you have not configured some settings yet! Please complete the following instructions:")
    print("\nLogin at https://developer.spotify.com/dashboard/ and create a developer account. After that, create an application and input the following details here:")
    clientId = input("\nClient id: ")
    clientSecret = input("Client secret: ")

    print("\nClick the \"Edit Settings\" button and add the following URL to your redirect uri list: http://localhost:3000")
    print("\nOpen the following link in a new window and then give permission to your application. After redirection copy the redirected url here!")
    print("\nhttps://accounts.spotify.com/authorize?client_id=" + clientId + "&response_type=code&redirect_uri=" + urllib.parse.quote("http://localhost:3000"))
    redirectedUrl = input("\nRedirected url: ")
    code = json.loads(json.dumps(urllib.parse.parse_qs(urllib.parse.urlparse(redirectedUrl)[4])))["code"][0]

    clientCode = clientId + ":" + clientSecret
    clientCodeBase64 = base64.b64encode(clientCode.encode("utf-8")).decode("utf-8")

    tokenQuery = requests.post("https://accounts.spotify.com/api/token", data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": "http://localhost:3000"
    }, headers = {
        "Authorization": "Basic " + clientCodeBase64
    })
    accessToken = json.loads(tokenQuery.text)["access_token"]
    refreshToken = json.loads(tokenQuery.text)["refresh_token"]

    createConfig = open("config.txt", "w")
    createConfig.write(accessToken + "\n" + refreshToken + "\n" + clientId + "\n" + clientSecret)
    createConfig.close()

    print("\nYou are all set! A config.txt file has been created, please do not delete it unless you want to link another Spotify Account!")
    print("\nRun the python3 generate.py command again to generate the receipt picture")
    sys.exit()

# Load authorization tokens
tokenFile = open("config.txt", "r")
tokenLines = tokenFile.readlines()
accessToken = tokenLines[0].replace("\n", "")
refreshToken = tokenLines[1].replace("\n", "")
clientId = tokenLines[2].replace("\n", "")
clientSecret = tokenLines[3].replace("\n", "")


# Ask for the album name
print("\n")
albumName = input("Please input the name of your album: ")
print("\n")


# Get the top 10 albums with the input name
headers = {'Authorization': 'Bearer ' + accessToken}
albumsQuery = requests.get("https://api.spotify.com/v1/search?q=" + urllib.parse.quote(albumName) + "&type=album&limit=10", headers=headers)
albums = json.loads(albumsQuery.text)


# Check if authorization code has expired
if albumsQuery.status_code == 401:
    clientCode = clientId + ":" + clientSecret
    clientCodeBase64 = base64.b64encode(clientCode.encode("utf-8")).decode("utf-8")
    newTokenQuery = requests.post("https://accounts.spotify.com/api/token", data = {
        "grant_type": "refresh_token",
        "refresh_token": refreshToken
    }, headers = {
        "Authorization": "Basic " + clientCodeBase64
    })
    accessToken = json.loads(newTokenQuery.text)["access_token"]
    updateConfigFile = open("config.txt", "w")
    updateConfigFile.write(accessToken + "\n" + refreshToken + "\n" + clientId + "\n" + clientSecret)
    updateConfigFile.close()

    # Run the query again
    headers = {'Authorization': 'Bearer ' + accessToken}
    albumsQuery = requests.get("https://api.spotify.com/v1/search?q=" + urllib.parse.quote(albumName) + "&type=album&limit=10", headers=headers)
    albums = json.loads(albumsQuery.text)



# Print list for user to select the right artist
print("Select the artist:")
for i, album in enumerate(albums["albums"]["items"]):
    print('#' + str(i+1) + ' : ' + album["artists"][0]["name"])
print("\n")
albumIndex = input("Whose artist is the album from? (enter the number)" + "\n")
print("\n")
# Force integer input
while True:
    try:
        val = int(albumIndex)
        break
    except ValueError:
        albumIndex = input("Please enter a integer" + "\n")
artistName = albums["albums"]["items"][int(albumIndex) - 1]["artists"][0]["name"]

# Prompt all the albums in the artist to select the right one
albumsInArtistQuery = requests.get("https://api.spotify.com/v1/search?q=" + urllib.parse.quote("album:"+albumName+" artist:"+artistName) + "&type=album&limit=10", headers=headers)
albumsInArtist = json.loads(albumsInArtistQuery.text)
if len(albumsInArtist["albums"]["items"]) > 1:
    print("Select the correct album:")
    for i, album in enumerate(albumsInArtist["albums"]["items"]):
        print('#' + str(i+1) + ' : ' + album["name"])
    print("\n")
    albumVersionIndex = input("What version do you wish to select? (enter the number and press enter)" + "\n")
    # Force integer input
    while True:
        try:
            val = int(albumVersionIndex)
            break
        except ValueError:
            albumVersionIndex = input("Please enter a integer" + "\n")
    album = albumsInArtist["albums"]["items"][int(albumVersionIndex) - 1]
else:
    album = albumsInArtist["albums"]["items"][0]

# Get the track list for the selected album
tracksQuery = requests.get("https://api.spotify.com/v1/albums/" + album["id"] + "/tracks?limit=21", headers=headers)
tracks = json.loads(tracksQuery.text)


# Confirm the track list for image creation
print("_" * 56)
print(" " * 21 + "LIST OF TRACKS")
print("‾" * 56)
print("NUMBER  NAME" + (" " * 36) + "DURATION")
for i, track in enumerate(tracks["items"]):
    seconds = str(round((track["duration_ms"]/1000)%60)).zfill(2) + "s"
    minutes = str(math.floor((track["duration_ms"]/(1000*60))%60)).zfill(2) + "m"
    duration = seconds if int(minutes.replace("m", "")) == 0 else minutes + seconds
    name = track["name"] if len(track["name"]) <= 40 else track["name"][:36] + "... "
    print('#' + str(i+1).zfill(2) + "     " + name + (" " * (40 - len(track["name"]))) + duration)
print("_" * 56)
print("‾" * 56)
print("\n")
print("Do you wish to create the picture with this tracklist? (yes/no)")
confirmation = input()
while True:
    if confirmation not in ["yes", "no"]:
        confirmation = input()
    else:
        break
if confirmation == "no":
    sys.exit()


# Create image

# Download artwork
albumArtwork = album["images"][0]["url"]
urllib.request.urlretrieve(albumArtwork, "artwork.png")

# Make background
artwork = Image.open("artwork.png").convert('RGBA').resize((1000, 1000))
filtered = artwork.filter(ImageFilter.GaussianBlur(radius=8))

# Overlay receipt
receipt = Image.open("assets/receipt.png").convert('RGBA').resize((1000, 1000))
filtered.paste(receipt, (0, 0), receipt)

# Define fonts
title = ImageFont.truetype("assets/Oswald-Bold.ttf", 36)
subtitle = ImageFont.truetype("assets/Oswald-SemiBold.ttf", 25)
normal = ImageFont.truetype("assets/Oswald-Medium.ttf", 18)
draw = ImageDraw.Draw(filtered)

# Add album name
i = 0
while True:
    if title.getsize(album["name"])[0] >= 495:
        title = ImageFont.truetype("assets/Oswald-Bold.ttf", 30 - i)
        i += 1
    else:
        break

draw.text(((1000 - title.getsize(album["name"])[0]) / 2,150), album["name"], font=title, fill=(0,0,0,255))

# Add artist name
i = 0
while True:
    if subtitle.getsize(album["artists"][0]["name"])[0] >= 400:
        subtitle = ImageFont.truetype("assets/Oswald-Bold.ttf", 30 - i)
        i += 1
    else:
        break

draw.text(((1000 - subtitle.getsize(album["artists"][0]["name"])[0]) / 2,200), album["artists"][0]["name"], font=subtitle, fill=(0,0,0,255))


heightMiddle = 250 + (500 - 80 - len(tracks["items"]) * 20) / 2

# Add date
draw.text((240, heightMiddle), datetime.now().strftime("%d %B %Y, %H:%M:%S"), font=normal, fill=(0,0,0,255))

# Add lines
heightMiddle += 15
draw.text((237, heightMiddle), "-" * 88, font=normal, fill=(0,0,0,255))

# Add tracks
heightMiddle += 30
totalDuration = 0
for i, track in enumerate(tracks["items"]):
    if i == 20:
        heightMiddle -= 8
        draw.text(((1000 - normal.getsize("......")[0]) / 2, heightMiddle), "......", font=normal, fill=(0,0,0,255))
        break
    totalDuration += track["duration_ms"]
    seconds = str(round((track["duration_ms"]/1000)%60)).zfill(2) + "s"
    minutes = str(math.floor((track["duration_ms"]/(1000*60))%60)).zfill(2) + "m"
    duration = seconds if int(minutes.replace("m", "")) == 0 else minutes + seconds
    name = track["name"] if len(track["name"]) <= 40 else track["name"][:36] + "... "
    draw.text((260, heightMiddle), str(i + 1).zfill(2), font=normal, fill=(0,0,0,255))
    draw.text((303, heightMiddle), name, font=normal, fill=(0,0,0,255))
    draw.text((685, heightMiddle), duration, font=normal, fill=(0,0,0,255))
    heightMiddle += 22

# Add lines
heightMiddle += 19
draw.text((237, heightMiddle), "-" * 88, font=normal, fill=(0,0,0,255))

# Add count
seconds = str(round((totalDuration/1000)%60)).zfill(2) + "s"
minutes = str(math.floor((totalDuration/(1000*60))%60)).zfill(2) + "m"
hours = str(math.floor((totalDuration/(1000*60*60))%60)).zfill(2) + "h"
totalDuration = minutes + seconds if int(hours.replace("h", "")) == 0 else hours + minutes + seconds

draw.text((275, 785), "Item Count:", font=subtitle, fill=(0,0,0,255))
draw.text((645 + (normal.getsize(totalDuration)[0] / 2) - (normal.getsize(str(len(tracks["items"])))[0] / 2), 785), str(len(tracks["items"])), font=subtitle, fill=(0,0,0,255))

draw.text((275, 820), "Total:", font=subtitle, fill=(0,0,0,255))
draw.text((640, 820), totalDuration, font=subtitle, fill=(0,0,0,255))

# Add details
draw.text(((1000 - normal.getsize("CS50 Final Project by Fred Morais")[0]) / 2, 870), "CS50 Final Project by Fred Morais", font=normal, fill=(0,0,0,120))


# Save picture
filtered.save("exports/" + album["name"] + ".png")
os.remove("artwork.png")