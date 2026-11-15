# -- coding: utf-8 --
"""安裝頁、使用說明、/download 自動導到最新版安裝檔。"""
import requests

from conftest import FakeResponse

API = 'https://api.github.com/repos/windskyshao/tw-land-tools/releases/latest'
LATEST = 'https://github.com/windskyshao/tw-land-tools/releases/latest'
DL = 'https://github.com/windskyshao/tw-land-tools/releases/download/'


def _assets(*names):
    return {'assets': [{'name': n, 'browser_download_url': DL + 'v1.2.3/' + n} for n in names]}


def test_install_and_help_pages_load(client):
    for path in ('/install', '/help'):
        r = client.get(path)
        assert r.status_code == 200 and b'<html' in r.data.lower()


def test_install_page_points_to_download(client):
    assert b'/download' in client.get('/install').data


def test_help_images_referenced_by_help_page_exist(client):
    import re
    html = client.get('/help').get_data(as_text=True)
    names = set(re.findall(r'help_img/([\w.\-]+)', html))
    assert names
    missing = [n for n in sorted(names) if client.get('/help_img/' + n).status_code != 200]
    assert missing == []


def test_download_prefers_zip(client, net):
    net.add(API, FakeResponse(200, _assets('tw-land-tools-setup_v1.2.3.exe', 'tw-land-tools-setup_v1.2.3.zip', 'other.zip')))
    r = client.get('/download')
    assert r.status_code == 302
    assert r.headers['Location'] == DL + 'v1.2.3/tw-land-tools-setup_v1.2.3.zip'


def test_download_type_exe(client, net):
    net.add(API, FakeResponse(200, _assets('tw-land-tools-setup_v1.2.3.exe', 'tw-land-tools-setup_v1.2.3.zip')))
    assert client.get('/download?type=exe').headers['Location'].endswith('.exe')


def test_download_gives_exe_when_release_has_no_zip(client, net):
    net.add(API, FakeResponse(200, _assets('tw-land-tools-setup_v1.2.3.exe')))
    assert client.get('/download').headers['Location'].endswith('tw-land-tools-setup_v1.2.3.exe')


def test_download_result_cached(client, net):
    net.add(API, FakeResponse(200, _assets('tw-land-tools-setup_v1.2.3.zip')))
    client.get('/download')
    client.get('/download')
    assert len(net.calls_to(API)) == 1


def test_download_falls_back_when_github_api_blocked(client, net):
    net.add(API, FakeResponse(403, {'message': 'API rate limit exceeded'}))
    net.add(LATEST, FakeResponse(302, headers={'Location': 'https://github.com/windskyshao/tw-land-tools/releases/tag/v1.2.4'}), method='HEAD')
    net.add(DL, FakeResponse(302), method='HEAD')
    r = client.get('/download')
    assert r.headers['Location'] == DL + 'v1.2.4/tw-land-tools-setup_v1.2.4.zip'


def test_download_goes_to_release_page_when_everything_fails(client, net):
    net.add('https://api.github.com/', requests.exceptions.ConnectionError('x'))
    net.add('https://github.com/', requests.exceptions.ConnectionError('x'))
    r = client.get('/download')
    assert r.status_code == 302 and r.headers['Location'] == LATEST


def test_version_shows_deployed_commit(client, monkeypatch):
    """推完程式後用 /version 確認 Render 真的換上新版(只回版本編號，不洩漏設定)"""
    monkeypatch.setenv('RENDER_GIT_COMMIT', 'abcdef1234567890')
    monkeypatch.setenv('RENDER_GIT_BRANCH', 'main')
    r = client.get('/version')
    assert r.status_code == 200
    assert r.get_json() == {'commit': 'abcdef1', 'branch': 'main'}


def test_version_without_render_env(client, monkeypatch):
    monkeypatch.delenv('RENDER_GIT_COMMIT', raising=False)
    monkeypatch.delenv('RENDER_GIT_BRANCH', raising=False)
    assert client.get('/version').get_json() == {'commit': '', 'branch': ''}
