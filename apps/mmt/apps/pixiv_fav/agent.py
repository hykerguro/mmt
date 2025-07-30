import litter
from confctl import config, util
from .archiver import PixivFavArchiver

APP_NAME = 'pixiv_fav.agent'


@litter.subscribe("pixiv_fav.archive.fav")
def archive_fav(message: litter.Message):
    PixivFavArchiver().archive_fav()


@litter.subscribe("pixiv_fav.archive.follow")
def archive_fav(message: litter.Message):
    PixivFavArchiver().archive_follow()


def serve(host, port):
    litter.listen(host, port, APP_NAME)


if __name__ == '__main__':
    util.default_arg_config_loggers("pixiv_fav/logs")
    serve(config.get("redis/host"), config.get("redis/port"))
