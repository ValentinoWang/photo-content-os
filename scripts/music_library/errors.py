class MusicError(Exception):
    """A Chinese, credential-free failure suitable for the CLI."""


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
