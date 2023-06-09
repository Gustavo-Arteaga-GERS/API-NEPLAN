from flask import Flask, render_template, Blueprint, request, flash, redirect, url_for,jsonify,redirect, make_response

import untangle
import copy
import json
import numpy as np
import pandas as pd
import random
import datetime
from pulp import *
import pymongo
from pymongo import MongoClient
from dotenv import load_dotenv
from shapely.geometry import shape, Point
from flask_cors import CORS
from flask_cors import cross_origin
import bson
import bson
from clcWebService import WebService
from bs4 import BeautifulSoup
import xmltodict
import uuid
import os
from threading import Timer
from waitress import serve

load_dotenv()
app = Flask(__name__)

cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

# database_mongo 
MONGO_URI = os.getenv('MONGO_URI_LOCAL')
MONGO_DATABASE = os.getenv('MONGO_DATABASE')
MONGO_COLLECTION = os.getenv('MONGO_COLLECTION')


MONGO_DATABASE_USER = os.getenv('MONGO_DATABASE_USER')
MONGO_COLLECTION_USER = os.getenv('MONGO_COLLECTION_USER')
MONGO_COLLECTION_USER_RESULTS = os.getenv('MONGO_COLLECTION_USER_RESULTS')
MONGO_COLLECTION_USER_NEPLAN = os.getenv('MONGO_COLLECTION_USER_NEPLAN')

Puerto = os.getenv('PORT')
client = pymongo.MongoClient(MONGO_URI)
dataBase_ = client[MONGO_DATABASE]


dataBase_User = client[MONGO_DATABASE_USER]
collection_Users = dataBase_User[MONGO_COLLECTION_USER]
collection_Users_results = dataBase_User[MONGO_COLLECTION_USER_RESULTS]
collection_Users_neplan = dataBase_User[MONGO_COLLECTION_USER_NEPLAN]




# web_service_credentials
user_name = os.getenv('USER_NAME')
password = os.getenv("PASSWORD")
project_name = os.getenv("PROJECT_NAME")
yourURL = os.getenv('YOUR_URL')
webservice = WebService()


def delateResults(*id_user):
    
    collection_Users_results.delete_one({'id_user': "".join(id_user)})

def delateResultsNeplan(*id_user):
    
    collection_Users_results.delete_one({'id_user_neplan': "".join(id_user)})

@app.route("/calculator_neplan", methods = ['POST'])
def neplan():
   
    # input_data:
    jsonInput = request.get_json()
   
    id_user = jsonInput['id_user']
    # input_demand_profile:
    Dem = jsonInput['demand_profile']

    # input_solar_profile:
    Pv1kw = jsonInput['solar_profile']

    # input_battery_profile:
    Bess = jsonInput['battery_profile']

    cuenta_disponible = collection_Users_neplan.find_one({'available': True})
    obj_id = bson.ObjectId(cuenta_disponible["_id"])
   
    collection_Users_neplan.update_one({"_id": obj_id},{"$set":{"available": False}}, upsert=False)
    print(cuenta_disponible)
    neplanservice, project = webservice.logging(cuenta_disponible["user_acount"], cuenta_disponible["password"], project_name, yourURL)
    # make_a_random_UUID
    ID = uuid.uuid4()

    # empty_list_to_store_voltage
    volt = []

    # web_services_parameters:
    elementID_1 = "86e22b5d-742d-838c-9527-3a09ba3069d4" # Los_Cerros_MRload_ID
    elementID_2 = "fb3191d4-ded1-1ba7-43b8-3a09ba3069de" # Los_Cerros_MRpv_ID
    elementID_3 = "b3a2c1b0-ccb9-be9f-71b3-3a09ba3069df" # Los_Cerros_MRbess_ID
    elementID_4 = "05e06fd9-248d-5c23-6065-3a09ba306991" # Los_Cerros_MRPCCnode_ID
    attributeName_1 = "P"
    attributeName_2 = "Pset"
    attributeName_3 = "Pset"

    for i in range(0, 48):

        neplanservice.SetElementAttribute(project, "Demand_MR", "Load", attributeName_1, Dem[i])
        neplanservice.SetElementAttribute(project, "PV_MR", "ACDisperseGenerator", attributeName_2, Pv1kw[i])
        neplanservice.SetElementAttribute(project, "ESS_MR", "EnergyStorage", attributeName_3, Bess[i])
        neplanservice.AnalyseVariant(project, str(ID), "LoadFlow", "Default", str(), str(), str())
        #nodeResult = neplanservice.GetResultElementByName(project, "Node_MR", "Busbar", -1, "LoadFlow", None)
        elementName = "Node_MR"
        elementTypeName = "Busbar"
        portNr = "-1"
        analysisType = "LoadFlow"
        nodeResult = neplanservice.GetResultElementByName(project, elementName, elementTypeName, portNr, analysisType, None)
        parsed_data = untangle.parse(nodeResult)
        Unode = parsed_data.LoadFlowNodeResultSym.U
        resultado = volt.append(Unode.cdata)
        # get_voltage_profile_in_PCC:
        # soup = BeautifulSoup(nodeResult, 'xml')
        # root = soup.prettify()
        # o = xmltodict.parse(root)
        # for key, val in o.items():
        #     if isinstance(val, dict):
        #         temp = val.get('U')
        #         volt.append(temp)
    
    volt = [float(i) for i in volt]

    # logic_to_recalculate_volt_as_array_get_per_unit_volt_and_return_volt_as_list:
    volt = np.array(volt)
    volt = volt / 13.2
    volt = volt.tolist()

    # show_results:
    response = [
        {
        "voltage_profile": volt,
        }
    ]
    results_neplan = { "id_user_neplan": id_user, "results": response }
    collection_Users_results.insert_one(results_neplan)
    collection_Users_neplan.update_one({"_id": obj_id},{"$set":{"available": True}}, upsert=False)
    deleter = Timer(800,  delateResultsNeplan, id_user)
    deleter.start()
    res = make_response(jsonify(response), 200)
    return res





@app.route("/calculator_map", methods = ['POST'])
def map():
     # input_data:
    jsonInput = request.get_json()

    # point of reference
    lng = jsonInput['lng']
    ltd = jsonInput['ltd']
    point = Point(lng, ltd)

    # for_cycle_goes_through_collection_shapes
    radiation_level = None
    for i in range(3, 10):
        MONGO_COLLECTION_B ="shape_RL"+ str(i)
        collection_b = dataBase_[MONGO_COLLECTION_B]

        # for_cycle_goes_through_collection_shape
        for ind in collection_b.find():
            ind.pop('_id')
            for feature in ind['features']:
                polygon = shape(feature['geometry'])
                if polygon.contains(point):
                    radiation_level = i
                    print(radiation_level)
                
    if radiation_level == None:
        radiation_level = 0
        print(radiation_level)
    
    # show_results:
    response = [
        {
        "radiation_level": radiation_level,
        },

    ]

    res = make_response(jsonify(response), 200)
    return res



@app.route("/get_results_neplan", methods = ['POST'])
def resultsNeplan():
    jsonInput = request.get_json()
   
    # point of reference
    id_user_neplan = jsonInput['id_user']
    results = collection_Users_results.find_one({'id_user_neplan': id_user_neplan})

    copy_results = copy.deepcopy(results["results"])
    collection_Users_results.delete_one({'id_user_neplan': id_user_neplan})
    res = make_response(jsonify(copy_results), 200)
    return res


@app.route("/get_results", methods = ['POST'])
def results():
    jsonInput = request.get_json()

    # point of reference
    id_user = jsonInput['id_user']
    results = collection_Users_results.find_one({'id_user': id_user})
    copy_results = copy.deepcopy(results["results"])
    collection_Users_results.delete_one({'id_user': id_user})
   
   
    res = make_response(jsonify(copy_results), 200)
    return res

@app.route("/calculator", methods = ['POST'])
def microgrid():

    # input_data:
    jsonInput = request.get_json()
    id_user = jsonInput['id_user']
    
    # input_radiation_level:

        # 1 - 1.5 - 2.0 kWh/m2 day
        # 2 - 2.0 - 2.5 kWh/m2 day
        # 3 - 2.5 - 3.0 kWh/m2 day
        # 4 - 3.0 - 3.5 kWh/m2 day
        # 5 - 3.5 - 4.0 kWh/m2 day
        # 6 - 4.0 - 4.5 kWh/m2 day
        # 7 - 4.5 - 5.0 kWh/m2 day
        # 8 - 5.0 - 5.5 kWh/m2 day
        # 9 - 5.5 - 6.0 kWh/m2 day
    
    radiation_level = jsonInput['radiation_level']
    
    # input_economic_level_(1, 2...6):

    economic_level = jsonInput['economic_level']

    # input_energy_company:

        # 1 - CEO
        # 2 - CELSIA
        # 3 - ENEL
        # 4 - AIR-E
        # 5 - EMCALI
        # 6 - EPM
        # 7 - Average

    energy_company = jsonInput['energy_company']

    # input_failure_scenario

        # Day
        # Month
        # Hour

    day_month = jsonInput['day_month']
    month_year = jsonInput['month_year']
    time_day = jsonInput['time_day']
 
    # annualized_investment_costs_at_12%_discount_rate_20_years:
    Cpv = 361370  # [$/kW]
    Cpvh = 402760  # [$/kW]
    Ckwh = 75941  # [$/kWh]
    Cinvc = 206173  # [$/kW]

    # energy_tariffs_(subsistence_consumption_$/kWh)_by_economic_level_and_energy_company:
    
    # CEO:
    if economic_level == 1 and energy_company == 1:
        Cgrid = 368.8
    elif economic_level == 2 and energy_company == 1:
        Cgrid = 461.0
    elif economic_level == 3 and energy_company == 1:
        Cgrid = 736.8
    elif economic_level == 4 and energy_company == 1:
        Cgrid = 866.9
    elif economic_level == 5 and energy_company == 1:
        Cgrid = 866.9
    elif economic_level == 6 and energy_company == 1:
        Cgrid = 866.9

    # CELSIA:
    if economic_level == 1 and energy_company == 2:
        Cgrid = 319.6
    elif economic_level == 2 and energy_company == 2:
        Cgrid = 399.5
    elif economic_level == 3 and energy_company == 2:
        Cgrid = 679.2
    elif economic_level == 4 and energy_company == 2:
        Cgrid = 799.0
    elif economic_level == 5 and energy_company == 2:
        Cgrid = 958.8
    elif economic_level == 6 and energy_company == 2:
        Cgrid = 958.8

    # ENEL:
    if economic_level == 1 and energy_company == 3:
        Cgrid = 297.1
    elif economic_level == 2 and energy_company == 3:
        Cgrid = 371.4
    elif economic_level == 3 and energy_company == 3:
        Cgrid = 631.3
    elif economic_level == 4 and energy_company == 3:
        Cgrid = 742.7
    elif economic_level == 5 and energy_company == 3:
        Cgrid = 891.3
    elif economic_level == 6 and energy_company == 3:
        Cgrid = 891.3

    # AIR-E:
    if economic_level == 1 and energy_company == 4:
        Cgrid = 343.4
    elif economic_level == 2 and energy_company == 4:
        Cgrid = 429.2
    elif economic_level == 3 and energy_company == 4:
        Cgrid = 729.6
    elif economic_level == 4 and energy_company == 4:
        Cgrid = 858.4
    elif economic_level == 5 and energy_company == 4:
        Cgrid = 1030.0
    elif economic_level == 6 and energy_company == 4:
        Cgrid = 1030.0

    # EMCALI:
    if economic_level == 1 and energy_company == 5:
        Cgrid = 334.8
    elif economic_level == 2 and energy_company == 5:
        Cgrid = 418.5
    elif economic_level == 3 and energy_company == 5:
        Cgrid = 677.5
    elif economic_level == 4 and energy_company == 5:
        Cgrid = 797.1
    elif economic_level == 5 and energy_company == 5:
        Cgrid = 956.5
    elif economic_level == 6 and energy_company == 5:
        Cgrid = 956.5

    # EPM:
    if economic_level == 1 and energy_company == 6:
        Cgrid = 307.6
    elif economic_level == 2 and energy_company == 6:
        Cgrid = 384.5
    elif economic_level == 3 and energy_company == 6:
        Cgrid = 651.0
    elif economic_level == 4 and energy_company == 6:
        Cgrid = 765.9
    elif economic_level == 5 and energy_company == 6:
        Cgrid = 919.0
    elif economic_level == 6 and energy_company == 6:
        Cgrid = 919.0

    # average_energy_company:
    if economic_level == 1 and energy_company == 7:
        Cgrid = 320.5
    elif economic_level == 2 and energy_company == 7:
        Cgrid = 400.6
    elif economic_level == 3 and energy_company == 7:
        Cgrid = 673.7
    elif economic_level == 4 and energy_company == 7:
        Cgrid = 729.6
    elif economic_level == 5 and energy_company == 7:
        Cgrid = 951.1
    elif economic_level == 6 and energy_company == 7:
        Cgrid = 951.1

    # energy_sales_tariff_[$/kWh]
    Cout = Cgrid * 0.37  

    # others_input_data:
    etaC = 0.9
    etaD = 1/0.9
    rMax = 10  
    EbatMin = 0.06
    hoursFailure = 2
    deltaT = 1
    horizon = list(range(8760))
    M = 1e6
    FE = 0.126

    # load_and_solar_profile_reading_from MONGODB:
    # pv_profile_according_to_the_radiation_level:
    collection_ = dataBase_[MONGO_COLLECTION]
    Pv1kw_tmp = []
    if radiation_level == 1:
        for ind in collection_.find():
            temp = ind["Solar_1"]
            Pv1kw_tmp.append(temp)
        Pv1kw = np.array(Pv1kw_tmp)
    elif radiation_level == 2:
        for ind in collection_.find():
            temp = ind["Solar_2"]
            Pv1kw_tmp.append(temp)
        Pv1kw = np.array(Pv1kw_tmp)
    elif radiation_level == 3:
        for ind in collection_.find():
            temp = ind["Solar_3"]
            Pv1kw_tmp.append(temp)
        Pv1kw = np.array(Pv1kw_tmp)
    elif radiation_level == 4:
        for ind in collection_.find():
            temp = ind["Solar_4"]
            Pv1kw_tmp.append(temp)
        Pv1kw = np.array(Pv1kw_tmp)
    elif radiation_level == 5:
        for ind in collection_.find():
            temp = ind["Solar_5"]
            Pv1kw_tmp.append(temp)
        Pv1kw = np.array(Pv1kw_tmp)
    elif radiation_level == 6:
        for ind in collection_.find():
            temp = ind["Solar_6"]
            Pv1kw_tmp.append(temp)
        Pv1kw = np.array(Pv1kw_tmp)
    elif radiation_level == 7:
        for ind in collection_.find():
            temp = ind["Solar_7"]
            Pv1kw_tmp.append(temp)
        Pv1kw = np.array(Pv1kw_tmp)
    elif radiation_level == 8:
        for ind in collection_.find():
            temp = ind["Solar_8"]
            Pv1kw_tmp.append(temp)
        Pv1kw = np.array(Pv1kw_tmp) 
    elif radiation_level == 9:
        for ind in collection_.find():
            temp = ind["Solar_9"]
            Pv1kw_tmp.append(temp)
        Pv1kw = np.array(Pv1kw_tmp)
        
    # load_profile_according_to_economic_level:
    Dem_tmp = []
    if economic_level == 1:
        for ind in collection_.find():
            temp = ind["Demand_1"]
            Dem_tmp.append(temp)
        Dem = np.array(Dem_tmp)
    elif economic_level == 2:
        for ind in collection_.find():
            temp = ind["Demand_2"]
            Dem_tmp.append(temp)
        Dem = np.array(Dem_tmp)
    elif economic_level == 3:
        for ind in collection_.find():
            temp = ind["Demand_3"]
            Dem_tmp.append(temp)
        Dem = np.array(Dem_tmp)
    elif economic_level == 4:
        for ind in collection_.find():
            temp = ind["Demand_4"]
            Dem_tmp.append(temp)
        Dem = np.array(Dem_tmp)
    elif economic_level == 5:
        for ind in collection_.find():
            temp = ind["Demand_5"]
            Dem_tmp.append(temp)
        Dem = np.array(Dem_tmp)
    elif economic_level == 6:
        for ind in collection_.find():
            temp = ind["Demand_6"]
            Dem_tmp.append(temp)
        Dem = np.array(Dem_tmp)

    # line_of_code_with_preset_order_of-data:
    myOrder = []
    for ind in collection_.find():
        temp = ind["Order"]
        myOrder.append(temp)

    # function_get_time_of_the_year
    dt = datetime.datetime(2021, month_year, day_month, time_day)
    def get_time_of_year(dt, type='hours_of_year'):
        intitial_date = datetime.datetime(2021, 1, 1, 0)
        duration = dt - intitial_date
        days, seconds = duration.days, duration.seconds
        hours = days * 24 + seconds // 3600
        
        return hours

    time_of_year = get_time_of_year(dt, 'hours_of_year')

    # function_create_failure_in_power_grid:
    def createFailure(h, n, dt):
        h = int(h // dt)
        vFailure = np.ones(n)
        start_ = time_of_year
        vFailure[start_:start_ + h] = np.zeros(h)
        dateFailure = datetime.timedelta(hours=start_ * dt)

        return vFailure, dateFailure, h, start_
    
    vFailure, dateFailure, h, start_ = createFailure(hoursFailure, len(Dem), deltaT)

    # logic_for_indexing_the_failure_date_according_to_the_annual_start_time:
    dailyProfile_tmp = []
    for ind in collection_.find():
        temp = ind["Day"]
        dailyProfile_tmp.append(temp)
    dailyProfile = np.array(dailyProfile_tmp)

    monthProfile_tmp = []
    for ind in collection_.find():
        temp = ind["Month"]
        monthProfile_tmp.append(temp)
    monthProfile = np.array(monthProfile_tmp)

    hourlyProfile_tmp = []
    for ind in collection_.find():
        temp = ind["Hour"]
        hourlyProfile_tmp.append(temp)
    hourlyProfile = np.array(hourlyProfile_tmp)

    day = int(dailyProfile[start_])
    month = int(monthProfile[start_])
    hour = int(hourlyProfile[start_])

    # optimization_model_written_with_Pulp_syntax
    prob = LpProblem("model_a", LpMinimize)

    # variables_definition
    Pgrid = LpVariable.dicts('Pgrid', horizon, lowBound=0, cat=LpContinuous)
    Pout = LpVariable.dicts("Pout", horizon, lowBound=0, cat=LpContinuous)
    Pinst = LpVariable("Pinst", 0, 3, LpContinuous)
    Pinsth = LpVariable("Pinsth", 0, 3, LpContinuous)
    Ebat = LpVariable("Ebat", 0, 1e4, LpContinuous)
    Pinvc = LpVariable("Pinvc", 0, 1e4, LpContinuous)
    xc = LpVariable.dicts("xc", horizon, lowBound=0, cat=LpBinary)
    xd = LpVariable.dicts("xd", horizon, lowBound=0, cat=LpBinary)
    x_pinst = LpVariable("x_pinst", 0, 1e4, LpBinary)
    x_pinsth = LpVariable("x_pinsth", 0, 1e4, LpBinary)
    Pch = LpVariable.dicts("Pch", horizon, lowBound=0, cat=LpContinuous)
    Pdch = LpVariable.dicts("Pdch", horizon, lowBound=0, cat=LpContinuous)
    E = LpVariable.dicts("E", horizon, lowBound=0, cat=LpContinuous)
    EbatRes = LpVariable("EbatRes", 0, 1e4, LpContinuous)
    x_bat = LpVariable("x_bat", 0, 1e4, LpBinary)
    x_tmp = LpVariable("x_tmp", 0, 1e4, LpBinary)
    tmp = LpVariable("tmp")
    tmp2 = LpVariable("tmp2")
    tmp3 = LpVariable("tmp3")

    # definition_of_constraints:
    # constrainst_set_1_(battery_capacity):
    prob += Ebat >= min(0, EbatMin), "cEbatRes_1"
    prob += Ebat <= M, "cEbatRes_2"
    prob += Ebat >= EbatMin * x_bat, "cEbatRes_3"
    prob += Ebat <= M * x_bat, "cEbatRes_4"
    prob += Ebat >= EbatRes - (1 - x_bat) * M, "cEbatRes_5"
    prob += Ebat <= EbatRes - (1 - x_bat) * EbatMin, "cEbatRes_6"
    prob += Ebat <= EbatRes + (1 - x_bat) * M, "cEbatRes_7"
    
    # constrainst_set_2_(pv_capacity):
    prob += Pinst <= M * x_pinst, "cPinst"
    prob += Pinsth <= M * x_pinsth, "cPinsth"
    prob += x_pinst + x_pinsth <= 1, "cBin_2"

    # constrainst_set_3_(failure_hours):
    if hoursFailure > 0:
        prob += Ebat >= Pinst * (1 / (4 * rMax / 100 * 60)), "EbatMin"
        prob += E[0] == 1.0 * Ebat, "cargaInicial"
        prob += tmp == 1 / 2 * Pinst, "tmp"
        prob += tmp2 == max(Dem[start_:start_ + h]), "tmp2"
        prob += tmp3 <= tmp, "tmp3_1"
        prob += tmp3 <= tmp2, "tmp3_2"
        prob += tmp3 >= tmp - M * x_tmp, "tmp3_3"
        prob += tmp3 >= tmp2 - M * (1 - x_tmp), "tmp3_4"
        prob += Pinvc >= tmp3, "PinvcMin"

    # constrainst_set_4_(power_balance_injected_power_charge_discharge_and_battery_energy):
    for i in range(len(Dem)):
        if vFailure[i] == 0:
            prob += Pinst * Pv1kw[i] + Pinsth * Pv1kw[i] - Pch[i] + Pdch[i] >= Dem[i], "cPotInq" + str(i)
            prob += Pgrid[i] == 0, "cPgridFalla" + str(i)
            prob += Pout[i] == 0, "cPoutFalla" + str(i)
        else:
            prob += Pinst * Pv1kw[i] + Pinsth * Pv1kw[i] - Pch[i] + Pdch[i] - Pout[i] + Pgrid[i] == Dem[i], "cPotEq" + str(i)
        prob += Pch[i] <= M * xc[i], "cBatChM" + str(i)
        prob += Pch[i] <= Pinvc + Pinsth, "cBatCh" + str(i)
        prob += Pdch[i] <= M * xd[i], "cBatDchM" + str(i)
        prob += Pdch[i] <= Pinvc + Pinsth, "cBatDch" + str(i)
        prob += xc[i] + xd[i] <= 1, "cBin_1" + str(i)
        prob += Pout[i] <= Pinst * Pv1kw[i] + Pinsth * Pv1kw[i], "cPout" + str(i)
        prob += E[i] <= 1.0 * Ebat, "cEmax" + str(i)
        prob += E[i] >= 0.2 * Ebat, "cEmin" + str(i)

    # constrainst_set_5_(initial_SOC):
    for i in range(len(Dem)):
        if i == 0:
            if hoursFailure > 0:
                prob += E[i] == 1.0 * Ebat + Pch[i] * etaC * deltaT - (Pdch[i] * etaD) * deltaT, "cE" + str(i)
            else:
                prob += E[i] == 0.2 * Ebat + Pch[i] * etaC * deltaT - (Pdch[i] * etaD) * deltaT, "cE" + str(i)
        else:
            prob += E[i] == E[i - 1] + Pch[i] * etaC * deltaT - (Pdch[i] * etaD) * deltaT, "cE" + str(i)

    # objective_function:
    prob += lpSum([Cgrid * Pgrid[i] * deltaT for i in horizon]) + Cpv * Pinst + Cpvh * Pinsth + Ckwh * Ebat + Cinvc * Pinvc - lpSum([Cout * Pout[i] * deltaT for i in horizon])

    # optimization_problem_solution:
    #prob.solve(PULP_CBC_CMD(fracGap = 0.00001, maxSeconds = 180, threads = None))
    prob.solve(PULP_CBC_CMD(timeLimit=180, threads = None))
    #prob.solve(PULP_CBC_CMD())
    #prob.solve(GUROBI_CMD())
    
    # re-defining_time-dependent_variables_(empty_initial_state):
    Pgrid_ = []
    Pout_ = []
    Pch_ = []
    Pdch_ = []
    E_ = []

    # loop_to_extract_variables_from_the_Pulp_dictionary:
    for v in prob.variables():
        if v.name == "Pinst":
            x1 = v.varValue
        elif v.name == "Pinsth":
            x3 = v.varValue
        elif v.name == "Ebat":
            x2 = v.varValue
        elif v.name == "Pinvc":
            x4 = v.varValue
        elif v.name.startswith("Pgrid_"):
            Pgrid_.append(v.varValue)
        elif v.name.startswith("Pout_"):
            Pout_.append(v.varValue)
        elif v.name.startswith("Pch_"):
            Pch_.append(v.varValue)
        elif v.name.startswith("Pdch_"):
            Pdch_.append(v.varValue)
        elif v.name.startswith("E_"):
            E_.append(v.varValue)
    
    # logic_that_reorganizes_the_list_of_values_according_to_the_variable's_subindex:
    Pgrid_ = [Pgrid_[i] for i in myOrder]
    Pout_ = [Pout_[i] for i in myOrder]
    Pch_ = [Pch_[i] for i in myOrder]
    Pdch_ = [Pdch_[i] for i in myOrder]
    E_ = [E_[i] for i in myOrder]

    # logic_to_recalculate_E__as_array_get_SOC_as_percentage_and_return_E__as_list:
    E_ = np.array(E_)
    E_ = E_ / x2 * 100
    E_ = E_.tolist()

    # logic_to_recalculate_Pch__as_array_get_multiply_with_-1_and_return_as_list:
    Pch_ = np.array(Pch_)
    Pch_ = Pch_ * -1
    Pch_ = Pch_.tolist()

    # logic_to_recalculate_Pout__as_array_get_multiply_with_-1_and_return_as_list:
    Pout_ = np.array(Pout_)
    Pout_ = Pout_ * -1
    Pout_ = Pout_.tolist()

    # recalculated_objective_function:
    obj = Cgrid * np.sum(Pgrid_) * deltaT + Cpv * x1 + Cpvh * x3 + Ckwh * x2 + Cinvc * x4 - Cout * np.sum(Pout_) * deltaT * -1

    # set_of_results:
    failureE = np.sum(Dem[start_:start_ + h]) * deltaT
    importedE = np.sum(Pgrid_) * deltaT
    exportedE = np.sum(Pout_) * deltaT * -1
    investmentC = Cpv * x1 + Cpvh * x3 + Cinvc * x4
    bankC = Ckwh * x2
    investmentT = investmentC + bankC
    purchaseC = np.sum(Pgrid_) * Cgrid * deltaT
    saleC = np.sum(Pout_) * Cout * deltaT * -1
    energySav = np.sum(Dem) * deltaT - importedE
    economicSav = np.sum(Dem) * deltaT * Cgrid - obj
    environSav = energySav * FE
    
    # conditional_to_show_PV_results_with_inverter(s)_type:
    if x1 != 0:
        xinv = x1
        InvType = "Ongrid e inversor cargador"
        xinvc = "{:.2f}".format(x4)
        Pv1kw = Pv1kw * x1
    else:
        xinv = x3
        InvType = "Híbrido"
        xinvc = "No se requiere inversor cargador"
        Pv1kw = Pv1kw * x3
    
    # conditional_to_show_economic_savings:
    if economicSav <= 0:
        economicSav = "La configuración actual no genera beneficios económicos"
    else:
        economicSav = "{:.0f}".format(economicSav)

    # conversion_from_array_to_list
    Dem = Dem.tolist()
    Pv1kw = Pv1kw.tolist()

    # battery_charge_and_discharge_curve_(single vector):
    lists_of_lists = [Pch_, Pdch_]
    Bess = [sum(x) for x in zip(*lists_of_lists)]

    # bucle_to_get_the_48_values:_24_houres_before_failure_and_24_after_failure
    Dem_48 = []
    Pv1kw_48 = []
    Bess_48 = []
    Pgrid_48 = []
    Pout_48 = []
    Pch_48 = []
    Pdch_48 = []
    E_48 = []
    
    for i in range(start_ - 24, start_ + 24):
        Dem_48.append(Dem[i])
        Pv1kw_48.append(Pv1kw[i])
        Bess_48.append(Bess[i])
        Pgrid_48.append(Pgrid_[i])
        Pout_48.append(Pout_[i])
        Pch_48.append(Pch_[i])
        Pdch_48.append(Pdch_[i])
        E_48.append(E_[i])
    
    # bucles_to_get_hour_indexes
    index_48 = []
    hour_index = []
    for i in range(start_- 24, start_ + 24):
        index_48.append(i)

    for i in index_48:
        hour_index.append(int(hourlyProfile[i]))
   
    # show_results:
    response = [
        {
        "energy_saving": "{:.0f}".format(energySav),
        "economic_saving": economicSav,
        "environmental_saving": "{:.0f}".format(environSav),
        },

        {
        "pv_power": "{:.2f}".format(xinv),
        "inverter_type": InvType,
        "charger_inverter_power": xinvc,
        "battery_bank_power": "{:.2f}".format(x2),
        },

        {
        "failure_day": day, 
        "failure_month": month, 
        "failure_hour": hour,
        "failure_duration": "{:.0f}".format(hoursFailure),
        "failure_energy": "{:.2f}".format(failureE),
        },

        {
        "imported_energy": "{:.0f}".format(importedE),
        "exported_energy": "{:.0f}".format(exportedE),
        "energy_purchases": "{:.0f}".format(purchaseC),
        "energy_sales": "{:.0f}".format(saleC),
        "pv_and_inverter_cost": "{:.0f}".format(investmentC),
        "battery_bank_cost": "{:.0f}".format(bankC),
        "investment_cost": "{:.0f}".format(investmentT),       
        },

        {
        "demand_profile": Dem_48,
        "solar_profile": Pv1kw_48,
        "imported_energy_profile": Pgrid_48,
        "exported_energy_profile": Pout_48,
        "charge_battery_profile": Pch_48,
        "discharge_battery_profile": Pdch_48,
        "battery_energy": E_48,
        "battery_profile": Bess_48,
        "hour_index": hour_index,
        },

    ]

    

    # obj_id = bson.ObjectId(result1["_id"])
    # collection_Users_results.update_one({"_id": obj_id},{"$set":{"results": response}}, upsert=False)

    results = { "id_user": id_user, "results": response }
    collection_Users_results.insert_one(results)

    deleter = Timer(240.0,  delateResults, id_user)
    deleter.start()
    res = make_response(jsonify(response), 200)
    return res


@app.route('/')
def index():
  return render_template('index.html')

if __name__ == '__main__':
 app.run(host="0.0.0.0", port=Puerto, debug=True, ssl_context='adhoc', threaded=True)
 #serve(app, host='0.0.0.0', port=2096, url_scheme='https')