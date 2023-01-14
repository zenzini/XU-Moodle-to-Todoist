import markdownify as md
import re
import json

from moodle import Moodle
from todoist_api_python.api import TodoistAPI
from datetime import datetime

doist = TodoistAPI('168fac870c8650d3a6ea1ab7b049b8c83cdd73ac')
url = 'https://elearn.xu.edu.ph/webservice/rest/server.php?moodlewsrestformat=json'
token = 'f3d438c32a3444766af8ced8a5b7ff55'
xu = Moodle(url, token)


# id's: cscc 14.1 b, cscc 15 b, cscc 21.1 b,
# cscc 32.1 b cscc 37 b, fl 2.3 ccb,
# math 117 edb, philo 23


def main():
    print(datetime.now().strftime("%B %d, %Y | %H:%M:%S"))
    # crit = xu('core_webservice_get_site_info')
    ids = {10771: 2161285287, 9505: 2161285285, 10715: 2161285292,
           10717: 2161285298, 9688: 2161345015, 10871: 2161354487,
           9914: 2161349813, 10523: 2161285296}

    with open("store.json", 'r') as f:
        exists = json.load(f)

    for key in ids:
        dCal = (xu('core_calendar_get_calendar_upcoming_view', courseid=key))
        # for key2, value in dict.items(dCal):
            # print(key2, ' : ', value)
            # print('\n')

        updates(key, ids, exists)

        for event in dCal['events']:
            todo(event, ids, key, exists)

    print('________________________________________')
    with open('store.json', 'w') as f:
        json.dump(exists, f, indent=2)


def todo(event, ids, key, exists):
    name = event['name']
    eUrl = event['url']
    time = validTime(event['formattedtime'])

    modded = datetime.fromtimestamp(event['timemodified']).strftime("%B %d %Y, %H:%M:%S")
    try:
        starts = datetime.fromtimestamp(event['course']['startdate']).strftime("%B %d %Y, %H:%M:%S")
    except Exception as error:
        starts = datetime.fromtimestamp(event['timestart']).strftime("%B %d %Y, %H:%M:%S")

    dReq = md.markdownify(event['description'], heading_style="ATX")
    desc = (dReq + '--- \n\n **Opens:** ' + starts + '\n\n **Last modified:** ' + modded +
            '\n\n**[Click me to open the requirement in E-Learn.](' + eUrl + ')**')

    result = inTodo(name, modded, exists, time)

    if result < 2:
        if result == 1:
            desc = '**RECENTLY MODIFIED!** \n\n' + desc
        try:
            doist.add_task(
                content=name,
                description=desc,
                due_string=time,
                due_lang='en',
                priority=2,
                label_ids=[
                    ids[key],
                    2159902367],
                section_id=96723857,
            )
        except Exception as error:
            print(error)


def inTodo(name, modded, exists, time):
    try:
        if name not in exists["events"].keys():
            add = {name: {"modified": "", "due": ""}}
            exists["events"].update(add)

            exists["events"][name]["modified"] = modded
            exists["events"][name]["due"] = time

            print('Task: ' + name + ' has been added!')
            with open('store.json', 'w', encoding="utf-8") as f:
                json.dump(exists, f, indent=2)
            return 0

        elif exists["events"][name]["modified"] != modded:
            exists["events"][name]["modified"] = modded
            exists["events"][name]["due"] = time

            print('Task has been recently modified!')
            with open('store.json', 'w', encoding="utf-8") as f:
                json.dump(exists, f, indent=2)
            return 1

        elif exists["events"][name]["modified"] == modded:
            print('Task: ' + name + ' has already been added!')
            return 2

    except KeyError as e:
        print("A KeyError. Oops! Error: ", e)

    print('\n')


def updates(key, ids, exists):
    try:
        sKey = str(key)
        e = exists["update"][sKey]

        dUpdate = (xu('core_course_get_updates_since', courseid=key, since=e))
        print(dUpdate)

        if dUpdate['instances']:
            for x in range(len(dUpdate['instances'])):
                uList = "**Updates on:** "
                d = datetime.fromtimestamp(int(e)).strftime("%B %d, %Y | %H:%M:%S")
                header = "* UPDATE on a " + dUpdate['instances'][x]['contextlevel'] + "!"

                rUpdates = len((dUpdate['instances'][x]["updates"]))
                for y in range(rUpdates):
                    if not y == (rUpdates - 1):
                        uList += dUpdate['instances'][x]["updates"][y]["name"] + ", "
                    else:
                        uList += dUpdate['instances'][x]["updates"][y]["name"] + "."

                desc = "**Updated since:** " + d + "\n" + uList + "\n **ID:** " + str(dUpdate['instances'][x]['id'])

                exists["update"][sKey] = str(round(datetime.timestamp(datetime.now())))

                try:
                    doist.add_task(
                        content=header,
                        description=desc,
                        due_lang='en',
                        priority=1,
                        label_ids=[
                            ids[key],
                            2159902367],
                        section_id=97223485,
                    )

                except Exception as error:
                    print(error)

    except TypeError as e:
        print("A TypeError. Oops! Error: ", e)


def validTime(tTemp):
    time = md.markdownify(tTemp, heading_style="ATX")
    time = re.sub(r'https?:\/\/\S*', '', time)
    time = " ".join(re.findall("[a-zA-Z0-9:,]+", time))

    return time


if __name__ == '__main__':
    main()
