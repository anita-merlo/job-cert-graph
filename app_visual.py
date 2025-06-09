import streamlit as st
import pandas as pd
from streamlit_agraph import agraph, Node, Edge, Config

st.set_page_config(layout="wide")
st.title("Job Title ↔ Certification Graph")

# --- 1. Load Data ---
@st.cache_data
def load_data(n_jobs_limit=20):
    path = "job_with_cluster_and_description.csv"
    df = pd.read_csv(path)
    df = df[df['llm_evaluation'] == 'MATCH'].copy()
    df['parsed_jt'] = df['parsed_jt'].astype(str)
    df['certification_names'] = df['certification'].astype(str)
    #df = df[~df['certification_names'].str.contains('CPR', case=False, na=False)]
    # Limit to N jobs (at load time!)
    job_subset = df['parsed_jt'].drop_duplicates().head(n_jobs_limit)
    df = df[df['parsed_jt'].isin(job_subset)]
    return df[['parsed_jt', 'certification_names', 'cluster_label', 'seniority']]

# --- 2. App Main ---
# --- 2. App Main ---
with st.spinner("Loading and building graph..."):
    n_jobs = st.slider("Max job titles to display", 5, 1000, 50)
    df = load_data(n_jobs_limit=n_jobs)

    # -- Streamlit filter values --
    all_jobs = sorted(df['parsed_jt'].unique())
    all_certs = sorted({c.strip() for s in df['certification_names'] for c in s.split(';') if c.strip()})
    all_clusters = sorted(df['cluster_label'].dropna().unique())
    all_seniority = sorted(df['seniority'].dropna().unique())

    # -- Start columns --
    col1, col2 = st.columns([1, 3])

    with col1:
        st.markdown("### Filters")
        selected_jobs = st.multiselect("Job Title", all_jobs)
        selected_certs = st.multiselect("Certification", all_certs)
        selected_clusters = st.multiselect("Cluster Label", all_clusters)
        selected_seniority = st.multiselect("Seniority", all_seniority)

        st.markdown("### Cluster Color Legend")
        cluster_palette = {
            "Skilled Trades & Technicians":        "#A259FF",  # purple
            "Healthcare Professionals":            "#F94144",  # red
            "Education Professionals":             "#43AA8B",  # green
            "Allied Health & Biomedical":          "#577590",  # blue-grey
            "Construction and Facilities":         "#F3722C",  # orange
            "Certified Nursing Assistants":        "#FFB703",  # yellow-orange
            "Athletics/Sports Staff":              "#3A86FF",  # blue
            "Behavioral Health Specialists":       "#F8961E",  # amber
            "Community & Recreation Services":     "#277DA1",  # steel blue
            "Nursing & Healthcare":                "#90BE6D",  # light green
        }
        legend = ""
        for name, color in cluster_palette.items():
            legend += f"<span style='display:inline-block;width:16px;height:16px;background:{color};border-radius:4px;margin-right:8px;'></span>{name}<br>"
        st.markdown(legend, unsafe_allow_html=True)

    with col2:
        # --- Apply filters ---
        filtered_df = df.copy()
        if selected_jobs:
            filtered_df = filtered_df[filtered_df['parsed_jt'].isin(selected_jobs)]
        if selected_certs:
            filtered_df = filtered_df[
                filtered_df['certification_names'].apply(
                    lambda x: any(c.strip() in selected_certs for c in x.split(';'))
                )
            ]
        if selected_clusters:
            filtered_df = filtered_df[filtered_df['cluster_label'].isin(selected_clusters)]
        if selected_seniority:
            filtered_df = filtered_df[filtered_df['seniority'].isin(selected_seniority)]

        # --- Build nodes and edges for agraph ---
        job_nodes = {}
        cert_nodes = {}
        edges = []
        for idx, row in filtered_df.iterrows():
            job = row["parsed_jt"]
            certs = [c.strip() for c in row["certification_names"].split(";") if c.strip()]
            cluster_label = row.get("cluster_label", "Unknown")
            seniority = row.get("seniority", "Unknown")
            job_color = cluster_palette.get(cluster_label, "gray")
            if job not in job_nodes:
                job_nodes[job] = Node(
                    id=job,
                    label=f"{job}\n({cluster_label}, {seniority})",
                    size=25,
                    color=job_color
                )
            for cert in certs:
                if cert not in cert_nodes:
                    cert_nodes[cert] = Node(id=cert, label=cert, size=20, color="blue")
                edges.append(Edge(source=job, target=cert))

        nodes = list(job_nodes.values()) + list(cert_nodes.values())

        # -- Graph config --
        static_graph = st.toggle("Static Graph Mode (faster, drag-and-drop enabled)", value=False)

        config = Config(
            width=1100,
            height=700,
            directed=False,
            nodeHighlightBehavior=True,
            highlightColor="#F7A7A6",
            collapsible=True,
            physics=not static_graph,
            staticGraphWithDragAndDrop=static_graph
        )

        st.subheader("Interactive Job ↔ Certification Network")
        agraph(nodes=nodes, edges=edges, config=config)