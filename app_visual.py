import streamlit as st
import pandas as pd
import networkx as nx
from pyvis.network import Network
from collections import defaultdict
import community as community_louvain
import streamlit.components.v1 as components

st.set_page_config(layout="wide")
st.title("Job Title ↔ Certification Graph")

# 📂 Load Excel file
@st.cache_data
def load_data():
    path = "certificate_file.csv"
    df = pd.read_csv(path)
    df = df[df['llm_evaluation'] == 'MATCH'].copy()
    df['parsed_jt'] = df['parsed_jt'].astype(str)
    df['certification_names'] = df['certification'].astype(str)
    return df[['parsed_jt', 'certification_names']]

# 🔗 Build the networkx graph
@st.cache_data
def build_graph(network_df):
    jt_cert_map = {}
    for _, row in network_df.iterrows():
        job = row['parsed_jt']
        certs = row['certification_names'].split(';')
        if job not in jt_cert_map:
            jt_cert_map[job] = set()
        jt_cert_map[job].update([c.strip() for c in certs if c.strip()])

    G = nx.Graph()
    edges = [(job, cert) for job, certs in jt_cert_map.items() for cert in certs]
    G.add_edges_from(edges)

    node_attrs = {node: {'type': 'Job Title'} for node in jt_cert_map}
    for _, certs in jt_cert_map.items():
        for cert in certs:
            node_attrs[cert] = {'type': 'Certification'}
    nx.set_node_attributes(G, node_attrs)

    partition = community_louvain.best_partition(G)
    nx.set_node_attributes(G, partition, "community")

    return G

# ✅ Cached full graph (used when filters are empty)
@st.cache_data
def build_full_graph():
    full_df = load_data()
    return build_graph(full_df)

# 🌐 Generate interactive PyVis graph
def generate_pyvis_graph(_G):
    net = Network(height="750px", width="100%", bgcolor="#ffffff", font_color="black")
    net.from_nx(_G)

    for node in net.nodes:
        nid = node['id']
        typ = _G.nodes[nid].get('type', 'Unknown')
        comm = _G.nodes[nid].get('community', 0)
        node['title'] = f"{typ} — Community {comm}"
        node['label'] = str(nid)
        node['color'] = f"hsl({comm * 37 % 360}, 70%, 60%)"
        if typ == 'Certification':
            node['font'] = {'color': 'darkblue'}
        else:
            node['font'] = {'color': 'darkgreen'}

    net.save_graph("graph.html")
    with open("graph.html", "r", encoding='utf-8') as f:
        return f.read()

# 🧠 Main logic
with st.spinner("Loading and building graph..."):
    df = load_data()

    # --- Dropdown filters ---
    all_jobs = sorted(df['parsed_jt'].unique())
    all_certs = sorted({c.strip() for s in df['certification_names'] for c in s.split(';') if c.strip()})

    selected_jobs = st.multiselect("🔍 Filter by Job Title", all_jobs)
    selected_certs = st.multiselect("📛 Filter by Certification", all_certs)

    # --- Apply Job/Cert filters ---
    filtered_df = df.copy()
    if selected_jobs:
        filtered_df = filtered_df[filtered_df['parsed_jt'].isin(selected_jobs)]
    if selected_certs:
        filtered_df = filtered_df[
            filtered_df['certification_names'].apply(
                lambda x: any(c.strip() in selected_certs for c in x.split(';'))
            )
        ]

    # --- Temporary graph (used for community list and fallback) ---
    temp_graph = build_graph(filtered_df if selected_jobs or selected_certs else df)

    # --- Community filter ---
    all_communities = sorted(set(nx.get_node_attributes(temp_graph, "community").values()))
    selected_comms = st.multiselect("🧠 Filter by Community ID", all_communities)

    # --- Smart graph selection ---
    if not selected_jobs and not selected_certs and not selected_comms:
        G = build_full_graph()
    else:
        G = temp_graph
        if selected_comms:
            nodes_to_keep = [n for n, d in G.nodes(data=True) if d.get("community") in selected_comms]
            G = G.subgraph(nodes_to_keep).copy()

    # --- Render graph ---
    html = generate_pyvis_graph(G)
    components.html(html, height=750, scrolling=True)