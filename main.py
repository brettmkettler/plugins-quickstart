import os
from flask import Flask, Response, request, jsonify, send_from_directory
from flask_cors import CORS
from sentence_transformers import SentenceTransformer, util
import requests
import yaml
import json
import openai
import numpy as np
import spacy
import keys

openai.api_key = keys.openai_key

################
# VARIABLES
################

# TODO: Update in lower app routes
service_now_uri = "https://rydersystemsdev.service-now.com"
username = "AppDynamicAlert"
password = "appdynamics01"

app = Flask(__name__)
CORS(app)


##################### MODULES ##############################


############################################################
############### APP DYNAMICS API CREDENTIALS ###############
############################################################


# def check_licensing_consumption(controller_url, api_account_name, api_account_access_key):
#     appd_username = "brett.kettler@capgemini.com"
#     appd_password = "4esEsg27!!"
#     appd_account = "rydertest"
#     controller_url = "https://rydertest.saas.appdynamics.com"
#     api_account_name = "rydertest"
#     api_account_access_key = appd_username + "@" + appd_account + ":" + appd_password
#     # Construct the API URL
#     url = f"{controller_url}/controller/rest/applications"

#     # Set the API headers
#     headers = {
#         "Content-Type": "application/json",
#         "Authorization": f"Basic {api_account_access_key}"
#     }

#     try:
#         # Send GET request to retrieve the applications
#         response = requests.get(url, headers=headers)

#         # Check if the request was successful
#         if response.status_code == 200:
#             applications = response.json()

#             # Iterate over the applications and retrieve licensing information
#             licensing_consumption = []
#             for app in applications:
#                 app_name = app["name"]
#                 app_id = app["id"]

#                 # Construct the URL for retrieving licensing information
#                 licensing_url = f"{controller_url}/controller/rest/applications/{app_id}/license"

#                 # Send GET request to retrieve the licensing information
#                 licensing_response = requests.get(licensing_url, headers=headers)

#                 # Check if the licensing request was successful
#                 if licensing_response.status_code == 200:
#                     licensing_info = licensing_response.json()

#                     # Extract the licensing consumption details
#                     total_license_units = licensing_info["totalLicenseUnits"]
#                     used_license_units = licensing_info["usedLicenseUnits"]

#                     # Append the licensing consumption details to the result
#                     licensing_consumption.append({
#                         "application_name": app_name,
#                         "total_license_units": total_license_units,
#                         "used_license_units": used_license_units
#                     })
#                 else:
#                     # Handle errors in retrieving licensing information
#                     error_message = f"Failed to retrieve licensing information for application: {app_name}"
#                     raise Exception(error_message)

#             # Return the licensing consumption details
#             return licensing_consumption
#         else:
#             # Handle errors in retrieving applications
#             error_message = "Failed to retrieve applications from the AppDynamics controller"
#             raise Exception(error_message)
#     except Exception as e:
#         # Handle exceptions
#         return {"error": str(e)}

    
#########################################################
######### FUNCTIONS ###########
#########################################################
def check_current_ticket_resolution(incident):
    # Get the current incident resolution
    print("Checking current incident resolution...\n\n")
    

def summarize_incident_comments(comments, work_notes, comments_and_work_notes, close_notes):
    print("Summarizing comments to a resolution...\n\n")
    
    # Get only most recent work notes, comments, and close notes
    comments = comments[-4:]
    work_notes = work_notes[-4:]
    comments_and_work_notes = comments_and_work_notes[-4:]
    
    incident_prompt = (
        "You are a helpful AI Assistant named Gemi. How would you summarize the work notes and comments please provide a very detailed 2 paragraph recommending a solution to this incident based on the comments given below: "
        + "\n"
        #+ "Comments: "
        #+ comments
        #+ "\n"
        + "Work Notes: "
        + work_notes
        + "\n"
        + "Comments and Work Notes: "
        + comments_and_work_notes
        + "Close Notes: "
        + close_notes
        )

    #print("Incident Prompt: " + incident_prompt)

    # Generate recommendation using OpenAI
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=incident_prompt,
        max_tokens=1000,
        n=1,
        stop=None,
        temperature=0.3
        )
    
    summarize = response.choices[0].text.strip()
    print("Summarized Resolution: " + summarize)
    return summarize
    
    

# ANALYZE & GET ONLY SIMILAR INCIDENTS
# Step 
def analyze_incidents(description, incidents):
    print("Analyzing incidents...\n\n")
    
    print("Description to Analyze: ", description)
    
    print("Incidents to Analyze: ", incidents)
    
    model = SentenceTransformer('bert-base-nli-mean-tokens')  # Load the Sentence Transformers model
    
    relevantinfo = []
    relevantincidents = []
    
    similarity_threshold = 0.8  # Adjust the threshold based on your requirements

    for incident in incidents:
        incident_description = incident.get('short_description', '')
        incident_number = incident.get('number', '')
        incident_desc = incident.get('description', '')
        incident_closenotes = incident.get('close_notes', '')
        incident_worknotes = incident.get('work_notes', '')
        incident_comments = incident.get('comments', '')
        incident_comments_and_worknotes = incident.get('comments_and_work_notes', '')
        
        print("Analyzing Incident Number: ", incident_number)
        
        # Embed the incident description into a fixed-dimensional vector
        incident_embedding = model.encode([description], convert_to_tensor=True)

        # Compare the current incident with previously analyzed incidents
        issue_embedding = model.encode([incident_description], convert_to_tensor=True)
        similarity_score = util.pytorch_cos_sim(incident_embedding, issue_embedding)
        
        #checking if the description is similar to the incident description
        print("Similarity Score: ", similarity_score.item())
        
        if similarity_score.item() > similarity_threshold:
            # Get comments for the incident
            #incident_comments = get_incident_comments(incident_number)
            
            # Summarize the comments
            summarize = summarize_incident_comments(incident_comments, incident_worknotes, incident_comments_and_worknotes, incident_closenotes)
        
            # If similarity score is above the threshold, consider them similar issues
            print(f"Similar issue found between current incident and previous issue: {incident_description}")
            print(f"Incident number: {incident_number}")
            print(f"Resolution Summary: {summarize}")
            #print(f"Resolution for previous issue: {incident_closenotes}")
            #print(f"Work notes for previous issue: {incident_worknotes}")
            #print(f"Comments for previous issue: {incident_comments}")
            #print(f"Comments and work notes for previous issue: {incident_comments_and_worknotes}")
            
            # Add relevant info to list if match is found
            #relevantinfo.append(incident_closenotes)
            #relevantinfo.append(incident_comments)
            #relevantinfo.append(incident_worknotes)
            #relevantinfo.append(incident_comments_and_worknotes)
            
            relevantinfo.append(summarize)
            relevantincidents.append(incident_number)
        
        # Add the current incident's description to the list of common issues
        #common_issues.append(incident_description)
    
    # combine relevantinfo and relevantincidents into a dictionary
    relevantinfo = dict(zip(relevantincidents, relevantinfo))
    print("Relevant Info: ", relevantinfo)
        
    return relevantinfo, relevantincidents




def create_service_request(service_now_uri, username, password, short_description, description):
    # Developer instance URL
    url = f"https://dev59033.service-now.com/api/now/table/sc_request"
    username = "admin_api"
    password = "(Bf?6H{B<{ED.^[Ht%CSz#WxPm4Wxvp?hl!fuHl.yJJds3dq(l0p^WTB_v9C(-Fo%nHP03K))SHW6R>HDJ}@<E=GV){Y5}9Rl.s?"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    auth = (username, password)
    payload = {
        "short_description": short_description,
        "description": description,
        "opened_by": "Gemi_AI"
    }

    response = requests.post(url, headers=headers, auth=auth, json=payload)

    if response.status_code == 201:
        result = response.json()
        return result.get("result", {})
    else:
        raise Exception(f"Error: {response.status_code}, {response.text}")

# # Work in progress
# def get_sla_time(service_now_uri, username, password, sys_id):
#     url = f"https://rydersystemsdev.service-now.com/api/now/table/incident_sla"
#     headers = {
#         "Content-Type": "application/json",
#         "Accept": "application/json"
#     }
#     auth = (username, password)
#     params = {
#         "sysparm_query": f"sys_id={sys_id}",
#     }

#     response = requests.get(url, headers=headers, auth=auth, params=params)
#     print(response)
    
#     if response.status_code == 200:
#         result = response.json()

#         if "result" in result and len(result["result"]) > 0:
#             sla = result["result"][0]
#             sla_time = sla.get("sla_time")
#             print(f"SLA Time: {sla_time}")
#             return sla_time
#         else:
#             raise Exception("SLA not found or API response empty")
#     else:
#         raise Exception(f"Error: {response.status_code}, {response.text}")


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
        "sysparm_query": f"assigned_to.user_name={user_name}^active=true^stateNOTIN6,7,8"
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



def get_cmdb_item_from_incident(incident_number):
    username = "AppDynamicAlert"
    password = "appdynamics01"
    api_url = 'https://rydersystemsdev.service-now.com/api/now/table/incident'
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }
    params = {
        'sysparm_query': f'number={incident_number}',
        'sysparm_limit': 1
    }
    response = requests.get(api_url, headers=headers, auth=(username, password), params=params)
    print(response)
    if response.status_code == 200:
        try:
            data = response.json()  # Try parsing response as JSON
            result = data.get('result')
            print (result)
            if result:
                #
                # if cmdb is null, return None
                if result[0].get('cmdb_ci') is None:
                    print('No CMDB item found for the given incident.')
                    return None
                else:
                    cmdb_item = result[0].get('cmdb_ci')
                    print(f'CMDB item: {cmdb_item}')

                    cmdb_item_value = cmdb_item.get('value')  # Use .get() to access the value
                    print(f'CMDB item value: {cmdb_item_value}')

                    return cmdb_item_value
            else:
                print('No incident found with the given number.')
                return None
        except json.JSONDecodeError:
            print('Error occurred while decoding response JSON.')
            return None
    else:
        print('Error occurred while fetching incident details:', response.text)
        return None




# Needs to be renamed
def get_incident_info(service_now_uri, username, password, incident_number):
    url = f"https://rydersystemsdev.service-now.com/api/now/table/incident"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    auth = (username, password)
    params = {
        "sysparm_query": f"number={incident_number}",  # Only retrieve incidents with state 6 (Resolved) or 7 (Closed)
        'sysparm_limit': 100,  # Adjust the limit based on your requirements
        'sysparm_sort': 'sys_updated_on:desc',  # Sort incidents by the latest updated date in descending order
        'sysparm_display_value': 'true'  # Display display values instead of sys_ids
    }

    response = requests.get(url, headers=headers, auth=auth, params=params)

    if response.status_code == 200:
        result = response.json()

        if "result" in result and len(result["result"]) > 0:
            incident = result["result"][0]  # Assuming only one incident is returned

            # Extract work notes and comments
            description = incident.get("description", "")
            work_notes = incident.get("work_notes", "")
            comments = incident.get("comments", "")
            number = incident.get("number", "")
            comments_and_work_notes = ("comments_and_work_notes", "")
            
            # Only get 3 most recent work notes and comments
            comments_and_work_notes = comments_and_work_notes[-4:]

            # Add work notes and comments to incident information
            #incident["work_notes"] = work_notes
            #incident["comments"] = comments
            
            ########################################
            # Get relevant information from incident
            ########################################
            
            
            #cmdb_item = get_cmdb_item_from_incident(incident_number)
            
            #incidents = fetch_related_incidents(cmdb_item)
            
            #relatedinfo = analyze_incidents(description, incidents)
            
            relatedinfo = "Provide a general recommendation for this incident."
            
            print("Common Issues Resolution notes: " + str(relatedinfo))
            
            incident_prompt = (
                "You are a helpful AI Assistant named Gemi. How would you help resolve this incident given the incident description, work notes, comments, and relevant incident details. Check the work notes to see if the someone has already fixed the item. Please provide a very detailed 2 paragraph recommending a solution to this incident based on the information given below. Note that this recommendation is only based on the ticket details and recommend to the user that they can ask for a more detailed recommendation if needed: "
                + "\n"
                + "Incident Description: "
                + description
                + "\n"
                + "Work Notes: "
                + str(work_notes)
                + "\n"
                + "Comments and Work Notes: "
                + str(comments_and_work_notes)
                + "\n"
                + "Comments:"
                + str(comments)
                + "Relevant Incident details: "
                + str(relatedinfo)
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


# # Not used
# def search_service_now(service_now_uri, username, password, description):
#     url = f"https://rydersystemsdev.service-now.com/api/now/table/incident"

#     nlp = spacy.load("en_core_web_md")

#     doc = nlp(description)
#     entities = [ent.text for ent in doc.ents]

#     if not entities:
#         print("No entities found.")
#         exit()

#     headers = {
#         "Content-Type": "application/json",
#         "Accept": "application/json"
#     }
#     auth = (username, password)
    
#     ################################
#     # number of incidents to return
#     numberlimit = 30
#     ################################
    
#     params = {
#         "sysparm_query": f"^{','.join(entities)}^stateIN6,7^ORDERBYDESCsys_created_on",
#         "sysparm_limit": f"{numberlimit}"
#     }
#     print(params)
#     print(f"Searching for {numberlimit} records of {','.join(entities)} in incidents...")

#     response = requests.get(url, headers=headers, auth=auth, params=params)

#     relevantinfo = []

#     if response.status_code == 200:
#         data = response.json()

#         if "result" in data:
#             for item in data["result"]:
#                 relevantinfo.append(item['description'])
#                 relevantinfo.append(item['work_notes'])
#                 relevantinfo.append(item['comments'])
#                 relevantinfo.append(item['close_notes'])
#                 relevantinfo.append(item['resolved_by'])

#         else:
#             print("No results found")
#             return []
#     return relevantinfo


def fetch_related_incidents(cmdb_item_identifier):
    print(f"Fetching related incidents for CMDB item: {cmdb_item_identifier}")
    username = "AppDynamicAlert"
    password = "appdynamics01"
    api_url = 'https://rydersystemsdev.service-now.com/api/now/table/incident'
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }
    params = {
        'sysparm_query': f'cmdb_ci={cmdb_item_identifier}^stateIN6,7',  # Only retrieve incidents with state 6 (Resolved) or 7 (Closed)
        'sysparm_limit': 100,  # Adjust the limit based on your requirements
        'sysparm_sort': 'sys_updated_on:desc',  # Sort incidents by the latest updated date in descending order
        'sysparm_display_value': 'true'  # Display display values instead of sys_ids
    }
    response = requests.get(api_url, headers=headers, auth=(username, password), params=params)
    if response.status_code == 200:
        print(response.json().get('result'))
        return response.json().get('result')
    else:
        print('Error occurred while fetching related incidents:', response.text)
        return None
    
    
def get_entity_incidents(username, password, description):
    url = f"https://rydersystemsdev.service-now.com/api/now/table/incident"

    # Extracting key terms from description of the incident
    nlp = spacy.load("en_core_web_md")
    doc = nlp(description)
    entities = [ent.text for ent in doc.ents]
    if not entities:
        print("No entities found.")
        exit()

    # Searching for incidents with the same key terms
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    auth = (username, password)

    ################################
    # number of incidents to return
    numberlimit = 100
    ################################
    
    params = {
        "sysparm_query": f"^{','.join(entities)}^stateIN6,7^ORDERBYDESCsys_created_on",
        'sysparm_limit': numberlimit,  # Adjust the limit based on your requirements
        'sysparm_sort': 'sys_updated_on:desc'  # Sort incidents by the latest updated date in descending order
    }
    print(params)

    print(f"Searching for {numberlimit} records of {','.join(entities)} in incidents...")

    # Response from ServiceNow on the search
    response = requests.get(url, headers=headers, auth=auth, params=params)

    #convert response to json
    incidents_raw = response.json().get('result')
    
    return incidents_raw


def generate_recommendation(username, password, description, work_notes, comments, relevantinfo, incident_number):
    
    print("Generating recommendation...")

    cmdb_item = get_cmdb_item_from_incident(incident_number)
    
    # if cmdb_item is empty, then cmdb_item = "No CMDB Item found"
    if not cmdb_item:
        print("No CMDB Item found")
        cmdb_item = "No CMDB Item found"
    
    
    print(f"CMDB Item: {cmdb_item}")
    
    incidents_raw = fetch_related_incidents(cmdb_item)
    
    #analyze incidents        
    relevantinfodata = analyze_incidents(description, incidents_raw)
    
    # if relevantinfodata is empty, then relevantinfodata = "No relevant information found"
    if not relevantinfodata:
        relevantinfodata = "No relevant information found provide a recommendation based on the information given"

    # Create incident prompt
    incident_prompt = (
        "You are a helpful AI Assistant named Gemi. How would you help resolve this incident given the incident description, work notes, comments, and relevant incident details. Check the work notes to see if the someone has already fixed the item. Please provide a very detailed 2 paragraph recommending a solution to this incident based on the information given below. Note that this recommendation is only based on the ticket details and recommend to the user that they can ask for a more detailed recommendation if needed: "
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
        + str(relevantinfodata)
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


# get sys_id of incident
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


##########################################################################
######################### APP ROUTES #####################################
##########################################################################

@app.route('/create-service-request', methods=['POST'])
def create_service_request_route():
    data = request.get_json()
    service_now_uri = data.get('service_now_uri')
    username = "AppDynamicAlert"
    password = "appdynamics01"
    short_description = data.get('short_description')
    description = data.get('description')
    

    try:
        service_request = create_service_request(service_now_uri, username, password, short_description, description)
        return jsonify(service_request)
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    

# @app.route('/check-licensing-consumption', methods=['GET'])
# def check_licensing_consumption_route():
#     result = check_licensing_consumption(controller_url, api_account_name, api_account_access_key)

#     if "error" in result:
#         return jsonify({"error": result["error"]}), 500
#     else:
#         licensing_consumption = []
#         for licensing_info in result:
#             app_name = licensing_info["application_name"]
#             total_license_units = licensing_info["total_license_units"]
#             used_license_units = licensing_info["used_license_units"]

#             licensing_consumption.append({
#                 "application_name": app_name,
#                 "total_license_units": total_license_units,
#                 "used_license_units": used_license_units
#             })

#         return jsonify(licensing_consumption)
    
    
# @app.route('/get-sla-time', methods=['POST'])
# def get_sla_time_route():
#     data = request.get_json()
#     service_now_uri = data.get('service_now_uri')
#     username = "AppDynamicAlert"
#     password = "appdynamics01"
#     incident_number = data.get('incident_number')
    
#     sys_id = get_incident_sys_id(service_now_uri, username, password, incident_number)

#     try:
#         sla_time = get_sla_time(service_now_uri, username, password, sys_id)
#         return jsonify({'sla_time': sla_time})
#     except Exception as e:
#         return jsonify({"error": str(e)}), 400
    

@app.route('/generate-recommendation', methods=['POST'])
def generate_recommendation_route():
    data = request.get_json()
    service_now_uri = data.get('service_now_uri')
    username = "AppDynamicAlert"
    password = "appdynamics01"
    description = data.get('description')
    work_notes = data.get('work_notes', [])
    #comments = data.get('comments', [])
    comments = data.get("comments_and_work_notes", "")
    relevantinfo = data.get('relevantinfo', [])
    incident_number = data.get('incident_number')
    #comments_and_work_notes = data.get("comments_and_work_notes", "")
    print(f"Incident Number: {incident_number}")

    try:
        recommendation = generate_recommendation(username, password, description, work_notes, comments, relevantinfo, incident_number)
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
