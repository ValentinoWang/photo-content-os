"""Package constants."""

from __future__ import annotations
from pathlib import Path

# --- ai_generate.py ---
WAVESPEED_MODEL = 'wavespeed-ai/ace-step-1.5'
WAVESPEED_SUBMIT_URL = 'https://api.wavespeed.ai/api/v3/wavespeed-ai/ace-step-1.5'
WAVESPEED_POLL_URL = 'https://api.wavespeed.ai/api/v3/predictions/{prediction_id}/result'
WAVESPEED_DOC_URL = 'https://wavespeed.ai/models/wavespeed-ai/ace-step-1.5/llms.txt'
BAILIAN_MODEL = 'fun-music-v1'
BAILIAN_DEFAULT_SUBMIT_URL = 'https://dashscope.aliyuncs.com/api/v1/services/audio/music/generation'
BAILIAN_WORKSPACE_URL = 'https://{workspace_id}.cn-beijing.maas.aliyuncs.com/api/v1/services/audio/music/generation'
BAILIAN_DOC_URL = 'https://help.aliyun.com/zh/model-studio/fun-music-api'
DEFAULT_STT_ENV_PATH = Path.home() / '.config' / 'harness' / 'speech-to-text.env'
AUDIO_EXTENSIONS = ('.wav', '.mp3', '.flac', '.m4a', '.mp4', '.ogg', '.aac')
PROVIDERS = {
    'wavespeed': {
        'model': WAVESPEED_MODEL,
        'label': 'WaveSpeed ACE-Step 1.5',
        'keychain_service': 'wavespeed-api-key',
        'unit_price': 0.0003,
        'currency': 'USD',
        'min_seconds': 5.0,
        'max_seconds': 240.0,
        'doc_url': WAVESPEED_DOC_URL,
    },
    'bailian': {
        'model': BAILIAN_MODEL,
        'label': '百炼 Fun-Music',
        'keychain_service': 'bailian-api-key',
        'unit_price': 0.002,
        'currency': 'CNY',
        'min_seconds': 1.0,
        'max_seconds': 300.0,
        'doc_url': BAILIAN_DOC_URL,
    },
}

# --- browser_cookies.py ---
BROWSERS = {
    'chrome': ('Google/Chrome', 'Chrome Safe Storage', 'Chrome'),
    'edge': ('Microsoft Edge', 'Microsoft Edge Safe Storage', 'Microsoft Edge'),
}

# --- cache.py ---
USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/130.0.0.0 Safari/537.36'

# --- client_files.py ---
CORE_KEY = b'hzHRAmso5kInbaxW'
META_KEY = b"#14ljk_!\\]&0U<'("

# --- douyin_api.py ---
REGISTER = 'https://ttwid.bytedance.com/ttwid/union/register/'
REGISTER_DATA = b'{"region":"cn","aid":1768,"needFid":false,"service":"www.ixigua.com","migrate_info":{"ticket":"","source":"node"},"cbUrlProtocol":"https","union":true}'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36'

# --- douyin_share.py ---
IPHONE_SAFARI = ('Mozilla/5.0 (iPhone; CPU iPhone OS 17_6 like Mac OS X) '
                 'AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Mobile/15E148 Safari/604.1')

# --- errors.py ---
DOUYIN_IMPORT_FAILURE_MESSAGE = '没从抖音取到这首的音乐。可以在剪映里直接用原声，或者找这首歌在汽水音乐、网易云音乐的分享链接。'
MEMBER_MESSAGE = '这首需要网易云会员，你的账号不是会员；可以换一首，或者加 --search-elsewhere 在汽水音乐里找同名的歌'
REGION_MESSAGE = '网易云限制了你当前所在地区播放这首（你现在的网络不在大陆），需要从大陆网络导入'

# --- library.py ---
SCHEMA = Path(__file__).resolve().parents[2] / 'schemas/music-track.schema.json'

# --- network.py ---
PROXY_ENV = 'CONTENT_OS_MUSIC_PROXY'
