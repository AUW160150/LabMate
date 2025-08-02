import requests
from bs4 import BeautifulSoup

def fetch_plasmid_info(plasmid_id):
    url = f"https://www.addgene.org/{plasmid_id}/"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    name = soup.find("h1").text.strip()
    features = [li.text for li in soup.select(".features-list li")]

    return {
        "name": name,
        "features": features,
        "url": url
    }
