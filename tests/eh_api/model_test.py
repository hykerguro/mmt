import unittest
from eh_api.model import GalleryMetadata

class TestModel(unittest.TestCase):
    def test_gallery(self):
        jstr = """{
    "gmetadata": [
        {
            "gid": 2231376,
            "token": "a7584a5932",
            "archiver_key": "459562--7e27d313c50099214fde6bf74f8014d9309a2bb8",
            "title": "[Gentsuki] Kininaru Danshi ni 〇〇 suru Onnanoko. [Color Ban] [Ongoing]",
            "title_jpn": "[ゲンツキ] 気になる男子に〇〇する女の子。【カラー版】 [進行中]",
            "category": "Artist CG",
            "thumb": "https://ehgt.org/1f/f5/1ff5e361bbf7eaa235e9560dc5d12e624959e9e7-2722367-1882-3000-jpg_l.jpg",
            "uploader": "Pokom",
            "posted": "1653702810",
            "filecount": "329",
            "filesize": 419547090,
            "expunged": false,
            "rating": "4.78",
            "torrentcount": "2",
            "torrents": [
                {
                    "hash": "25198ccc3cd88393897aa5c630eb95d5ec4f695e",
                    "added": "1634958428",
                    "name": "(同人CG集) [ゲンツキ] 気になる男子に〇〇する女の子。【カラー版】 [進行中].zip",
                    "tsize": "12256",
                    "fsize": "310511523"
                },
                {
                    "hash": "62c960eb1c7a0e00dc2933a0c83dd43e2e6ebd48",
                    "added": "1639495362",
                    "name": "[Artist CG] Gentsuki - Kininaru Danshi ni 〇〇 suru Onnanoko (14 December 2021).zip",
                    "tsize": "27652",
                    "fsize": "357426803"
                }
            ],
            "tags": [
                "artist:gentsuki",
                "female:ponytail",
                "female:schoolgirl uniform",
                "female:stockings",
                "female:swimsuit",
                "female:tanlines",
                "female:twintails",
                "other:no penetration",
                "other:nudity only"
            ],
            "parent_gid": "2197090",
            "parent_key": "2f440c5f01",
            "first_gid": "2043548",
            "first_key": "bdb0cd9ec2"
        }
    ]
}"""
        gallery = GalleryMetadata.from_json(jstr, ["gmetadata", 0])
        self.assertIsNotNone(gallery)
        self.assertEqual(gallery.gid, 2231376)
        print(gallery)

