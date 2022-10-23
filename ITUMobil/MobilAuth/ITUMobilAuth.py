import getpass
import requests
import os
import base64

from ..configuration import (
    ITU_MOBIL_API_BASE_URL,
    ITU_MOBIL_SECURITY_ID,
    ITU_MOBIL_DEVICE_NAME,
    ITU_MOBIL_DEVICE_MODEL,
    ITU_MOBIL_OS_TYPE,
    ITU_MOBIL_LOCALE,
)


class ITUMobilAuthHandler:
    def __init__(self, username="", password=""):
        self.username = username
        self.password = password
        self.b64username = None
        self.b64password = None

    def login_to_itu_mobil(self):
        if not self.username:
            self.username = input("Username: ")
        if not self.password:
            self.password = getpass.getpass("Password: ")
        self.b64username = base64.b64encode(self.username.encode("utf-8"))
        self.b64password = base64.b64encode(self.password.encode("utf-8"))

        params = {
            "method": "LoginSessionEncoded",
            "UserName": self.b64username,
            "Password": self.b64password,
            "SecurityId": ITU_MOBIL_SECURITY_ID,
            "DeviceName": ITU_MOBIL_DEVICE_NAME,
            "DeviceModel": ITU_MOBIL_DEVICE_MODEL,
            "OSType": ITU_MOBIL_OS_TYPE,
            "Locale": ITU_MOBIL_LOCALE,
        }
        response = requests.get(ITU_MOBIL_API_BASE_URL, params=params)
        response = response.json()
        if response["StatusCode"] != 0:
            print("Login failed.")
            print("Error: " + response["ResultMessage"])
        else:
            if response["Session"]["IsAuthenticated"]:
                print("Login successful.")
                print("Username: " + response["Session"]["UserName"])
                print("Mail: " + response["Session"]["ITUMail"])
                print("Session Expiration: " + response["Session"]["ValidUntil"])
                os.environ["ITU_MOBIL_TOKEN"] = response["Session"]["Token"]
        return response

    def logout_from_itu_mobil(self):
        params = {
            "method": "LogoutSession",
            "Token": os.environ.get("ITU_MOBIL_TOKEN"),
            "SecurityId": ITU_MOBIL_SECURITY_ID,
        }
        response = requests.get(ITU_MOBIL_API_BASE_URL, params=params)
        response = response.json()
        if response["StatusCode"] == 0:
            print("Logged out from ITU Mobil successfully.")
            os.environ["ITU_MOBIL_TOKEN"] = ""
        else:
            print("Logout failed.")
            print("Error: " + response["ResultMessage"])
        return response
