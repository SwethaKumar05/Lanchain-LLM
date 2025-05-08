

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from db import save_token, get_token
import requests, urllib.parse, dbm

CLIENT_ID = "70931aae5de1d9fe06fb693f39ef7b72"
CLIENT_SECRET = "bfa5bd3e6605febc47bff5e79d5c0e21"
REDIRECT_URI = "http://localhost:8080/linear/callback"

AUTHORIZE_URL = "https://linear.app/oauth/authorize"
TOKEN_URL = "https://api.linear.app/oauth/token"
API_URL = "https://api.linear.app/graphql"

router = APIRouter()

@router.get("/login")
async def login(uuid: str):
    state = uuid  # use UUID as state
    save_token(uuid, {"platform": "linear", "state": state})

    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": "read",
        "state": state,
    }
    url = f"{AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"
    return RedirectResponse(url=url)


@router.get("/callback")
async def callback(code: str, state: str):
    token_record = get_token(state)
    if not token_record or token_record.get("state") != state:
        raise HTTPException(status_code=400, detail="Invalid or expired state")

    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
        "code": code,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    token_resp = requests.post(TOKEN_URL, data=data, headers=headers)
    if token_resp.status_code != 200:
        raise HTTPException(status_code=500, detail="Failed to get access token from Linear")

    access_token = token_resp.json().get("access_token")
    save_token(state, {"platform": "linear", "access_token": access_token})

    chat_url = f'http://localhost:8501/chat?platform=linear&uuid={state}'
    return RedirectResponse(url=chat_url)


@router.get("/get-data")
async def get_full_linear_data(uuid: str):
    token_data = get_token(uuid)
    if not token_data or token_data.get("platform") != "linear":
        raise HTTPException(status_code=400, detail="Invalid Linear session")

    headers = {
        "Authorization": f"Bearer {token_data['access_token']}",
        "Content-Type": "application/json"
    }

    query = {
        "query": """
        query {
            viewer {
                id
                name
                email
            }
            teams {
                nodes {
                    id
                    name
                    key
                    issues(first: 10) {
                        nodes {
                            id
                            title
                            description
                            state {
                                id
                                name
                            }
                            assignee {
                                id
                                name
                                email
                            }
                            project {
                                id
                                name
                            }
                        }
                    }
                    projects {
                        nodes {
                            id
                            name
                            description
                        }
                    }
                }
            }
        }
        """
    }

    resp = requests.post(API_URL, json=query, headers=headers)
    if resp.status_code == 200:
        return resp.json()
    else:
        raise HTTPException(status_code=500, detail=f"Failed to fetch Linear data: {resp.text}")
