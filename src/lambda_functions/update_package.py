import json
import requests
import datetime
import random

def lambda_handler(event, context):

    date = datetime.datetime.utcnow().isoformat() # used https://stackoverflow.com/questions/2150739/iso-time-iso-8601-in-python for utc iso date
    log_id = date + '-' + str(int(random.random()*1000000))
    # https://cloud.google.com/storage/docs/uploading-objects#rest-upload-objects
    url = "https://storage.googleapis.com/upload/storage/v1/b/acme-register-logging/o?uploadType=media&name="+log_id
    # https://www.w3schools.com/python/ref_requests_post.asp
    requests.post(url, data=json.dumps(event), timeout=60)

    # return event["body"]
    data = json.loads(event["body"])

    package_name = data["metadata"]["Name"]
    package_version = data["metadata"]["Version"]
    package_id = data["metadata"]["ID"]
    
    package_content = data["data"].get("Content", "notFound")
    package_url = data["data"].get("URL", "notFound")
    package_jsprogram = data["data"].get("JSProgram", "notFound")
    
    # NOTE: I'm assuming that we don't rate the package on update because there is no error code for it
    
    # possibly check that the id passed in to the call and the one in the metadata is the same

    url = "https://firestore.googleapis.com/v1/projects/acme-register/databases/(default)/documents/packages/" + package_id
    document = requests.get(url, timeout=60).json()
    # print(document)
    
    if "error" in document or document["fields"]['Name']['stringValue'] != package_name or document["fields"]['Version']['stringValue'] != package_version:
        
        return {
            "statusCode": 404,
            "headers": {
                "Content-Type": "application/json",
                'Access-Control-Allow-Origin': '*',
            },
            "body": "Package does not exist."
        }
        
    # for reference
    # document = {
    #     "fields" : {
    #         "name" : {
    #             "stringValue" : package_name
    #         },
    #         "version" : {
    #             "stringValue" : package_version
    #         },
    #         "id" : {
    #             "stringValue" : package_id
    #         },
    #         "content" : {
    #             "stringValue" : package_content
    #         },
    #         "url" : {
    #             "stringValue" : package_url
    #         },
    #         "jsprogram" : {
    #             "stringValue" : package_jsprogram
    #         },
    #         "history" : {
    #             "arrayValue" : {
    #                 'values' : [
    #                     {
    #                         'mapValue': {
    #                             'fields': {
    #                                 'Action': {
    #                                     'stringValue': 'CREATE'
    #                                 }, 
    #                                 'User': {
    #                                     'mapValue': {
    #                                         'fields': {
    #                                             'name': {
    #                                                 'stringValue': 'UNIMPLEMENTED'
    #                                             }, 
    #                                             'isAdmin': {
    #                                                 'booleanValue': True
    #                                             }
    #                                         }
    #                                     }
    #                                 }, 
    #                                 'Date': {
    #                                     'stringValue': date
    #                                 }
    #                             }
    #                         }
    #                     }
    #                 ]
    #             }
    #         }
    #     }
    # } 

    # do we need to check that union type is maintained here?
    if package_url != 'notFound' and package_url != None: 
        document["fields"]['URL'] = {}
        document["fields"]['URL']['stringValue'] = package_url
    if package_jsprogram != 'notFound' and package_jsprogram != None: 
        document["fields"]['JSProgram'] = {}
        document["fields"]['JSProgram']['stringValue'] = package_jsprogram
    if package_content != 'notFound' and package_content != None: 
        # https://cloud.google.com/storage/docs/json_api/v1/objects/delete
        url = "https://storage.googleapis.com/storage/v1/b/acme-register-contents/o/"+package_id
        requests.delete(url, timeout=60)

        # https://cloud.google.com/storage/docs/uploading-objects#rest-upload-objects
        url = "https://storage.googleapis.com/upload/storage/v1/b/acme-register-contents/o?uploadType=media&name="+package_id
        # https://www.w3schools.com/python/ref_requests_post.asp
        requests.post(url, data=package_content, timeout=60)
    
    

    # used https://stackoverflow.com/questions/2150739/iso-time-iso-8601-in-python for utc iso date
    date = datetime.datetime.utcnow().isoformat()
    date = date[0:date.index('.')]+'Z'

    history_entry = {
        'mapValue': {
            'fields': {
                'Action': {
                    'stringValue': 'UPDATE'
                }, 
                'User': {
                    'mapValue': {
                        'fields': {
                            'name': {
                                'stringValue': 'UNIMPLEMENTED'
                            }, 
                            'isAdmin': {
                                'booleanValue': True
                            }
                        }
                    }
                }, 
                'Date': {
                    'stringValue': date
                }
            }
        }
    }

    document['fields']['History']['arrayValue']['values'].append(history_entry)

    document.pop('name') # NOT the name field; necessary to remove for posting

    url = "https://firestore.googleapis.com/v1/projects/acme-register/databases/(default)/documents/packages/" + package_id
    requests.delete(url, timeout=60).json() # unchecked
        
    url = "https://firestore.googleapis.com/v1/projects/acme-register/databases/(default)/documents/packages?documentId=" + package_id
    requests.post(url, json.dumps(document), timeout=60).json()
    
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            'Access-Control-Allow-Origin': '*',
        },
        "body": "Version is updated."
    }