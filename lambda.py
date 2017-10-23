from base64 import b64decode
from urlparse import parse_qs
import boto3
import json
import logging
import re
import urllib2
import random
import datetime

expected_token = "YOUR SLACK TOKEN HERE"

logger = logging.getLogger()
logger.setLevel(logging.INFO)

spreadsheet = "SPREADSHEET ID"
locations = []


def lambda_handler(event, context):
    req_body = event["body"]
    params = parse_qs(req_body)
    token = params["token"][0]
    if token != expected_token:
        logger.error("Request token (%s) does not match expected", token)
        raise Exception("Invalid request token")

    #user = params["user_name"][0]
    #command = params["command"][0]
    #channel = params["channel_name"][0]

    # get lunch data from google speadsheets
    parse(spreadsheet)
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


def parse(url):
    spreadsheetUrl = "https://spreadsheets.google.com/feeds/list/%s/od6/public/basic?alt=json" % url
    data = urllib2.urlopen(spreadsheetUrl).read()
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
    isTuesday = True if datetime.datetime.now().weekday() == 1 else False

    pick = random.choice(locations)

    # select a weighted choice
    total = 0
    for location in locations:
        weight = 1
        try:
            weight = int(location["weight"])
        except:
            pass

        # taco-tuesday-bias
        if isTuesday and "emoji" in location and location["emoji"] == ":taco:":
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
