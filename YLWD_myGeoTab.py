import arcpy
import mygeotab
import json
import config
import datetime
import time
import pytz


def date_handler(obj):
    if hasattr(obj, 'isoformat'):
        return obj.isoformat()
    else:
        raise TypeError


def get_odo(id):
    odo = api.call('Get', typeName='StatusData', search={
        'deviceSearch': {
            'id': id
        },
        'diagnosticSearch': {
            'id': "DiagnosticOdometerAdjustmentId",
        },
        'fromDate': today_utz,
        'toDate': today_utz
    })

    meters_to_miles = int(round(odo[0]['data'] * 0.00062137))

    return meters_to_miles


def removeKey(d, key):
    r = dict(d)
    for i in range(len(key)):
        testKey = key[i]
        del r[testKey]
    return r


def insert_new_vehicles(vehicle_fc, vehicle_data):
    print time.strftime('%m/%d/%Y %H:%M:%S') + " Adding any new vehicles..."
    notHereList = []
    for index in range(len(vehicle_data)):
        inVehicleDict = vehicle_data[index]
        inVehicleDict2 = removeKey(inVehicleDict, ['lat', 'long', 'id'])
        inVehicleList = inVehicleDict2.values()
        inSerialNumber = inVehicleList[1]

        with arcpy.da.SearchCursor(vehicle_fc, ['serialNumber'],
                                   where_clause="{} = '{}'".format(arcpy.AddFieldDelimiters(vehicle_fc, 'serialNumber'),
                                                                   inSerialNumber)) as searchCursor:
            for row in searchCursor:
                break
            else:
                notHereList.append(inVehicleList)

    if not notHereList:
        print time.strftime('%m/%d/%Y %H:%M:%S') + " No new vehicles added..."
    else:
        print time.strftime('%m/%d/%Y %H:%M:%S') + " Adding new vehicles...\n"

    cursor = arcpy.da.InsertCursor(vehicle_fc, ["name", "serialNumber", "vin", "isOn", "odometer", "speed"])
    # inserts our vehicle_list to our FC
    for row in notHereList:
        cursor.insertRow(row)  # get rid of brackets around row


def update_fc(vehicles_fc, location_list):
    for index in range(len(location_list)):
        upVehicleDict = location_list[index]
        upSerialNumber = upVehicleDict['serialNumber']
        upIsOn = upVehicleDict['isOn']
        upOdometer = upVehicleDict['odometer']
        upSpeed = upVehicleDict['speed']
        upLat = upVehicleDict['lat']
        upLong = upVehicleDict['long']

        #  updating the geometry and whether the vehicle is on or off
        with arcpy.da.UpdateCursor(vehicles_fc, ["serialNumber", "SHAPE@XY", "isOn", "odometer", "speed"]) as cursor:
            for row in cursor:
                # comparing the location list vehicle ID to the FC vehicle ID
                # when the IDs match it will then update the geometry and keyOn
                if row[0] == upSerialNumber:
                    pnt.X = upLong
                    pnt.Y = upLat
                    # setting the projections so it can be displayed correctly
                    pntGeometry1 = arcpy.PointGeometry(pnt, projections[startProjection])
                    pntStatePlaneVGeometry1 = pntGeometry1.projectAs(projections[targetProjection], transformation)
                    # setting both the geometry and keyOn to the updated values
                    row[1] = pntStatePlaneVGeometry1
                    row[2] = upIsOn
                    row[3] = upOdometer
                    row[4] = upSpeed
                    cursor.updateRow(row)
            del cursor
    return


today_utz = datetime.datetime.now(pytz.timezone('US/Pacific'))
cfg = config.cfg
user = cfg['username']
passW = cfg['password']

vehicles_FC = cfg["vehicles_FC"]

projections = cfg["projections"]
startProjection = "GCS_WGS_1984"
targetProjection = "NAD_1983_StatePlane_California_VI_FIPS_0406_Feet"
transformation = "WGS_1984_(ITRF00)_To_NAD_1983"

pnt = arcpy.Point()

api = mygeotab.API(username=user, password=passW, database='ylwd')

api.authenticate()

device = api.get('Device')
deviceInfo = api.get('DeviceStatusInfo')

# print json.dumps(testTrip, indent=2, default=date_handler)

# print json.dumps(testTest, indent=2, default=date_handler)
#
# test = "-*"*100
#
# print json.dumps(device, indent=2, default=date_handler)
# print test
# print json.dumps(deviceInfo, indent=2, default=date_handler)

testList = []
count = 1

for iD in range(len(device)):
    testDict = {}
    for iDI in range(len(deviceInfo)):
        deviceID = device[iD]['id']
        deviceInfoID = deviceInfo[iDI]['device']['id']
        if deviceID == deviceInfoID:
            kmh_to_mph = int(round(deviceInfo[iDI]['speed'] * 0.62137119223733))

            testDict['id'] = device[iD]['id']
            testDict['name'] = device[iD]['name']
            testDict['serialNumber'] = device[iD]['serialNumber']
            testDict['VIN'] = device[iD]['vehicleIdentificationNumber']
            testDict['isOn'] = deviceInfo[iDI]['isDriving']
            testDict['speed'] = kmh_to_mph
            testDict['odometer'] = get_odo(deviceID)
            testDict['lat'] = deviceInfo[iDI]['latitude']
            testDict['long'] = deviceInfo[iDI]['longitude']

            testList.append(testDict)

print json.dumps(testList, indent=2)

insert_new_vehicles(vehicles_FC, testList)

update_fc(vehicles_FC, testList)
