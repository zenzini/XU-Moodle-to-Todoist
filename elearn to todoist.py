import sys

import markdownify as md
import re
import json
import os
import traceback
import time as tm
import winrt.windows.ui.notifications as notifications
import winrt.windows.data.xml.dom as dom

from datetime import datetime
from dotenv import load_dotenv
from moodle import Moodle
from todoist_api_python.api import TodoistAPI

load_dotenv()
eToken = os.getenv("ELEARN")
tToken = TodoistAPI(os.getenv("DOIST"))

url = 'https://elearn.xu.edu.ph/webservice/rest/server.php?moodlewsrestformat=json'
xu = Moodle(url, eToken)
date = datetime.now().strftime("%B %d %Y, %A at %I:%M%p")
sDate = datetime.now().strftime("%b %d %y, %I:%M%p")
nEvents = ""

nManager = notifications.ToastNotificationManager
notifier = nManager.create_toast_notifier("C:\\Users\\User\\AppData\\Local\\Programs\\Python\\Python39\\python.exe")

def main():
    print("Running on " + date)

    with open("store.json", 'r') as f:
        exists = json.load(f)

    # crit = xu('core_webservice_get_site_info')
    # print(crit)

    for key in exists["ids"]:
        try:
            check = int
            dCal = xu('core_calendar_get_action_events_by_course', courseid=key)
            # for key2, value in dict.items(dCal):
            # print(key2, ' : ', value)
            # print('\n')

            updates(key, exists["ids"], exists)

            for event in dCal['events']:
                check = todo(event, exists["ids"], key, exists)

            print(check)
            if check == 1:
                tString = """
                <toast>
                    <visual>
                        <binding template='ToastGeneric'>
                            <text>
                """ + exists["ids"][key] + " has new requirements! " + """
                            </text>
                            <text> 
                """ + "Checked on " + sDate + ": \n\n" + nEvents + """
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
            """ + "Error with" + exists["ids"][key] + "!" + """"
                        </text>
                        <text> 
            """ + "Checked on " + sDate + ": \n\n" + traceback.format_exc() + """
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
            print("Error with " + exists["ids"][key] + "! Details: ")
            tm.sleep(0.01)
            traceback.print_exc()

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

    if result < 2:
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

        return 1

    return 0


def updates(key, ids, exists):
    nUps = 0
    tTemp = ""

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

                exists["update"][sKey] = str(round(datetime.timestamp(datetime.now())))

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

            tString = """
                        <toast>
                            <visual>
                                <binding template='ToastGeneric'>
                                    <text>
                        """ + exists["ids"][key] + " has new updates! " + """
                                    </text>
                                    <text> 
                        """ + "Checked on " + sDate + ": \n\n" + "There have been " + \
                      str(nUps) + " updates since last checked on " + format_time(int(e)) + """
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
    global nEvents
    try:
        if name not in exists["events"].keys():
            nEvents += name + "\n"
            add = {name: {"modified": "", "due": ""}}
            exists["events"].update(add)

            exists["events"][name]["modified"] = modded
            exists["events"][name]["due"] = time
            exists["events"][name]["tstamp"] = tstamp

            print('Task: ' + name + ' has been added!')
            with open('store.json', 'w', encoding="utf-8") as f:
                json.dump(exists, f, indent=2)
            return 0

        elif exists["events"][name]["modified"] != modded:
            nEvents += "UPDATED: " + name + "\n"
            exists["events"][name]["modified"] = modded
            exists["events"][name]["due"] = time
            exists["events"][name]["tstamp"] = tstamp

            print('Task has been recently modified!')
            with open('store.json', 'w', encoding="utf-8") as f:
                json.dump(exists, f, indent=2)
            return 1

        elif exists["events"][name]["modified"] == modded:
            delTodo(exists, name)
            return 2

    except KeyError as e:
        print("A KeyError. Oops! Error: ", e)

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
