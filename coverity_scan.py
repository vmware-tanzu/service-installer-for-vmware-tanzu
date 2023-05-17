import argparse
import sys

import requests

url_api = {
    "base_url": "https://coverity.eng.vmware.com",
    "api_view_content": "/api/v2/views/viewContents/",
}

headers = {
    "accept": "application/json",
    "Authorization": "Basic c3ZjLnNpdnQtc2VjLXNjYW46JW5QL1Mrbm1lNDhuVz1WOE4jMQ==",
}


def query_for_snapshot(project_ids):
    return {"projectId": project_ids}


def query_for_latest_view(project_ids):
    return {
        "projectId": project_ids,
        "rowCount": "100",
        "offset": "0",
        "sortKey": "displayImpact",
        "sortOrder": "desc",
        "locale": "en_us",
        "expression": "357826",
    }


def get_snapshot_details(views_id, projects_id):
    response = requests.get(
        url_api["base_url"] + url_api["api_view_content"] + views_id,
        headers=headers,
        params=query_for_latest_view(projects_id),
    )
    return response.json()


def get_high_impact_issue_sivt(view, project):
    response = get_snapshot_details(view, project)
    if not int(response.get("totalRows")) == 0:
        print(response.get("totalRows"))
        sys.exit(-1)
    else:
        print(response.get("totalRows"))
        return response.get("totalRows")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--view", type=str, required=True)
    parser.add_argument("--project", type=str, required=True)
    args, unknown = parser.parse_known_args()
    view_id = args.view
    project_id = args.project
    get_high_impact_issue_sivt(view_id, project_id)
