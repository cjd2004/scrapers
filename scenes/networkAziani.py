import re
import string
from urllib.parse import urlencode
import datetime
import scrapy
from slugify import slugify
from tldextract import tldextract
from tpdb.BaseSceneScraper import BaseSceneScraper
from tpdb.items import SceneItem


class AzianiScraper(BaseSceneScraper):
    name = 'Aziani'
    network = 'nomadmedia'
    cookies = {'X-NATS-cms-area-id': '3',}
    start = 0
'''
    custom_settings = {'X-NATS-cms-area-id': '3',
                       # ~ 'AUTOTHROTTLE_ENABLED': 'True',
                       # ~ 'AUTOTHROTTLE_DEBUG': 'False',
                       # ~ 'DOWNLOAD_DELAY': '2',
                       # ~ 'CONCURRENT_REQUESTS_PER_DOMAIN': '2',
                       }

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(url=url, callback=self.parse, headers=self.headers, cookies=self.cookies,
                                 meta={'url': url})
                       
'''
    start_urls = [
        # Only need one starting URL per "site", pulls everything through common feed

        'https://azianistudios.com',

    ]

    selector_map = {
        'external_id': 'scene\\/(\\d+)'
        'pagination':tour_api.php/content/sets?cms_set_ids=&data_types=1&content_count=1&count=48&start=%s&cms_area_id=3&cms_block_id=106775&orderby=published_desc&content_type=video&status=enabled'


    def get_next_page_url(self, base, page):
        return self.format_url(base, self.get_selector_map('pagination') % start)

    def parse(self, response):
        token = self.get_token(response)

        headers = {
            'instance': token,
        }

        response.meta['headers'] = headers
        response.meta['limit'] = 25
        # ~ response.meta['page'] = -1
        response.meta['page'] = self.page - 1
        response.meta['url'] = response.url

        return self.get_next_page(response)

    def get_scenes(self, response):
        scene_count = 0

        for scene in response.json()['sets']:
            item = SceneItem()
            if scene['collections'] and len(scene['collections']):
                item['site'] = scene['collections'][0]['name']
            else:
                item['site'] = tldextract.extract(response.meta['url']).domain

            if "men.com" in response.url and item['site'] == 'tp':
                item['site'] = 'Twink Pop'

            if tldextract.extract(
                    response.meta['url']).domain == 'digitalplayground':
                item['site'] = 'digitalplayground'

            item['image'] = self.get_image(scene)

            item['image_blob'] = self.get_image_blob_from_link(item['image'])

            item['trailer'] = self.get_trailer(scene)
            if not item['trailer']:
                item['trailer'] = ''
            item['date'] = self.parse_date(scene['dateReleased']).isoformat()
            item['id'] = scene['id']
            item['network'] = self.network
            item['parent'] = tldextract.extract(response.meta['url']).domain

            if 'name' in scene:
                item['title'] = scene['title']
            else:
                item['title'] = item['site'] + ' ' + self.parse_date(scene['dateReleased']).strftime('%b/%d/%Y')

            if 'description' in scene:
                item['description'] = scene['description']
            else:
                item['description'] = ''

            item['performers'] = []
            for model in scene['actors']:
                item['performers'].append(model['name'])

            if 'actors' not in scene or not item['performers']:
                item['performers'] = []

            item['tags'] = []
            for tag in scene['tags']:
                item['tags'].append(tag['name'])

            if "isVR" in scene:
                if scene['isVR']:
                    item['tags'].append("VR")

            try:
                item['duration'] = scene['videos']['mediabook']['length']
            except Exception:
                item['duration'] = ''

            item['markers'] = []
            if "timeTags" in scene:
                for timetag in scene['timeTags']:
                    timestamp = {}
                    timestamp['name'] = self.cleanup_title(timetag['name'])
                    timestamp['start'] = str(timetag['startTime'])
                    timestamp['end'] = str(timetag['endTime'])
                    item['markers'].append(timestamp)
                    scene['tags'].append(timestamp['name'])
                item['markers'] = self.clean_markers(item['markers'])
                item['tags'] = list(map(lambda x: string.capwords(x.strip()), list(set(item['tags']))))

            # Deviante abbreviations
            if item['site'] == "fmf":
                item['site'] = "Forgive Me Father"
                item['parent'] = "Deviante"
            if item['site'] == "sw":
                item['site'] = "Sex Working"
                item['parent'] = "Deviante"
            if item['site'] == "pdt":
                item['site'] = "Pretty Dirty Teens"
                item['parent'] = "Deviante"
            if item['site'] == "lha":
                item['site'] = "Love Her Ass"
                item['parent'] = "Deviante"
            if item['site'] == "es":
                item['site'] = "Erotic Spice"
                item['parent'] = "Deviante"
            if item['site'] == "dlf":
                item['site'] = "DILFed"
                item['parent'] = "DILFed"

            siteurl = re.compile(r'\W')
            siteurl = re.sub(siteurl, '', item['site']).lower()
            brand = scene['brand'].lower().strip()

            if brand == "brazzers" or brand == "deviante" or brand == "bangbros" or brand == "bromo":
                item['url'] = f"https://www.{brand}.com/video/{scene['id']}/{slugify(item['title'])}"
            elif brand == "men":
                item['url'] = f"https://www.{brand}.com/sceneid/{scene['id']}/{slugify(item['title'])}"
            elif brand == "mofos" or brand == "realitykings" or brand == "sexyhub" or brand == "twistys" or brand == "babes":
                item['url'] = f"https://www.{brand}.com/scene/{scene['id']}/{slugify(item['title'])}"
            else:
                item['url'] = f"https://www.{siteurl}.com/scene/{scene['id']}/{slugify(item['title'])}"

            item['parent'] = string.capwords(item['parent'])

            yield_item = True
            if brand == "bangbros" and item['date'] < "2023-06-21":
                yield_item = False

            if item['site'] == "Sex Selector" and item['date'] < "2024-01-13":
                yield_item = False

            if self.check_item(item, self.days) and yield_item:
                scene_count = scene_count + 1
                yield item

        if scene_count > 0:
            if 'page' in response.meta and (
                    response.meta['page'] % response.meta['limit']) < self.limit_pages:
                yield self.get_next_page(response)

    def get_next_page(self, response):
        meta = response.meta

        tomorrow = datetime.date.today() + datetime.timedelta(days=1)
        query = {
            'dateReleased': f"<{tomorrow}",
            'limit': meta['limit'],
            'type': 'scene',
            'orderBy': '-dateReleased',
            'offset': (meta['page'] * meta['limit']),
            'referrer': meta['url'],
        }
        meta = {
            'url': response.meta['url'],
            'headers': response.meta['headers'],
            'page': (response.meta['page'] + 1),
            'limit': response.meta['limit']
        }

        print('NEXT PAGE: ' + str(meta['page']))

        link = 'https://site-api.project1service.com/v2/releases?' + \
            urlencode(query)
        return scrapy.Request(url=link, callback=self.get_scenes,
                              headers=response.meta['headers'], meta=meta)

    def get_token(self, response):
        token = re.search('instance_token=(.+?);',
                          response.headers.getlist('Set-Cookie')[0].decode("utf-8"))
        return token.group(1)

    def get_image(self, scene):
        image_arr = []
        if 'card_main_rect' in scene['images'] and len(
                scene['images']['card_main_rect']):
            image_arr = scene['images']['card_main_rect']
        elif 'poster' in scene['images'] and len(scene['images']['poster']):
            image_arr = scene['images']['poster']

        sizes = ['xx', 'xl', 'lg', 'md', 'sm']
        for index in image_arr:
            image = image_arr[index]
            for size in sizes:
                if size in image:
                    return image[size]['url']

    def get_trailer(self, scene):
        for index in scene['videos']:
            trailer = scene['videos'][index]
            for size in ['720p', '576p', '480p', '360p', '320p', '1080p', '4k']:
                if size in trailer['files']:
                    return trailer['files'][size]['urls']['view']

    def clean_markers(self, markers):
        markers = sorted(markers, key=lambda k: (k['name'].lower(), int(k['start']), int(k['end'])))
        marker_final = []
        marker_work = markers.copy()
        marker2_work = markers.copy()
        for test_marker in marker_work:
            if test_marker in markers:
                for marker in marker2_work:
                    if test_marker['name'].lower().strip() == marker['name'].lower().strip():
                        test_start = int(test_marker['start'])
                        mark_start = int(marker['start'])
                        test_end = int(test_marker['end'])
                        mark_end = int(marker['end'])
                        if test_start < mark_start or test_start == mark_start:
                            test1 = mark_start - test_end
                            test2 = mark_start - test_start
                            if 0 < test1 < 60 or 0 < test2 < 60 or test1 == 0 or test2 == 0:
                                if mark_end > test_end:
                                    test_marker['end'] = marker['end']
                                    if marker in markers:
                                        markers.remove(marker)
                            if test_end > mark_start and mark_end > test_end:
                                test_marker['end'] = marker['end']
                                if marker in markers:
                                    markers.remove(marker)
                            if test_start < mark_start and (mark_end < test_end or test_end == mark_end):
                                if marker in markers:
                                    markers.remove(marker)
                marker2_work = markers.copy()

                if test_marker in markers:
                    marker_final.append(test_marker)
                    markers.remove(test_marker)
        marker_final = sorted(marker_final, key=lambda k: (int(k['start']), int(k['end'])))
        return marker_final
