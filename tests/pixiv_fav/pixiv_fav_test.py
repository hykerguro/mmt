import unittest

from confctl import config
from pixiv_fav.main import PixivFavArchiver
from pixiv_fav.model import initialize_database


class PixivFavTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        config.load_config("config/pixiv_fav.yaml")
        cls.archiver = PixivFavArchiver()
        cls.archiver.verify_papi()
        initialize_database(config.get("db_url"))
        print("数据库初始化")

    def test_get_new_follows_one_page(self):
        ret = self.archiver.get_new_follows()
        self.assertTrue(len(ret) == 60)

    def test_get_new_follows_multiple_pages(self):
        firstpage = self.archiver.get_new_follows()
        max_illust_id = int(firstpage[10]['id'])
        ret = self.archiver.get_new_follows(max_illust_id)
        self.assertTrue(len(ret) == 10)

    def test_archive_follow(self):
        from pixiv_fav.model import db
        from playhouse import db_url as _db_url

        # initialize_database(config.get("db_url"))
        print(db.initialize(_db_url.connect(config.get("db_url"))))
        self.archiver.archive_follow()


if __name__ == '__main__':
    unittest.main()
