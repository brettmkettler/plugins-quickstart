# apiUrl: https://rydersystemsdev.service-now.com
# username: AppDynamicAlert
# password: appdynamics01
# incidentNumber:  INC1280089

import os
from flask import Flask, Response, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
import yaml
import json
import openai

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
            work_notes = []
            comments = []
            for entry in incident.get("work_notes", []):
                work_notes.append(entry.get("value"))
            for entry in incident.get("comments", []):
                comments.append(entry.get("value"))

            # Add work notes and comments to incident information
            incident["work_notes"] = work_notes
            incident["comments"] = comments
            
            incident_prompt = "Given the incident description, please provide a recommended solution to the following: " + "\n" + "Incident Description: " + incident.get("description", "") + "\n" + "Work Notes: " + str(work_notes) + "\n" + "Comments: " + str(comments) + "\n" + "Recommendation:"
         
            # Generate recommendation using OpenAI
            response = openai.Completion.create(
                engine="text-davinci-003",
                prompt=incident_prompt,
                max_tokens=500,
                n=1,
                stop=None,
                temperature=0.4
            )

            recommendation = response

            # Add recommendation to incident information
            incident["INCIDENT RECOMMENDATIONS: "] = recommendation

            return incident
        else:
            raise Exception("Incident not found or API response empty")
    else:
        raise Exception(f"Error: {response.status_code}, {response.text}")


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



####

    
#########################################################
@app.get("/logo.png")
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
