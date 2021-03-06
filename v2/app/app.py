"""
This app functions as a REST api endpoint

Have the ability to utilize API keys -- or use VPN to limit to internal traffic
"""
import os
import sys
sys.path.append(".")
from pathlib import Path
import json
import subprocess
import requests
import pandas as pd

# Flask stuff
from flask import Flask, request, jsonify, render_template, flash, redirect
from flask_wtf.csrf import CSRFProtect
from flask_restful import reqparse, abort, Api, Resource

# Import the cache
from extensions import cache

# Import forms
from forms import symptomForm, jsonForm

# Model stuff
from model.fit import fit_to_model

# ==============================================================================
# Initiatlize
# ==============================================================================


app = Flask(__name__)
api = Api(app)
app.config['SECRET_KEY'] = 'any secret string'
csrf = CSRFProtect(app)

# Initialize the cache
cache.init_app(app=app, config={"CACHE_TYPE": "filesystem",'CACHE_DIR': '/tmp'})

# Initialize args
parser = reqparse.RequestParser()

# Configure args per endpoint
# parser.add_argument('data', type=str, required=True, help='Data to be fitted')



# ==============================================================================
# QA Test
# ==============================================================================

# If current model isn't loaded, load it
model_path = Path("data/tmp/best_model.pkl")

if not os.path.isfile(model_path):
    app.logger.info('Training and loading a new model')
    file_path = Path("model/batch_commands/new_model.py")
    command = f"python3 {file_path}"
    subprocess.call(command, shell=True)


# ==============================================================================
# Define Routes
# ==============================================================================


# Home
@app.route('/')
def index():
    # I'd love to display all the endpoints...
    all_routes = ["train_model", "fit_data/"]

    return render_template('index.html', title='Home')

# ------------------------------------------------------------------------------

# User submits data manually
@app.route('/submit-data/',  methods=['GET', 'POST'])
def submit_data():

    form = symptomForm(request.form)

    if request.method == 'POST':
        if form.validate():

            # All code below is to coerce submitted data to required schema
            my_data = {}
            for key, value in form.allFields.data.items():
                if type(value)==dict:
                    my_data.update(value)
            # get rid of the csrf token
            del my_data["csrf_token"]

            # Properly structure the data
            for x in ["calendar","diagnosis"]:
                my_data[x] = {}
                for key, value in my_data.items():
                    if x in key and type(value) == str:
                        new_key = key.split("_")[-1]
                        my_data[x].update({new_key:value})

            # Set the values for symptoms
            all_symptoms = my_data.get("symptoms")
            my_data["symptoms"] = {y:True for y in all_symptoms}

            # save data to cache
            cache.set("my_data", my_data)
            return redirect('/submit-data-success/')
    else:
        return render_template('submit-data.html', title='Submit Data', form=form)


# ------------------------------------------------------------------------------

# User submits data by pasting a json
@app.route('/submit-data-json/',  methods=['GET', 'POST'])
def submit_data_json():

    form = jsonForm(request.form)

    if request.method == 'POST':

        if form.validate():
            my_data = form.allFields.data.get("jsonData")
            my_data = json.loads(my_data)

            # Properly structure the data
            for x in ["calendar","diagnosis"]:
                my_data[x] = {}
                for key, value in my_data.items():
                    if x in key and type(value) == str:
                        new_key = key.split("_")[-1]
                        my_data[x].update({new_key:value})

            cache.set("my_data", my_data)

        else:
            my_errors = {k:v for k,v in form.errors.get("allFields",{}).items()}
            cache.set("errors", my_errors)

        # Now send data along
        return redirect('/submit-data-success/')

    else:
        return render_template('submit-data-json.html', title='Submit Data (Json)', form=form)


# ------------------------------------------------------------------------------

# Submitted data is fitted to model
@app.route('/submit-data-success/',  methods=['GET'])
def fit_my_data():

    data = cache.get("my_data")

    # Success vs. Failure
    if data:

        # Drop the user id
        for x in ["user_id", "userid"]:
            if x in data.keys():
                print("DELETING", x)
                del(data[x])
        # Right now, no test on the data to make sure it complies with API...
        #  *  *  *  *  *  *  *  *  *  *  *  *
        #  This is where the magic happens
        prediction = fit_to_model(data)
        #  *  *  *  *  *  *  *  *  *  *  *  *

        # return jsonify(prediction)
        return render_template('submit-data-success.html', title="Success", data=prediction)

    else:
        errors = cache.get("errors")
        return render_template('submit-data-failure.html', title="Failure", errors=errors)

# ------------------------------------------------------------------------------


# Convert to post...
@app.route('/train_model/', methods=['GET'])
def train_model():
    """
    Will train the model
    """

    # Consider mandating api key
    # api_key = request.args.get('api_key')
    #
    # if not api_key:
    #     return jsonify({
    #         "ERROR": "api_key not found."
    #     })

    # -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -

    # otherwise
    file_path = Path("model/batch_commands/new_model.py")
    command = f"python3 {file_path}"
    subprocess.call(command, shell=True)

    # Add this option to distinct the POST request
    return jsonify({
        "Message": "Finished training the model",
        "METHOD" : "POST"
    })


# ------------------------------------------------------------------------------

# TO DO: Not used yet....
@app.route('/fit_data/', methods=['POST','GET'])
def respond():

    app.logger.info('Fitting data to model')

    # Retrieve the data from  parameter
    data = request.form.get("data", None)
    data = json.loads(data)

    # Alternatively:
    # args = parser.parse_args()
    # data = args.get("data")

    # Success vs. Failure
    if data:
        #  *  *  *  *  *  *  *  *  *  *  *  *
        #  This is where the magic happens
        prediction = fit_to_model(data)
        #  *  *  *  *  *  *  *  *  *  *  *  *

        return jsonify(prediction)
    return jsonify({
            "ERROR": "data not found."
        })
    # # -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -







# ------------------------------------------------------------------------------
if __name__ == '__main__':
    # Threaded option to enable multiple instances for multiple user access support
    app.run(host="0.0.0.0", debug=False)
