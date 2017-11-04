import json
import logging
try:
    from urllib import quote_plus
    from urlparse import urljoin
except ImportError:
    from urllib.parse import urljoin, quote_plus

import requests
from bs4 import BeautifulSoup, SoupStrainer

BASE_URL = 'https://play.google.com/store/apps'

import sys

print sys.version


def _parse_app_details(soup):
    """Extracts an app's details from its info page.
    :param soup: a strained BeautifulSoup object of an app
    :return: a dictionary of app details
    """
    app_id = soup.select_one('div[data-uitype=209]').attrs['data-docid']
    #url = build_url('details', app_id)
    url=BASE_URL+'/details?id='+app_id+"&hl=en"
    title = soup.select_one('div.id-app-title').string
    icon = urljoin(
        BASE_URL,
        soup.select_one('img.cover-image').attrs['src'].split('=')[0])
    screenshots = [urljoin(
        BASE_URL,
        img.attrs['src']) for img in soup.select('img.full-screenshot')]
    thumbnails = [urljoin(
        BASE_URL,
        img.attrs['src']) for img in soup.select('img.screenshot')]

    try:
        video = soup.select_one('span.preview-overlay-container').attrs.get('data-video-url', None)
        if video is not None:
            video = video.split('?')[0]
    except AttributeError:
        video = None
        pass

    # Main category will be first
    category = [c.attrs['href'].split('/')[-1] for c in soup.select('.category')]

    description_soup = soup.select_one('div.show-more-content.text-body div')
    if description_soup:
        description = "\n".join(description_soup.stripped_strings)
        description_html = description_soup.encode_contents().decode('utf-8')
    else:
        description = ''
        description_html = ''

    # Reviews & Ratings
    try:
        score = float(soup.select_one('meta[itemprop="ratingValue"]').attrs['content'])
    except AttributeError:
        score = None
        pass

    histogram = {}
    try:
        reviews = int(soup.select_one('meta[itemprop="ratingCount"]').attrs['content'])
        ratings_section = soup.select_one('div.rating-histogram')
        ratings = [int(r.string.replace(',', '')) for r in ratings_section.select('span.bar-number')]
        for i in range(5):
            histogram[5 - i] = ratings[i]
    except AttributeError:
        reviews = 0
        pass

    recent_changes = "\n".join([x.string.strip() for x in soup.select('div.recent-change')])
    top_developer = bool(soup.select_one('meta[itemprop="topDeveloperBadgeUrl"]'))
    editors_choice = bool(soup.select_one('meta[itemprop="editorsChoiceBadgeUrl"]'))
    try:
        price = soup.select_one('meta[itemprop="price"]').attrs['content']
    except AttributeError:
        try:
            price = soup.select_one('div.preregistration-text-add').string.strip()
        except AttributeError:
            price = 'Not Available'

    free = (price == '0')

    # Additional information section
    additional_info = soup.select_one('div.metadata div.details-section-contents')
    updated = additional_info.select_one('div[itemprop="datePublished"]')
    if updated:
        updated = updated.string

    size = additional_info.select_one('div[itemprop="fileSize"]')
    if size:
        size = size.string.strip()

    try:
        installs = [int(n.replace(',', '')) for n in additional_info.select_one(
            'div[itemprop="numDownloads"]').string.strip().split(" - ")]
    except AttributeError:
        installs = [0, 0]

    """genre = additional_info.select_one('div[itemprop="genre"]')
    if genre:
        try:
            genre = genre.string.strip()
        except AttributeError:
            genre = genre.span.string.strip()"""

    current_version = additional_info.select_one('div[itemprop="softwareVersion"]')
    if current_version:
        try:
            current_version = current_version.string.strip()
        except AttributeError:
            current_version = current_version.span.string.strip()

    required_android_version = additional_info.select_one('div[itemprop="operatingSystems"]')
    if required_android_version:
        required_android_version = required_android_version.string.strip()

    content_rating = additional_info.select_one('div[itemprop="contentRating"]')
    if content_rating:
        content_rating = content_rating.string

    meta_info = additional_info.select('.title')
    meta_info_titles = [x.string.strip() for x in meta_info]
    try:
        i_elements_index = meta_info_titles.index('Interactive Elements')
        interactive_elements = meta_info[i_elements_index].next_sibling.next_sibling.string.split(', ')
    except ValueError:
        interactive_elements = []
        pass

    offers_iap = bool(soup.select_one('div.inapp-msg'))
    iap_range = None
    if offers_iap:
        try:
            iap_price_index = meta_info_titles.index('In-app Products')
            iap_range = meta_info[iap_price_index].next_sibling.next_sibling.string
        except ValueError:
            iap_range = 'Not Available'
            pass

    developer = soup.select_one('span[itemprop="name"]').string

    dev_id = soup.select_one('a.document-subtitle.primary').attrs['href'].split('=')[1]
    developer_id = dev_id if dev_id.isdigit() else None

    try:
        developer_email = additional_info.select_one('a[href^="mailto"]').attrs['href'].split(":")[1]
    except AttributeError:
        developer_email = None
    developer_url = additional_info.select_one('a[href^="https://www.google.com"]')
    if developer_url:
        developer_url = developer_url.attrs['href'].split("&")[0].split("=")[1]
    developer_address = additional_info.select_one('.physical-address')
    if developer_address:
        developer_address = developer_address.string

    return {
        'app_id': app_id,
        'title': title,
        'icon': icon,
        'url': url,
        'screenshots': screenshots,
        'thumbnails': thumbnails,
        'video': video,
        'category': category,
        'score': score,
        'histogram': histogram,
        'reviews': reviews,
        'description': description,
        'description_html': description_html,
        'recent_changes': recent_changes,
        'top_developer': top_developer,
        'editors_choice': editors_choice,
        'price': price,
        'free': free,
        'updated': updated,
        'size': size,
        'installs': installs,
        'current_version': current_version,
        'required_android_version': required_android_version,
        'content_rating': content_rating,
        'interactive_elements': interactive_elements,
        'iap': offers_iap,
        'iap_range': iap_range,
        'developer': developer,
        'developer_id': developer_id,
        'developer_email': developer_email,
        'developer_url': developer_url,
        'developer_address': developer_address
	}


def details(app_id):
    """Sends a GET request and parses an application's details.
    :param app_id: the app to retrieve details from, e.g. 'com.nintendo.zaaa'
    :return: a dictionary of app details
    """
    url=BASE_URL+'/details?id='+app_id+"&hl=en"
    r = requests.get(url)
    soup = BeautifulSoup(r.content, "lxml")
    return _parse_app_details(soup)
    """try:
        response = send_request('GET', url)
        soup = BeautifulSoup(response.content, 'lxml')
    except requests.exceptions.HTTPError as e:
        raise ValueError('Invalid application ID: {app}. {error}'.format(
            app=app_id, error=e))"""
	


inp=details('com.android.chrome')
print inp['app_id']
da=json.dumps(inp)
fo=open('/home/harshul/Desktop/n1.json', "w")
fo.write(da)
fo.close()

with open('/home/harshul/Desktop/n1.json', "r") as f:
	d=json.load(f)
	print d['app_id']