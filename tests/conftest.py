# -- coding: utf-8 --
"""測試共用設定：假的 LINE、假的 MongoDB、假的對外連線。

全部在本機跑，不會真的推 LINE、不會連資料庫、也不會連阿生地圖或 GitHub。
任何沒有事先安排的對外連線都會讓測試直接失敗，避免測試偷偷打到真的服務。
"""
import base64
import hashlib
import hmac
import json
import os
import sys
import types

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTRACTS = os.path.join(ROOT, 'tests', 'contracts')

TEST_ENV = {
    'CHANNEL_ACCESS_TOKEN': 'test-access-token',
    'CHANNEL_SECRET': 'test-channel-secret',
    'FEEDBACK_TOKEN': 'test-feedback-token',
    'CONTACTS_DL_TOKEN': 'test-contacts-dl-token',
    'CONTACTS_ADMIN_TOKEN': 'test-contacts-admin-token',
    'ADMIN_USER_ID': 'Uadmin',
    'IMGUR_CLIENT_ID': '',
    'MONGODB_URI': '',
}
# 一定要在 import app 之前設好：app.py / line_bot.py 在載入時就把環境變數讀進去了
os.environ.update(TEST_ENV)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import requests  # noqa: E402

import app as bot  # noqa: E402
import mongodb  # noqa: E402

ADMIN_UID = TEST_ENV['ADMIN_USER_ID']
FEEDBACK_TOKEN = TEST_ENV['FEEDBACK_TOKEN']


def load_contract(name):
    """讀 tests/contracts 的介面範例，把權杖佔位字換成測試用權杖。"""
    with open(os.path.join(CONTRACTS, name), encoding='utf-8') as f:
        raw = f.read()
    return json.loads(raw.replace('__FEEDBACK_TOKEN__', FEEDBACK_TOKEN))


# ───────────────────────── 假的 LINE ─────────────────────────
class FakeLine:
    """記下機器人「回覆」與「推播」了什麼，不真的送出去。"""

    def __init__(self):
        self.replies = []      # [(reply_token, [訊息…])]
        self.pushes = []       # [(收件人, [訊息…])]
        self.display_name = '測試使用者'
        self.push_error = None

    def get_profile(self, user_id):
        return types.SimpleNamespace(user_id=user_id, display_name=self.display_name)

    def reply_message(self, reply_token, messages, *a, **kw):
        self.replies.append((reply_token, messages if isinstance(messages, list) else [messages]))

    def push_message(self, to, messages, *a, **kw):
        if self.push_error:
            raise self.push_error
        self.pushes.append((to, messages if isinstance(messages, list) else [messages]))

    def get_message_content(self, message_id):
        return types.SimpleNamespace(content=b'\xff\xd8fake-jpeg')

    # 方便檢查
    @staticmethod
    def _texts(batches):
        return [m.text for _to, msgs in batches for m in msgs if hasattr(m, 'text')]

    @property
    def reply_texts(self):
        return self._texts(self.replies)

    @property
    def push_texts(self):
        return self._texts(self.pushes)


# ───────────────────────── 假的 MongoDB ─────────────────────────
class FakeDB:
    def __init__(self):
        self.files = {}        # name → (data_b64, updated)
        self.cron = {}
        self.followers = []

    def save_app_file(self, name, data_b64, updated_iso):
        self.files[name] = (data_b64, updated_iso)

    def get_app_file(self, name):
        return self.files.get(name, (None, None))

    def get_cron_last_run(self, key):
        return self.cron.get(key)

    def set_cron_last_run(self, key, date_str):
        self.cron[key] = date_str

    def get_all_followers(self):
        return list(self.followers)


# ───────────────────────── 假的對外連線 ─────────────────────────
class FakeResponse:
    def __init__(self, status=200, json_data=None, text='', headers=None):
        self.status_code = status
        self._json = json_data
        self.text = text if text else (json.dumps(json_data, ensure_ascii=False) if json_data is not None else '')
        self.content = self.text.encode('utf-8')
        self.headers = headers or {}

    def json(self):
        if self._json is None:
            raise ValueError('not json')
        return self._json


class FakeNet:
    """照網址開頭決定回什麼；沒安排的網址一律讓測試失敗。"""

    def __init__(self):
        self.routes = []       # [(method 或 None, 網址開頭, 回應 / 例外 / 函式)]
        self.calls = []        # [{'method','url','json','headers','cookies'}]

    def add(self, url_prefix, response, method=None):
        self.routes.insert(0, (method, url_prefix, response))

    def calls_to(self, url_prefix):
        return [c for c in self.calls if c['url'].startswith(url_prefix)]

    def _handle(self, method, url, **kw):
        body = kw.get('json')
        if body is None and isinstance(kw.get('data'), (str, bytes)):
            try:
                body = json.loads(kw['data'])
            except Exception:
                body = kw['data']
        call = {'method': method, 'url': url, 'json': body,
                'headers': kw.get('headers') or {}, 'cookies': kw.get('cookies') or {}}
        self.calls.append(call)
        for m, prefix, resp in self.routes:
            if (m is None or m == method) and url.startswith(prefix):
                if callable(resp) and not isinstance(resp, type):
                    resp = resp(call)
                if isinstance(resp, BaseException):
                    raise resp
                return resp
        raise AssertionError('測試中出現沒安排的對外連線：%s %s' % (method, url))


@pytest.fixture(autouse=True)
def net(monkeypatch):
    fake = FakeNet()
    fake.add('https://api.line.me/v2/bot/chat/loading/start', FakeResponse(202, {}))   # 「…」載入動畫
    for name in ('get', 'post', 'head', 'put', 'delete'):
        monkeypatch.setattr(requests, name, lambda url, _m=name.upper(), **kw: fake._handle(_m, url, **kw))

    def _blocked(self, method, url, *a, **kw):
        raise AssertionError('測試中出現沒安排的對外連線：%s %s' % (method, url))
    monkeypatch.setattr(requests.sessions.Session, 'request', _blocked)
    return fake


@pytest.fixture(autouse=True)
def line(monkeypatch):
    fake = FakeLine()
    monkeypatch.setattr(bot, 'line_bot_api', fake)
    return fake


@pytest.fixture(autouse=True)
def db(monkeypatch):
    fake = FakeDB()
    for name in ('save_app_file', 'get_app_file', 'get_cron_last_run', 'set_cron_last_run', 'get_all_followers'):
        monkeypatch.setattr(mongodb, name, getattr(fake, name))

    def _no_real_db(*a, **kw):
        raise AssertionError('測試中不可以連真的 MongoDB')
    monkeypatch.setattr(mongodb, 'MongoClient', _no_real_db)
    return fake


@pytest.fixture(autouse=True)
def clean_state(monkeypatch, tmp_path):
    """每個測試都從乾淨的狀態開始；截圖等檔案寫到暫存資料夾，不弄髒 repo。"""
    monkeypatch.setattr(bot, 'CHART_DIR', str(tmp_path))
    monkeypatch.setattr(bot, 'FEEDBACK_TOKEN', FEEDBACK_TOKEN)
    monkeypatch.setattr(bot, 'CONTACTS_DL_TOKEN', TEST_ENV['CONTACTS_DL_TOKEN'])
    monkeypatch.setattr(bot, 'CONTACTS_ADMIN_TOKEN', TEST_ENV['CONTACTS_ADMIN_TOKEN'])
    bot._FB_HITS.clear()
    bot._CO_CACHE.clear()
    bot._DL_CACHE.clear()
    yield
    bot._FB_HITS.clear()
    bot._CO_CACHE.clear()
    bot._DL_CACHE.clear()


@pytest.fixture
def client():
    bot.app.config['TESTING'] = True
    return bot.app.test_client()


@pytest.fixture
def chart_dir(tmp_path):
    return tmp_path


# ───────────────────────── 假的 LINE webhook ─────────────────────────
@pytest.fixture
def say(client):
    """模擬使用者在 LINE 傳一句話給機器人：say('檢查', uid='Uadmin')。回 HTTP 回應。"""
    def _say(text, uid='Utestuser', source_type='user'):
        source = {'type': source_type, 'userId': uid}
        if source_type == 'group':
            source['groupId'] = 'Cgroup'
        body = json.dumps({
            'destination': 'Ubot',
            'events': [{
                'type': 'message', 'mode': 'active', 'timestamp': 1700000000000,
                'webhookEventId': '01TEST', 'deliveryContext': {'isRedelivery': False},
                'replyToken': 'reply-token', 'source': source,
                'message': {'id': '1', 'type': 'text', 'text': text, 'quoteToken': 'q'},
            }],
        }, ensure_ascii=False)
        return client.post('/callback', data=body.encode('utf-8'),
                           headers={'X-Line-Signature': sign(body), 'Content-Type': 'application/json'})
    return _say


def sign(body, secret=TEST_ENV['CHANNEL_SECRET']):
    mac = hmac.new(secret.encode('utf-8'), body.encode('utf-8'), hashlib.sha256).digest()
    return base64.b64encode(mac).decode()
