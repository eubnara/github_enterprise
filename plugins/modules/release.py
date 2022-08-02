#!/usr/bin/python

# Copyright: (c) 2022, Yubi Lee <eubnara@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
from ansible.module_utils.basic import AnsibleModule

__metaclass__ = type
import os
import requests


DOCUMENTATION = r"""
---
module: release

short_description: This is a module to download assets from repository in github enterprise environment.

version_added: "1.0.0"

description: "This is a module to download assets from repository in github enterprise environment.
It allows you to choose latest release or release by tag and specify asset names to download."

options:
    url:
        description: url to github enterprise server
        required: true
        type: str
    owner:
        description: owner in github repository path
        required: true
        type: str
    repo:
        description: repo in github repository path
        required: true
        type: str
    token:
        description: github access token
        required: true
        type: str
    tag:
        description: release tag
        required: false
        type: str
    output_path:
        description: path to locate downloaded assets
        required: false
        type: str
    asset_names:
        description: asset names to download
        required: false
        type: str

author:
    - Yubi Lee (@eubnara)
"""

EXAMPLES = r"""
- name: Download all assets in latest release
  eubnara.github_enterprise.release:
    url: https://github.example.com
    owner: eub
    repo: something-magnificent
    token: token-hard-to-guess

- name: Specify output path
  eubnara.github_enterprise.release:
    url: https://github.example.com
    owner: eub
    repo: something-magnificent
    token: token-hard-to-guess
    output_path: output

- name: Specify asset names you want to get
  eubnara.github_enterprise.release:
    url: https://github.example.com
    owner: eub
    repo: something-magnificent
    token: token-hard-to-guess
    asset_names:
      - this-is-the-only-asset-to-download.tar.gz
      - second-one.zip
"""


def run_module():

    module_args = dict(
        url=dict(type="str", required=True),
        owner=dict(type="str", required=True),
        repo=dict(type="str", required=True),
        token=dict(type="str", required=True),
        tag=dict(type="str", required=False),
        output_path=dict(type="str", required=False),
        asset_names=dict(type="list", required=False),
    )

    result = dict(changed=False, msg="")

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    if module.check_mode:
        module.exit_json(**result)

    owner = module.params["owner"]
    repo = module.params["repo"]
    token = module.params["token"]
    tag = module.params["tag"]
    output_path = module.params["output_path"]
    asset_names = module.params["asset_names"]

    # get release
    github_endpoint_url = f"{module.params['url']}/api/v3/repos/{owner}/{repo}"
    url = (
        f"{github_endpoint_url}/releases/latest"
        if tag is None
        else f"{github_endpoint_url}/releases/tags/{tag}"
    )
    try:
        r = requests.get(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"token {token}",
            },
        )
    except requests.exceptions.ConnectionError:
        result["msg"] = f"Failed to connect {url}"
        module.fail_json(**result)
    if r.status_code == 401:
        result["msg"] = "401 Unauthorized"
        module.fail_json(**result)
    elif r.status_code == 404:
        result["msg"] = "404 Not Found"
        module.fail_json(**result)

    # get assets
    json_data = r.json()
    assets = json_data["assets"]
    assets_to_download = {}
    for asset in assets:
        name = asset["name"]
        if asset_names is not None and name not in asset_names:
            continue
        assets_to_download.update({asset["id"]: name})

    if len(assets_to_download) == 0:
        result["msg"] = "There is no asset to download"
        module.fail_json(**result)

    for asset_id, asset_name in assets_to_download.items():
        url = f"{github_endpoint_url}/releases/assets/{asset_id}"
        r = requests.get(
            url,
            headers={
                "Accept": "application/octet-stream",
                "Authorization": f"token {token}",
            },
            stream=True,
        )
        if r.status_code != 200:
            result["msg"] = f"Failed to download {asset_name}"
            module.fail_json(**result)
        parent_dir = os.getcwd() if output_path is None else output_path
        with open(os.path.join(parent_dir, asset_name), "wb") as f:
            for chunk in r:
                f.write(chunk)

    result["msg"] = f"Completed to download assets on {parent_dir}"
    module.exit_json(**result)


def main():
    run_module()


if __name__ == "__main__":
    main()
