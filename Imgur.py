import matplotlib
matplotlib.use('Agg')
import datetime
from imgurpython import ImgurClient
client_id =  '66e769b3bc72457'
client_secret = '5b852c0034da7d04ef3a29f47a35496996936647'
album_id = 'KU0WuRa'
access_token = '5135271236a17c01bad31ed0e7da92435ffeecf7'
refresh_token = 'ac74809a778e084b4be68a6ca07344d42350464f'

def showImgur(fileName):
    #conect imgur
    client = ImgurClient(client_id, client_secret, access_token, refresh_token)

    #params
    config = {
        'album': album_id, #album name
        'name': fileName, # pics name
        'title':fileName, #pics title
        'description': str(datetime.date.today())
        }
    #Upload file
    try:
        print("[log:INFO]Uploading image...")
        imgur = client.upload_from_path(fileName+'.png', config=config, anon=False)['link']
        #string to dict
        print("[log:INFO]Done upload. ")
    except:
        # if faild to upload
        imgurl = 'https://i.imgur.com/RFmkvQX.jpg'
        print("[log:ERROR]Unable upload ! ")

    return imgurl