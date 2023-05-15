from flask import Blueprint, render_template, request, flash, redirect, url_for, Flask,jsonify,redirect, make_response,session, app
import json
import numpy as np
import pandas as pd
from clcWebService import WebService
from bs4 import BeautifulSoup
import xmltodict
import uuid
import os
from dotenv import load_dotenv
from flask_cors import CORS
from flask_cors import cross_origin

from datetime import timedelta

load_dotenv()
app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

# web_service_credentials
user_name = os.getenv('USER_NAME')
password = os.getenv("PASSWORD")
project_name = os.getenv("PROJECT_NAME")
yourURL = os.getenv('YOUR_URL')
webservice = WebService()
neplanservice, project = webservice.logging(user_name, password, project_name, yourURL)

@app.route("/calculator_neplan", methods = ['POST'])

def make_session_permanent():
  session.permanent = True
  app.permanent_session_lifetime = timedelta(minutes=8)


def neplan():

    # input_data:
    jsonInput = request.get_json()

    # input_demand_profile:
    Dem = jsonInput['demand_profile']

    # input_solar_profile:
    Pv1kw = jsonInput['solar_profile']

    # input_battery_profile:
    Bess = jsonInput['battery_profile']

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

        neplanservice.SetElementAttributeByID(project, elementID_1, attributeName_1, Dem[i])
        neplanservice.SetElementAttributeByID(project, elementID_2, attributeName_2, Pv1kw[i])
        neplanservice.SetElementAttributeByID(project, elementID_3, attributeName_3, Bess[i])
        neplanservice.AnalyseVariant(project, str(ID), "LoadFlow", "Default", str(), str(), str())
        nodeResult = neplanservice.GetResultElementByID(project, elementID_4, -1, "LoadFlow")

        # get_voltage_profile_in_PCC:
        soup = BeautifulSoup(nodeResult, 'xml')
        root = soup.prettify()
        o = xmltodict.parse(root)
        for key, val in o.items():
            if isinstance(val, dict):
                temp = val.get('U')
                volt.append(temp)
    
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

    res = make_response(jsonify(response), 200)
    return res

    
@app.route('/')
def index():
  return render_template('index.html')

if __name__ == '__main__':
  app.run(port=5000)
