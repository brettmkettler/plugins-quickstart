import requests
import json
import spacy
import openai
import os

openai.api_key = "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"

# ServiceNow API credentials
instance = "rydersystemsdev"
username = "AppDynamicAlert"
password = "appdynamics01"

# Search query parameters
table = "incident"  # The table to search in, e.g., "incident", "problem", "change_request"


############################




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
            recommendations = search_service_now(service_now_uri, username, password, description)


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
                + str(recommendations)
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
                temperature=0.4
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


service_now_uri = "https://rydersystemsdev.service-now.com"
username = "AppDynamicAlert"
password = "appdynamics01"
print("Welcome to the Incident Recommender!")
print("Please enter the incident number to get started.")
incident_number = input("Enter incident number: ")

incident_info = get_incident_info(service_now_uri, username, password, incident_number)