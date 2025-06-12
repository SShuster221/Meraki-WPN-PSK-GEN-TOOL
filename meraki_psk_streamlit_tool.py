
import streamlit as st
import pandas as pd
import requests
import random
import string

st.set_page_config(page_title="Meraki PSK Provisioning Tool", layout="centered")
st.title("🔐 Meraki PSK Provisioning Tool")

# Step 1: API Key
api_key = st.text_input("Enter your Meraki API Key", type="password")

# Helper functions
def get_organizations(api_key):
    url = "https://api.meraki.com/api/v1/organizations"
    headers = {"X-Cisco-Meraki-API-Key": api_key}
    r = requests.get(url, headers=headers)
    return r.json() if r.status_code == 200 else []

def get_networks(api_key, org_id):
    url = f"https://api.meraki.com/api/v1/organizations/{org_id}/networks"
    headers = {"X-Cisco-Meraki-API-Key": api_key}
    r = requests.get(url, headers=headers)
    return r.json() if r.status_code == 200 else []

def generate_password(length=12):
    charset = string.ascii_letters + string.digits + "!@#$"
    return ''.join(random.choices(charset, k=length))

def post_wpn(api_key, network_id, name, passphrase):
    url = f"https://api.meraki.com/api/v1/networks/{network_id}/wireless/ssids/8/wpn"
    headers = {
        "X-Cisco-Meraki-API-Key": api_key,
        "Content-Type": "application/json"
    }
    data = {
        "name": name,
        "passphrase": passphrase,
        "groupPolicyId": "Resident_150Mbps",
        "ssidNumber": 8
    }
    r = requests.post(url, headers=headers, json=data)
    return r.status_code, r.text

if api_key:
    orgs = get_organizations(api_key)
    org_map = {o['name']: o['id'] for o in orgs}
    org_choice = st.selectbox("Select Organization", list(org_map.keys()))
    org_id = org_map.get(org_choice)

    if org_id:
        networks = get_networks(api_key, org_id)
        net_map = {n['name']: n['id'] for n in networks}
        net_choice = st.selectbox("Select Network", list(net_map.keys()))
        net_id = net_map.get(net_choice)

        # Manual or CSV mode
        mode = st.radio("Choose Input Mode", ["Manual", "CSV Upload"])
        units = []

        if mode == "Manual":
            units_str = st.text_input("Enter unit numbers (comma-separated)", placeholder="101,102A,103")
            if units_str:
                units = [u.strip() for u in units_str.split(",")]
        else:
            uploaded_file = st.file_uploader("Upload CSV file with unit numbers", type=["csv"])
            if uploaded_file:
                df = pd.read_csv(uploaded_file)
                if "unit" in df.columns:
                    units = df["unit"].dropna().astype(str).tolist()
                else:
                    st.error("CSV must have a column labeled 'unit'")

        prefix = st.text_input("Prefix for PSK name (e.g. APT)", placeholder="APT")
        if st.button("Generate PSKs"):
            if not units:
                st.warning("Please enter or upload at least one unit.")
            else:
                results = []
                for unit in units:
                    psk_name = f"{prefix}-{unit}".upper()
                    passphrase = generate_password()
                    code, resp = post_wpn(api_key, net_id, psk_name, passphrase)
                    results.append({"Unit": unit, "PSK Name": psk_name, "Password": passphrase, "Status": code})
                st.success("PSKs generated.")
                df_results = pd.DataFrame(results)
                st.dataframe(df_results)
                csv = df_results.to_csv(index=False).encode("utf-8")
                st.download_button("Download Results CSV", csv, "generated_psks.csv", "text/csv")
