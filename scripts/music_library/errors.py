class MusicError(Exception):
    """A Chinese, credential-free failure suitable for the CLI."""


DOUYIN_IMPORT_FAILURE_MESSAGE = '没从抖音取到这首的音乐。可以在剪映里直接用原声，或者找这首歌在汽水音乐、网易云音乐的分享链接。'


def import_failure_message(platform, error):
    """Render public copy without changing the diagnostic kept in the cache."""
    return DOUYIN_IMPORT_FAILURE_MESSAGE if platform == 'douyin' else str(error)


MEMBER_MESSAGE = '这首需要网易云会员，你的账号不是会员；可以换一首，或者加 --search-elsewhere 在汽水音乐里找同名的歌'


class MemberRequired(MusicError):
    def __init__(self, title, artist):
        super().__init__(MEMBER_MESSAGE)
        self.title, self.artist = title, artist


REGION_MESSAGE = '网易云限制了你当前所在地区播放这首（你现在的网络不在大陆），需要从大陆网络导入'


class RegionRestricted(MusicError):
    def __init__(self):
        super().__init__(REGION_MESSAGE)
        self.diagnostic = {'failure_class': 'region_restricted'}


class NetworkFailure(MusicError):
    def __init__(self, message, diagnostic):
        super().__init__(message)
        self.diagnostic = diagnostic
