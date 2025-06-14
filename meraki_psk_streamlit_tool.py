PK     
�Z͹\�a  a     meraki_psk_streamlit_tool.pyimport streamlit as st
import pandas as pd
import requests

st.set_page_config(page_title="Meraki WPN PSK Provisioning Tool", layout="centered")
st.title("🔐 Meraki WPN PSK Provisioning Tool")

api_key = st.text_input("Enter your Meraki API Key", type="password")

if api_key:
    headers = {
        "X-Cisco-Meraki-API-Key": api_key,
        "Accept": "application/json"
    }
    try:
        orgs = requests.get("https://api.meraki.com/api/v1/organizations", headers=headers).json()
        org_options = {org["name"]: org["id"] for org in orgs}
        org_name = st.selectbox("Select Organization", list(org_options.keys()))
        org_id = org_options[org_name]

        networks = requests.get(f"https://api.meraki.com/api/v1/organizations/{org_id}/networks", headers=headers).json()
        net_options = {net["name"]: net["id"] for net in networks}
        net_name = st.selectbox("Select Network", list(net_options.keys()))
        network_id = net_options[net_name]

        prefix = st.text_input("Prefix before APT number (e.g., 'CC')", value="APT")
        method = st.radio("Choose input method", ["Manual Entry", "CSV Upload"])

        units = []
        if method == "Manual Entry":
            units_input = st.text_area("Enter unit numbers (one per line)")
            if units_input:
                units = [line.strip() for line in units_input.splitlines() if line.strip()]
        else:
            csv_file = st.file_uploader("Upload CSV file", type="csv")
            if csv_file:
                df = pd.read_csv(csv_file)
                units = df.iloc[:, 0].dropna().astype(str).tolist()

        if units:
            if st.button("Generate and Upload PSKs"):
                results = []
                for unit in units:
                    psk_name = f"{prefix} APT-{unit}"
                    password = f"{prefix}{unit}!"
                    payload = {
                        "name": psk_name,
                        "passphrase": password,
                        "ssidNumber": 8,
                        "groupPolicyId": "Resident_150Mbps"
                    }
                    url = f"https://api.meraki.com/api/v1/networks/{network_id}/wireless/ssids/8/wpn/personal/psks"
                    response = requests.post(url, headers=headers, json=payload)
                    status = "✅ Success" if response.status_code == 201 else f"❌ Failed: {response.text}"
                    results.append({"Unit": unit, "SSID": psk_name, "Password": password, "Status": status})

                results_df = pd.DataFrame(results)
                st.success("Provisioning complete!")
                st.dataframe(results_df)

                csv = results_df.to_csv(index=False).encode("utf-8")
                st.download_button("Download Result CSV", data=csv, file_name="psk_results.csv", mime="text/csv")
    except Exception as e:
        st.error(f"Error: {e}")
PK     
�Z͹\�a  a             ��    meraki_psk_streamlit_tool.pyPK      J   �    