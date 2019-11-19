from flask import Flask, session, redirect, url_for, escape, request, render_template, jsonify
import json,os,time
import random,string
from flask_socketio import SocketIO
from linkedin_api.linkedin import Linkedin
from flask_cors import CORS

app = Flask(__name__)

socketio = SocketIO(app)


# @app.route("/login", methods = ['GET', 'POST'])
# def login():
#     with open("config.json","r") as out_file:
#         config = json.loads(out_file.read())
#     if request.method == 'POST':
#         name = request.form['id']
#         password = request.form['password']
#         for user in config['users']:
#             if user["id"]==name and user["password"]==password:
#                 print(f"user {name} logged in successfully")
#                 app.secret_key = ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(75))
#                 return {"message":"success", "key":app.secret_key}
#             return {"message":"invalid username or password"}


# def authorized(auth):
#     if auth == app.secret_key and not auth==None:
#         return True
#     else:
#         return {"message": "ERROR: Unauthorized"}

# Sending Message To Linked In connections

def send_message(data, api):
    # auth = authorized(data["key"])
    linkedin_ids = data.get("linkedInIDs")
    msg = data['message']
    if not linkedin_ids:
        print("Getting basic profile info....")
        urn_id = api.get_profile()
        urn_id = urn_id['entityUrn'].split(":")[-1]
        # connections = api.get_profile_connections(urn_id)
        all_connections=[]
        print("Getting profile connections...")

        while True:
            connections = api.exclusive_get_request('https://www.linkedin.com/voyager/api/search/blended?count=49&filters=List(network-%3EF,resultType-%3EPEOPLE)&origin=MEMBER_PROFILE_CANNED_SEARCH&q=all&queryContext=List(spellCorrectionEnabled-%3Etrue)&start='+str(len(all_connections)))
            data = json.loads(connections)
            total_results =data.get("metadata")
            print(f"Total profile connections is {total_results.get('totalResultCount')}")
            numVisibleResults = total_results.get("numVisibleResults")
            if numVisibleResults==0:
                break
            for dt in data.get('elements',[]):
                con = dt.get('elements',[])
                if con:
                    for x in con:
                        all_connections.append({"urn_id":x.get("targetUrn").split(":")[-1],"public_id":x.get("publicIdentifier")})
                    print(f"connections grew to {len(all_connections)}")

        print("Total connections found is ",len(all_connections))
        import pdb; pdb.set_trace()
        for index, x in enumerate(all_connections):
            print("Sending Msg to: ",x['public_id'])
            urn_id = x['urn_id']
            res = api.send_message(recipients=[urn_id], message_body=msg)
            if res==False:
                print("Msg sent to: ",x['public_id'])
            yield {"sent":index+1,"total":len(all_connections)}

    if linkedin_ids:
        all_people = linkedin_ids
        for index, x in enumerate(all_people):
            print("Sending Msg to: ",x)
            try:
                urn_id = api.get_profile(x)
                urn_id = urn_id['entityUrn'].split(":")[-1]
                res = api.send_message(recipients=[urn_id], message_body=msg)
                if res==False:
                    print("Msg sent to: ",x)
                    yield {"sent":index+1,"total":len(all_people)}
            except Exception:
                pass
  

@app.route("/")
def index():
    return render_template('index.html')
    
# @socketio.on('key')
# def key():
#     socketio.emit('key',{"key":app.secret_key})



@socketio.on('send_message')
def api(message):
    data = json.loads(message)
    print(data)
    api=''
    lnk_id = data['username']
    lnk_pass = data['password']
    try:
        print("logging in api")
        api = Linkedin(lnk_id, lnk_pass)
        print("loggein in successfully")
    except Exception:
        print("Invalid linkedin_id or password")
        socketio.emit('update', {"error":"Invalid Linkedin Id or Password"})

    if api:
        for x in send_message(data, api):
            socketio.emit('update', x)


if __name__ =="__main__":
    socketio.run(app, host="localhost" , port=5000, debug=True)
