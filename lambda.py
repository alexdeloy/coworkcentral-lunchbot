from urllib.parse import urlsplit, parse_qs
from urllib.request import urlopen
import datetime
import json
import random
import re
import os

spreadsheet = os.environ["spreadsheet"]
locations = []

def lambda_handler(event, context):
    if "body-json" in event:
        body = event["body-json"]
        params = parse_qs(urlsplit("http://cowork.localhost/?" + body).query)
    else:
        venue = event.get("venue", 0)
        vote = event.get("vote", 0)
        voteLocation(venue, vote)
        return

    sheet = 1 # defaults to Cais de Sodré
    if params["channel_name"][0] == "cais-do-sodré":
        sheet = 1
    if params["channel_name"][0] == "principe-real":
        sheet = 2

    # get lunch data from google speadsheets
    parse(spreadsheet, sheet)
    pick = pickRandomLocation()

    emojis = [
        [":+1:", ":-1:"],
        [":yum:", ":nauseated_face:"],
        [":arrow_up:", ":arrow_down:"],
        [":knife_fork_plate:", ":poop:"]
    ]

    labels = [
        ["Yay", "Nay"],
        ["Yes", "No"],
        ["Sure!", "Nah.."],
        ["Recommend", "No"]
    ]

    emoji = random.choice(emojis)
    label = random.choice(labels)

    messageText = "%s \n%s" % (pick["emoji"], pick["type"])

    if "address" in pick:
        messageText += "\n> <%s|%s>" % ("https://www.google.com/maps/place/" + pick["address"], pick["address"])

    if "link" in pick:
        messageText += "\n> <%s|%s>" % (pick["link"], "Website")

    slackMessage = {
        "response_type": "in_channel",
        "channel": "lunch",
        "username": "Lunchy",
        "icon_emoji": pick["emoji"],
        "attachments": [
            {
                "color": "#D82C00",
                "title": "What about *%s* today?" % (pick["location"],),
                "text": messageText
            },
            """
            {
                "title": "Would you recommend this ",
                "callback_id": "lunchrecommend",
                "actions": [
                    {
                        "text": "%s %s" % (emoji[0], label[0]),
                        "type": "button",
                        "url": "http://localhost/yes"
                    },
                    {
                        "text": "%s %s" % (emoji[1], label[1]),
                        "type": "button",
                        "url": "http://localhost/no"
                    }
                ]
            }
            """
        ]
    }

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


def voteLocation(venue, vote):
    pass

def pickRandomLocation():
    isWedneysay = True if datetime.datetime.now().weekday() == 2 else False

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
            pick = locations[k]
            break

    # fill up to prevent errors
    if "emoji" not in pick:
        pick["emoji"] = ":knife_fork_plate:"
    if "type" not in pick:
        pick["type"] = "no description set"

    return pick
