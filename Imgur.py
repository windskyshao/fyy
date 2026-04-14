import matplotlib
matplotlib.use('Agg')
import datetime
from imgurpython import ImgurClient
client_id =  '66e769b3bc72457'
client_secret = '5b852c0034da7d04ef3a29f47a35496996936647'
album_id = 'KU0WuRa'
access_token = '5135271236a17c01bad31ed0e7da92435ffeecf7'
refresh_token = 'ac74809a778e084b4be68a6ca07344d42350464f'

RENDER_URL = 'https://fyy-l8a3.onrender.com'

def showImgur(fileName):
    import os, shutil
    png_file = fileName + '.png'

    # 優先嘗試 Imgur
    try:
        client = ImgurClient(client_id, client_secret, access_token, refresh_token)
        config = {
            'album': album_id,
            'name': fileName,
            'title': fileName,
            'description': str(datetime.date.today())
        }
        print("[log:INFO]Uploading image to Imgur...")
        imgurl = client.upload_from_path(png_file, config=config, anon=False)['link']
        print(f"[log:INFO]Imgur upload done: {imgurl}")
        return imgurl
    except Exception as e:
        print(f"[log:WARN]Imgur failed: {e}, using local fallback")

    # Imgur 失敗，複製到 charts 資料夾用本地路由
    try:
        chart_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'charts')
        os.makedirs(chart_dir, exist_ok=True)
        dest = os.path.join(chart_dir, png_file)
        shutil.copy2(png_file, dest)
        local_url = f"{RENDER_URL}/charts/{png_file}"
        print(f"[log:INFO]Using local: {local_url}")
        return local_url
    except Exception as e:
        print(f"[log:ERROR]Local fallback also failed: {e}")
        return 'https://i.imgur.com/RFmkvQX.jpg'
