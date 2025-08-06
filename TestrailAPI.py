


import base64
from datetime import datetime
import json
import math
import os
import sys
import time

import requests
import yaml
from exceptiongroup import catch
from wheel.macosx_libfile import read_mach_header

showTimes  = False
class APIClient:
    def __init__(self, base_url):
        self.user = ''
        self.password = ''
        if not base_url.endswith('/'):
            base_url += '/'
        self.__url = base_url + 'index.php?/api/v2/'

    def send_get(self, uri, filepath=None):
        """Issue a GET request (read) against the API.

        Args:
            uri: The API method to call including parameters, e.g. get_case/1.
            filepath: The path and file name for attachment download; used only
                for 'get_attachment/:attachment_id'.

        Returns:
            A dict containing the result of the request.
        """
        return self.__send_request('GET', uri, filepath)

    def send_post(self, uri, data):
        """Issue a POST request (write) against the API.

        Args:
            uri: The API method to call, including parameters, e.g. add_case/1.
            data: The data to submit as part of the request as a dict; strings
                must be UTF-8 encoded. If adding an attachment, must be the
                path to the file.

        Returns:
            A dict containing the result of the request.
        """
        return self.__send_request('POST', uri, data)

    def __send_request(self, method, uri, data):
        url = self.__url + uri

        auth = str(
            base64.b64encode(
                bytes('%s:%s' % (self.user, self.password), 'utf-8')
            ),
            'ascii'
        ).strip()
        headers = {'Authorization': 'Basic ' + auth}

        if method == 'POST':
            if uri[:14] == 'add_attachment':    # add_attachment API method
                files = {'attachment': (open(data, 'rb'))}
                response = requests.post(url, headers=headers, files=files)
                files['attachment'].close()
            else:
                headers['Content-Type'] = 'application/json'
                payload = bytes(json.dumps(data), 'utf-8')
                response = requests.post(url, headers=headers, data=payload)
        else:
            headers['Content-Type'] = 'application/json'
            response = requests.get(url, headers=headers)

        if response.status_code > 201:
            try:
                error = response.json()
            except:     # response.content not formatted as JSON
                error = str(response.content)
            raise APIError('TestRail API returned HTTP %s (%s)' % (response.status_code, error))
        else:
            if uri[:15] == 'get_attachment/':   # Expecting file, not JSON
                try:
                    open(data, 'wb').write(response.content)
                    return (data)
                except:
                    return ("Error saving attachment.")
            else:
                try:
                    return response.json()
                except: # Nothing to return
                    return {}



class APIError(Exception):
    pass


file = sys.argv[0]
pathname = os.path.dirname(file)

# Create a TestRail API client instance
client = APIClient("https://rl-test.com/")

def macDirectory(input_string):
    return input_string.replace('\\', '/')

try:
    with open(pathname + '\\Configuration.yaml', 'r') as f:
        config = yaml.safe_load(f)
        client.user = config["testrail"]["user"]
        client.password = config["testrail"]["apiKey"]
except:
    with open(pathname + '/Configuration.yaml', 'r') as f:
        config = yaml.safe_load(f)
        client.user = config["testrail"]["user"]
        client.password = config["testrail"]["apiKey"]


def finalTime(startTime):
    totalTime = round(time.time()-startTime)
    hours = totalTime // 3600
    minutes = (totalTime % 3600) // 60
    seconds = totalTime % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def getTestResults(test_id): #'status_id': 1-Passed, 2-Blocked, 3-Untested 4-Retest, 5-Failed, 6-NotApplicable, 7-NotYetImplemented, 8-Warned, 9-Assigned
    testResult = client.send_get("get_results/" + str(test_id))
    # print(testResult)
    return testResult

def getAllFinishedTestsCountFromTestRun(testrunId):
    total = 0
    plan = None
    try:
        plan = client.send_get("get_plan/" + str(testrunId))  #test plan
        total = plan.get("passed_count") + plan.get("blocked_count") +plan.get("retest_count") +plan.get("failed_count") +plan.get("custom_status1_count")+plan.get("custom_status2_count")+plan.get("custom_status3_count")+plan.get("custom_status4_count")+plan.get("custom_status5_count")+plan.get("custom_status6_count")+plan.get("custom_status7_count")
        # print(plan)
    except:
        # print("single test run")
        plan = client.send_get("get_tests/" + str(testrunId)) #single test run
        for t in plan.get("tests"):
            # print(t.get("status_id"))
            if t.get("status_id") != 3:
                total += 1

    return total

def getAllFinishedTestsCountFromMilestone(milestoneId):
    total = 0
    finishedTestRuns = getAllFinishedTestRunsFromMilestone(milestoneId)
    # print(finishedTestRuns)
    for t in finishedTestRuns:
        total += getAllFinishedTestsCountFromTestRun(t.get("id"))
    return total

def getAllSubMilestones(milestoneId): #get all sub-milestones and current milestone, and puts them into a list
    milestonesList = []
    milestone = client.send_get("/get_milestone/" + str(milestoneId))  ##idealy should use parent milestone: 8219
    # print(milestone)
    subMilestones = milestone["milestones"]
    for a in subMilestones:
        # print(a.get("name") + ": " + str(a.get("id")) )
        milestonesList.append(a)
    # print(milestonesList)
    return milestonesList

def find_all_occurrences(text, pattern):
    indices = []
    start_index = 0
    while True:
        index = text.find(pattern, start_index)
        if index == -1:
            break
        indices.append(index)
        start_index = index + 1
    return indices

def getAllBugsFromTestRun(testrunId): #finds all the bugs in test run and saves the test cases (case_id) affected
    startTime = time.time()
    bugs = {}
    tests = getTests(testrunId)
    # print(len(tests))
    # print("total test cases: " + str(len(tests)))
    for t in tests: #traverses all tests
        if t.get("status_id") != 1 and t.get("status_id") != 3 and t.get("status_id") != 6: #finds all tests that aren't  pass, untested or not applicable
            defect = getTestResults(t.get("id")).get("results")[0].get("defects") # get the results
            # print("defect: " , defect)
            if bugs.get(defect) is None and defect is not None: #new task identified (not in bugs)
                # print("adding new task: [" , defect, "] with " , str(t.get("case_id")))
                # print()

                # bugs[defect] = [client.send_get("/get_case/" + str(t.get("case_id")))]
                bugs[defect] = [t.get("case_id")] #test for speed
            elif defect is not None and bugs.get(defect) is not None: #preexisting task, but check to see if case id is included

                if bugs[defect].count(t.get("case_id")) == 0:
                    # bugs[defect].append(client.send_get("/get_case/" + str(t.get("case_id"))))
                    bugs[defect].append(t.get("case_id")) #test for speed
                    # print("add", t.get("case_id"), "to preexisting task:",defect)
                # else:
                    # print("do nothing,",t.get("id"),"already included in", defect)

    if showTimes: print("getAllBugsFromTestRun" + "(" + str(testrunId) + "): " + finalTime(startTime))
    return bugs

def getAllBugsFromMilestone(milestoneId):#finds all the bugs in a milestone and saves the test cases (case_id) affected
    startTime = time.time()
    bugs = {}
    testRuns = getAllFinishedTestRunsFromMilestone(milestoneId)
    totalTestCaseCount = 0
    for bugsInTestrun in testRuns: #traverse all test runs and get dict of -> taskId:[list of affected cases]
        print("\n"+ bugsInTestrun.get("name"))
        testRunBugs = getAllBugsFromTestRun(bugsInTestrun.get("id")) # try to make this not as taxing!!!!!!!!!!!!!!!!!
        # print(testRunBugs)

        for task in testRunBugs:#traverse each task testRunBugs
            # print(task)
            if bugs.get(task) is None: #task from testrunbug is not already in bugs, add it
                bugs[task] = testRunBugs[task]
                print("[milestone]adding new task: " , task)
                # print(testRunBugs[task])
            else:#task from testrunbug already in bugs, but need to check if test cases affected are different

                for affectedTestCase in testRunBugs[task]:#traverse each affected test case in bug list
                    # print(bugs[task])
                    # print(affectedTestCase)
                    if bugs[task].count(affectedTestCase) == 0:
                        print("[milestone]adding case to existing " + task + ":" , affectedTestCase)
                        bugs[task].append(affectedTestCase)

    if showTimes: print("getAllBugsFromMilestone" + "(" + str(milestoneId) + "): " + finalTime(startTime))
    return bugs




def getAllFinishedTestRunsFromMilestone(milestoneId): #gets all test runs from a milestone (excludes test runs that have untested test cases)
    testRunsList = []
    testRuns = client.send_get("/get_plans/" + str(157) + "&milestone_id=" + str(milestoneId))
    # print(testRuns)
    testRuns = testRuns.get("plans")
    for a in testRuns:
        # print(a)
        if a.get("untested_count") > 0:
            continue
        testRunsList.append(a)
    # print(testRuns)
    return testRunsList #returns a []

def getAllTestRunsFromMilestone(milestoneId):
    testRunsList = []
    testRuns = client.send_get("/get_plans/" + str(157) + "&milestone_id=" + str(milestoneId))
    # print(testRuns)
    testRuns = testRuns.get("plans")
    for a in testRuns:
        # print(a)
        testRunsList.append(a)
    # print(testRuns)
    return testRunsList  # returns a []


def getAllUnfinishedTestRunsFromMilestone(milestoneId): #gets all test runs from a milestone (excludes test runs that have untested test cases)
    testRunsList = []
    testRuns = client.send_get("/get_plans/" + str(157) + "&milestone_id=" + str(milestoneId))
    # print(testRuns)
    testRuns = testRuns.get("plans")
    for a in testRuns:
        # print(a)
        if a.get("untested_count") > 0:
            testRunsList.append(a)

    # print(testRuns)
    return testRunsList #returns a []



def StuSanityMilestoneReport(parentMilestoneId):#only counts testruns in sub-milestones labeled with "sanity" or "stu", ignores every other milestones
    parentMilestoneInfo = client.send_get("/get_milestone/" + str(parentMilestoneId))
    milestones = getAllSubMilestones(parentMilestoneId)
    stuMileStoneIds = []
    sanityMileStoneIds = []
    for m in milestones:#adds saves all the intended milestone ids
        # print(m)
        if m.get("name").lower().count("sanity") > 0:
            # print("added to sanity")
            sanityMileStoneIds.append(m.get("id"))
        elif m.get("name").lower().count("stu") > 0:
            # print("added to stu")
            stuMileStoneIds.append(m.get("id"))
    totalStuTestRuns = []
    totalSanityTestRuns = []

    #goes through each stu milestone and add it to total count
    for m in stuMileStoneIds:
        totalStuTestRuns = totalStuTestRuns + getAllFinishedTestRunsFromMilestone(m)

    #goes through each sanity milestone and add it to total count
    for m in sanityMileStoneIds:
        totalSanityTestRuns = totalSanityTestRuns + getAllFinishedTestRunsFromMilestone(m)


    print("\n--------------------STU/Sanity Testrail Report--------------------")
    print(parentMilestoneInfo.get("name"))
    print("total testruns completed in milestone: " + str(len(totalStuTestRuns) + len(totalSanityTestRuns)))
    print("totalStuTestRuns: " + str(len(totalStuTestRuns)))
    print("totalSanityTestRuns: " + str(len(totalSanityTestRuns)))
    print("------------------------------------------------------------------")




def addTestResult (status_id,comment,defects,version,test_id,custom_device,elapsed):#'status_id': 1-Passed, 2-Blocked, 3-Untested 4-Retest, 5-Failed, 6-NotApplicable, 7-NotYetImplemented, 8-Warned, 9-Assigned
    request_body = {
        "status_id": status_id,
        "comment": str(comment),
        "elapsed": str(elapsed),
        "defects": str(defects),
        "version": str(version),
        "custom_device":custom_device,
    }
    try:
        addTest = client.send_post("add_result/"+str(test_id), request_body)
        print(addTest)
    except Exception as e:
        print("test case does not exist")
        print(e)


def getMilestoneName(milestoneId):
    milestone = client.send_get("/get_milestone/" + str(milestoneId))
    return milestone.get("name")

def getTests(testrunId): ##takes in id of test plan, returns all tests
    startTime = time.time()
    plan = None
    testSuiteRuns = []
    tests = []
    try:
        plan = client.send_get("get_plan/" + str(testrunId))
    except:
        #Single Test Run
        run = client.send_get("get_tests/" + str(testrunId))
        offset = 0
        while len(run.get("tests")) != 0: #done to accommodate when there are more than 250 test cases
            for t in run.get("tests"):
                # print(t.get("title"))
                tests.append(t)
            offset += 250
            run = client.send_get("get_tests/" + str(testrunId) + "&offset=" + str(offset))

        # print(run)
        for t in run.get("tests"):
            tests.append(t)


        if showTimes: print("getTests" + "(" + str(testrunId) + "): "+ str(len(tests))+ "  ->" + finalTime(startTime))
        return tests  # returns a list []


    #get all test runs/suites
    for a in plan.get('entries'):
        # print(a)
        testSuiteRuns.append(a.get('runs')[0].get('id'))
    #get all tests from test runs/suites
    # print(testSuiteRuns)
    for a in testSuiteRuns:
        run = client.send_get("get_tests/" + str(a))

        offset = 0
        while len(run.get("tests")) != 0:#done to accommodate when there are more than 250 test cases
            for t in run.get("tests"):
                # print(t.get("title"))
                tests.append(t)
            offset += 250
            run = client.send_get("get_tests/" + str(a) + "&offset=" + str(offset))
            # print("offset: " + str(offset) + "        total: " + str(len(run.get("tests"))))

        for t in run.get("tests"):
            tests.append(t)

    if showTimes: print("getTests" + "(" + str(testrunId) + "): " + finalTime(startTime))
    return tests #returns a list []




def CTP(plan_1_id,plan_2_id,newVersion, device): # from plan1 to plan 2
    plan1 = getTests(plan_1_id)
    plan2 = getTests(plan_2_id)
    for p1 in plan1:
        print()
        print(p1.get("title"))
        p2Id = ""
        try:
            p1Results = getTestResults(p1.get("id")).get("results")[0]
        except:
            continue


        for p2 in plan2:
            if p2.get("title") == p1.get("title"):
                p2Id = str(p2.get("id"))
                break
        if len(p2Id) > 0:
            # print(p1Results)
            addTestResult(p1Results.get('status_id'), p1Results.get('comment'), p1Results.get('defects'), newVersion, p2Id, device, "")

        else:
            print(p1.get("title") , " is not found in plan 2")

def createDailyReport(milestoneId, date, name):
    milestones = getAllSubMilestones(milestoneId)
    # print(milestones)
    testRuns = []
    for m in milestones:
        testRuns += getAllFinishedTestRunsFromMilestone(m.get("id"))
    workedOnTestRuns = []
    for tr in testRuns:
        # print(tr.get("name"))
        if tr.get("name").count(name) > 0 and tr.get("name").count(date) > 0:
            workedOnTestRuns.append(tr)

    for a in workedOnTestRuns:
        # print(a)
        print(a.get("name"), a.get("url"))
        mr = getTests(a.get("id"))
        oneResult = getTestResults(mr[0].get("id")).get("results")[0]
        # print(oneResult)
        print("Device(s): " + str(oneResult.get("custom_device")))
        print("Status: " , "\033[1m" , math.ceil(round(((float(a.get("passed_count"))/len(mr)) * 100),2)),"% Passed, ", math.ceil(round(((float(a.get("failed_count"))/len(mr)) * 100),2)),"% Failed", "\033[0m")
        print("Build: " ,oneResult.get("version")) # work on getting build


        print()

def getAllCaseIdFromTestrun(testrunId):
    tests = getTests(testrunId)
    testcases = []

    for t in tests:
        # print(t + "\n")
        testcases.append(t.get("case_id"))

    return testcases

def getTestSuiteAndCaseIds(testrunId):
    startTime = time.time()
    plan = None
    testSuiteRuns = []
    suiteEntries = {}
    tests = []
    try:
        plan = client.send_get("get_plan/" + str(testrunId))
    except:
        # Single Test Run
        run = client.send_get("get_tests/" + str(testrunId))
        offset = 0
        while len(run.get("tests")) != 0:  # done to accommodate when there are more than 250 test cases
            for t in run.get("tests"):
                # print(t.get("title"))
                tests.append(t)
                # suiteEntries[a.get("suite_id")].append(t.get("case_id")) #might not work with just one run (work on this when you get back)
            offset += 250
            run = client.send_get("get_tests/" + str(testrunId) + "&offset=" + str(offset))

        # print(run)
        for t in run.get("tests"):
            tests.append(t)
            # suiteEntries[a.get("suite_id")].append(t.get("case_id")) #might not work with just one run (work on this when you get back)

        if showTimes: print("getTests" + "(" + str(testrunId) + "): " + str(len(tests)) + "  ->" + finalTime(startTime))
        return suiteEntries  # returns a list []



    # get all test runs/suites

    for a in plan.get('entries'):
        # print("Printing Entries: " , a)######################
        testSuiteRuns.append(a.get('runs')[0])#######################
        suiteEntries[a.get("suite_id")] = [] ###############################


    # get all tests from test runs/suites
    # print("testSuiteRuns: " ,testSuiteRuns)
    for a in testSuiteRuns:
        run = client.send_get("get_tests/" + str(a.get('id')))

        offset = 0
        while len(run.get("tests")) != 0:  # done to accommodate when there are more than 250 test cases
            for t in run.get("tests"):
                # print(t.get("title"))
                tests.append(t)
                suiteEntries[a.get("suite_id")].append(t.get("case_id"))
            offset += 250
            run = client.send_get("get_tests/" + str(a.get('id')) + "&offset=" + str(offset))
            # print("offset: " + str(offset) + "        total: " + str(len(run.get("tests"))))

        for t in run.get("tests"):
            tests.append(t)
            suiteEntries[a.get("suite_id")].append(t.get("case_id"))

    if showTimes: print("getTests" + "(" + str(testrunId) + "): " + finalTime(startTime))


    # for t in tests:
    #     print(t.get("title"))




    return suiteEntries  # returns a list []

def createDailyTestRun(buildNum, milestoneIds):

    #grab testrun id
    testrunList = []
    templateTestrunList = []
    for m in milestoneIds:
        testrunList = getAllTestRunsFromMilestone(m)
        # print("m: " , m)

        for t in testrunList:
            # print(t.get("name"))
            if t.get("name").lower().count("[template]") == 1:
                print("using " + t.get("name"))
                templateTestrunList.append(t) #commented out for testing, uncomment later


    for t in templateTestrunList:
        newPlanId = -1 #change this to -1 later, this is for testing for now


        newName = t.get("name").replace("[TEMPLATE]", "Elygh-(" + datetime.now().strftime("%m/%d/%Y") + ")")
        newDescription = t.get("description").replace("Build:", "Build: " + str(buildNum))
        # newName += "notready" #delete this later




        print("newName: " + newName)
        print("newDescription: " + newDescription)

        request_body = {
            "name": newName,
            "description": newDescription,
            "milestone_id": t.get("milestone_id")
        }
        try:
            # print("adding plan...using" , 1120470 , " for now")
            addPlan = client.send_post("add_plan/157", request_body)
            print(addPlan)
            newPlanId = addPlan.get("id")
        except Exception as e:
            print("creating test run failed: " + t.get("name"))
            print(e)


        #need to figure out how to add run to plan entry


        print("t is: ",  t.get("id"))
        runEntries = getTestSuiteAndCaseIds(t.get("id"))
        print(runEntries)
        print("\n\n\n")



        print(runEntries)

        for r in runEntries:
            request_body = {
                "suite_id": r,
                "assignedto_id": 1,
                "include_all": False,
                "config_ids": [],
                "case_ids": runEntries[r]

            }
            addEntry = client.send_post("add_plan_entry/" + str(newPlanId), request_body) #uncomment this later





if __name__ == '__main__':
    totalStartTime = time.time()

    print("testrail API py file")
    # StuSanityMilestoneReport(8735)
    # CTP(1156432,1156455," 8479.0.1471", "Pismo P1.1 HMD")
    createDailyTestRun("8515.0.1471", [8867, 8868])
    # createDailyTestRun(123123, [8016,7946]) #pismo testing milestones



    print("\n\nTOTAL TIME: " + finalTime(totalStartTime))
