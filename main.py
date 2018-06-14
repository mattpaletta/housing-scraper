import logging
import math
import os

import pandas as pd
from bs4 import BeautifulSoup
import requests


def get_tag(soup, tag):
    return soup.find_all(tag)


def get_websites():
    return ["https://victoria.craigslist.ca/d/rooms-shares/search/roo",
            "https://victoria.craigslist.ca/d/rooms-shares/search/roo?s=120",
            "https://victoria.craigslist.ca/d/rooms-shares/search/roo?s=240"]


class CraiglistPosting(object):
    def __init__(self, link, price, name, distance=0, desc=""):
        self.link = link
        self.price = price
        self.name = name
        self.distance = distance
        self.desc = desc


def dist(x1, x2, y1, y2):
    return math.sqrt((x2 - x1)**2 + (y2-y1)**2)


def toRadians(x):
    return float(x) * (math.pi / 360.0)


def dist_lat_long_to_km(lat1, lon1, lat2, lon2):

    EARTH_RADIUS = 6371e3  # metres
    KM_PER_MILE = 1.60934

    x1 = toRadians(lat1)
    x2 = toRadians(lat2)

    y1 = toRadians(lat2 - lat1)
    y2 = toRadians(lon2 - lon1)

    a = math.sin(y1 / 2) * math.sin(y1 / 2) + \
        math.cos(x1) * math.cos(x2) * \
        math.sin(y2 / 2) * math.sin(y2 / 2)

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    d = EARTH_RADIUS * c
    return d * KM_PER_MILE


def process_posting(craigslist_posting: CraiglistPosting):
    page = requests.get(craigslist_posting.link)
    soup = BeautifulSoup(page.content, "html.parser")

    map = soup.select_one("#map")
    try:
        post_body = soup.select_one("#postingbody").get_text()
    except:
        print(soup)
        return

    if map is not None:
        latitude = map.get("data-latitude")
        longitude = map.get("data-longitude")

        dist_to_uvic = dist_lat_long_to_km(float(latitude), float(longitude),
                                           48.4634, 123.3117)

        if dist_to_uvic > 10:
            logging.info("Place too far: " + str(dist_to_uvic))
            return
    else:
        dist_to_uvic = 0

    for bad in ["female only",
                "until september",
                "until august",
                "for female student",
                "until august 31"]:
        if str(post_body).lower().__contains__(bad):
            return

    craigslist_posting.distance = dist_to_uvic
    craigslist_posting.desc = post_body

    return craigslist_posting



def crawl_craiglist(config):
    for site in get_websites():
        page = requests.get(site)
        soup = BeautifulSoup(page.content, "html.parser")

        posts: BeautifulSoup = soup.find_all(class_="result-row")

        for post in posts:
            try:
                price = post.select_one(".result-price").get_text().strip("$")
                link = post.select_one('a').get("href")
                name = post.select_one('.result-title').get_text()
                # meta = post.select_one("result-meta")
                print(name, price)
                if int(price) <= config["max_price"] and link not in config["previous"]:
                    yield CraiglistPosting(price=price, link=link, name=name)
            except AttributeError:
                #print(post)
                pass

def obj_to_dict(x):
    if x is not None:
        return x.__dict__

def obj_to_dataframe(posting):
    print(list(map(obj_to_dict, posting)))

    #df = pd.DataFrame(list(map(dict, list(filter(lambda x: x is not None, posting)))))
    #df.to_csv("housing.csv")

if __name__ == "__main__":
    MAXPRICE = 800

    if os.path.exists("housing.csv"):
        #df = pd.DataFrame.from_csv("housing.csv")
        #previous_links = df["links"]
        previous_links = []
    else:
        previous_links = []

    posts = crawl_craiglist({
        "max_price": MAXPRICE,
        "previous": []
    })

    obj_to_dataframe(map(process_posting, posts))


