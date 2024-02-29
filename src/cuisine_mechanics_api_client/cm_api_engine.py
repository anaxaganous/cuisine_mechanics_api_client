
import requests
from urllib.parse import urljoin
import sys
import json

class APIClient:
    API_TOKEN_PAIR_PATH = "/api/token/pair"
    API_TOKEN_REFRESH_PATH = "/api/token/refresh"
    API_TOKEN_VERIFY_PATH = "/api/token/verify"

    ADD_RECIPE_FROM_LDJSON_PATH = "/api/v1/recipes/from-ldjson"

    LIST_INTERNET_SOURCES_PATH = "/api/v1/internet_sources"


    def __init__(self, url_base, username, password):
        self.url_base = url_base
        self.username = username
        self.password = password
        self.access_token = None
        self.refresh_token = None
        self.session = requests.Session()
        self.last_status_code = None
        self.last_content = None

    def update_header(self):
        self.session.headers.update({
            "Authorization": f"Bearer {self.access_token}"
        })

    def cycle_token(self):
        if self.refresh_token:
            url = urljoin(self.url_base, self.API_TOKEN_REFRESH_PATH)
            msg = {
                "refresh": self.refresh_token,
            }
            response = self.session.post(url, json=msg)
            if response.status_code == 200:
                response_json = response.json()
                self.access_token = response_json['access']
                self.refresh_token = response_json['refresh']
                self.update_header()
                return True

        url = urljoin(self.url_base, self.API_TOKEN_PAIR_PATH)
        msg = {
            "username": self.username,
            "password": self.password,
        }
        response = self.session.post(url, json=msg)
        if response.status_code != 200:
            return False

        response_json = response.json()
        self.access_token = response_json['access']
        self.refresh_token = response_json['refresh']
        self.update_header()
        return True

    def add_recipe_ldjson(self, original_url, ldjson_str):
        url = urljoin(self.url_base, self.ADD_RECIPE_FROM_LDJSON_PATH)
        msg = {
            "url": original_url,
            "ldjson": ldjson_str,
        }
        response = self.session.post(url, json=msg)
        self.last_status_code = response.status_code
        self.last_content = response.content
        if response.status_code == 200:
            return True
        
        if response.status_code == 409:
            print(f"Recipe already exists for url {original_url}")
            return True
        if response.status_code == 422:
            print(f"Parsing error on recipe for url {original_url}")
            return True
        if response.status_code == 401:
            if self.cycle_token():
                return self.add_recipe_ldjson(original_url, ldjson_str)

        
        print(f"Add ldjson recipe got status code {response.status_code} with content: {response.content}")
        return False
    
    def list_internet_sources(self, title__icontains=None, authors__icontains=None, description__icontains=None, url__iexact=None, url__icontains=None):
        url = urljoin(self.url_base, self.LIST_INTERNET_SOURCES_PATH)
        msg = {}
        if title__icontains is not None:
            msg['title__icontains'] = title__icontains
        if authors__icontains is not None:
            msg['authors__icontains'] = authors__icontains
        if description__icontains is not None:
            msg['description__icontains'] = description__icontains
        if url__iexact is not None:
            msg['url__iexact'] = url__iexact
        if url__icontains is not None:
            msg['url__icontains'] = url__icontains
        
        results = []
        while url: 
            response = self.session.get(url, data=msg)
            js = response.json()
            url = js['next']
            results.extend(js['results'])
        return results


if __name__ == "__main__":
    client = APIClient("http://mintydev:8000", username="admin", password="admin")
    with open(sys.argv[1], "r") as ldjson_file:
        for line in ldjson_file:
            js = json.loads(line)
            print(f"Now working adding recipe from {js['url']}")
            status = client.add_recipe_ldjson(original_url=js['url'], ldjson_str=js['ldjson'])
            if not status:
                print(f"Failure during recipe add. Stopping. Failed recipe is url: {js['url']}")
                break
                