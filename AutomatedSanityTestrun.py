import datetime
import io
import os
import subprocess
import sys
import time


def verifyPythonLibInstalled():
    print("Verifying all PIP Needed Libraries are Installed...")
    installedLib = subprocess.getoutput("pip list")
    installedLibP3 = subprocess.getoutput("pip3 list")
    # print(installedLib)
    libraries = ["PyYAML", "requests", "pynput", "exceptiongroup"]
    for lib in libraries:
        if installedLib.count(lib) < 1 and installedLibP3.count(lib) < 1:
            print("\nInstalling: " + lib + "\n")
            subprocess.run("python -m pip install " + lib, shell=True)
            subprocess.run("python3 -m pip install " + lib, shell=True)

    print("All Python Libraries are Installed :)\n")
    time.sleep(1)


verifyPythonLibInstalled()
import TestrailAPI
import yaml

###############################################################################


maduieFlash = "maduie f -w && adb wait-for-device"
getFingerprint = "adb shell getprop ro.build.fingerprint"
logcat = "adb logcat --max-count 50"
shellServices = "adb shell service list"
cls = "cls"
rebootToFastboot = "adb reboot bootloader"
rebootToAdbFromFB = "fastboot reboot"
fastbootDevices = "fastboot devices"
adbDevices = "adb devices"
adbReboot = "adb reboot"
waitForAdb = "adb wait-for-device"
bootComplete = "adb shell getprop | grep sys.boot_completed"
adbRoot = "adb root && adb wait-for-device"
unitTest = 'adb shell "syndbosd_consumers_ctl stop && syndbosd_unit_tests && syndbosd_consumers_ctl start && exit"'
updateFirmware = 'adb shell "syndbosd_consumers_ctl stop && fw_init --syndbosd && syndbosd_print_fw_version && syndbosd_consumers_ctl start && exit"'
audioCheck = "adb shell audio_tool -m wav_player -s 450 --volume 15"
sensorToolCommand1 = "adb shell sensor_tool -Pdownward-active_slots -PworldTracking-active_slots -Peye-active_slots -Tdownward-codecOnHands-2 -TworldTracking-lowLightHandsDoubleFlood-2 -Teye-utilityNoSequencing-2 -t 10 --exp --gain"
sensorToolCommand2 = "adb shell sensor_tool -PworldTracking-active_slots -PworldTracking-hand -Peye-active_slots -Tdownward-empty-0 -TworldTracking-lowLightHandsFlood-2 -TworldTracking-lowLightHandsDoubleFlood-4 -TworldTracking-lowLightController-6 -Teye-utilityNoSequencing-2 -t 10 --exp --gain"
cameraSetup = (
    "adb root && adb remount && adb shell stop trackingservice mrsystemservice"
)
slamOnly = "adb shell cameratool -i 0 -i 1 -i 2 -i 3 -t 10"
etOnly = "adb shell cameratool --cascade -t 10"
slamEt = "adb shell cameratool -i 0 -i 1 -i 2 -i 3 -i 6 -i 7 -i 8 -i 9 -t 10"
dtcOnly = "adb shell cameratool -i 4 -i 5 -t 10"
slamDtcEt = "adb shell cameratool -C --cascade -t 10"
vrsRecorder = ""
bluetoothDiscovery = (
    "adb shell am broadcast -a com.oculus.vrbtcontrol.EVENT -n com.oculus.vrbtcontrol/.VrBtControlBroadcastReceiver --es cmd_type "
    "DISCOVER"
    ""
)

bluetoothGetEvent = "adb shell getevent -c 500"
deviceIdleDisable = "adb shell dumpsys deviceidle disable"
wifiScan = "adb shell cmd wifi status && adb shell cmd wifi set-wifi-enabled enabled && adb shell cmd wifi start-scan && adb shell cmd wifi list-scan-results"
wifiPing = 'adb shell "ping -c 5 -w 10 www.facebook.com"'

curTime = ""

# Configurations
curBuild = ""
pathname = ""
resultName = ""
results = ""
runVrsPlayer = ""
planId = ""
testList = []
useTestrail = False  # change to False when testing -> makes the program not send to testrail api when false
curDevice = ""
wifiSanityNetwork = ""
wifiSanityPassword = ""
wifiCastNetwork = ""  # wifi network of mobile hotspot
wifiCastPassword = ""
operatingSystem = ""
bluetoothDevice = ""
wifiCastIpPing = ""
maduieSkoobeUsername = ""
maduieSkoobePassword = ""
maduieSkoobeNetworkName = ""
maduieSkoobeNetworkPassword = ""
maduieUsePersonalSO = False
pythonVersion = ""


class Tee(io.TextIOWrapper):
    def __init__(self, *files):
        self.files = files
        super().__init__(io.BytesIO(), encoding="utf-8")

    def write(self, message):
        for file in self.files:
            file.write(message)

    def flush(self):
        for file in self.files:
            file.flush()


class OutputCapture:
    def __init__(self):
        self.output = io.StringIO()

    def __enter__(self):
        self.original_stdout = sys.stdout
        sys.stdout = Tee(sys.stdout, self.output)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout = self.original_stdout
        if exc_type is not None:
            raise

    def get_output(self):
        return self.output.getvalue()


def getPlanId():
    return planId


def directory(input_string):
    if operatingSystem.count("mac") > 0:
        return input_string.replace("\\", "/")
    return input_string


def saveResult(
    caseId, testName, testResult, elapsed
):  # used to save test result in text file and send it to test rail if testResult is True
    print("\n" + str(caseId) + ": " + testName)
    results.write("\n\n" + str(caseId) + ": " + testName + "\n")
    # for a in testList:
    #     print(a.get("case_id") , ": " , a.get("title"))
    if testResult:
        if useTestrail:
            try:
                testId = 0
                for t in testList:
                    # print(t.get("title"))
                    if t.get("case_id") == caseId:
                        # print("found test")
                        testId = t.get("id")
                        break
                TestrailAPI.addTestResult(
                    1, "", "", curBuild, testId, curDevice, elapsed
                )
            except:
                print("\n\nTest case not present in current test plan")
        results.write("(Automated)Results-> Passed")
        print("\n(Automated)Results-> Passed")
    else:
        results.write("(Automated)Results-> Failed")
        print("\n(Automated)Results-> Failed")


def finalTime(startTime):
    totalTime = round(time.time() - startTime)
    hours = totalTime // 3600
    minutes = (totalTime % 3600) // 60
    seconds = totalTime % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def flashingmaduie():
    testResult = True
    startTime = time.time()
    testName = (
        "Verify maduie flash commands flash correctly fetched userdebug build onto Device device"
    )
    caseId = 1564690071
    ########################################################################
    print("\n\n\n\n\n\n********" + testName + "********")
    time.sleep(2)
    ######## no maduie f -w command, this command proved to be too troublesome

    try:
        subprocess.run(waitForAdb, shell=True)
        time.sleep(1)
        maduieFlashBuild = "maduie f " + curBuild + " -w"

        subprocess.run("adb reboot bootloader", shell=True)
        time.sleep(10)
        print("disabling linux console")
        subprocess.run("fastboot oem disable-linux-console", shell=True)
        time.sleep(1)
        subprocess.run("fastboot reboot", shell=True)

        waitForBootComplete()
        print("\n\nattempting maduie f " + curBuild + " -w")
        flashOutput = str(
            subprocess.run(maduieFlashBuild, capture_output=True, shell=True)
        )
        print(flashOutput)

        while flashOutput.lower().count("fail") > 0:
            print("maduie FLASH FAILED, RETRY")
            subprocess.run("fastboot reboot", shell=True)
            waitForBootComplete()
            flashOutput = str(
                subprocess.run(maduieFlashBuild, capture_output=True, shell=True)
            )

        subprocess.run(waitForAdb, shell=True)

        waitForBootComplete()
        print("Build attempted to flash: " + curBuild)
        print("\nBuild Flashed: ")
        time.sleep(5)
        currentFingerprintOutput = subprocess.getoutput(getFingerprint)
        print(currentFingerprintOutput)
        if currentFingerprintOutput.count(curBuild) != 1:
            testResult = False
        if flashOutput.count("Waiting for the device to fully reboot") != 1:
            testResult = False
        subprocess.run(waitForAdb, shell=True)
    except subprocess.CalledProcessError as e:
        testResult = False

    saveResult(
        caseId, testName, testResult, finalTime(startTime)
    )  # saving result in txt file and sending to testRail


def fastbootUserFlash():
    testResult = True
    startTime = time.time()
    testName = ""
    caseId = 0

    testName = "Verify latest user build can be flashed onto Device device manually"
    caseId = 1602043051
    ########################################################################
    print("\n\n\n\n\n\n********" + testName + "********")
    time.sleep(1)

    try:
        subprocess.run(waitForAdb, shell=True)
        fastbootDownload = "maduie fetch-build -f user -i"

        print("\n\nDownloading fastboot USER Build...")
        downloadOutput = str(
            subprocess.run(fastbootDownload, capture_output=True, shell=True)
        )
        print(downloadOutput)

        addressText = ""
        print("operating systems: " + operatingSystem)
        if operatingSystem.count("windows") > 0:
            addressText = downloadOutput[downloadOutput.find("C:") :]
            addressText = addressText[: addressText.find("\\n")]
            addressText = addressText.replace("\\\\", "\\")
            print(directory(addressText))

        elif operatingSystem.count("mac") > 0:
            addressText = downloadOutput[downloadOutput.find("/Users") :]
            print(addressText)
            addressText = addressText[: addressText.find("\\n")]
            addressText = addressText.replace("\\\\", "\\")
            print(directory(addressText))

        addressText = directory(pythonVersion + " " + addressText + "\\flash_all.py")
        print("addressText: " ,addressText)

        print("\nrebooting into bootloader")
        subprocess.run("adb reboot bootloader", shell=True)
        time.sleep(15)

        print("Attempting: '", addressText, "'")
        time.sleep(1)
        print("\n\nFLASHING BUILD...")
        fastbootFlashOutput = subprocess.getoutput(addressText)
        print(fastbootFlashOutput)

        if waitForBootComplete():
            print("Build attempted to flash: " + curBuild)
            print("\nBuild Flashed: ")
        else:
            print("boot complete never returned, failing test case")
            testResult = False


        currentFingerprintOutput = subprocess.getoutput(getFingerprint)
        print(currentFingerprintOutput)

        if (
            fastbootFlashOutput.count(
                'REMINDER: YOU MUST FLASH WITH "-w" TO ERASE USERDATA WHEN:'
            )
            < 1
        ):
            print("did not finish build, failing test case")
            testResult = False


    except subprocess.CalledProcessError as e:
        testResult = False

    saveResult(
        caseId, testName, testResult, finalTime(startTime)
    )  # saving result in txt file and sending to testRail



def fastbootFlash():
    testResult = True
    startTime = time.time()
    testName = ""
    caseId = 0
    if operatingSystem.count("windows") > 0:
        testName = "Verify latest userdebug build can be flashed onto Device device manually with WINDOWS computer"
        caseId = 1558349195
    elif operatingSystem.count("mac") > 0:
        testName = "Verify latest userdebug build can be flashed onto Device device manually with MAC Computer"
        caseId = 1564664435
    ########################################################################
    print("\n\n\n\n\n\n********" + testName + "********")
    time.sleep(1)

    try:
        subprocess.run(waitForAdb, shell=True)
        fastbootDownload = "maduie fetch-build -n " + curBuild

        print("\n\nDownloading fastboot Build...")
        downloadOutput = str(
            subprocess.run(fastbootDownload, capture_output=True, shell=True)
        )
        print(downloadOutput)

        addressText = ""
        print("operating systems: " + operatingSystem)
        if operatingSystem.count("windows") > 0:
            addressText = downloadOutput[downloadOutput.find("C:") :]
            addressText = addressText[: addressText.find("\\n")]
            addressText = addressText.replace("\\\\", "\\")
            print(directory(addressText))

        elif operatingSystem.count("mac") > 0:
            addressText = downloadOutput[downloadOutput.find("/Users") :]
            print(addressText)
            addressText = addressText[: addressText.find("\\n")]
            addressText = addressText.replace("\\\\", "\\")
            print(directory(addressText))

        addressText = directory(pythonVersion + " " + addressText + "\\flash_all.py")
        print(addressText)

        print("\nrebooting into bootloader")
        subprocess.run("adb reboot bootloader", shell=True)
        time.sleep(15)

        print("Attempting: '", addressText, "'")
        time.sleep(1)
        print("\n\nFLASHING BUILD...")
        fastbootFlashOutput = subprocess.getoutput(addressText)
        print(fastbootFlashOutput)

        if waitForBootComplete():
            print("Build attempted to flash: " + curBuild)
            print("\nBuild Flashed: ")
        else:
            print("boot complete never returned, failing test case")
            testResult = False

        currentFingerprintOutput = subprocess.getoutput(getFingerprint)
        print(currentFingerprintOutput)
        if currentFingerprintOutput.count(curBuild) != 1:
            testResult = False
        if (
            fastbootFlashOutput.count(
                'REMINDER: YOU MUST FLASH WITH "-w" TO ERASE USERDATA WHEN:'
            )
            < 1
        ):
            print("did not finish build, failing test case")
            testResult = False

    except subprocess.CalledProcessError as e:
        testResult = False

    saveResult(
        caseId, testName, testResult, finalTime(startTime)
    )  # saving result in txt file and sending to testRail


def QfilFlash():
    testResult = True
    startTime = time.time()
    testName = "Verify latest qfil userdebug build can be flashed onto Device device manually with WINDOWS computer"
    caseId = 1564664434
    ########################################################################
    print("\n\n\n\n\n\n********" + testName + "********")
    time.sleep(1)

    try:
        subprocess.run(waitForAdb, shell=True)
        maduieQfilDownload = "maduie fetch-build -q -n " + curBuild

        print("\n\nDownloading Qfil Build...")
        qFilDownloadOutput = str(
            subprocess.run(maduieQfilDownload, capture_output=True, shell=True)
        )
        print(qFilDownloadOutput)

        addressText = ""
        print("operating systems: " + operatingSystem)
        if operatingSystem.count("windows") > 0:
            addressText = qFilDownloadOutput[qFilDownloadOutput.find("C:") :]
            addressText = addressText[: addressText.find("\\n")]
            addressText = addressText.replace("\\\\", "\\")
            print(directory(addressText))

        elif operatingSystem.count("mac") > 0:
            addressText = qFilDownloadOutput[qFilDownloadOutput.find("/Users") :]
            print(addressText)
            addressText = addressText[: addressText.find("\\n")]
            addressText = addressText.replace("\\\\", "\\")
            print(directory(addressText))

        addressText = directory(
            pythonVersion + " " + addressText + "\\flash_qfil_package.py -i"
        )

        print(addressText)
        subprocess.run("adb reboot edl", shell=True)
        print("Putting device into EDL MODE")
        time.sleep(10)

        print("Attempting: '", addressText, "'")
        time.sleep(1)
        print("\n\nFLASHING BUILD...")
        qfilFlashOutput = subprocess.getoutput(addressText)
        print(qfilFlashOutput)
        if qfilFlashOutput.count("{All Finished Successfully}") == 0:
            print("Qfil flash failed, did not finish. Failing test caseß")
            testResult = False

        if waitForBootComplete():
            print("Build attempted to flash: " + curBuild)
            print("\nBuild Flashed: ")
        else:
            print("boot complete never returned, failing test case")
            testResult = False


        subprocess.run(waitForAdb, shell=True)
        currentFingerprintOutput = subprocess.getoutput(getFingerprint)
        print(currentFingerprintOutput)
        if currentFingerprintOutput.count(curBuild) != 1:
            testResult = False
        if qfilFlashOutput.count("100.00%") < 1:
            testResult = False

    except subprocess.CalledProcessError as e:
        testResult = False

    # if maduie qfil flash works, manual qfil flash will work. If maduie qfil flash fails, retest manual qfil flash
    saveResult(
        caseId, testName, testResult, finalTime(startTime)
    )  # saving result in txt file and sending to testRail


########################################################################
def adbSanityCheck():
    testResult = True
    startTime = time.time()
    caseId = 1558350509
    testName = "Verify device passes adb/fastboot sanity check"
    print("\n\n\n\n\n\n********" + testName + "********")
    time.sleep(1)
    try:
        subprocess.run(waitForAdb, shell=True)
        print("\n\n\nRunning Logcat")
        logcatOutput = subprocess.getoutput(logcat)
        print(logcatOutput)
        if len(logcatOutput) < 4800:
            testResult = False

        print("\n\n\nRebooting To Fastboot")
        subprocess.run(rebootToFastboot, shell=True)
        time.sleep(10)
        print("\n\n\nListing Fastboot Devices")
        time.sleep(1)
        fastbootOutput = subprocess.getoutput(fastbootDevices)
        print(fastbootOutput)
        if fastbootOutput.lower().count("fastboot") == 0:
            testResult = False

        print("\n\n\nRebooting To ADB")
        subprocess.run(rebootToAdbFromFB, shell=True)
        waitForBootComplete()
        print("\n\n\nListing ADB Devices")
        time.sleep(10)
        adbDevicesOutput = subprocess.getoutput(adbDevices)
        if (
            adbDevicesOutput.lower().count("device") == 0
        ):  # rewrite this later to include ssn
            testResult = False
    except subprocess.CalledProcessError as e:
        testResult = False

    saveResult(
        caseId, testName, testResult, finalTime(startTime)
    )  # saving result in txt file and sending to testRail


########################################################################
def bootCom():
    testResult = True
    startTime = time.time()
    caseId = 1558350510
    testName = "Verify boot complete returns true"
    print("\n\n\n\n\n\n********" + testName + "********")

    try:
        subprocess.run(waitForAdb, shell=True)
        waitForBootComplete()
        bootComOutput = subprocess.getoutput(bootComplete)
        print(bootComOutput)
        if bootComOutput.count("[sys.boot_completed]: [1]") != 1:
            testResult = False
    except subprocess.CalledProcessError:
        testResult = False

    saveResult(
        caseId, testName, testResult, finalTime(startTime)
    )  # saving result in txt file and sending to testRail


########################################################################
def shellServ():
    subprocess.run(waitForAdb, shell=True)
    testResult = True
    startTime = time.time()
    caseId = 1558350512
    testName = "Verify shell services can be listed"
    print("\n\n\n\n\n\n********" + testName + "********")
    time.sleep(2)
    servicesOutput = ""
    try:
        # subprocess.run(shellServices, shell=True)
        servicesOutput = subprocess.getoutput(shellServices)
        print(shellServices)
    except subprocess.CalledProcessError as e:
        testResult = False

    if servicesOutput.lower().count("found") == 0:
        print("Found Services Keyword not found, failing testing case")
        testResult = False

    time.sleep(1)
    saveResult(
        caseId, testName, testResult, finalTime(startTime)
    )  # saving result in txt file and sending to testRail


########################################################################
def updateFirm():
    subprocess.run(waitForAdb, shell=True)
    testResult = True
    startTime = time.time()
    caseId = 1558350515
    testName = "Verify user can update firmware"
    print("\n\n\n\n\n\n********" + testName + "********")
    time.sleep(1)
    try:
        subprocess.run(adbRoot, shell=True)
        firmwareOutput = subprocess.getoutput(updateFirmware)
        print(firmwareOutput)
        print(firmwareOutput.count("100.0%"))
        if firmwareOutput.count("100.0%") == 0:
            testResult = False
    except subprocess.CalledProcessError as e:
        testResult = False

    saveResult(
        caseId, testName, testResult, finalTime(startTime)
    )  # saving result in txt file and sending to testRail


########################################################################
def syndbosdUnit():
    subprocess.run(waitForAdb, shell=True)
    testResult = True
    startTime = time.time()
    caseId = 1558350600
    testName = "Verify device passes syndbosd unit tests"
    print("\n\n\n\n\n\n********" + testName + "********")
    subprocess.run(adbReboot, shell=True)
    waitForBootComplete()
    try:
        subprocess.run(adbRoot, shell=True)
        print(
            "Starting syndbosd Unit Test. May fail if controllers are not paired or are asleep. (estimate time: ~ 10 min)"
        )
        unitTestOutput = subprocess.getoutput(unitTest)
        print(unitTestOutput)
        if unitTestOutput.count("FAILED") > 0:
            print('"fail" key word found, failing test case')
            testResult = False

    except subprocess.CalledProcessError as e:
        testResult = False

    saveResult(
        caseId, testName, testResult, finalTime(startTime)
    )  # saving result in txt file and sending to testRail


########################################################################
def wifiSanity():
    subprocess.run(waitForAdb, shell=True)
    testResult = True
    startTime = time.time()
    caseId = 1558350706
    testName = "Verify device passes wifi sanity check"
    print("\n\n\n\n\n\n********" + testName + "********")

    try:
        print("\nRestarting...")
        subprocess.run(adbReboot, shell=True)
        subprocess.run(waitForAdb, shell=True)
        waitForBootComplete()
        subprocess.run(adbRoot, shell=True)
        subprocess.run('adb shell "rm -rf /data/misc/wifi"', shell=True)
        print("Waiting for wifi service...")
        time.sleep(1)
        subprocess.run(deviceIdleDisable, shell=True)
        print("\nStarting Scan...")

        subprocess.run(wifiScan, shell=True)
        time.sleep(2)
        wifiConnect = (
            "adb shell cmd wifi connect-network "
            + wifiSanityNetwork
            + " wpa2 "
            + wifiSanityPassword
        )
        print("Connecting to " + wifiSanityNetwork)
        subprocess.run(wifiConnect, shell=True)
        time.sleep(1)
        subprocess.run(wifiConnect, shell=True)
        print("Pinging 'www.facebook.com'...")
        time.sleep(5)
        pingOutput = subprocess.getoutput(wifiPing)
        print(pingOutput)

        pingOutput2 = subprocess.getoutput(wifiPing)
        print(pingOutput2)

        if pingOutput.count("facebook.com") != 7 and pingOutput2.count("facebook.com") != 7:
            testResult = False
    except subprocess.CalledProcessError as e:
        testResult = False

    saveResult(
        caseId, testName, testResult, finalTime(startTime)
    )  # saving result in txt file and sending to testRail


########################################################################
def bluetoothSanity():
    subprocess.run(waitForAdb, shell=True)
    testResult = True
    startTime = time.time()
    caseId = 1558350827
    testName = "Verify device passes Bluetooth sanity check"
    print("\n\n\n\n\n\n********" + testName + "********")
    time.sleep(1)
    # print("Restarting...")
    # subprocess.run(adbReboot, shell=True)  # uncomment this later
    # subprocess.run(waitForAdb, shell=True)
    # subprocess.run(adbRoot, shell=True)
    waitForBootComplete()
    print(
        "\n\n-Put Bluetooth device into pairing mode. Going to attempt to connect to: "
        + bluetoothDevice
    )
    input("\n####Press enter when ready####")
    subprocess.run(adbRoot, shell=True)
    subprocess.run(bluetoothDiscovery, shell=True)
    time.sleep(3)
    subprocess.run(adbRoot, shell=True)
    subprocess.run(bluetoothDiscovery, shell=True)
    bluetoothList = 'adb root && adb logcat -e "Device: ' + bluetoothDevice + '" -m 1'
    print("grabbing " + bluetoothDevice + " bt address")
    bluetoothListOutput = subprocess.getoutput(bluetoothList)
    print("bluetooth output: " + bluetoothListOutput)

    btAddrLine = bluetoothListOutput.find("btAddr")  # get line with logi mouse
    bluetoothCode = bluetoothListOutput[
        btAddrLine + 8 : btAddrLine + 25
    ]  # acquire associated bt address
    print("bluetooth Code: " + bluetoothCode)

    bluetoothPair = (
        "adb shell am broadcast -a com.oculus.vrbtcontrol.EVENT -n com.oculus.vrbtcontrol/.VrBtControlBroadcastReceiver --es cmd_type "
        "PAIR"
        ' --es bd_addr "" ' + bluetoothCode + '""'
    )
    bluetoothUnpair = (
        "adb shell am broadcast -a com.oculus.vrbtcontrol.EVENT -n com.oculus.vrbtcontrol/.VrBtControlBroadcastReceiver --es cmd_type "
        "UNPAIR"
        ' --es bd_addr ""' + bluetoothCode + '""'
    )
    time.sleep(1)
    subprocess.run(adbRoot, shell=True)
    subprocess.run(bluetoothPair, shell=True)
    time.sleep(1)
    subprocess.run(bluetoothPair, shell=True)
    time.sleep(1)
    subprocess.run(bluetoothPair, shell=True)
    time.sleep(3)
    print(
        "\n\n\n*******************Verify Bluetooth device input by moving device*******************"
    )
    subprocess.run(bluetoothGetEvent, shell=True)
    print("\nUnpairing bluetooth device...")
    time.sleep(2)
    subprocess.run(bluetoothUnpair, shell=True)

    testResultOutput = input("####Test Result ->")
    if testResultOutput.lower().count("retry") != 0:
        bluetoothSanity()
        return
    if testResultOutput.lower().count("pass") == 0:
        testResult = False
    saveResult(
        caseId, testName, testResult, finalTime(startTime)
    )  # saving result in txt file and sending to testRail


########################################################################
def sensorTool():
    subprocess.run(waitForAdb, shell=True)
    testResult = True
    startTime = time.time()
    caseId = 1554462513
    testName = "Sensor Tool Validation"
    print("\n\n\n\n\n\n********" + testName + "********")
    try:
        print("Quickly restarting...")
        subprocess.run(adbReboot, shell=True)
        subprocess.run(waitForAdb, shell=True)
        waitForBootComplete()
        subprocess.run(cameraSetup, shell=True)
        subprocess.run("adb shell stop trackingservice mrsystemservice trackingfidelityservice", shell=True)
        time.sleep(3)
        print(
            "\n\nSensor Tool Validation: Command 1----------------------------------------------------------------------------"
        )
        command1Output = subprocess.getoutput(sensorToolCommand1)
        print(command1Output.count("frames dropped: 0"))
        print(command1Output)
        framesDropped = TestrailAPI.find_all_occurrences(
            command1Output, "frames dropped:"
        )
        for f in framesDropped:
            print("Looking at -> " + command1Output[f : f + 17])
            if command1Output[f : f + 17].count("frames dropped: 0") == 0:
                print("Command 1 (frames dropped)-> FAILED")
                testResult = False
        if command1Output.count("error") != 0:
            print("Command 1 (error)-> FAILED")
            testResult = False
        if command1Output.count("frames dropped:") == 0:
            print("Command 2 (INCOMPLETE)-> FAILED")
            testResult = False

        print(
            "\n\nSensor Tool Validation: Command 2----------------------------------------------------------------------------"
        )
        command2Output = subprocess.getoutput(sensorToolCommand2)
        if command2Output.count("frames dropped: 0") != 3:
            testResult = False
        print(command2Output)
        framesDropped = TestrailAPI.find_all_occurrences(
            command2Output, "frames dropped:"
        )
        print(framesDropped)
        for f in framesDropped:
            print("Looking at -> " + command2Output[f : f + 17])
            if command2Output[f : f + 17].count("frames dropped: 0") == 0:
                print("Command 2 (frames dropped)-> FAILED")
                print("ignore if this is frame dropped is for \"downward-hand\" or is seen more than once")
                # testResult = False
        if command2Output.count("error") != 0:
            print("Command 2 (error)-> FAILED")
            testResult = False
        if command2Output.count("frames dropped:") == 0:
            print("Command 2 (INCOMPLETE)-> FAILED")
            testResult = False

    except subprocess.CalledProcessError as e:
        testResult = False

    saveResult(
        caseId, testName, testResult, finalTime(startTime)
    )  # saving result in txt file and sending to testRail


########################################################################
def camTool():
    testResult = True
    startTime = time.time()
    testName = "Camera Tool Validation"
    caseId = 1554462514
    subprocess.run(waitForAdb, shell=True)

    try:
        print("\n\n\n\n\n\n********" + testName + "********")
        print("Rebooting...")
        subprocess.run(adbReboot, shell=True)
        waitForBootComplete()
        subprocess.run(cameraSetup, shell=True)
        time.sleep(3)
        print(
            "\n\nCamera Tool Validation: SLAM Only----------------------------------------------------------------------------"
        )
        slamOutput = subprocess.getoutput(slamOnly)
        print(slamOutput)
        framesDropped = TestrailAPI.find_all_occurrences(
            slamOutput, "frames dropped: 0"
        )

        for f in framesDropped:
            print("Looking at -> " + slamOutput[f : f + 17])
            if slamOutput[f : f + 17].count("frames dropped: 0") == 0:
                print("SLAM Only (frames dropped)-> FAILED")
                testResult = False
        if slamOutput.count("error") != 0:
            print("SLAM Only (error)-> FAILED")
            testResult = False
        if slamOutput.count("frames dropped:") == 0:
            print("SLAM Only (INCOMPLETE)-> FAILED")
            testResult = False

        print(
            "\n\nCamera Tool Validation: ET Only----------------------------------------------------------------------------"
        )
        etOutput = subprocess.getoutput(etOnly)
        print(etOutput)
        framesDropped = TestrailAPI.find_all_occurrences(etOutput, "frames dropped: 0")
        for f in framesDropped:
            print("Looking at -> " + etOutput[f : f + 17])
            if etOutput[f : f + 17].count("frames dropped: 0") == 0:
                print("ET Only (frames dropped)-> FAILED")
                testResult = False
        if etOutput.count("error") != 0:
            print("ET Only (error)-> FAILED")
            testResult = False
        if etOutput.count("frames dropped: 0") == 0:
            print("ET Only (INCOMPLETE)-> FAILED")
            testResult = False

        print(
            "\n\nCamera Tool Validation: SLAM + ET Only----------------------------------------------------------------------------"
        )
        time.sleep(1)
        slamEtOutput = subprocess.getoutput(slamEt)
        print(slamEtOutput)
        framesDropped = TestrailAPI.find_all_occurrences(
            slamEtOutput, "frames dropped: 0"
        )
        for f in framesDropped:
            print("Looking at -> " + slamEtOutput[f : f + 17])
            if slamEtOutput[f : f + 17].count("frames dropped: 0") == 0:
                print("SLAM + ET Only (frames dropped)-> FAILED")
                testResult = False
        if slamEtOutput.count("error") != 0:
            print("SLAM + ET Only (error)-> FAILED")
            testResult = False
        if slamEtOutput.count("frames dropped: 0") == 0:
            testResult = False
            print("SLAM + ET Only (INCOMPLETE)-> FAILED")

        print(
            "\n\nCamera Tool Validation: DTC Only----------------------------------------------------------------------------"
        )
        time.sleep(1)
        dtcOutput = subprocess.getoutput(dtcOnly)
        print(dtcOutput)
        framesDropped = TestrailAPI.find_all_occurrences(dtcOutput, "frames dropped: 0")
        for f in framesDropped:
            print("Looking at -> " + dtcOutput[f : f + 17])
            if dtcOutput[f : f + 17].count("frames dropped: 0") == 0:
                print("DTC Only (frames dropped)-> FAILED")
                testResult = False
        if dtcOutput.count("error") != 0:
            print("DTC Only (error)-> FAILED")
            testResult = False
        if dtcOutput.count("frames dropped: 0") == 0:
            print("DTC Only (INCOMPLETE)-> FAILED")
            testResult = False

        print(
            "\n\nCamera Tool Validation: SLAM + DTC + ET Only----------------------------------------------------------------------------"
        )
        time.sleep(1)
        slamDtcEtOutput = subprocess.getoutput(slamDtcEt)
        print(slamDtcEtOutput)
        framesDropped = TestrailAPI.find_all_occurrences(
            slamDtcEtOutput, "frames dropped: 0"
        )

        for f in framesDropped:
            print("Looking at -> " + slamDtcEtOutput[f : f + 17])
            if slamDtcEtOutput[f : f + 17].count("frames dropped: 0") == 0:
                print("SLAM + DTC + ET Only (frames dropped)-> FAILED")
                testResult = False
        if slamDtcEtOutput.count("error") != 0:
            print("SLAM + DTC + ET Only (error)-> FAILED")
            testResult = False
        if slamDtcEtOutput.count("frames dropped: 0") == 0:
            print("SLAM + DTC Only (INCOMPLETE)-> FAILED")
            testResult = False

    except subprocess.CalledProcessError as e:
        testResult = False

    saveResult(
        caseId, testName, testResult, finalTime(startTime)
    )  # saving result in txt file and sending to testRail


########################################################################
def vrsRec():
    # global runVrsPlayer
    # runVrsPlayer = directory(
    #     pathname + "\\Extras\\vrsplayer.exe " + pathname + "\\Extras\\default.vrs"
    # )

    testResult = True
    startTime = time.time()
    testName = (
        "Verify VRS Recorder - Worldtracking + downward + imu + static exposure/gain"
    )
    caseId = 1555512132

    subprocess.run(waitForAdb, shell=True)

    try:

        vrsRecorder = (
            " adb shell vrs-recorder --sensoraccess_purposes=downward/active_slots,worldTracking/active_slots  --cmm_allowed_mux_modes=downward/codecOnHands,worldTracking/lowLightHands --duration=2 --headset_magnetometer=false --slam_magnetometer=false --slam_static_exposure_ms=1 --slam_static_gain=4 --downward_static_exposure_ms=1 --downward_static_gain=4 && adb pull /data/misc/default.vrs "
            + directory(pathname + "\\Extras")
        )
        vrsRecorder = directory(vrsRecorder)
        print("\n\n\n\n\n\n********" + testName + "********")

        if os.path.exists(directory(pathname + "\\Extras\\default.vrs ")):
            print("deleting current default.vrs")
            os.remove(
                directory(pathname + "\\Extras\\default.vrs ")
            )  # delete current default vrs

        print("Quickly restarting...")
        subprocess.run(adbReboot, shell=True)
        subprocess.run(waitForAdb, shell=True)
        print("\n\nRunning VRS Recorder command...")
        waitForBootComplete()

        subprocess.run(cameraSetup, shell=True)
        subprocess.run(vrsRecorder, shell=True)
        time.sleep(3)
        if os.path.exists(directory(pathname + "\\Extras\\default.vrs")):
            print("default.vrs file created, passing test case")
            # subprocess.run(runVrsPlayer, shell=True)
            # os.remove(pathname + "\\default.vrs ")
        else:
            print("default.vrs file NOT created, failing test case")
            testResult = False

    except subprocess.CalledProcessError as e:
        testResult = False

    saveResult(
        caseId, testName, testResult, finalTime(startTime)
    )  # saving result in txt file and sending to testRail


########################################################################
def audioSanity():
    testResult = True
    startTime = time.time()
    testName = "Verify device passes audio sanity check"
    caseId = 1558350708
    subprocess.run(waitForAdb, shell=True)
    print("\n\n\n\n\n\n********" + testName + "********")
    time.sleep(2)
    subprocess.run(audioCheck, shell=True)

    testResultOutput = input("####Test Result ->")
    if testResultOutput.lower().count("retry") != 0:
        audioSanity()
        return
    if testResultOutput.lower().count("pass") == 0:
        testResult = False
    saveResult(
        caseId, testName, testResult, finalTime(startTime)
    )  # saving result in txt file and sending to testRail


########################################################################
def waitForBootComplete():
    print("Wait for Boot Complete...")
    startTime = time.time()
    subprocess.run(waitForAdb, shell=True)
    bootComOutput = ""
    count = 0
    while bootComOutput.count("[sys.boot_completed]: [1]") != 1:
        bootComOutput = subprocess.getoutput(
            "adb shell getprop | grep sys.boot_completed"
        )
        print("waiting for boot complete: ", finalTime(startTime))
        time.sleep(1)
        count += 1

        if count > 300:
            print("Has lasted longer than 5 minutes: return boot complete FAILED")
            return False

    subprocess.run(adbRoot, shell=True)
    print("waiting for adb loss error...")
    time.sleep(4)
    print("checking again...")

    bootComOutput = subprocess.getoutput("adb shell getprop | grep sys.boot_completed")
    while bootComOutput.count("[sys.boot_completed]: [1]") != 1:
        bootComOutput = subprocess.getoutput(
            "adb shell getprop | grep sys.boot_completed"
        )
        print("waiting for boot complete: ", finalTime(startTime))
        time.sleep(1)

        if count > 300:
            print("Has lasted longer than 5 minutes: return boot complete FAILED")
            return False

    print("BOOT COMPLETE FINISHED")
    return True


########################################################################
def micSanity():
    testResult = True
    startTime = time.time()
    caseId = 1571992597
    testName = "Verify device passes microphone sanity check"
    print("\n\n\n\n\n\n********" + testName + "********")

    print("Rebooting...")
    subprocess.run(adbReboot, shell=True)

    if os.path.exists(directory(pathname + "\\Extras\\test.wav")):
        os.remove(directory(pathname + "\\Extras\\test.wav"))

    waitForBootComplete()
    time.sleep(1)
    subprocess.run(adbRoot, shell=True)
    subprocess.run(
        directory("adb shell audio_tool -m recorder -o /sdcard/test.wav"), shell=True
    )
    time.sleep(1)
    subprocess.run(
        directory("adb pull /sdcard/test.wav " + pathname + "\\Extras"), shell=True
    )
    time.sleep(1)

    if operatingSystem.count("windows") > 0:
        subprocess.run(
            r"start " + pathname + "\\Extras\\test.wav", shell=True
        )  # windows
        subprocess.run(
            r'start "C:\Program Files (x86)\Windows Media Player\wmplayer.exe" '
            + pathname
            + "\\Extras\\test.wav",
            shell=True,
        )
        time.sleep(8)
        subprocess.run(r"taskkill /f /im Microsoft.Media.Player.exe", shell=True)
    elif operatingSystem.count("mac") > 0:
        print("\nThis test case is not implemented for MacOS yet. Please play test.wav file in \"Extras\" folder to verify mic")
        # implement for mac

    testResultOutput = input("####Test Result ->")
    if testResultOutput.lower().count("retry") != 0:
        micSanity()
        return
    if testResultOutput.lower().count("pass") == 0:
        testResult = False
    saveResult(
        caseId, testName, testResult, finalTime(startTime)
    )  # saving result in txt file and sending to testRail


########################################################################
def handheldController():
    testResult = True
    startTime = time.time()
    caseId = 1569223701
    testName = "Verify device can pair with Crystal(handheld) controllers"

    ctlStop = "adb shell syndbosd_consumers_ctl stop"
    unpairAllControllers = "adb shell syndbosd_input_tool --unpair-disconnected "
    pairControllers = "adb shell syndbosd_input_tool --pair"
    listPairedControllers = "adb shell syndbosd_input_tool --list"

    print("\n\n********" + testName + "********")
    time.sleep(2)

    try:
        subprocess.run(adbRoot, shell=True)
        subprocess.run(ctlStop, shell=True)
        print("Unpairing current controllers")
        print("\n\nPress Enter")
        subprocess.run(unpairAllControllers, shell=True)
        print(
            "\n\n\nPut the Crystal controllers in pairing mode  (“Menu” button + “Y” for left, and “Square” button + “B” for right)"
        )
        time.sleep(1)
        input("####Press enter when ready####")

        print(
            "\n\nNow pair a controller by entering the number (ex. 0) and pressing enter"
        )
        subprocess.run(pairControllers, shell=True)
        print(
            "\n\nNow pair the other controller by entering the number (ex. 0) and pressing enter"
        )
        subprocess.run(pairControllers, shell=True)

        print("Listing Paired Controllers")
        subprocess.run(listPairedControllers, shell=True)
        subprocess.run("adb shell syndbosd_consumers_ctl start", shell=True)

    except subprocess.CalledProcessError as e:
        testResult = False

    testResultOutput = input("####Test Result ->")
    if testResultOutput.lower().count("retry") != 0:
        wifiCast()
        return
    if testResultOutput.lower().count("pass") == 0:
        testResult = False
    saveResult(
        caseId, testName, testResult, finalTime(startTime)
    )  # saving result in txt file and sending to testRail


########################################################################
def adbInstallPlay():
    testResult = True
    startTime = time.time()
    caseId = 1571992595
    caseId2 = 1571992596
    testName = "Verify apps are able to be installed/launched in shell via adb commands"
    print("\n\n********" + testName + "********")
    time.sleep(2)

    try:
        waitForBootComplete()
        print()
        print("\nInstalling Laser Sword")
        file_location = directory(pathname + "\\Extras\\laser-sword.apk")
        subprocess.run("adb install " + file_location, shell=True)
        time.sleep(1)
        packagesOutput = subprocess.getoutput("adb shell pm list packages")
        print(packagesOutput)
        if packagesOutput.count("com.XRVerification.LaserSword") < 1:
            testResult = False
        else:
            time.sleep(2)
            print("\nStarting App")
            subprocess.run(
                "adb shell monkey -p com.XRVerification.LaserSword 1", shell=True
            )
            print("\n\nDon HMD and Play Laser Sword")

    except subprocess.CalledProcessError as e:
        testResult = False

    print(testName)
    testResultOutput = input("####Test Result ->")
    if testResultOutput.lower().count("pass") == 0:
        testResult = False
    saveResult(
        caseId, testName, testResult, finalTime(startTime)
    )  # saving result in txt file and sending to testRail

    print('\n\nVerify "Laser Sword" test app is playable')
    testResultOutput = input("####Test Result ->")
    if testResultOutput.lower().count("pass") == 0:
        testResult = False
    saveResult(
        caseId2,
        'Verify "Laser Sword" test app is playable',
        testResult,
        finalTime(startTime),
    )


########################################################################
def wifiCast():
    testResult = True
    caseId = 1570280583
    testName = "Verify Wifi casting passes"
    startTime = time.time()
    print("\n\n********" + testName + "********")

    try:
        print("Restarting...")
        subprocess.run(adbReboot, shell=True)
        subprocess.run(waitForAdb, shell=True)
        waitForBootComplete()
        subprocess.run(adbRoot, shell=True)
        subprocess.run('adb shell "rm -rf /data/misc/wifi"', shell=True)
        print("Waiting for wifi service...")
        subprocess.run(deviceIdleDisable, shell=True)
        print("\n\nMake sure " + wifiCastNetwork + " hotspot is setup")
        input("####Press when Ready####")
        print("\nStarting Scan...")
        time.sleep(1)
        subprocess.run(wifiScan, shell=True)
        time.sleep(5)
        wifiConnect = (
            "adb shell cmd wifi connect-network "
            + wifiCastNetwork
            + " wpa2 "
            + wifiCastPassword
        )
        print("Connecting to " + wifiCastNetwork)
        subprocess.run(wifiConnect, shell=True)
        time.sleep(5)

        verify = True
        while verify:
            print("\n\n\n\n\nVerify Connection: ")
            wifiStatusOutput = subprocess.run("adb shell cmd wifi status", shell=True)

            if (
                len(
                    input(
                        "\n\n####If correct -> enter ANY TEXT, then press enter. To try again -> press enter####\n"
                    )
                )
                == 0
            ):
                print("\nStarting Scan...")
                time.sleep(1)
                subprocess.run(wifiScan, shell=True)
                time.sleep(5)
                subprocess.run(wifiConnect, shell=True)
                continue
            verify = False

        ip = "172.20.10.1"
        time.sleep(2)
        print("Pinging Router")
        time.sleep(3)
        subprocess.run(
            "adb shell ping -s 2000 -c 300 -i 0.001 " + wifiCastIpPing, shell=True
        )

    except subprocess.CalledProcessError as e:
        testResult = False

    testResultOutput = input("####Test Result ->")
    if testResultOutput.lower().count("retry") != 0:
        wifiCast()
        return
    if testResultOutput.lower().count("pass") == 0:
        testResult = False
    saveResult(
        caseId, testName, testResult, finalTime(startTime)
    )  # saving result in txt file and sending to testRail


########################################################################
def skipNux():
    testResult = True
    startTime = time.time()
    caseId = 1572712926
    testName = "Verify user is able to skip NUX without test credentials"
    print("\n\n********" + testName + "********")
    time.sleep(1)

    try:
        subprocess.run(waitForAdb, shell=True)
        waitForBootComplete()
        time.sleep(5)

        preNuxOutput = subprocess.getoutput("adb shell dumpsys CompanionService")
        print(preNuxOutput)
        if (
            preNuxOutput.count("NUX State: NUX_COMPLETE") != 0
        ):  # check to make sure device is in pre-nux
            print("\n\nDevice not in pre-nux. Wiping device.")
            subprocess.run("maduie factory-reset", shell=True)
            waitForBootComplete()

        subprocess.run(
            "adb root && adb shell am startservice -a nux.ota.SKIP_NUX -n com.oculus.nux.ota/.NuxOtaIntentService",
            shell=True,
        )
        time.sleep(15)
        subprocess.run(waitForAdb, shell=True)
        waitForBootComplete()
        postNuxOutput = subprocess.getoutput("adb shell dumpsys CompanionService")
        print(postNuxOutput)
        if postNuxOutput.count("NUX State: NUX_COMPLETE") == 0:
            print("did not complete nux, failing test case")
            testResult = False

    except subprocess.CalledProcessError as e:
        testResult = False

    saveResult(
        caseId, testName, testResult, finalTime(startTime)
    )  # saving result in txt file and sending to testRail


########################################################################
def adbBugreport():
    testResult = True
    startTime = time.time()
    caseId = 1496901768
    testName = "Verify user can collect a bugreport from the Headset"
    print("\n\n********" + testName + "********")
    time.sleep(1)

    try:
        print("Emptying out this folder")
        folder_path = directory(pathname + "\\BugReports\\")

        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
                print(filename, "is removed")

        subprocess.run(waitForAdb, shell=True)
        print("Grabbing bugreport...")
        bugReportOutput = subprocess.getoutput(
            directory("adb bugreport " + pathname + "\\BugReports\\")
        )

        print(bugReportOutput)
        if bugReportOutput.count("Bug report copied to") < 1:
            print("Bug report not saved to computer: failing test case")
            testResult = False

    except subprocess.CalledProcessError as e:
        testResult = False

    saveResult(
        caseId, testName, testResult, finalTime(startTime)
    )  # saving result in txt file and sending to testRail


########################################################################
def testTracking():
    testResult = True
    startTime = time.time()
    caseId = 294665257
    caseId2 = 294665258
    testName = "Verify HMD orientation tracking works properly (Pitch, Roll, Yaw)"
    testName2 = "Verify HMD positional tracking works properly (X, Y, Z)"
    print("\n\n********" + testName + "********")
    print("\n\n********" + testName2 + "********")
    time.sleep(1)

    testResultOutput = input("####Test Result ->")
    if testResultOutput.lower().count("pass") == 0:
        testResult = False
    saveResult(
        caseId, testName, testResult, finalTime(startTime)
    )  # saving result in txt file and sending to testRail
    saveResult(
        caseId2, testName2, testResult, finalTime(startTime)
    )  # saving result in txt file and sending to testRail


########################################################################
def testControllerFunctionality():
    testResult = True
    startTime = time.time()
    caseId = 294662322
    testName = "Verify long-press Oculus recenter function resets the HMD's forward facing position"
    caseId2 = 294662082
    testName2 = "Verify trigger presses work as intended"
    caseId3 = 294662083
    testName3 = "Verify the Oculus button can hide and show the AUI in Shell"
    print("\n\n********" + testName + "********")
    print("\n\n********" + testName2 + "********")
    print("\n\n********" + testName3 + "********")
    time.sleep(1)

    testResultOutput = input("####Test Result ->")
    if testResultOutput.lower().count("pass") == 0:
        testResult = False
    saveResult(
        caseId, testName, testResult, finalTime(startTime)
    )  # saving result in txt file and sending to testRail
    saveResult(
        caseId2, testName2, testResult, finalTime(startTime)
    )  # saving result in txt file and sending to testRail
    saveResult(
        caseId3, testName3, testResult, finalTime(startTime)
    )  # saving result in txt file and sending to testRail


########################################################################
def selectInstalledApp():
    testResult = True
    startTime = time.time()
    caseId = 507249977
    testName = "Verify selecting an installed application launches it"
    print("\n\n********" + testName + "********")
    time.sleep(1)

    testResultOutput = input("####Test Result ->")
    if testResultOutput.lower().count("pass") == 0:
        testResult = False
    saveResult(
        caseId, testName, testResult, finalTime(startTime)
    )  # saving result in txt file and sending to testRail


########################################################################
def skipNuxUsingmaduieSkoobe():
    testResult = True
    startTime = time.time()
    caseId = 1580550283
    testName = "Verify user is able to skip NUX with test user credentials"
    print("\n\n********" + testName + "********")

    try:

        subprocess.run(waitForAdb, shell=True)
        print("Rebooting...")
        subprocess.run(adbReboot, shell=True)
        time.sleep(1)
        waitForBootComplete()
        preNuxOutput = subprocess.getoutput("adb shell dumpsys CompanionService")
        print(preNuxOutput)

        if (
            preNuxOutput.count("NUX State: NUX_COMPLETE") != 0
        ):  # check to make sure device is in pre-nux
            print("\n\nDevice not in pre-nux. Wiping device.")
            subprocess.run("maduie factory-reset", shell=True)

        waitForBootComplete()
        time.sleep(1)
        preNuxOutput = subprocess.getoutput("adb shell dumpsys CompanionService")
        print(preNuxOutput)
        if maduieUsePersonalSO:
            subprocess.run(
                "maduie skoobe -e "
                + maduieSkoobeUsername
                + " -p "
                + maduieSkoobePassword
                + " -n "
                + maduieSkoobeNetworkName
                + " -k "
                + maduieSkoobeNetworkPassword
                + " --disable-hand-tracking",
                shell=True,
            )
        else:
            subprocess.run("maduie skoobe -n" + maduieSkoobeNetworkName + " -k " + maduieSkoobeNetworkPassword , shell=True)
        waitForBootComplete()
        time.sleep(5)
        postNuxOutput = subprocess.getoutput("adb shell dumpsys CompanionService")
        print(postNuxOutput)
        if postNuxOutput.count("NUX State: NUX_COMPLETE") == 0:
            print("did not complete nux, failing test case")
            testResult = False

    except subprocess.CalledProcessError as e:
        testResult = False

    saveResult(
        caseId, testName, testResult, finalTime(startTime)
    )  # saving result in txt file and sending to testRail


########################################################################


def on_press(key):
    from pynput import keyboard

    if key == keyboard.Key.enter:
        process.terminate()
        return False


def displayTestCases():
    from pynput import keyboard

    testResult = True
    startTime = time.time()
    caseId = 1558350707
    testName = "Verify device passes display sanity check"
    print("\n\n********" + testName + "********")

    waitForBootComplete()
    try:
        subprocess.run(adbRoot, shell=True)

        listener = keyboard.Listener(on_press=on_press)
        listener.start()
        global process
        process = subprocess.Popen("adb shell draw_frame -r 255 ", shell=True)
        time.sleep(1)
        print("Verify Red Display. Press Enter To Continue...")
        listener.join()

    except subprocess.TimeoutExpired as e:
        print("")

    try:
        file_path = directory(pathname + "\\Extras\\image.png")
        subprocess.run(directory("adb push " + file_path + " /data"), shell=True)

        listener = keyboard.Listener(on_press=on_press)
        listener.start()
        process = subprocess.Popen(
            "adb shell draw_frame -p /data/image.png", shell=True
        )
        time.sleep(1)
        print("Verify Image on Display. Press Enter To Continue...")
        listener.join()

    except subprocess.TimeoutExpired as e:
        print("")

    try:
        print("Starting Display Validator Test Steps -> Rebooting...")
        subprocess.run(adbReboot, shell=True)

        waitForBootComplete()
        subprocess.run(waitForAdb, shell=True)
        subprocess.run(adbRoot, shell=True)
        subprocess.run(
            "adb shell setprop ctl.stop vendor.qti.hardware.display.composer",
            shell=True,
        )
        print("wait 5 sec to start display validator...")
        time.sleep(5)
        print("running display validator")

        from pynput import keyboard

        listener = keyboard.Listener(on_press=on_press)
        listener.start()
        process = subprocess.Popen("adb shell display_validator", shell=True)
        time.sleep(1)
        print(
            "Verify White Display on both Screens (Left/Right). Press Enter To Continue..."
        )
        listener.join()

    except subprocess.TimeoutExpired as e:
        print("error")

    time.sleep(2)
    testResultOutput = input("####(press 1x before typing in result)Test Result->")
    if testResultOutput.lower().count("pass") == 0:
        testResult = False
    if testResultOutput.lower().count("retry") != 0:
        displayTestCases()
        return

    saveResult(
        caseId, testName, testResult, finalTime(startTime)
    )  # saving result in txt file and sending to testRail
    print("rebooting...")
    subprocess.run(adbReboot,shell=True)

########################################################################


def downgradehandheldControllers():
    testResult = True
    startTime = time.time()
    testName = "Verify HMD pushes the firmware on the system to the connected controller if the controller is on a lower version number"
    print("\n\n********" + testName + "********")

    try:
        subprocess.run(waitForAdb, shell=True)
        subprocess.run(adbRoot, shell=True)
        waitForBootComplete()

        rstestOutput = subprocess.getoutput("adb shell rstest info")
        print(rstestOutput)
        if rstestOutput.count("CONNECTED") < 2:
            testResult = False
            print("Failing, controllers not connected to prior")

        leftID = rstestOutput.find("(LeftHand)  id")
        rightID = rstestOutput.find("(RightHand)  id")
        leftID = rstestOutput[leftID + 16 : leftID + 32]
        rightID = rstestOutput[rightID + 17 : rightID + 33]

        subprocess.run("adb shell syndbosd_consumers_ctl stop", shell=True)
        print("Downgrading Both Controllers...")
        subprocess.run(
            "adb shell syndbosd_input_tool --fw-update "
            + leftID
            + " /odm/firmware/handheld_prq-downgrade.bin",
            shell=True,
        )
        subprocess.run(
            "adb shell syndbosd_input_tool --fw-update "
            + rightID
            + " /odm/firmware/handheld_prq-downgrade.bin",
            shell=True,
        )

        connectedBeforeUpdate = subprocess.getoutput(
            "adb shell syndbosd_input_tool --list"
        )
        print(connectedBeforeUpdate)
        if connectedBeforeUpdate.count("Expected") == 0:
            testResult = False
            print("Failing, controllers did not downgrade successfully")

        subprocess.run("adb shell syndbosd_consumers_ctl start", shell=True)

        print(
            "Restarted syndbosd service, controllers should upgrade. Please Check HMD"
        )
        time.sleep(3)
        getRSTest = subprocess.getoutput("adb shell rstest info")
        print(getRSTest)
        print("Rebooting device....verify controllers update")
        subprocess.run(adbReboot, shell=True)

    except subprocess.TimeoutExpired as e:
        print("downgradehandheldControllers() failed")
    print("testResult:", testResult)
    # saveResult(caseId, testName,testResult, finalTime(startTime)) #not applicable

    return testResult

########################################################
def dtofCalibration():
    testResult = True
    startTime = time.time()
    testName = "Performing DTOF Calibration Script"
    print("\n\n********" + testName + "********")

    subprocess.run(adbRoot, shell=True)
    subprocess.run("adb shell \"syndbosd_dtof_calibration_tool --write-file /vendor/provisioning/calibration/dtof/mode1a/reg_config.csv\"",shell=True)
    time.sleep(1)
    subprocess.run(adbReboot, shell=True)
    print("Finished DTOF Calibration, Rebooting Device\n\n\n\n\n")

########################################################################


def basicTestrun():
    print("RUNNING basicTestrun")
    totalStartTime = time.time()

    fastbootFlash()  # fully automated
    QfilFlash()  # fully automated

    if not waitForBootComplete():
        print("&*&*&*&*&*&*&*&*&*&*&*&*&*&*&*&*&*&*")
        print("BOOT Complete never returned, stopping test run")
        print("&*&*&*&*&*&*&*&*&*&*&*&*&*&*&*&*&*&*")
        return
    else:
        print("BOOT Complete returned, continuing TEST RUN")

    adbSanityCheck()  # fully automated
    bootCom()  # fully automated
    shellServ()  # fully automated
    updateFirm()  # fully automated
    wifiSanity()  # fully automated
    adbBugreport()  # fully automated


    # print("\n\n" + "Downgraded Controllers Test Case:", controllersUpdated)
    print("\n\n\n&*&*&*&*&*&*&*&*&*&*&*&*&*&*&*&*&*&*")
    print("*&*&*&*&*TEST RUN COMPLETE&*&*&*&*&")
    print("&*&*&*&*&*&*&*&*&*&*&*&*&*&*&*&*&*&*")
    time.sleep(2)
    print("\n\nTOTAL TIME: " + finalTime(totalStartTime))





def devBoard1():
    print("RUNNING Ddeeev TEST RUN")
    totalStartTime = time.time()

    # flashingmaduie()  # fully automated

    fastbootFlash()  # fully automated
    QfilFlash()  # fully automated

    if not waitForBootComplete():
        print("&*&*&*&*&*&*&*&*&*&*&*&*&*&*&*&*&*&*")
        print("BOOT Complete never returned, stopping test run")
        print("&*&*&*&*&*&*&*&*&*&*&*&*&*&*&*&*&*&*")
        return
    else:
        print("BOOT Complete returned, continuing TEST RUN")

    adbSanityCheck()  # fully automated
    bootCom()  # fully automated
    shellServ()  # fully automated
    updateFirm()  # fully automated
    syndbosdUnit()  # fully automated
    wifiSanity()  # fully automated
    sensorTool()  # fully automated
    camTool()  # fully automated
    vrsRec()  # fully automated
    adbBugreport()  # fully automated

    wifiCast()  # semi automated
    audioSanity()  # semi automated
    micSanity()  # semi automated
    displayTestCases()
    bluetoothSanity()  # semi automated
    handheldController()  # semi automated

    print("\n\n\n&*&*&*&*&*&*&*&*&*&*&*&*&*&*&*&*&*&*")
    print("*&*&*&*&*TEST RUN COMPLETE&*&*&*&*&")
    print("&*&*&*&*&*&*&*&*&*&*&*&*&*&*&*&*&*&*")
    time.sleep(2)
    print("\n\nTOTAL TIME: " + finalTime(totalStartTime))


def Passinghmd():
    print("RUNNING Passing HMD TEST RUN")
    totalStartTime = time.time()

    flashingmaduie()  # fully automated
    fastbootFlash()  # fully automated
    QfilFlash()  # fully automated

    if not waitForBootComplete():
        print("&*&*&*&*&*&*&*&*&*&*&*&*&*&*&*&*&*&*")
        print("BOOT Complete never returned, stopping test run")
        print("&*&*&*&*&*&*&*&*&*&*&*&*&*&*&*&*&*&*")
        return
    else:
        print("BOOT Complete returned, continuing TEST RUN")

    adbSanityCheck()  # fully automated
    bootCom()  # fully automated
    shellServ()  # fully automated
    updateFirm()  # fully automated
    # syndbosdUnit()  # fully automated
    wifiSanity()  # fully automated
    sensorTool()  # fully automated
    camTool()  # fully automated
    vrsRec()  # fully automated
    adbBugreport()  # fully automated
    skipNux()  # fully automated

    wifiCast()  # semi automated
    audioSanity()  # semi automated
    micSanity()  # semi automated
    bluetoothSanity()  # semi automated
    handheldController()  # semi automated
    displayTestCases()

    adbInstallPlay()  # not automated at all
    testTracking()  # not automated at all
    testControllerFunctionality()  # not automated at all
    selectInstalledApp()  # not automated at all

    print("\n\n\n&*&*&*&*&*&*&*&*&*&*&*&*&*&*&*&*&*&*")
    print("*&*&*&*&*TEST RUN COMPLETE&*&*&*&*&")
    print("&*&*&*&*&*&*&*&*&*&*&*&*&*&*&*&*&*&*")
    time.sleep(2)
    print("\n\nTOTAL TIME: " + finalTime(totalStartTime))


def Passing1HMD():
    print("RUNNING Passing.1 HMD TEST RUN")
    totalStartTime = time.time()

    # flashingmaduie()  # fully automated -> fails on Passing.1 due to error

    fastbootUserFlash()
    fastbootFlash()  # fully automated
    QfilFlash()  # fully automated


    if not waitForBootComplete():
        print("&*&*&*&*&*&*&*&*&*&*&*&*&*&*&*&*&*&*")
        print("BOOT Complete never returned, stopping test run")
        print("&*&*&*&*&*&*&*&*&*&*&*&*&*&*&*&*&*&*")
        return
    else:
        print("BOOT Complete returned, continuing TEST RUN")

    adbSanityCheck()  # fully automated
    bootCom()  # fully automated
    shellServ()  # fully automated
    updateFirm()  # fully automated
    syndbosdUnit()  # fully automated
    wifiSanity()  # fully automated
    sensorTool()  # fully automated
    camTool()  # fully automated
    vrsRec()  # fully automated
    adbBugreport()  # fully automated
    skipNux()  # fully automated
    skipNuxUsingmaduieSkoobe()  # fully automated

    dtofCalibration() #not part of sanity, added for "quality of life"
    # controllersUpdated = downgradehandheldControllers() #not part of sanity test run, but nice to run for stu

    wifiCast()  # semi automated
    audioSanity()  # semi automated
    micSanity()  # semi automated
    bluetoothSanity()  # semi automated
    handheldController()  # semi automated
    displayTestCases()


    adbInstallPlay()  # not automated at all
    testTracking()  # not automated at all
    testControllerFunctionality()  # not automated at all
    selectInstalledApp()  # not automated at all

    # print("\n\n" + "Downgraded Controllers Test Case:", controllersUpdated)
    print("\n\n\n&*&*&*&*&*&*&*&*&*&*&*&*&*&*&*&*&*&*")
    print("*&*&*&*&*TEST RUN COMPLETE&*&*&*&*&")
    print("&*&*&*&*&*&*&*&*&*&*&*&*&*&*&*&*&*&*")
    time.sleep(2)
    print("\n\nTOTAL TIME: " + finalTime(totalStartTime))


#################################################################


def setup():
    print('Setting up Script with "Configuration.yaml"')
    # verifyPythonLibInstalled()  # used to make sure all necessary python libraries are installed

    file = sys.argv[0]
    global pathname
    pathname = os.path.dirname(file)
    try:
        with open(directory(pathname + "\\Configuration.yaml"), "r") as f:
            config = yaml.safe_load(f)
    except:
        with open(directory(pathname + "/Configuration.yaml"), "r") as f:
            config = yaml.safe_load(f)

    global useTestrail
    useTestrail = config["runConfig"]["useTestrail"]
    global curBuild
    curBuild = str(config["runConfig"]["curBuild"])
    global planId
    planId = config["runConfig"]["planId"]
    global curDevice
    curDevice = config["runConfig"]["curDevice"]
    global operatingSystem
    operatingSystem = config["runConfig"]["operatingSystem"].lower()

    global wifiSanityNetwork
    wifiSanityNetwork = config["wifiSanity"]["networkName"]
    global wifiSanityPassword
    wifiSanityPassword = config["wifiSanity"]["password"]
    global wifiCastNetwork
    wifiCastNetwork = config["wifiCast"]["networkName"]
    global wifiCastPassword
    wifiCastPassword = config["wifiCast"]["password"]
    global wifiCastIpPing
    wifiCastIpPing = config["wifiCast"]["ipPing"]

    global bluetoothDevice
    bluetoothDevice = config["bluetoothDevice"]

    global maduieUsePersonalSO
    maduieUsePersonalSO = config["maduieSkoobe"]["usePersonalSO"]
    global maduieSkoobeUsername
    maduieSkoobeUsername = config["maduieSkoobe"]["username"]
    global maduieSkoobePassword
    maduieSkoobePassword = config["maduieSkoobe"]["password"]
    global maduieSkoobeNetworkName
    maduieSkoobeNetworkName = config["maduieSkoobe"]["networkName"]
    global maduieSkoobeNetworkPassword
    maduieSkoobeNetworkPassword = config["maduieSkoobe"]["networkPassword"]

    global pythonVersion
    pythonVersion = config["runConfig"]["pythonVersion"]

    #######################################################################
    now = datetime.datetime.now()
    formatted_date = now.strftime("%m-%d-%y")
    formatted_time = now.strftime("%Hh%Mm%Ss")
    global curTime
    curTime = formatted_date

    global resultName
    resultName = directory(
        ""
        + pathname
        + "\\TestResults\\"
        + curDevice
        + " "
        + str(curBuild)
        + "  "
        + curTime
        + " TestResults"
        + ".txt"
    )
    global results
    results = open(resultName, "w")
    results.write("" + curDevice)
    results.write("\nTEST RESULTS for " + str(curBuild) + ": " + curTime + "\n\n\n")

    print("useTestrail:", useTestrail)
    print("curDevice: " + curDevice)
    time.sleep(1)


########################################################
def runCurDevice():  # add curDevice here for usage
    global useTestrail
    if useTestrail:
        global testList
        testList = TestrailAPI.getTests(planId)

    print("\nEnter ONLY RESULT after each test case -->Pass/Fail")
    time.sleep(1)
    print("Starting Test Run...")
    time.sleep(1)
    print("Using Testrail API: " + str(useTestrail))

    if curDevice.count("Device Passing") != 0:
        Passinghmd()
    elif curDevice.count("Device Deeedv ") != 0:
        devBoard1()
    elif curDevice.count("Device Passing.1") != 0:
        Passing1HMD()
    elif curDevice.count("Downgrade Controllers") != 0:
        print("Downgrade Controllers")
        downgradehandheldControllers()
    elif curDevice.count("basicTestrun") != 0: #running this one for basic tests
        print(basicTestrun)
        basicTestrun()
    elif curDevice.count("Testing") != 0:
        print("Running Testing")
        useTestrail = False
        fastbootUserFlash()


############################################################
if __name__ == "__main__":

    setup()

    with OutputCapture() as capture:
        runCurDevice()

    output = capture.get_output()
    outputName = directory(
        ""
        + pathname
        + "\\CapturedOutput\\"
        + curDevice
        + " "
        + str(curBuild)
        + "  "
        + curTime
        + " Ouptut"
        + ".txt"
    )
    with open(outputName, "w") as file:
        print("SAVING CAPTURED OUTPUT")
        file.write(output)
