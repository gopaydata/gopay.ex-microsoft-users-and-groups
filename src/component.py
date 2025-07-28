import requests
import csv
import os
from keboola.component.base import ComponentBase


class Component(ComponentBase):

    def __init__(self):
        super().__init__()

    def get_access_token(self, config):
        url = f"https://login.microsoftonline.com/{config['tenant_id']}/oauth2/v2.0/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "client_id": config["client_id"],
            "scope": "https://graph.microsoft.com/.default",
            "client_secret": config["client_secret"],
            "grant_type": "client_credentials"
        }
        response = requests.post(url, headers=headers, data=data)
        response.raise_for_status()
        return response.json()["access_token"]

    def get_all_users(self, access_token):
        users = []
        url = "https://graph.microsoft.com/v1.0/users"
        headers = {"Authorization": f"Bearer {access_token}"}
        while url:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            users.extend(data.get("value", []))
            url = data.get("@odata.nextLink")
        return users

    def get_user_licenses(self, access_token, user_id):
        url = f"https://graph.microsoft.com/v1.0/users/{user_id}/licenseDetails"
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json().get("value", [])

    def get_user_groups(self, access_token, user_id):
        url = f"https://graph.microsoft.com/v1.0/users/{user_id}/memberOf"
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json().get("value", [])

    def run(self):
        config = {
            "tenant_id": self.configuration.parameters["tenant_id"],
            "client_id": self.configuration.parameters["client_id"],
            "client_secret": self.configuration.parameters["client_secret"]
        }

        token = self.get_access_token(config)
        users = self.get_all_users(token)

        print(f"🔍 Načteno {len(users)} uživatelů.")

        output_rows = []
        for user in users:
            user_id = user.get("id")
            display_name = user.get("displayName")
            upn = user.get("userPrincipalName")
            account_enabled = user.get("accountEnabled")

            licenses = self.get_user_licenses(token, user_id)
            groups = self.get_user_groups(token, user_id)

            license_names = ", ".join([lic.get("skuPartNumber", "") for lic in licenses])
            group_names = ", ".join([g.get("displayName", "") for g in groups])

            output_rows.append({
                "Display Name": display_name,
                "User Principal Name": upn,
                "ID": user_id,
                "Account Enabled": account_enabled,
                "Licenses": license_names,
                "Groups": group_names
            })

        output_path = "/data/out/tables/users_summary.csv"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, mode="w", newline="", encoding="utf-8") as f:
            fieldnames = [
                "Display Name",
                "User Principal Name",
                "ID",
                "Account Enabled",
                "Licenses",
                "Groups"
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(output_rows)

        print(f"✅ Data byla uložena do {output_path}")


if __name__ == "__main__":
    component = Component()
    component.run()
    