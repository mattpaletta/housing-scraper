import logging
import os
import sys

import pandas as pd
import requests
from bs4 import BeautifulSoup


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


def dist_lat_long_to_km(lat1, lon1, lat2, lon2):
    from geopy.distance import distance
    return distance((lat1, lon1), (lat2, lon2)).km


def process_posting(craigslist_posting: CraiglistPosting):
    page = requests.get(craigslist_posting.link)
    soup = BeautifulSoup(page.content, "html.parser")

    map = soup.select_one("#map")
    try:
        post_body = soup.select_one("#postingbody").get_text()
    except:
        logging.info("Post was probably deleted.")
        return

    if map is not None:
        latitude = map.get("data-latitude")
        longitude = map.get("data-longitude")

        dist_to_uvic = dist_lat_long_to_km(float(latitude), float(longitude),
                                           48.4634, -123.3117)

        if dist_to_uvic > 10:
            print(craigslist_posting.link)
            logging.info("Place too far: " + str(dist_to_uvic))
            return
    else:
        logging.info("No map found.")
        dist_to_uvic = 0

    for bad in ["female only",
                "until september",
                "until august",
                "for female student"]:
        if str(post_body).lower().__contains__(bad):
            logging.info("Post matches exclusion keywords.")
            return

    craigslist_posting.distance = round(dist_to_uvic, 4)
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
                pass


def obj_to_dataframe(posting):
    postings_dict = []
    for post in posting:
        if post is not None:
            x = post.__dict__
            postings_dict.append(x)

    df = pd.DataFrame(postings_dict)
    df = df[['name', 'price', 'distance', 'link', 'desc']]
    df.to_csv("housing.csv")


if __name__ == "__main__":
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s - [%(filename)s:%(lineno)s]')
    ch.setFormatter(formatter)
    root.addHandler(ch)

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
