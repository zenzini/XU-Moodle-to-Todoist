import markdownify as md
import re
import json
import os
import traceback
import winrt.windows.ui.notifications as notifications
import winrt.windows.data.xml.dom as dom
import requests

from datetime import datetime
from dotenv import load_dotenv
from moodle import Moodle
from todoist_api_python.api import TodoistAPI

load_dotenv()
get_token = "https://elearn.xu.edu.ph/login/token.php?username=" + os.getenv("user") + "&password=" + \
            os.getenv("pass") + "&service=moodle_mobile_app"

eToken_json = (requests.get(get_token)).json()
eToken = eToken_json["token"]
tToken = TodoistAPI(os.getenv("DOIST"))

url = 'https://elearn.xu.edu.ph/webservice/rest/server.php?moodlewsrestformat=json'
xu = Moodle(url, eToken)
date = datetime.now().strftime("%B %d %Y, %A at %I:%M%p")
sDate = datetime.now().strftime("%b %d %y, %I:%M%p")
nEvents = ""

nManager = notifications.ToastNotificationManager
notifier = nManager.create_toast_notifier("C:\\Users\\User\\AppData\\Local\\Programs\\Python\\Python39\\python.exe")

nUps = 0
nTasks = 0
nTUps = 0


def main():
    global nUps, nTasks, nTUps
    print("Running on " + date)

    with open("store.json", 'r') as f:
        exists = json.load(f)

    # crit = xu('core_webservice_get_site_info')
    # print(crit)

    for key in exists["ids"]:
        try:
            dCal = xu('core_calendar_get_action_events_by_course', courseid=key)
            # for key2, value in dict.items(dCal):
            # print(key2, ' : ', value)
            # print('\n')

            nUps = 0
            nTasks = 0
            nTUps = 0

            updates(key, exists["ids"], exists)

            for event in dCal['events']:
                todo(event, exists["ids"], key, exists)

            sTemp = ""

            print(nTasks)

            if nUps or nTasks or nTUps != 0:
                sKey = str(key)
                e = exists["update"][sKey]

                if nUps == 1:
                    sTemp += "There has been " + str(nUps) + " update since last checked on " + \
                             format_time(int(e))
                else:
                    sTemp += "There have been " + str(nUps) + " updates since last checked on " + \
                             format_time(int(e))

                if nTasks == 0 & nTUps == 0:
                    sTemp += ". "
                elif nTasks != 0 & nTUps == 0:
                    sTemp += " and " + str(nTasks) + " new requirement\s."
                elif nTasks != 0 & nTUps != 0:
                    sTemp += ", " + str(nTasks) + " new requirement\s and " + \
                             str(nTUps) + " requirement\s updated."
                elif nTasks == 0 & nTUps != 0:
                    sTemp += " and " + str(nTUps) + " requirement\s updated."

                exists["update"][sKey] = str(round(datetime.timestamp(datetime.now())))

                tString = """
                            <toast>
                                <visual>
                                    <binding template='ToastGeneric'>
                                        <text>
                            """ + exists["ids"][key] + " has new updates! " + """
                                        </text>
                                        <text> 
                            """ + sTemp + """
                                        </text>
                                    </binding>
                                </visual>
                                <audio silent='True'/>
                            </toast>
                              """

                # add notif

                # convert notification to an XmlDocument
                xDoc = dom.XmlDocument()
                xDoc.load_xml(tString)

                # display notification
                notifier.show(notifications.ToastNotification(xDoc))

        except Exception:
            tString = """
            <toast>
                <visual>
                    <binding template='ToastGeneric'>
                        <text>
            """ + "Error with " + exists["ids"][key] + "!" + """"
                        </text>
                        <text> 
            """ + sDate + ": \n" + traceback.format_exc() + """
                        </text>
                    </binding>
                </visual>
                <audio silent='True'/>
            </toast>
              """

            # add notif

            # convert notification to an XmlDocument
            xDoc = dom.XmlDocument()
            xDoc.load_xml(tString)

            # display notification
            notifier.show(notifications.ToastNotification(xDoc))

            print("\n")
            print("Error with " + exists["ids"][key] + "! Details: " + traceback.format_exc())

    print('________________________________________')
    with open('store.json', 'w') as f:
        json.dump(exists, f, indent=2)


def todo(event, ids, key, exists):
    name = event['name']
    eUrl = event['url']

    starts = ""
    desc = " "
    prio = ""

    tstamp = validTime(event['formattedtime'])
    time = format_time(int(tstamp))

    modded = format_time(event['timemodified'])

    try:
        starts = format_time(event['course']['startdate'])
    except Exception:
        starts = format_time(event['timestart'])

    result = inTodo(exists, name, modded, time, tstamp)

    if event['modulename'] == 'assign':
        prio = 3
    elif event['modulename'] == 'quiz':
        prio = 4
    else:
        prio = 2

    if result is None:
        print(name + " is past deadline!")

    elif result < 2:
        if result == 1:
            desc += '**RECENTLY MODIFIED!** \n\n'

        try:
            dReq = md.markdownify(event['description'], heading_style="ATX")
            desc += (dReq + '--- \n\n **Opens:** ' + starts + '\n\n **Last modified:** ' + modded +
                     '\n\n**[Click me to open the requirement in E-Learn!](' + eUrl + ')**')

            tToken.add_task(
                content=name,
                description=desc,
                due_string=time,
                due_lang='en',
                priority=prio,
                labels=[
                    ids[key],
                    "NEW"],
                section_id="96723857",
            )
        except Exception as error:
            print(error)


def updates(key, ids, exists):
    global nUps

    try:
        sKey = str(key)
        e = exists["update"][sKey]

        dUpdate = (xu('core_course_get_updates_since', courseid=key, since=e))

        if dUpdate['instances']:
            print(dUpdate)
            for x in range(len(dUpdate['instances'])):
                cid = dUpdate['instances'][x]['id']
                uList = ""
                new = (xu('core_course_get_course_module', cmid=cid))
                print(new)

                header = "* UPDATE on **" + str(new['cm']['name']) + "**!"
                nUps += 1
                cname = str(new['cm']['modname'])

                rUpdates = len((dUpdate['instances'][x]["updates"]))
                for y in range(rUpdates):
                    try:
                        iname = dUpdate['instances'][x]["updates"][y]["name"]
                        f = dUpdate['instances'][x]["updates"][y]["timeupdated"]
                        uList += "- " + iname + " on " + format_time(f)
                    except Exception:
                        iname = dUpdate['instances'][x]["updates"][y]["name"]
                        f = int(e)
                        uList += "- " + iname + " since last checked on " + format_time(f)

                    if not y == (rUpdates - 1):
                        uList += ", \n"
                    else:
                        uList += "."

                eUrl = "https://elearn.xu.edu.ph/mod/" + cname + "/view.php?id=" + str(cid)
                desc = "\n **Update on " + cname + ",** specifically: \n" \
                       + uList + '\n\n --- \n\n**[Click me to open the update in E-Learn!](' + eUrl + ')**'

                try:
                    tToken.add_task(
                        content=header,
                        description=desc,
                        due_lang='en',
                        labels=[
                            ids[key],
                            "NEW"],
                        section_id="97223485",
                    )

                except Exception as error:
                    print(error)

    except TypeError as e:
        print("A TypeError. Oops! Error: ", e)


def validTime(tTemp):
    time = md.markdownify(tTemp, heading_style="ATX")
    time = re.search("(?P<url>https?://[^\s]+)", time).group("url")
    time = " ".join(re.findall("[0-9]+", time))
    return time


def format_time(temp):
    fTime = datetime.fromtimestamp(temp).strftime("%B %d, %A at %I:%M%p")
    return fTime


def inTodo(exists, name, modded, time, tstamp):
    global nTUps, nTasks
    now = datetime.now()

    if int(datetime.timestamp(now)) < int(tstamp):
        try:
            if name not in exists["events"].keys():
                add = {name: {"modified": "", "due": ""}}
                exists["events"].update(add)

                exists["events"][name]["modified"] = modded
                exists["events"][name]["due"] = time
                exists["events"][name]["tstamp"] = tstamp

                print('Task: ' + name + ' has been added!')
                with open('store.json', 'w', encoding="utf-8") as f:
                    json.dump(exists, f, indent=2)

                nTasks += 1
                return 0

            elif exists["events"][name]["modified"] != modded:
                exists["events"][name]["modified"] = modded
                exists["events"][name]["due"] = time
                exists["events"][name]["tstamp"] = tstamp

                print('Task has been recently modified!')
                with open('store.json', 'w', encoding="utf-8") as f:
                    json.dump(exists, f, indent=2)

                nTUps += 1
                return 1

            elif exists["events"][name]["modified"] == modded:
                delTodo(exists, name)
                return 2

        except KeyError as e:
            print("A KeyError. Oops! Error: ", e)

        else:
            print(name + " is past deadline!")

    print('\n')


def delTodo(exists, name):
    now = datetime.now()
    if int(exists["events"][name]["tstamp"]) < int(datetime.timestamp(now)):
        print("Task: " + name + " has been added AND is past the deadline! Deleting...")
        del exists["events"][name]
    else:
        print("Task: " + name + " has been added AND is within deadline!")


if __name__ == '__main__':
    main()
