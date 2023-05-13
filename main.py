# <add key="apiUrl" value="https://rydersystemsdev.service-now.com/api/now/table/incident" />
# <add key="username" value="AppDynamicAlert" />
# <add key="password" value="appdynamics01" />

import os
from flask import Flask, request, jsonify, send_from_directory
import requests

app = Flask(__name__)

def get_incident_info(service_now_uri, username, password, incident_number):
    url = f"{service_now_uri}/api/now/table/incident"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    auth = (username, password)
    params = {
        "sysparm_query": f"number={incident_number}"
    }

    response = requests.get(url, headers=headers, auth=auth, params=params)

    if response.status_code == 200:
        result = response.json()
        incident = result["result"][0]  # Assuming only one incident is returned
        return incident
    else:
        raise Exception(f"Error: {response.status_code}, {response.text}")


@app.route('/get-incident', methods=['POST'])
def get_incident():
    data = request.get_json()
    service_now_uri = data.get('service_now_uri')
    username = data.get('username')
    password = data.get('password')
    incident_number = data.get('incident_number')

    try:
        incident_info = get_incident_info(service_now_uri, username, password, incident_number)
        return jsonify(incident_info)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

#########################################################

@app.get("/logo.png")
async def plugin_logo():
    filename = 'logo.png'
    return send_from_directory('.',
                               'logo.png',
                               mimetype='image/png')

@app.route('/.well-known/ai-plugin.json')
def serve_ai_plugin():
  return send_from_directory('.',
                             'ai-plugin.json',
                             mimetype='application/json')


@app.route('/.well-known/openapi.yaml')
def serve_openapi_yaml():
  return send_from_directory('.', 'openapi.yaml', mimetype='text/yaml')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5003)
