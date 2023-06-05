import os
from flask import Flask, Response, request, jsonify, send_from_directory
from flask_cors import CORS
from sentence_transformers import SentenceTransformer
import requests
import yaml
import json
import openai
import pinecone
import numpy as np

openai.api_key = "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"
pinecone.init(api_key="605e0e6f-413e-4dd5-a097-a43330ce543c", environment="us-west4-gcp-free")

index_name = "chat-app"

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

            # Initiate Sentence Transformer model vector 1536
            model = SentenceTransformer('all-MiniLM-L6-v2')

            def generate_vector_from_text(text):
                return model.encode([text])[0]

            # Generate a vector from the incident description
            vector = generate_vector_from_text(incident.get("description", ""))

            # Instantiate an instance of your Pinecone Index
            index_instance = pinecone.Index(index_name)

            # Fetch most similar items from Pinecone
            query_results = index_instance.query(queries=[vector.tolist()], top_k=5)

            # Here we are assuming the incident information is stored as documents in Pinecone,
            # and each document has a 'recommendation' field
            recommendations = []
            for result in query_results.results:
                for match in result.matches:
                    document_id = match.id
                    # Fetch the document from Pinecone
                    document = index_instance.fetch(ids=[document_id])

                    if document.items:
                        # Extract the recommendation
                        recommendation = document.items[0].data.get('recommendation')
                        recommendations.append(recommendation)
                        print("Document found:", document)
                    else:
                        print("Document not found:", document)

            # Convert ndarray to list for JSON serialization
            recommendations = [np.array(rec).tolist() for rec in recommendations]

            # Add the recommendations to the incident information
            incident["Pinecone Recommendations: "] = recommendations

            incident_prompt = (
                "Given the incident description and relevant documents, please provide a recommended solution to the following: "
                + "\n"
                + "Incident Description: "
                + incident.get("description", "")
                + "\n"
                + "Work Notes: "
                + str(work_notes)
                + "\n"
                + "Comments: "
                + str(comments)
                + "\n"
                + "Relevant Documents: "
                + str(recommendations)
                + "\nRecommendation:"
            )

            # Generate recommendation using OpenAI
            response = openai.Completion.create(
                engine="text-davinci-003",
                prompt=incident_prompt,
                max_tokens=500,
                n=1,
                stop=None,
                temperature=0.4
            )
            recommendation = response.choices[0].text.strip()

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

