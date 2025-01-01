import datetime
import unittest

from confctl import config
from eh_api import refresh_ds, get_gallery, get_fav, download_image
from eh_api.exception import GalleryNotAvailable
from eh_api.model import Image


class DataSourceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        config.load_config("config/dev.yaml")
        refresh_ds()
        
    def test_get_gallery_v2(self):
        gallery = get_gallery(3040421, "5d31f7e90e")
        print("gallery:", gallery)
        self.assertEqual(gallery.title, "[Fanbox / Patreon] houk1se1 (2021.09.05 - 2024.08.21)")
        it = gallery.images_iter
        i1 = next(it)
        print("i1", i1)
        i2 = next(it)
        print("i2", i2)
        self.assertIsInstance(i1, Image)
        self.assertIsInstance(i2, Image)
        download_image(i1, directory='assets', original=True)
        download_image(i2, directory='assets', original=False)

    def test_get_gallery_by_url(self):
        gallery = get_gallery("https://e-hentai.org/g/3042669/d2fc84fae6/")
        print("gallery:", gallery)
        self.assertEqual(gallery.title, "[Fanbox] Mochirong (6005584)")
        it = gallery.images_iter
        i1 = next(it)
        print("i1", i1)
        i2 = next(it)
        print("i2", i2)
        self.assertIsInstance(i1, Image)
        self.assertIsInstance(i2, Image)
        download_image(i1, directory='assets', original=True)
        download_image(i2, directory='assets', original=False)

    def test_get_gallery_not_available(self):
        self.assertRaises(GalleryNotAvailable, get_gallery, "https://exhentai.org/g/2666289/5e6f7f7322/")

    def test_metadata_newer(self):
        gallery = get_gallery(3016050, "eb2fa9626b")
        print(gallery)
        self.assertIsNotNone(gallery)
        self.assertGreater(len(gallery.newer), 0)
        self.assertIsInstance(gallery.newer[0][0], str)
        self.assertIsInstance(gallery.newer[0][1], datetime.datetime)

    def test_get_fav(self):
        favs = get_fav()
        print(favs)
        self.assertGreater(len(favs), 0)


if __name__ == '__main__':
    unittest.main()
