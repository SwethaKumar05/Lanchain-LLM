
from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
from db import save_token, get_token
import requests, dbm

CLIENT_ID = "6H0BEBMCU404BO9FP92C3E59CA7ZOI0A"  # Replace with your ClickUp client ID
CLIENT_SECRET = "DXAA159BLNLOYF6UY19I1Z1JI7I0CBUNIZ0AJR13PBLM5AQ02VZIKXO7VH3CMQQS"  # Replace with your ClickUp client secret
REDIRECT_URI = "http://localhost:8080/clickup/callback"

AUTHORIZE_URL = "https://app.clickup.com/api"
TOKEN_URL = "https://api.clickup.com/api/v2/oauth/token"

router = APIRouter()

@router.get("/login")
async def login(uuid: str):
    save_token(uuid, {"platform": "clickup"})
    url = f"{AUTHORIZE_URL}?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}"
    return RedirectResponse(url=url)

@router.get("/callback")
async def callback(code: str):
    uuid = None
    for key in dbm.open("session_store.db").keys():
        data = get_token(key.decode())
        if data.get("platform") == "clickup" and "access_token" not in data:
            uuid = key.decode()
            break

    if not uuid:
        raise HTTPException(status_code=400, detail="Session expired")

    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "redirect_uri": REDIRECT_URI,
    }
    resp = requests.post(TOKEN_URL, data=data)
    if resp.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to get ClickUp access token")
    access_token = resp.json().get("access_token")

    save_token(uuid, {"platform": "clickup", "access_token": access_token})

    chat_url = f'http://localhost:8501/chat?platform=clickup&uuid={uuid}'
    return RedirectResponse(url=chat_url)
@router.get("/get-data")
async def get_full_clickup_data(uuid: str):
    token_data = get_token(uuid)
    if not token_data or token_data.get("platform") != "clickup":
        raise HTTPException(status_code=401, detail="No ClickUp token found")

    headers = {
        "Authorization": token_data["access_token"],
        "Content-Type": "application/json"
    }

    # 1. Get Teams
    teams_resp = requests.get("https://api.clickup.com/api/v2/team", headers=headers)
    if teams_resp.status_code != 200:
        raise HTTPException(status_code=500, detail="Failed to fetch teams")
    teams = teams_resp.json().get("teams", [])

    full_data = []

    for team in teams:
        team_id = team["id"]
        team_data = {"team_id": team_id, "spaces": []}

        # 2. Get Spaces
        spaces_resp = requests.get(f"https://api.clickup.com/api/v2/team/{team_id}/space", headers=headers)
        if spaces_resp.status_code != 200:
            continue
        spaces = spaces_resp.json().get("spaces", [])

        for space in spaces:
            space_id = space["id"]
            space_data = {"space_id": space_id, "name": space["name"], "folders": [], "lists": []}

            # 3. Get Folders
            folders_resp = requests.get(f"https://api.clickup.com/api/v2/space/{space_id}/folder", headers=headers)
            folders = folders_resp.json().get("folders", []) if folders_resp.status_code == 200 else []

            for folder in folders:
                folder_id = folder["id"]
                folder_data = {"folder_id": folder_id, "name": folder["name"], "lists": []}

                # 4. Get Lists in Folder
                lists_resp = requests.get(f"https://api.clickup.com/api/v2/folder/{folder_id}/list", headers=headers)
                lists = lists_resp.json().get("lists", []) if lists_resp.status_code == 200 else []

                for lst in lists:
                    list_id = lst["id"]
                    list_data = {"list_id": list_id, "name": lst["name"], "tasks": []}

                    # 5. Get Tasks in List
                    tasks_resp = requests.get(f"https://api.clickup.com/api/v2/list/{list_id}/task", headers=headers)
                    tasks = tasks_resp.json().get("tasks", []) if tasks_resp.status_code == 200 else []
                    list_data["tasks"] = tasks

                    folder_data["lists"].append(list_data)

                space_data["folders"].append(folder_data)

            # 6. Get Folderless Lists
            fl_lists_resp = requests.get(f"https://api.clickup.com/api/v2/space/{space_id}/list", headers=headers)
            fl_lists = fl_lists_resp.json().get("lists", []) if fl_lists_resp.status_code == 200 else []

            for lst in fl_lists:
                list_id = lst["id"]
                list_data = {"list_id": list_id, "name": lst["name"], "tasks": []}
                tasks_resp = requests.get(f"https://api.clickup.com/api/v2/list/{list_id}/task", headers=headers)
                list_data["tasks"] = tasks_resp.json().get("tasks", []) if tasks_resp.status_code == 200 else []
                space_data["lists"].append(list_data)

            team_data["spaces"].append(space_data)

        full_data.append(team_data)

    return {"clickup_data": full_data}