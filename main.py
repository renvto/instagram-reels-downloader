from flask import Flask, request, render_template, send_file
import instaloader
import re
import os
import time
import shutil
import threading
import requests

app = Flask(__name__)

DOWNLOAD_FOLDER = "/tmp/downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

def resolve_instagram_url(url):
    if "instagram.com/share/reel/" in url:
        try:
            response = requests.get(url, allow_redirects=True)
            final_url = response.url
            return final_url
        except Exception as e:
            print(f"Error resolving URL: {e}")
            return None
    return url

def download_reel(url):
    real_url = resolve_instagram_url(url)
    if not real_url:
        return None, None, "Failed to resolve Instagram URL"
   
    match = re.search(r'instagram.com/reel/([^/?]+)', real_url)
    if not match:
        return None, None, "Invalid Instagram reel URL"
   
    shortcode = match.group(1)
    L = instaloader.Instaloader(download_videos=True)
   
    try:
        post = instaloader.Post.from_shortcode(L.context, shortcode)
        target_dir = os.path.join(DOWNLOAD_FOLDER, shortcode)
       
        if os.path.exists(target_dir):
            shutil.rmtree(target_dir, ignore_errors=True)
       
        os.makedirs(target_dir, exist_ok=True)
       
        os.chdir(DOWNLOAD_FOLDER)
        L.download_post(post, target=shortcode)
        os.chdir("..")
       
        for file in os.listdir(target_dir):
            if file.endswith(".mp4"):
                return os.path.join(target_dir, file), shortcode, None
        
        return None, None, "Video file not found after download"
    except Exception as e:
        print(f"Error downloading reel: {e}")
        return None, None, f"Error downloading reel: {str(e)}"

def delete_folder_delayed(folder_path):
    def delayed_delete():
        time.sleep(3)
        try:
            if os.path.exists(folder_path):
                shutil.rmtree(folder_path, ignore_errors=True)
                print(f"Folder removed successfully: {folder_path}")
        except Exception as e:
            print(f"Error deleting folder: {e}")
   
    thread = threading.Thread(target=delayed_delete)
    thread.daemon = True
    thread.start()

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        url = request.form.get('url')
        video_path, shortcode, error = download_reel(url)
       
        if error:
            return render_template('index.html', error=error)
       
        if video_path and os.path.exists(video_path):
            folder_path = os.path.dirname(video_path)
           
            response = send_file(
                video_path,
                as_attachment=True,
                download_name=f"instagram_reel_{shortcode}.mp4",
                conditional=True,
                mimetype='video/mp4'
            )
           
            delete_folder_delayed(folder_path)
           
            return response
        else:
            return render_template('index.html', error="Unable to download the video. Please check the URL.")
           
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)