import pytest

from scripts.avatar.videoretalk import AvatarError, Client
from tests.test_avatar_videoretalk import Fake


def test_signed_http_oss_upgrades_without_changing_query(tmp_path):
    source = tmp_path / 'source'
    source.write_bytes(b'video')
    fake = Fake(source)
    target = tmp_path / 'out'
    Client('SECRET', fake).download('http://dashscope-test.oss-cn-shanghai.aliyuncs.com/out?signature=a%2Bb&expires=123', target)
    assert fake.gets[-1][0] == 'https://dashscope-test.oss-cn-shanghai.aliyuncs.com/out?signature=a%2Bb&expires=123'
    assert target.read_bytes() == b'video'


def test_http_untrusted_host_is_rejected(tmp_path):
    with pytest.raises(AvatarError, match='avatar_result_url_invalid'):
        Client('SECRET', Fake(tmp_path / 'missing')).download('http://evil.com/out?signature=a', tmp_path / 'out')
