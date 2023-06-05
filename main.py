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
            work_notes = [entry.get("value") for entry in incident.get("work_notes", [])]
            comments = [entry.get("value") for entry in incident.get("comments", [])]

            # Add work notes and comments to incident information
            incident["work_notes"] = work_notes
            incident["comments"] = comments

            # Search for recommendations using description
            description = incident.get("short_description", "")
            #print("Short Description: " + description)
            relevantinfo = search_service_now(service_now_uri, username, password, description)
            
            #format list to json
            relevantinfo = json.dumps(relevantinfo)
            
            #format json to string
            
            

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
    
    # Load spaCy's English language model 
    # python -m spacy download <model>

    #nlp = spacy.load("en_core_web_sm")
    nlp = spacy.load("en_core_web_md")

    # Perform entity extraction on the description
    doc = nlp(description)
    entities = [ent.text for ent in doc.ents]

    # If no entities are extracted, skip the search
    if not entities:
        print("No entities found.")
        exit()
        
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    auth = (username, password)
    # params = {
    #     "sysparm_query": f"descriptionLIKE{description}^stateIN6,7",
    #     "sysparm_limit": "5"
    # }
    
    # Set request parameters
    params = {
        "sysparm_query": f"^{','.join(entities)}^stateIN6,7",
        "sysparm_limit": "5"
    }
    print (params)
    print(f"Searching for {','.join(entities)} in incidents...")

    response = requests.get(url, headers=headers, auth=auth, params=params)
    
    # Create a list to store the relevant info
    relevantinfo = []
        
    if response.status_code == 200:
        data = response.json()
    
        #print(data)

        # Print the results
        if "result" in data:
            for item in data["result"]:
                # print(f"ID: {item['sys_id']}")
                # print(f"Description: {item['description']}")
                # print(f"Work Notes: {item['work_notes']}")
                # print(f"Comments: {item['comments']}")
                # print(f"Resolution Notes: {item['close_notes']}")
                # print(f"Resolved By: {item['resolved_by']}")
                # Add the relevant info to the list
                #relevantinfo.append(item['sys_id'])
                relevantinfo.append(item['description'])
                relevantinfo.append(item['work_notes'])
                relevantinfo.append(item['comments'])
                relevantinfo.append(item['close_notes'])
                relevantinfo.append(item['resolved_by'])
                
        else:
            print("No results found")
            # Add the relevant info to the list as empty
            #relevantinfo.append("There are no current recommendations for this incident as there are no similar incidents in the database.")
            return []
    return relevantinfo


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
