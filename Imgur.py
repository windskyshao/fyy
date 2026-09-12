import matplotlib
matplotlib.use('Agg')
import datetime
import os          # 讀環境變數用(金鑰不再寫在程式碼裡)
from imgurpython import ImgurClient
client_id = os.environ.get('IMGUR_CLIENT_ID', '')
client_secret = os.environ.get('IMGUR_CLIENT_SECRET', '')
album_id = 'KU0WuRa'
access_token = os.environ.get('IMGUR_ACCESS_TOKEN', '')
refresh_token = os.environ.get('IMGUR_REFRESH_TOKEN', '')
RENDER_URL = 'https://fyy-l8a3.onrender.com'

def showImgur(fileName):
    import os, shutil
    png_file = fileName + '.png'

    # 優先使用本地路由（穩定）
    try:
        chart_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'charts')
        os.makedirs(chart_dir, exist_ok=True)
        dest = os.path.join(chart_dir, png_file)
        shutil.copy2(png_file, dest)
        local_url = f"{RENDER_URL}/charts/{png_file}"
        print(f"[log:INFO]Using local: {local_url}")
        return local_url
    except Exception as e:
        print(f"[log:WARN]Local failed: {e}, trying Imgur")

    # 本地失敗，備援用 Imgur（沒設定環境變數就略過：金鑰已移出公開程式碼，見檔頭說明）
    if not (client_id and client_secret and access_token and refresh_token):
        print("[log:WARN]Imgur keys not configured (env), skip fallback")
        return None
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
        print(f"[log:ERROR]Imgur also failed: {e}")
        return None
