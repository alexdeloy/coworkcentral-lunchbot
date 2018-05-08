from urllib.parse import urlsplit, parse_qs
from urllib.request import urlopen
import datetime
import json
import random
import re

spreadsheet = "" #spreadsheet id goes here
locations = []

def lambda_handler(event, context):
    body = event["body-json"]
    params = parse_qs(urlsplit("http://cowork.localhost/?" + body).query) # add a dummy hostname for parsing

    sheet = 1 # defaults to Cais de Sodré
    if params["channel_name"][0] == "cais-do-sodre":
        sheet = 1
    if params["channel_name"][0] == "principe-real":
        sheet = 2

    # get lunch data from google speadsheets
    parse(spreadsheet, sheet)
    pick = pickRandomLocation()

    slackMessage = {
        "response_type": "in_channel",
        "channel": "lunch",
        "username": "Lunchy",
        "icon_emoji": pick["emoji"],
        "text": "What about *%s* today? \n %s \n>%s" % (pick["location"], pick["emoji"], pick["type"])
    }

    if "address" in pick:
        slackMessage["text"] += "\n> <%s|%s>" % ("https://www.google.com/maps/place/" + pick["address"], pick["address"])

    if "link" in pick:
        slackMessage["text"] += "\n> <%s|%s>" % (pick["link"], "Website")

    return slackMessage


def parse(url, sheet):
    spreadsheetUrl = "https://spreadsheets.google.com/feeds/list/%s/%s/public/basic?alt=json" % (url, sheet)
    data = urlopen(spreadsheetUrl).read()
    output = json.loads(data)
    entries = output["feed"]["entry"]
    for entry in entries:
        matches = re.findall("(\w+): (.+?(?=(?:, \w+:|$)))", entry["content"]["$t"])
        content = {}
        content["location"] = entry["title"]["$t"]
        for match in matches:
            content[match[0]] = match[1]
        locations.append(content)


def pickRandomLocation():
    isWedneysay = True if datetime.datetime.now().weekday() == 2 else False

    pick = random.choice(locations)

    # select a weighted choice
    total = 0
    for location in locations:
        weight = 1
        try:
            weight = int(location["weight"])
        except:
            pass

        # taco-wednesday-bias
        if isWedneysay and "emoji" in location and location["emoji"] == ":taco:":
            weight *= 5

        total += weight

    treshold = random.uniform(0, total)
    for k, location in enumerate(locations):
        total -= int(location["weight"])
        if total < treshold:
            return locations[k]

    # fill up to prevent errors
    if "emoji" not in pick:
        pick["emoji"] = ":knife_fork_plate:"
    if "type" not in pick:
        pick["type"] = "no description set"
    return pick
