import requests
import json
import spacy
import openai
import os
from sentence_transformers import SentenceTransformer, util


openai.api_key = "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"

# ServiceNow API credentials
instance = "rydersystemsdev"
username = "AppDynamicAlert"
password = "appdynamics01"

# Search query parameters
table = "incident"  # The table to search in, e.g., "incident", "problem", "change_request"


############################


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
    if response.status_code == 200:
        result = response.json().get('result')
        if result:
            cmdb_item = result[0].get('cmdb_ci')
            print(f'CMDB item identifier: {cmdb_item}')
            return cmdb_item
        else:
            print('No incident found with the given number.')
            return None
    else:
        print('Error occurred while fetching incident details:', response.text)
        return None
    

### GO back and check this function
def fetch_related_incidents(cmdb_item_identifier):
    username = "AppDynamicAlert"
    password = "appdynamics01"
    api_url = 'https://rydersystemsdev.service-now.com/api/now/table/incident'
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }
    params = {
        'sysparm_query': f'cmdb_ci={cmdb_item_identifier}^stateIN6,7',  # Only retrieve incidents with state 6 (Resolved) or 7 (Closed)
        'sysparm_limit': 25,  # Adjust the limit based on your requirements
        'sysparm_sort': 'sys_updated_on:desc'  # Sort incidents by the latest updated date in descending order
    }
    response = requests.get(api_url, headers=headers, auth=(username, password), params=params)
    if response.status_code == 200:
        print(response.json().get('result'))
        return response.json().get('result')
    else:
        print('Error occurred while fetching related incidents:', response.text)
        return None

# GET SIMILAR INCIDENTS
def analyze_incidents(incidents):
    model = SentenceTransformer('bert-base-nli-mean-tokens')  # Load the Sentence Transformers model
    
    common_issues = []
    similarity_threshold = 0.8  # Adjust the threshold based on your requirements

    for incident in incidents:
        incident_description = incident.get('short_description', '')
        incident_number = incident.get('number', '')
        incident_desc = incident.get('description', '')
        incident_closenotes = incident.get('close_notes', '')

        
        # Embed the incident description into a fixed-dimensional vector
        incident_embedding = model.encode([incident_description], convert_to_tensor=True)

        # Compare the current incident with previously analyzed incidents
        for issue in common_issues:
            issue_embedding = model.encode([issue], convert_to_tensor=True)
            similarity_score = util.pytorch_cos_sim(incident_embedding, issue_embedding)
            if similarity_score.item() > similarity_threshold:
                # If similarity score is above the threshold, consider them similar issues
                print(f"Similar issue found between current incident and previous issue: {issue}")
                print(f"Incident number: {incident_number}")
                print(f"Resolution for previous issue: {incident_closenotes}")
    
        
                

        # Add the current incident's description to the list of common issues
        common_issues.append(incident_closenotes)
        
    return common_issues
        

   
######################################################################################################        

def get_incident_info(service_now_uri, username, password, incident_number, common_issues):
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
            
            # recommendations = search_service_now(service_now_uri, username, password, description)


            incident_prompt = (
                "Given the incident description, work notes, comments, and relevant incident details, please provide a very detailed recommended solution and person of contact or assignment group that has resolved incident in past: "
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
                + str(common_issues)
                + "\n"
                + "\nRecommendation:"
            )

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
            
            print("Incident Recommendations: " + recommendation)

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
                #print(f"Work Notes: {item['work_notes']}")
                print(f"Comments: {item['comments']}")
                print(f"Resolution Notes: {item['close_notes']}")
                # print(f"Resolved By: {item['resolved_by']}")
                # Add the relevant info to the list
                #relevantinfo.append(item['sys_id'])
                
                relevantinfo.append(item['description'])
                #relevantinfo.append(item['resolution_notes'])
                relevantinfo.append(item['work_notes'])
                relevantinfo.append(item['comments'])
                relevantinfo.append(item['close_notes'])
                relevantinfo.append(item['resolved_by'])
                relevantinfo.append(item['assigned_to'])
                
        else:
            print("No results found")
            # Add the relevant info to the list as empty
            #relevantinfo.append("There are no current recommendations for this incident as there are no similar incidents in the database.")
            return []
    print(relevantinfo)
    return relevantinfo


def get_incident_comments(incident_number):
    
    print(f"Retrieving comments for incident {incident_number}...")
    
    username = "AppDynamicAlert"
    password = "appdynamics01"
    
    # Set up authentication and headers
    auth = (username, password)
    headers = {'Accept': 'application/json'}

    # Get the sys_id for the incident
    sys_id = get_incident_sys_id(service_now_uri, username, password, incident_number)

    # Construct the API request URL
    url = f'https://rydersystemsdev.service-now.com/api/now/table/incident/{sys_id}?sysparm_fields=comments'

    # Send the API request
    response = requests.get(url, auth=auth, headers=headers)

    # Check the response status code
    if response.status_code == 200:
        # Parse the response JSON and extract the comments
        comments = response.json().get('result', [])
        return comments
    else:
        print(f"Failed to retrieve comments for incident {incident_number}. Status code: {response.status_code}")
        return []
    

####################


service_now_uri = "https://rydersystemsdev.service-now.com"
username = "AppDynamicAlert"
password = "appdynamics01"
print("Welcome to the Incident Recommender!")
print("Please enter the incident number to get started.")

incident_number = input("Enter incident number: ")

# similar incidents
cmdb_item = get_cmdb_item_from_incident(incident_number)

incidents = fetch_related_incidents(cmdb_item)

#print("Incidents: " + str(incidents))

get_incident_comments(incident_number)

if incidents:
    common_issues = analyze_incidents(incidents)
    
    print("Common Issues Resolution notes: " + str(common_issues))
    
    incident_info = get_incident_info(service_now_uri, username, password, incident_number, common_issues)

# common_issues


