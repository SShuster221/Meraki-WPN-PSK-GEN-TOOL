
import streamlit as st
import requests
import pandas as pd
import io

st.set_page_config(page_title="Meraki WPN PSK Provisioning Tool", layout="centered")

st.title("🔐 Meraki WPN PSK Provisioning Tool")

# Step 1: Meraki API Key input
api_key = st.text_input("Enter your Meraki API Key", type="password")
headers = {
    "X-Cisco-Meraki-API-Key": api_key,
    "Content-Type": "application/json",
    "Accept": "application/json"
}

# Step 2: Get Org and Network
org_id = None
net_id = None

if api_key:
    org_response = requests.get("https://api.meraki.com/api/v1/organizations", headers=headers)
    if org_response.status_code == 200:
        orgs = org_response.json()
        org_options = {org['name']: org['id'] for org in orgs}
        selected_org = st.selectbox("Select Organization", list(org_options.keys()))
        org_id = org_options[selected_org]

        if org_id:
            net_response = requests.get(f"https://api.meraki.com/api/v1/organizations/{org_id}/networks", headers=headers)
            if net_response.status_code == 200:
                networks = net_response.json()
                net_options = {net['name']: net['id'] for net in networks}
                selected_net = st.selectbox("Select Network", list(net_options.keys()))
                net_id = net_options[selected_net]

# Step 3: Prefix input
prefix = st.text_input("Prefix before APT number (e.g., 'CC')", max_chars=10)

# Step 4: Choose input method
input_method = st.radio("Choose input method", ("Manual Entry", "CSV Upload"))

unit_numbers = []
if input_method == "Manual Entry":
    manual_units = st.text_area("Enter unit numbers (one per line)")
    if manual_units:
        unit_numbers = manual_units.strip().split("\n")
else:
    uploaded_file = st.file_uploader("Upload CSV", type=["csv"])
    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        if 'unit' in df.columns:
            unit_numbers = df['unit'].astype(str).tolist()
        else:
            st.error("CSV must contain a column labeled 'unit'.")

# Step 5: Generate and upload PSKs
results = []
if st.button("Generate and Upload PSKs") and api_key and org_id and net_id and unit_numbers:
    ssid_name = "Resident-WiFi"
    group_policy = "Resident_150Mbps"

    ssids = requests.get(f"https://api.meraki.com/api/v1/networks/{net_id}/wireless/ssids", headers=headers)
    if ssids.status_code == 200:
        ssids_json = ssids.json()
        ssid_number = None
        for ssid in ssids_json:
            if ssid.get("name") == ssid_name:
                ssid_number = ssid["number"]
                break

        if ssid_number is not None:
            for unit in unit_numbers:
                name = f"{prefix} APT-{unit}"
                password = f"{prefix}{unit}!"  # Example password rule
                payload = {
                    "name": name,
                    "passphrase": password,
                    "groupPolicyId": group_policy
                }
                url = f"https://api.meraki.com/api/v1/networks/{net_id}/wireless/ssids/{ssid_number}/identityPsks"
                res = requests.post(url, headers=headers, json=payload)

                if res.status_code == 201:
                    results.append({"Unit": unit, "Name": name, "PSK": password, "Status": "✅ Success"})
                else:
                    results.append({"Unit": unit, "Name": name, "PSK": password, "Status": f"❌ Failed: {res.text}"})
        else:
            st.error(f"SSID '{ssid_name}' not found in network.")
    else:
        st.error("Failed to retrieve SSID list.")

# Step 6: Output table and download
if results:
    df_out = pd.DataFrame(results)
    st.dataframe(df_out)
    csv = df_out.to_csv(index=False).encode('utf-8')
    st.download_button("Download Result CSV", data=csv, file_name="meraki_psk_results.csv", mime="text/csv")
