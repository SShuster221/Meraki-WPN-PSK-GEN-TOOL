import streamlit as st
import requests, csv, io, random

# --- PSK Generation Logic ---
# Curated list of friendly words (replace with full 1000-word list)
friendly_words = [
    "apple", "bridge", "candle", "daisy", "eagle", "flower", "guitar", "hat",
    "island", "jacket", "ladder", "marble", "notebook", "orange", "pillow", 
    "quilt", "river", "sunset", "teapot", "umbrella", "vase", "window",
    "xylophone", "yarn", "zebra", "anchor", "balloon", "cloud", "drum", 
    "elephant", "feather", "garden", "hill", "igloo", "jungle", "kite", 
    "lantern", "moon", "nest", "ocean", "penguin", "quiet", "rainbow", 
    "shell", "tree", "under", "valley", "whale", "xray", "yonder", "zoo"
]

def generate_friendly_psk():
    w1, w2 = random.sample(friendly_words, 2)
    def cap_one(word):
        i = random.randint(0, len(word)-1)
        return word[:i] + word[i].upper() + word[i+1:]
    num = random.choice([n for n in range(10,100) if n != 69])
    return f"{cap_one(w1)}{num}{cap_one(w2)}"

# --- Meraki API Helpers ---
def meraki_get(path, api_key):
    url = f"https://api.meraki.com/api/v1{path}"
    return requests.get(url, headers={"X-Cisco-Meraki-API-Key": api_key}).json()

def meraki_post(path, api_key, payload):
    url = f"https://api.meraki.com/api/v1{path}"
    r = requests.post(url, headers={"X-Cisco-Meraki-API-Key": api_key}, json=payload)
    return r.status_code, r.json()

# --- UI Frontend ---
st.title("Meraki WPN PSK Provisioning Tool")

api_key = st.text_input("Meraki API Key", type="password")
if not api_key:
    st.stop()

orgs = meraki_get("/organizations", api_key)
org = st.selectbox("Organization", [o["name"] for o in orgs])
org_id = next(o["id"] for o in orgs if o["name"] == org)

nets = meraki_get(f"/organizations/{org_id}/networks", api_key)
net = st.selectbox("Network", [n["name"] for n in nets])
net_id = next(n["id"] for n in nets if n["name"] == net)

ssids = meraki_get(f"/networks/{net_id}/wireless/ssids", api_key)
ssid_num = next((s["number"] for s in ssids if s["name"] == "Resident-WiFi"), None)
if ssid_num is None:
    st.error("SSIID 'Resident-WiFi' not found.")
    st.stop()

gps = meraki_get(f"/networks/{net_id}/groupPolicies", api_key)
gp = next((g for g in gps if g["name"]=="Resident_150Mbps"), None)
if not gp:
    st.error("Group policy 'Resident_150Mbps' not found.")
    st.stop()
gp_id = gp["groupPolicyId"]
st.success(f"Using groupPolicyId: {gp_id}")

prefix = st.text_input("Prefix before '- APT'", value="CC")
mode = st.radio("Input Method", ["Manual", "Upload CSV (room column)"])

units = []
if mode == "Manual":
    text = st.text_area("Enter unit numbers (one per line):")
    units = [l.strip() for l in text.splitlines() if l.strip()]
else:
    f = st.file_uploader("Upload CSV file", type=["csv"])
    if f:
        df = csv.DictReader(io.StringIO(f.getvalue().decode()))
        units = [r["room"].strip() for r in df if r.get("room")]

if not units:
    st.info("Enter unit numbers to proceed")
else:
    if st.button("Generate & Provision PSKs"):
        results = []
        for unit in units:
            name = f"{prefix} - APT {unit}"
            psk = generate_friendly_psk()
            status, res = meraki_post(
                f"/networks/{net_id}/wireless/ssids/{ssid_num}/identityPsks",
                api_key,
                {"name": name, "passphrase": psk, "groupPolicyId": gp_id}
            )
            results.append({"unit":unit, "name":name, "psk":psk, "status":status})
        st.write(results)
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=["unit","name","psk","status"])
        writer.writeheader(); writer.writerows(results)
        st.download_button("Download CSV", buf.getvalue(), "psk_results.csv", "text/csv")
