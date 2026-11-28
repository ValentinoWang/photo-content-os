class MusicError(Exception):
    """A Chinese, credential-free failure suitable for the CLI."""


if __package__:
    from .constants import (
        DOUYIN_IMPORT_FAILURE_MESSAGE,
        MEMBER_MESSAGE,
        REGION_MESSAGE,
    )
else:
    try:
        from scripts.music_library.constants import (
            DOUYIN_IMPORT_FAILURE_MESSAGE,
            MEMBER_MESSAGE,
            REGION_MESSAGE,
        )
    except ImportError:
        from constants import (
            DOUYIN_IMPORT_FAILURE_MESSAGE,
            MEMBER_MESSAGE,
            REGION_MESSAGE,
        )


def import_failure_message(platform, error):
    """Render public copy without changing the diagnostic kept in the cache."""
    return DOUYIN_IMPORT_FAILURE_MESSAGE if platform == 'douyin' else str(error)




class MemberRequired(MusicError):
    def __init__(self, title, artist):
        super().__init__(MEMBER_MESSAGE)
        self.title, self.artist = title, artist




class RegionRestricted(MusicError):
    def __init__(self):
        super().__init__(REGION_MESSAGE)
        self.diagnostic = {'failure_class': 'region_restricted'}


class NetworkFailure(MusicError):
    def __init__(self, message, diagnostic):
        super().__init__(message)
        self.diagnostic = diagnostic
