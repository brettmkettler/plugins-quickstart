import os
from flask import Flask, Response, request, jsonify, send_from_directory
from flask_cors import CORS
from sentence_transformers import SentenceTransformer
import requests
import yaml
import json
import openai
import numpy as np
import spacy

openai.api_key = "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"


app = Flask(__name__)
CORS(app)

############### APP DYNAMICS API CREDENTIALS ###############

def check_licensing_consumption(controller_url, api_account_name, api_account_access_key):
    appd_username = "brett.kettler@capgemini.com"
    appd_password = "4esEsg27!!"
    appd_account = "rydertest"
    controller_url = "https://rydertest.saas.appdynamics.com"
    api_account_name = "rydertest"
    api_account_access_key = appd_username + "@" + appd_account + ":" + appd_password
    # Construct the API URL
    url = f"{controller_url}/controller/rest/applications"

    # Set the API headers
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Basic {api_account_access_key}"
    }

    try:
        # Send GET request to retrieve the applications
        response = requests.get(url, headers=headers)

        # Check if the request was successful
        if response.status_code == 200:
            applications = response.json()

            # Iterate over the applications and retrieve licensing information
            licensing_consumption = []
            for app in applications:
                app_name = app["name"]
                app_id = app["id"]

                # Construct the URL for retrieving licensing information
                licensing_url = f"{controller_url}/controller/rest/applications/{app_id}/license"

                # Send GET request to retrieve the licensing information
                licensing_response = requests.get(licensing_url, headers=headers)

                # Check if the licensing request was successful
                if licensing_response.status_code == 200:
                    licensing_info = licensing_response.json()

                    # Extract the licensing consumption details
                    total_license_units = licensing_info["totalLicenseUnits"]
                    used_license_units = licensing_info["usedLicenseUnits"]

                    # Append the licensing consumption details to the result
                    licensing_consumption.append({
                        "application_name": app_name,
                        "total_license_units": total_license_units,
                        "used_license_units": used_license_units
                    })
                else:
                    # Handle errors in retrieving licensing information
                    error_message = f"Failed to retrieve licensing information for application: {app_name}"
                    raise Exception(error_message)

            # Return the licensing consumption details
            return licensing_consumption
        else:
            # Handle errors in retrieving applications
            error_message = "Failed to retrieve applications from the AppDynamics controller"
            raise Exception(error_message)
    except Exception as e:
        # Handle exceptions
        return {"error": str(e)}
    

######### FUNCTIONS ###########

def get_sla_time(service_now_uri, username, password, sys_id):
    url = f"https://rydersystemsdev.service-now.com/api/now/table/incident_sla"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    auth = (username, password)
    params = {
        "sysparm_query": f"sys_id={sys_id}",
    }

    response = requests.get(url, headers=headers, auth=auth, params=params)
    print(response)
    
    if response.status_code == 200:
        result = response.json()

        if "result" in result and len(result["result"]) > 0:
            sla = result["result"][0]
            sla_time = sla.get("sla_time")
            print(f"SLA Time: {sla_time}")
            return sla_time
        else:
            raise Exception("SLA not found or API response empty")
    else:
        raise Exception(f"Error: {response.status_code}, {response.text}")


def get_user_name(service_now_uri, username, password, plain_text_name):
    url = f"https://rydersystemsdev.service-now.com/api/now/table/sys_user"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    auth = (username, password)
    params = {
        "sysparm_query": f"name={plain_text_name}",
        "sysparm_fields": "user_name"
    }

    response = requests.get(url, headers=headers, auth=auth, params=params)

    if response.status_code == 200:
        result = response.json()

        if "result" in result and len(result["result"]) > 0:
            user = result["result"][0]
            user_name = user.get("user_name")
            print(f"User name: {user_name}")
            return user_name
        else:
            raise Exception("User not found or API response empty")
    else:
        raise Exception(f"Error: {response.status_code}, {response.text}")

def get_incidents_by_user(service_now_uri, username, password, assigned_to):
    
    user_name = get_user_name(service_now_uri, username, password, assigned_to)
    
    url = f"https://rydersystemsdev.service-now.com/api/now/table/incident"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    auth = (username, password)
    params = {
        "sysparm_query": f"assigned_to.user_name={user_name}^active=true^stateNOTIN6,7,8",
    }

    response = requests.get(url, headers=headers, auth=auth, params=params)

    if response.status_code == 200:
        result = response.json()

        if "result" in result:
            incidents = result["result"]
            incident_count = len(incidents)

            return {"incident_count": incident_count, "incidents": incidents}
        else:
            raise Exception("No incidents found or API response empty")
    else:
        raise Exception(f"Error: {response.status_code}, {response.text}")



def get_incident_info(service_now_uri, username, password, incident_number):
    url = f"https://rydersystemsdev.service-now.com/api/now/table/incident"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    auth = (username, password)
    params = {
        "sysparm_query": f"number={incident_number}",
    }

    response = requests.get(url, headers=headers, auth=auth, params=params)

    if response.status_code == 200:
        result = response.json()

        if "result" in result and len(result["result"]) > 0:
            incident = result["result"][0]  # Assuming only one incident is returned

            # Extract work notes and comments
            description = incident.get("description", "")
            work_notes = [entry.get("value") for entry in incident.get("work_notes", [])]
            comments = [entry.get("value") for entry in incident.get("comments", [])]

            # Add work notes and comments to incident information
            incident["work_notes"] = work_notes
            incident["comments"] = comments

            # Search for recommendations using description
            description = incident.get("description", "")
            relevantinfo = search_service_now(service_now_uri, username, password, description)

            incident_prompt = (
                "You are a helpful AI Assistant named Gemi. How would you help resolve this incident given the incident description, work notes, comments, and relevant incident details, please provide a very detailed 2 paragraph recommending a solution to this incident based on the information given below: "
                + "\n"
                + "Incident Description: "
                + description
                + "\n"
                + "Work Notes: "
                + str(work_notes)
                + "\n"
                + "Comments: "
                + str(comments)
                + "\n"
                + "Relevant Incident details: "
                + str(relevantinfo)
                + "\n"
                + "\nRecommendation:"
            )

            print("Incident Prompt: " + incident_prompt)

            # Generate recommendation using OpenAI
            response = openai.Completion.create(
                engine="text-davinci-003",
                prompt=incident_prompt,
                max_tokens=1000,
                n=1,
                stop=None,
                temperature=0.3
            )
            recommendation = response.choices[0].text.strip()

            # Add recommendation to incident information
            incident["INCIDENT RECOMMENDATIONS: "] = recommendation

            print("Recommendation: " + recommendation)

            return incident
        else:
            raise Exception("Incident not found or API response empty")
    else:
        raise Exception(f"Error: {response.status_code}, {response.text}")


def search_service_now(service_now_uri, username, password, description):
    url = f"https://rydersystemsdev.service-now.com/api/now/table/incident"

    nlp = spacy.load("en_core_web_md")

    doc = nlp(description)
    entities = [ent.text for ent in doc.ents]

    if not entities:
        print("No entities found.")
        exit()

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    auth = (username, password)

    params = {
        "sysparm_query": f"^{','.join(entities)}^stateIN6,7^ORDERBYDESCsys_created_on",
        "sysparm_limit": "5"
    }
    print(params)
    print(f"Searching for {','.join(entities)} in incidents...")

    response = requests.get(url, headers=headers, auth=auth, params=params)

    relevantinfo = []

    if response.status_code == 200:
        data = response.json()

        if "result" in data:
            for item in data["result"]:
                relevantinfo.append(item['description'])
                relevantinfo.append(item['work_notes'])
                relevantinfo.append(item['comments'])
                relevantinfo.append(item['close_notes'])
                relevantinfo.append(item['resolved_by'])

        else:
            print("No results found")
            return []
    return relevantinfo

def generate_recommendation(username, password, description, work_notes, comments, relevantinfo):
    url = f"https://rydersystemsdev.service-now.com/api/now/table/incident"

    nlp = spacy.load("en_core_web_md")

    doc = nlp(description)
    entities = [ent.text for ent in doc.ents]

    if not entities:
        print("No entities found.")
        exit()

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    auth = (username, password)

    params = {
        "sysparm_query": f"^{','.join(entities)}^stateIN6,7^ORDERBYDESCsys_created_on",
        "sysparm_limit": "5"
    }
    print(params)
    print(f"Searching for {','.join(entities)} in incidents...")

    response = requests.get(url, headers=headers, auth=auth, params=params)

    relevantinfo = []

    if response.status_code == 200:
        data = response.json()

        if "result" in data:
            for item in data["result"]:
                relevantinfo.append(item['description'])
                relevantinfo.append(item['work_notes'])
                relevantinfo.append(item['comments'])
                relevantinfo.append(item['close_notes'])
                relevantinfo.append(item['resolved_by'])

        else:
            print("No results found")
    
    incident_prompt = (
        "You are a helpful AI Assistant named Gemi. How would you help resolve this incident given the incident description, work notes, comments, and relevant incident details, please provide a very detailed 2 paragraph recommending a solution to this incident based on the information given below: "
        + "\n"
        + "Incident Description: "
        + description
        + "\n"
        + "Work Notes: "
        + str(work_notes)
        + "\n"
        + "Comments: "
        + str(comments)
        + "\n"
        + "Relevant Incident details: "
        + str(relevantinfo)
        + "\n"
        + "\nRecommendation:"
    )

    print("Incident Prompt: " + incident_prompt)

    # Generate recommendation using OpenAI
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=incident_prompt,
        max_tokens=1000,
        n=1,
        stop=None,
        temperature=0.3
    )
    recommendation = response.choices[0].text.strip()

    print("Recommendation: " + recommendation)

    return recommendation

def get_incident_sys_id(service_now_uri, username, password, incident_number):
    url = f"https://rydersystemsdev.service-now.com/api/now/table/incident"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    auth = (username, password)
    params = {
        "sysparm_query": f"number={incident_number}",
        "sysparm_fields": "sys_id"
    }

    response = requests.get(url, headers=headers, auth=auth, params=params)

    if response.status_code == 200:
        result = response.json()

        if "result" in result and len(result["result"]) > 0:
            incident = result["result"][0]
            sys_id = incident.get("sys_id")
            print(f"Incident Sys ID: {sys_id}")
            return sys_id
        else:
            raise Exception("Incident not found or API response empty")
    else:
        raise Exception(f"Error: {response.status_code}, {response.text}")



######################### APP ROUTES #####################################



@app.route('/check-licensing-consumption', methods=['GET'])
def check_licensing_consumption_route():
    result = check_licensing_consumption(controller_url, api_account_name, api_account_access_key)

    if "error" in result:
        return jsonify({"error": result["error"]}), 500
    else:
        licensing_consumption = []
        for licensing_info in result:
            app_name = licensing_info["application_name"]
            total_license_units = licensing_info["total_license_units"]
            used_license_units = licensing_info["used_license_units"]

            licensing_consumption.append({
                "application_name": app_name,
                "total_license_units": total_license_units,
                "used_license_units": used_license_units
            })

        return jsonify(licensing_consumption)
    
    
@app.route('/get-sla-time', methods=['POST'])
def get_sla_time_route():
    data = request.get_json()
    service_now_uri = data.get('service_now_uri')
    username = "AppDynamicAlert"
    password = "appdynamics01"
    incident_number = data.get('incident_number')
    
    sys_id = get_incident_sys_id(service_now_uri, username, password, incident_number)

    try:
        sla_time = get_sla_time(service_now_uri, username, password, sys_id)
        return jsonify({'sla_time': sla_time})
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    

@app.route('/generate-recommendation', methods=['POST'])
def generate_recommendation_route():
    data = request.get_json()
    service_now_uri = data.get('service_now_uri')
    username = "AppDynamicAlert"
    password = "appdynamics01"
    description = data.get('description')
    work_notes = data.get('work_notes', [])
    comments = data.get('comments', [])
    relevantinfo = data.get('relevantinfo', [])

    try:
        recommendation = generate_recommendation(username, password, description, work_notes, comments, relevantinfo)
        return jsonify({'recommendation': recommendation})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route('/get-incident', methods=['POST'])
def get_incident():
    data = request.get_json()
    service_now_uri = data.get('service_now_uri')
    username = "AppDynamicAlert"
    password = "appdynamics01"
    incident_number = data.get('incident_number')

    try:
        incident_info = get_incident_info(service_now_uri, username, password, incident_number)
        return jsonify(incident_info)
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route('/get_assigned_to_user', methods=['POST'])
def get_incidents_by_user_route():
    data = request.get_json()
    service_now_uri = data.get('service_now_uri')
    username = "AppDynamicAlert"
    password = "appdynamics01"
    assigned_to = data.get('assigned_to')

    try:
        incidents = get_incidents_by_user(service_now_uri, username, password, assigned_to)
        return jsonify(incidents)
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/logo.png")
def plugin_logo():
    return send_from_directory('.', 'logo.png')


@app.route('/.well-known/ai-plugin.json')
def serve_manifest():
    return send_from_directory('.', 'ai-plugin.json')


@app.route('/openapi.yaml')
def serve_openapi_yaml():
    with open('openapi.yaml', 'r') as f:
        yaml_data = f.read()
    return Response(yaml_data, mimetype='text/yaml')


@app.route('/ai-plugin.json')
def serve_openapi_json():
    with open('ai-plugin.json', 'r') as f:
        json_data = json.load(f)
    return jsonify(json_data)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5003)
