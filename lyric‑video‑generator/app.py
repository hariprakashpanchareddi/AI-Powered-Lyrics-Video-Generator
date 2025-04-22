# app.py
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__,
            static_folder='.',
            static_url_path='')

@app.route('/')
def index():
    # serve index.html from project root
    return send_from_directory('.', 'index.html')

@app.route('/generate', methods=['POST'])
def generate():
    audio = request.files.get('audio')
    lyrics = request.files.get('lyrics')
    video_name = request.form.get('videoName')

    # print all received inputs to the console
    print(f"Received audio file:   {audio.filename if audio else 'None'}")
    print(f"Received lyrics file:  {lyrics.filename if lyrics else 'None'}")
    print(f"Received video name:   {video_name!r}")

    # return a minimal JSON so your existing script.js can parse it
    return jsonify({
        "video_url": "",
        "caption_url": ""
    })

if __name__ == '__main__':
    # by default runs on http://127.0.0.1:5000
    app.run(debug=True)
