from flask import Flask, render_template, jsonify, request, redirect, url_for
import pytchat
import threading
import time
import random
import json
import os

app = Flask(__name__)

### 📂 LOKASI FILE LOKAL ###
DATA_DIR = "data"
NAMES_FILE = os.path.join(DATA_DIR, "names.json")
RANDOM_NAMES_FILE = os.path.join(DATA_DIR, "random_names.json")
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")

os.makedirs(DATA_DIR, exist_ok=True)

### 🔧 HELPER UNTUK FILE JSON ###
def load_json(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, 'r') as f:
        return json.load(f)

def save_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f)

### 🔧 FUNGSI NAMA ###
def add_name(name):
    names = load_json(NAMES_FILE, [])
    names.append(name)
    save_json(NAMES_FILE, names)

def get_names():
    return load_json(NAMES_FILE, [])

def remove_name(name_to_remove):
    names = load_json(NAMES_FILE, [])
    names = [name for name in names if name != name_to_remove]
    save_json(NAMES_FILE, names)

def get_random_names():
    return load_json(RANDOM_NAMES_FILE, [])

### 🔧 FUNGSI VIDEO ID ###
def get_video_id():
    config = load_json(CONFIG_FILE, {})
    return config.get("video_id")

def set_video_id(video_id):
    config = load_json(CONFIG_FILE, {})
    config["video_id"] = video_id
    save_json(CONFIG_FILE, config)

def delete_video_id():
    config = load_json(CONFIG_FILE, {})
    config.pop("video_id", None)
    save_json(CONFIG_FILE, config)

### 🔧 FLASK ROUTES ###
@app.route('/')
def input_page():
    return render_template("input.html")

@app.route('/set_video_id', methods=['POST'])
def set_video_id_route():
    new_id = request.form.get("video_id")
    if not new_id:
        return "No video ID provided", 400
    set_video_id(new_id)
    return redirect(url_for('index_game'))

@app.route('/game')
def index_game():
    return render_template('index.html')

@app.route('/names')
def get_names_route():
    return jsonify(get_names())

@app.route('/remove_name', methods=['POST'])
def remove_name_route():
    name = request.json.get("name")
    if name:
        remove_name(name.strip())
        return jsonify({"status": "removed"})
    return jsonify({"status": "no name provided"}), 400

### 🔄 POLLING CHAT YOUTUBE ###
def polling_chat():
    print("\U0001F680 Memulai loop polling YouTube chat...")

    while True:
        video_id = get_video_id()
        if not video_id:
            print("⏳ Menunggu video ID diatur melalui /set_video_id ...")
            time.sleep(3)
            continue

        print(f"▶️ Mulai polling chat untuk video: {video_id}")

        try:
            chat = pytchat.create(video_id=video_id)

            if not chat.is_alive():
                print("❌ Chat tidak aktif (video mungkin tidak live atau ID salah).")
                delete_video_id()
                print("🗑️ Video ID telah dihapus. Tunggu input baru.")
                time.sleep(3)
                continue

            last_message_time = time.time()

            while chat.is_alive():
                try:
                    found_chat = False
                    print("💤 Polling aktif... menunggu pesan...")

                    for c in chat.get().sync_items():
                        message = c.message.strip()
                        if len(message.split()) == 1 and len(message) <= 8:
                            print(f"✅ Simpan dari chat: {message}")
                            add_name(message)
                            found_chat = True
                            last_message_time = time.time()
                            time.sleep(10)
                        else:
                            print(f"❌ Diabaikan: {message}")

                    if not found_chat and time.time() - last_message_time >= 15:
                        random_names = get_random_names()
                        if random_names:
                            random_name = random.choice(random_names)
                            print(f"🔄 Pakai nama random: {random_name}")
                            add_name(random_name)
                            last_message_time = time.time()
                        time.sleep(10)

                except Exception as e:
                    print("❌ Error saat polling chat:", e)
                    time.sleep(5)

        except Exception as e:
            print("❌ Gagal membuat objek chat:", e)
            time.sleep(3)

        print("🔁 Kembali ke awal polling...")

### 🚀 INISIASI SAAT RUN ###
if __name__ == '__main__':
    def run_flask():
        app.run(host='0.0.0.0', port=5000)

    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    while not get_video_id():
        print("⏳ Menunggu video ID diatur melalui /set_video_id ...")
        time.sleep(2)

    polling_chat()