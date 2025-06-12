import streamlit as st
import requests, csv, io
import random, string

# Helper functions
def random_psk():
    word = ''.join(random.choices(string.ascii_lowercase, k=5))
    # Make text easy: capitalize first and last
    return word.capitalize()

def fetch_orgs(api_key):
    r = requests.get("https://api.meraki.com/api/v1/organizations",
                     headers={"X-Cisco-Meraki-API-Key": api_key})
    return r.json()

def fetch_networks(api_key, org_id):
    r = requests.get(f"https://api.meraki.com/api/v1/organizations/{org_id}/networks",
                     headers={"X-Cisco-Meraki-API-Key": api_key})
    return r.json()

def fetch_group_policies(api_key, net_id):
    r = requests.get(f"https://api.meraki.com/api/v1/networks/{net_id}/groupPolicies",
                     headers={"X-Cisco-Meraki-API-Key": api_key})
    return r.json()

def fetch_ssids(api_key, net_id):
    r = requests.get(f"https://api.meraki.com/api/v1/networks/{net_id}/wireless/ssids",
                     headers={"X-Cisco-Meraki-API-Key": api_key})
    return r.json()

def create_psk(api_key, net_id, ssid_num, name, passphrase, groupPolicyId):
    r = requests.post(
        f"https://api.meraki.com/api/v1/networks/{net_id}/wireless/ssids/{ssid_num}/identityPsks",
        headers={"X-Cisco-Meraki-API-Key": api_key},
        json={"name": name, "passphrase": passphrase, "groupPolicyId": groupPolicyId}
    )
    return r.status_code, r.json()

# UI
st.title("Meraki WPN PSK Provisioning Tool")

api_key = st.text_input("Enter your Meraki API Key", type="password")
if not api_key:
    st.warning("API Key is required");
    st.stop()

# Load Orgs
orgs = fetch_orgs(api_key)
org_map = {o["name"]: o["id"] for o in orgs}
org_choice = st.selectbox("Select Organization", list(org_map.keys()))
org_id = org_map[org_choice]

nets = fetch_networks(api_key, org_id)
net_map = {n["name"]: n["id"] for n in nets}
net_choice = st.selectbox("Select Network", list(net_map.keys()))
net_id = net_map[net_choice]

# Get SSID # and Group Policy ID
ssids = fetch_ssids(api_key, net_id)
ssid_num = next((s["number"] for s in ssids if s["name"] == "Resident-WiFi"), None)
if ssid_num is None:
    st.error("Resident-WiFi SSID not found in selected network.")
    st.stop()

gps = fetch_group_policies(api_key, net_id)
match = [g for g in gps if g["name"] == "Resident_150Mbps"]
if not match:
    st.error("Group policy Resident_150Mbps not found.")
    st.stop()
gp_id = match[0]["groupPolicyId"]
st.success(f"Using Group Policy ID: {gp_id}")

# Prefix & Input Method
prefix = st.text_input("Prefix before APT number (before '- APT')", value="CC")
mode = st.radio("Choose input method", ("Manual", "Upload CSV (column 'room')"))

units = []
if mode == "Manual":
    text = st.text_area("Enter unit numbers (one per line)")
    units = [l.strip() for l in text.splitlines() if l.strip()]
else:
    f = st.file_uploader("Upload CSV", type="csv")
    if f:
        df = csv.DictReader(io.StringIO(f.getvalue().decode()))
        units = [r["room"].strip() for r in df if r.get("room")]

if not units:
    st.info("Enter or upload unit numbers to enable button")
else:
    if st.button("Generate and Upload PSKs"):
        out = []
        for unit in units:
            name = f"{prefix} - APT {unit}"
            psk = random_psk()
            status, res = create_psk(api_key, net_id, ssid_num, name, psk, gp_id)
            out.append({"unit": unit, "name": name, "psk": psk, "status": status})
        st.write(out)
        csv_buf = io.StringIO()
        writer = csv.DictWriter(csv_buf, fieldnames=["unit","name","psk","status"])
        writer.writeheader()
        writer.writerows(out)
        st.download_button("Download Results CSV", csv_buf.getvalue(), "psk_results.csv", "text/csv")
