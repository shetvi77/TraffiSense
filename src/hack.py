import streamlit as st
import osmnx as ox
import folium
from streamlit_folium import st_folium
import pandas as pd
import networkx as nx
import random
import os
from groq import Groq 

st.set_page_config(layout="wide", page_title="Traffic Incident Decision Support System", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}
        
       .stApp {
            background-color: #000000; /* Navy Blue */
        }
        
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
            max-width: 96%;
        }
    </style>
""", unsafe_allow_html=True)

if 'traffic_conditions' not in st.session_state:
    st.session_state.traffic_conditions = {}
if 'optimum_path_keys' not in st.session_state:
    st.session_state.optimum_path_keys = set()
if 'baseline_path_keys' not in st.session_state:
    st.session_state.baseline_path_keys = set()
if 'ambulance_path_keys' not in st.session_state:
    st.session_state.ambulance_path_keys = set()
if 'opt_path_nodes' not in st.session_state:
    st.session_state.opt_path_nodes = []
if 'optimized_signals' not in st.session_state:
    st.session_state.optimized_signals = []
if 'active_incident_street' not in st.session_state:
    st.session_state.active_incident_street = "None"
if 'render_key' not in st.session_state:
    st.session_state.render_key = 0
if 'start_node' not in st.session_state:
    st.session_state.start_node = None
if 'end_node' not in st.session_state:
    st.session_state.end_node = None
if 'hospital_node' not in st.session_state:
    st.session_state.hospital_node = None
if 'matrix_data' not in st.session_state:
    st.session_state.matrix_data = {"t_baseline": 0, "t_routed": 0}
if 'ambulance_time' not in st.session_state:
    st.session_state.ambulance_time = 0
if "messages" not in st.session_state:
    st.session_state.messages = []
if "public_alert" not in st.session_state:
    st.session_state.public_alert = ""

@st.cache_data
def get_ahmedabad_data():
    center_point = (23.0037, 72.5122) 
    with st.spinner("Initializing Grid..."):
        ox.settings.overpass_settings = '[out:json][timeout:60]'
        G = ox.graph_from_point(center_point, dist=1500, network_type='drive')
        nodes, edges = ox.graph_to_gdfs(G)
        edges = edges.reset_index()
        
        edges['u'] = edges['u'].astype(str)
        edges['v'] = edges['v'].astype(str)
        
        def clean_name(val):
            if isinstance(val, list): return " / ".join(map(str, val))
            return str(val) if val else "Local Road"
        
        edges['name'] = edges['name'].apply(clean_name)
    return nodes, edges, G

def get_incident_nodes(G, blocked_street):
    blocked_nodes = []
    for u, v, k, data in G.edges(keys=True, data=True):
        name_val = data.get('name', '')
        if blocked_street != "None" and blocked_street.lower() in str(name_val).lower():
            blocked_nodes.extend([u, v])

    if not blocked_nodes:
        return None, None

    blocked_nodes = list(set(blocked_nodes))
    start_node, end_node = blocked_nodes[0], blocked_nodes[-1]
    max_dist = -1

    for i in range(len(blocked_nodes)):
        for j in range(i + 1, len(blocked_nodes)):
            n1, n2 = blocked_nodes[i], blocked_nodes[j]
            dist = (G.nodes[n1]['x'] - G.nodes[n2]['y'])**2 + (G.nodes[n1]['y'] - G.nodes[n2]['y'])**2
            if dist > max_dist:
                max_dist = dist
                start_node, end_node = n1, n2

    return start_node, end_node

def randomize_city_traffic(edges_df):
    conditions = {}
    for _, row in edges_df.iterrows():
        u, v = str(row['u']), str(row['v'])
        state = random.choices(['Low', 'Medium', 'High'], weights=[70, 20, 10])[0]
        conditions[f"{u}-{v}"] = state
        conditions[f"{v}-{u}"] = state
    return conditions

def calculate_routes(G, start_node, end_node, traffic_conditions, blocked_street):
    G_temp = G.copy()
    
    for u, v, k, data in G_temp.edges(keys=True, data=True):
        edge_id = f"{str(u)}-{str(v)}"
        condition = traffic_conditions.get(edge_id, 'Low')
        name_val = str(data.get('name', ''))
        
        if condition == 'Congested': speed_kmh = 5
        elif condition == 'High': speed_kmh = 10
        elif condition == 'Medium': speed_kmh = 25
        else: speed_kmh = 40
            
        speed_mpm = speed_kmh * 16.6667 
        length = data.get('length', 100)
        
        data['weight_base'] = length / (40 * 16.6667)

        if blocked_street != "None" and blocked_street.lower() in name_val.lower():
            data['weight_traffic'] = 1_000_000 
        else:
            data['weight_traffic'] = length / speed_mpm  

    try:
        base_path = nx.astar_path(G_temp, start_node, end_node, weight='weight_base')
        base_keys = set()
        t_base = 0
        for i in range(len(base_path) - 1):
            base_keys.add(f"{str(base_path[i])}-{str(base_path[i + 1])}")
            base_keys.add(f"{str(base_path[i + 1])}-{str(base_path[i])}")
            edge_data = G_temp.get_edge_data(base_path[i], base_path[i+1])
            if edge_data and 0 in edge_data:
                t_base += edge_data[0].get('weight_base', 0)

        opt_path = nx.astar_path(G_temp, start_node, end_node, weight='weight_traffic')
        opt_keys = set()
        t_routed = 0
        for i in range(len(opt_path) - 1):
            opt_keys.add(f"{str(opt_path[i])}-{str(opt_path[i + 1])}")
            opt_keys.add(f"{str(opt_path[i + 1])}-{str(opt_path[i])}")
            edge_data = G_temp.get_edge_data(opt_path[i], opt_path[i+1])
            if edge_data and 0 in edge_data:
                t_routed += edge_data[0].get('weight_traffic', 0)
                
        return base_keys, opt_keys, opt_path, round(t_base, 1), round(t_routed, 1)
    except Exception as e:
        return set(), set(), [], 0, 0

def calculate_ambulance_route(G, hospital_node, incident_node, traffic_conditions):
    G_temp = G.copy()
    
    for u, v, k, data in G_temp.edges(keys=True, data=True):
        edge_id = f"{str(u)}-{str(v)}"
        condition = traffic_conditions.get(edge_id, 'Low')
        
        if condition == 'Congested': speed_kmh = 5
        elif condition == 'High': speed_kmh = 10
        elif condition == 'Medium': speed_kmh = 25
        else: speed_kmh = 40
            
        speed_mpm = speed_kmh * 16.6667 
        length = data.get('length', 100)
        data['weight_traffic'] = length / speed_mpm  

    try:
        amb_path = nx.astar_path(G_temp, hospital_node, incident_node, weight='weight_traffic')
        amb_keys = set()
        t_amb = 0
        for i in range(len(amb_path) - 1):
            amb_keys.add(f"{str(amb_path[i])}-{str(amb_path[i + 1])}")
            amb_keys.add(f"{str(amb_path[i + 1])}-{str(amb_path[i])}")
            edge_data = G_temp.get_edge_data(amb_path[i], amb_path[i+1])
            if edge_data and 0 in edge_data:
                t_amb += edge_data[0].get('weight_traffic', 0)
        return amb_keys, round(t_amb, 1)
    except Exception:
        return set(), 0

def optimize_city_signals(G, traffic_conditions, optimum_path_keys):
    signals = []
    for node in G.nodes():
        if G.in_degree(node) >= 4:
            worst_traffic = 'Low'
            is_on_detour = False
            
            for u, v, k, data in G.in_edges(node, data=True, keys=True):
                edge_id = f"{str(u)}-{str(v)}"
                cond = traffic_conditions.get(edge_id, 'Low')
                
                if edge_id in optimum_path_keys:
                    is_on_detour = True
                    
                if cond in ['High', 'Congested']:
                    worst_traffic = 'High'
                elif cond == 'Medium' and worst_traffic != 'High':
                    worst_traffic = 'Medium'
            
            if is_on_detour:
                green_time = 75
                color = '#10B981'
            elif worst_traffic == 'High':
                green_time = 60
                color = '#EF4444'
            elif worst_traffic == 'Medium':
                green_time = 45
                color = '#F59E0B'
            else:
                green_time = 30
                color = '#3B82F6'
                
            signals.append({
                'lat': G.nodes[node]['y'],
                'lon': G.nodes[node]['x'],
                'time': green_time,
                'color': color,
                'is_detour': is_on_detour
            })
    return signals

try:
    nodes, edges, G = get_ahmedabad_data()
    
    street_counts = edges['name'].value_counts()
    major_streets = street_counts[street_counts >= 4].index.tolist()
    valid_streets = sorted([s for s in major_streets if s not in ['Local Road', 'nan', '', 'None']])

    if st.session_state.hospital_node is None:
        st.session_state.hospital_node = ox.distance.nearest_nodes(G, 72.5122, 23.0037)

    if st.session_state.start_node is None:
        st.session_state.traffic_conditions = {f"{row['u']}-{row['v']}": 'Low' for _, row in edges.iterrows()}
        initial_street = random.choice(valid_streets) if valid_streets else "None"
        
        s_node, e_node = get_incident_nodes(G, initial_street)
        if s_node and e_node:
            st.session_state.start_node, st.session_state.end_node = s_node, e_node
            st.session_state.active_incident_street = "None" 
            b_keys, o_keys, o_nodes, t_b, t_r = calculate_routes(G, s_node, e_node, st.session_state.traffic_conditions, "None")
            st.session_state.baseline_path_keys = b_keys
            st.session_state.optimum_path_keys = o_keys
            st.session_state.opt_path_nodes = o_nodes
            st.session_state.matrix_data = {"t_baseline": t_b, "t_routed": t_r}

    st.title("Traffic Incident Decision Support System")
    st.markdown("Real-time Urban Grid Monitoring and Dynamic Rerouting Engine")
    st.divider()

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric(label="Active Blockage Status", value=st.session_state.active_incident_street if st.session_state.active_incident_street != "None" else "Clear")
    with m2:
        st.metric(label="Baseline Commute", value=f"{st.session_state.matrix_data['t_baseline']} min")
    with m3:
        saved_time = round(st.session_state.matrix_data['t_baseline'] - st.session_state.matrix_data['t_routed'], 1)
        delta_val = f"-{saved_time} min" if saved_time > 0 and st.session_state.active_incident_street != "None" else None
        st.metric(label="Dynamic Reroute Time", value=f"{st.session_state.matrix_data['t_routed']} min", delta=delta_val, delta_color="inverse")
    with m4:
        st.metric(label="Optimized Intersections", value=len(st.session_state.optimized_signals))

    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2 = st.columns([0.70, 0.30])

    with col1:
        m = folium.Map(location=[23.0037, 72.5122], zoom_start=15, tiles="cartodbpositron")
        
        edges_display = edges.copy()
        def assign_color(row):
            cond = st.session_state.traffic_conditions.get(f"{row['u']}-{row['v']}", 'Low')
            if cond == 'Congested': return '#8B0000'
            if cond == 'High': return '#EF4444'    
            if cond == 'Medium': return '#F59E0B'  
            return '#CBD5E1'                       
        edges_display['map_color'] = edges_display.apply(assign_color, axis=1)

        folium.GeoJson(
            edges_display,
            style_function=lambda x: {'color': x['properties']['map_color'], 'weight': 2, 'opacity': 0.5}
        ).add_to(m)

        incident = st.session_state.active_incident_street
        if incident != "None":
            incident_edges = edges_display[edges_display['name'].str.lower().str.contains(incident.lower(), na=False)]
            if not incident_edges.empty:
                folium.GeoJson(
                    incident_edges,
                    style_function=lambda x: {'color': '#991B1B', 'weight': 6, 'opacity': 0.9} 
                ).add_to(m)

        if st.session_state.baseline_path_keys:
            base_mask = edges_display.apply(lambda row: f"{row['u']}-{row['v']}" in st.session_state.baseline_path_keys, axis=1)
            base_edges = edges_display[base_mask]
            if not base_edges.empty:
                folium.GeoJson(
                    base_edges,
                    style_function=lambda x: {'color': '#334155', 'weight': 3, 'dashArray': '5, 8', 'opacity': 0.7}
                ).add_to(m)

        if st.session_state.optimum_path_keys:
            detour_mask = edges_display.apply(lambda row: f"{row['u']}-{row['v']}" in st.session_state.optimum_path_keys, axis=1)
            detour_edges = edges_display[detour_mask]
            if not detour_edges.empty:
                folium.GeoJson(
                    detour_edges,
                    style_function=lambda x: {'color': '#10B981', 'weight': 5, 'opacity': 1.0}
                ).add_to(m)

        if st.session_state.ambulance_path_keys:
            amb_mask = edges_display.apply(lambda row: f"{row['u']}-{row['v']}" in st.session_state.ambulance_path_keys, axis=1)
            amb_edges = edges_display[amb_mask]
            if not amb_edges.empty:
                folium.GeoJson(
                    amb_edges,
                    style_function=lambda x: {'color': '#8B5CF6', 'weight': 5, 'opacity': 1.0}
                ).add_to(m)

        if st.session_state.optimized_signals:
            for sig in st.session_state.optimized_signals:
                if sig.get('is_detour'):
                    tooltip_text = f"Detour Surge Signal | Extended Green Phase: {sig['time']} seconds"
                    radius_size = 5
                else:
                    tooltip_text = f"Standard Intersection | Optimal Green Phase: {sig['time']} seconds"
                    radius_size = 4
                    
                folium.CircleMarker(
                    location=[sig['lat'], sig['lon']],
                    radius=radius_size,
                    color='white',
                    weight=1,
                    fill=True,
                    fill_color=sig['color'],
                    fill_opacity=1.0,
                    tooltip=tooltip_text
                ).add_to(m)
        elif st.session_state.opt_path_nodes:
            for node_id in st.session_state.opt_path_nodes[1:-1]:
                node_data = G.nodes[node_id]
                folium.CircleMarker(
                    location=[node_data['y'], node_data['x']],
                    radius=3,
                    color='white',
                    weight=1,
                    fill=True,
                    fill_color='#10B981',
                    fill_opacity=1.0,
                    tooltip="Adaptive Signal: Green Phase Extended"
                ).add_to(m)

        if st.session_state.hospital_node:
            hosp_coords = [G.nodes[st.session_state.hospital_node]['y'], G.nodes[st.session_state.hospital_node]['x']]
            folium.Marker(hosp_coords, tooltip="Central Hospital", icon=folium.Icon(color="darkblue", icon="plus")).add_to(m)

        if st.session_state.start_node and st.session_state.end_node:
            start_coords = [G.nodes[st.session_state.start_node]['y'], G.nodes[st.session_state.start_node]['x']]
            end_coords = [G.nodes[st.session_state.end_node]['y'], G.nodes[st.session_state.end_node]['x']]
            folium.Marker(start_coords, tooltip="Origin", icon=folium.Icon(color="green", icon="play")).add_to(m)
            folium.Marker(end_coords, tooltip="Destination", icon=folium.Icon(color="red", icon="stop")).add_to(m)

        st_folium(m, width=1100, height=650, key=f"ahm_map_{st.session_state.render_key}")

    with col2:
        tab1, tab2 = st.tabs(["Control Panel", "AI Assistant"])
        
        with tab1:
            st.markdown("### System Commands")
            selected_street = st.selectbox("Target Blocked Road", ["Auto-Simulate Random Incident"] + valid_streets)
            
            if st.button("Trigger Incident and Reroute", type="primary", use_container_width=True):
                if selected_street == "Auto-Simulate Random Incident":
                    picked_street = random.choice(valid_streets) if valid_streets else "None"
                else:
                    picked_street = selected_street
                    
                s_node, e_node = get_incident_nodes(G, picked_street)
                
                if s_node and e_node:
                    st.session_state.start_node = s_node
                    st.session_state.end_node = e_node
                    st.session_state.active_incident_street = picked_street
                    st.session_state.public_alert = "" 
                    st.session_state.ambulance_path_keys = set()
                    st.session_state.ambulance_time = 0 
                    st.session_state.optimized_signals = []
                    
                    st.session_state.traffic_conditions = randomize_city_traffic(edges)
                    
                    mid_x = (G.nodes[s_node]['x'] + G.nodes[e_node]['x']) / 2
                    mid_y = (G.nodes[s_node]['y'] + G.nodes[e_node]['y']) / 2
                    
                    for u, v, k, data in G.edges(keys=True, data=True):
                        u_x, u_y = G.nodes[u]['x'], G.nodes[u]['y']
                        
                        dist_to_start = (u_x - G.nodes[s_node]['x'])**2 + (u_y - G.nodes[s_node]['y'])**2
                        dist_to_end = (u_x - G.nodes[e_node]['x'])**2 + (u_y - G.nodes[e_node]['y'])**2
                        dist_to_mid = (u_x - mid_x)**2 + (u_y - mid_y)**2
                        
                        if min(dist_to_start, dist_to_end, dist_to_mid) < 0.000003:
                            st.session_state.traffic_conditions[f"{str(u)}-{str(v)}"] = 'Congested'
                            st.session_state.traffic_conditions[f"{str(v)}-{str(u)}"] = 'Congested'
                    
                    b_keys, o_keys, o_nodes, t_b, t_r = calculate_routes(G, s_node, e_node, st.session_state.traffic_conditions, picked_street)
                    st.session_state.baseline_path_keys = b_keys
                    st.session_state.optimum_path_keys = o_keys
                    st.session_state.opt_path_nodes = o_nodes
                    st.session_state.matrix_data = {"t_baseline": t_b, "t_routed": t_r}
                    st.session_state.render_key += 1
                st.rerun()

            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("Optimize Signals", use_container_width=True):
                    st.session_state.optimized_signals = optimize_city_signals(G, st.session_state.traffic_conditions, st.session_state.optimum_path_keys)
                    st.session_state.render_key += 1
                    st.rerun()
            with col_b:
                if st.button("Dispatch Medevac", use_container_width=True):
                    if st.session_state.hospital_node and st.session_state.start_node:
                        a_keys, a_time = calculate_ambulance_route(G, st.session_state.hospital_node, st.session_state.start_node, st.session_state.traffic_conditions)
                        st.session_state.ambulance_path_keys = a_keys
                        st.session_state.ambulance_time = a_time
                        st.session_state.render_key += 1
                    st.rerun()

            if st.button("Clear Grid Data", use_container_width=True):
                st.session_state.active_incident_street = "None"
                st.session_state.public_alert = "" 
                st.session_state.ambulance_path_keys = set()
                st.session_state.ambulance_time = 0
                st.session_state.optimized_signals = []
                st.session_state.traffic_conditions = {f"{row['u']}-{row['v']}": 'Low' for _, row in edges.iterrows()}
                
                if st.session_state.start_node and st.session_state.end_node:
                    b_keys, o_keys, o_nodes, t_b, t_r = calculate_routes(G, st.session_state.start_node, st.session_state.end_node, st.session_state.traffic_conditions, "None")
                    st.session_state.baseline_path_keys = b_keys
                    st.session_state.optimum_path_keys = o_keys
                    st.session_state.opt_path_nodes = o_nodes
                    st.session_state.matrix_data = {"t_baseline": t_b, "t_routed": t_r}
                    
                st.session_state.render_key += 1
                st.rerun()
                
            st.divider()

            if st.session_state.active_incident_street != "None":
                if st.button("Generate Public Advisory", type="secondary", use_container_width=True):
                    with st.spinner("Drafting..."):
                        try:
                            groq_api_key = "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"
                            client = Groq(api_key=groq_api_key)
                            
                            creative_prompt = f"""
                            Write a short, engaging, and polite public service announcement SMS or Tweet for the citizens of Ahmedabad. 
                            Inform them that there is currently a blockage and heavy traffic on {st.session_state.active_incident_street}. 
                            Advise them to avoid the area and let them know that our smart routing system has activated a Green Wave on alternative routes to help clear the congestion. 
                            Keep it under 3 sentences. Be helpful and professional. Do not use any emojis.
                            """
                            
                            completion = client.chat.completions.create(
                                model="llama-3.1-8b-instant",
                                messages=[{"role": "user", "content": creative_prompt}],
                                temperature=0.7, 
                                max_tokens=150
                            )
                            st.session_state.public_alert = completion.choices[0].message.content
                        except Exception as e:
                            st.error(f"Failed to generate alert: {e}")
                
                if st.session_state.public_alert:
                    st.info(f"Broadcast Draft:\n\n{st.session_state.public_alert}")
                    
        with tab2:
            st.markdown("### Command Intelligence")
            
            prompt = st.chat_input("Query real-time grid data...")
            
            if prompt:
                st.session_state.messages.append({"role": "user", "content": prompt})
                
                groq_api_key = "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" 
                
                if not groq_api_key or groq_api_key == "PASTE_YOUR_GROQ_KEY_HERE":
                    st.session_state.messages.append({"role": "assistant", "content": "API Key missing."})
                else:
                    client = Groq(api_key=groq_api_key)
                    
                    congested_count = sum(1 for v in st.session_state.traffic_conditions.values() if v == 'Congested') // 2
                    heavy_count = sum(1 for v in st.session_state.traffic_conditions.values() if v == 'High') // 2
                    medium_count = sum(1 for v in st.session_state.traffic_conditions.values() if v == 'Medium') // 2
                    
                    system_context = f"""
                    You are the Traffic Command Assistant. Answer questions ONLY using the following real-time data about the city grid. Do NOT make up information or use outside knowledge. If the answer is not in this data, say I do not have that information based on the current dashboard. Keep answers concise and professional. Do not use any emojis.
                    
                    CURRENT DASHBOARD DATA:
                    - Active Complete Blockage: {st.session_state.active_incident_street}
                    - Baseline Commute Time (Assuming no traffic): {st.session_state.matrix_data['t_baseline']} minutes
                    - Dynamic Reroute Commute Time (Avoiding traffic): {st.session_state.matrix_data['t_routed']} minutes
                    - Severe Congestion Roads Count: {congested_count}
                    - High Traffic Roads Count: {heavy_count}
                    - Medium Traffic Roads Count: {medium_count}
                    - Total Optimized Intersections: {len(st.session_state.optimized_signals)}
                    - Ambulance ETA to incident: {st.session_state.ambulance_time} minutes.
                    """

                    api_messages = [{"role": "system", "content": system_context}]
                    api_messages.extend([{"role": m["role"], "content": m["content"]} for m in st.session_state.messages if m["role"] != "system"])

                    try:
                        completion = client.chat.completions.create(
                            model="llama-3.1-8b-instant", 
                            messages=api_messages,
                            temperature=0.3, 
                            max_tokens=256
                        )
                        response = completion.choices[0].message.content
                        st.session_state.messages.append({"role": "assistant", "content": response})
                    except Exception as api_e:
                        st.session_state.messages.append({"role": "assistant", "content": f"API Error: {api_e}"})

            chat_container = st.container(height=450)
            with chat_container:
                for message in st.session_state.messages:
                    with st.chat_message(message["role"]):
                        st.markdown(message["content"])

except Exception as e:
    st.error(f"System Error: {e}")