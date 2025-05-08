
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from requests_oauthlib import OAuth2Session
from db import save_token, get_token
import dbm


CLIENT_ID = "1210140774181039"  # Replace with your Asana App Client ID
CLIENT_SECRET = "913f6e9099ff0462b6a3903494261999" 
REDIRECT_URI = "http://localhost:8080/asana/callback"

AUTHORIZATION_BASE_URL = "https://app.asana.com/-/oauth_authorize"
TOKEN_URL = "https://app.asana.com/-/oauth_token"

router = APIRouter()

@router.get("/login")
async def login(uuid: str):
    asana = OAuth2Session(CLIENT_ID, redirect_uri=REDIRECT_URI)
    authorization_url, state = asana.authorization_url(AUTHORIZATION_BASE_URL)

    save_token(uuid, {"platform": "asana", "state": state})
    return RedirectResponse(url=authorization_url)


@router.get("/callback")
async def callback(request: Request):
    state = request.query_params.get("state")
    code = request.query_params.get("code")

    uuid = None
    for key in dbm.open("session_store.db").keys():
        data = get_token(key.decode())
        if data.get("state") == state:
            uuid = key.decode()
            break

    if not uuid:
        raise HTTPException(status_code=400, detail="Invalid or expired state")

    asana = OAuth2Session(CLIENT_ID, redirect_uri=REDIRECT_URI, state=state)
    token = asana.fetch_token(
        TOKEN_URL,
        client_secret=CLIENT_SECRET,
        code=code,
    )

    save_token(uuid, {"platform": "asana", "token": token})

    chat_url = f'http://localhost:8501/chat?platform=asana&uuid={uuid}'
    return RedirectResponse(url=chat_url)


@router.get("/get-data")
async def get_asana_data(uuid: str):
    data = get_token(uuid)
    if not data or data.get("platform") != "asana":
        raise HTTPException(status_code=400, detail="Invalid or missing Asana token")

    token = data.get("token")
    asana = OAuth2Session(CLIENT_ID, token=token)

    # Fetch user's workspaces (optional, may only have one)
    workspaces_resp = asana.get("https://app.asana.com/api/1.0/workspaces")
    if workspaces_resp.status_code != 200:
        raise HTTPException(status_code=500, detail="Failed to fetch Asana workspaces")
    workspaces = workspaces_resp.json().get("data", [])

    all_data = []

    # Fetch projects in each workspace
    for workspace in workspaces:
        workspace_id = workspace["gid"]
        projects_resp = asana.get(f"https://app.asana.com/api/1.0/projects?workspace={workspace_id}")
        if projects_resp.status_code != 200:
            continue
        projects = projects_resp.json().get("data", [])

        for project in projects:
            project_id = project["gid"]
            project_detail = {
                "project": project,
                "sections": [],
                "tasks": [],
            }

            # Get sections
            sections_resp = asana.get(f"https://app.asana.com/api/1.0/projects/{project_id}/sections")
            if sections_resp.status_code == 200:
                project_detail["sections"] = sections_resp.json().get("data", [])

            # Get tasks
            tasks_resp = asana.get(f"https://app.asana.com/api/1.0/projects/{project_id}/tasks")
            if tasks_resp.status_code == 200:
                tasks = tasks_resp.json().get("data", [])
                detailed_tasks = []
                for task in tasks:
                    task_id = task["gid"]
                    task_detail_resp = asana.get(f"https://app.asana.com/api/1.0/tasks/{task_id}")
                    if task_detail_resp.status_code == 200:
                        detailed_tasks.append(task_detail_resp.json().get("data"))
                project_detail["tasks"] = detailed_tasks

            all_data.append(project_detail)

    return {"asana_data": all_data}
