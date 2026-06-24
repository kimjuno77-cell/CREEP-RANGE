import streamlit as st
import pandas as pd
import numpy as np
import json
import io
import base64
import os
from calculations import CreepAssessment
from report_generator import generate_html_report

# --- App Configuration ---
st.set_page_config(page_title="API 579 Part 10 Creep Assessment", layout="wide")

st.title("API 579-1 / ASME FFS-1 Part 10")
st.subheader("Assessment of Components Operating in the Creep Range")

# --- Default Data ---
default_component = {
    "Component Name": "Example Component",
    "Component Type": "Combined (동체+경판)",
    "Material": "Carbon Steel",
    "Inside Diameter (mm)": 1900.0,
    "Shell Thickness (mm)": 32.0,
    "Head Thickness (mm)": 30.6,
    "Future Corrosion Allowance (mm)": 3.0,
    "Weld Joint Efficiency (E)": 1.0,
    "Weld Seam Temp Adjustment": True,
    "Assessment Level": "API 579-1_ASME FFS-1 Level 1",
    "Periods": [
        {"Period Type": "Operational", "Pressure": 0.405, "Pressure Unit": "kg/mm^2", "Temperature (C)": 250.0, "Duration (hrs)": 261840.0},
        {"Period Type": "Operational", "Pressure": 0.0051, "Pressure Unit": "kg/mm^2", "Temperature (C)": 538.0, "Duration (hrs)": 960.0}
    ]
}


example_1_component = {
    "Component Name": "Example Problem 1 (Cylindrical Shell)",
    "Component Type": "Shell (동체)",
    "Material": "Carbon Steel",
    "Inside Diameter (mm)": 1524.0,  # 60 in
    "Shell Thickness (mm)": 9.525,   # 0.375 in
    "Head Thickness (mm)": 0.0,
    "Future Corrosion Allowance (mm)": 2.54, # 0.1 in
    "Weld Joint Efficiency (E)": 1.0,
    "Weld Seam Temp Adjustment": True, # Excursion with weld seam
    "Assessment Level": "API 579-1_ASME FFS-1 Level 1",
    "Periods": [
        {"Period Type": "Operational", "Pressure": 0.5695, "Pressure Unit": "MPa", "Temperature (C)": 510.0, "Duration (hrs)": 20.0} # 82.6 psig, 950 F
    ]
}

example_2_component = {
    "Component Name": "Example Problem 2 (Cylindrical Shell)",
    "Component Type": "Shell (동체)",
    "Material": "Carbon Steel",
    "Inside Diameter (mm)": 1524.0,  # 60 in
    "Shell Thickness (mm)": 9.525,   # 0.375 in
    "Head Thickness (mm)": 0.0,
    "Future Corrosion Allowance (mm)": 2.54, # 0.1 in
    "Weld Joint Efficiency (E)": 1.0,
    "Weld Seam Temp Adjustment": False,
    "Assessment Level": "API 579-1_ASME FFS-1 Level 1",
    "Periods": [
        {"Period Type": "Operational", "Pressure": 0.34474, "Pressure Unit": "MPa", "Temperature (C)": 454.44, "Duration (hrs)": 87600.0}, # 50 psig, 850 F
        {"Period Type": "Operational", "Pressure": 0.34474, "Pressure Unit": "MPa", "Temperature (C)": 510.0, "Duration (hrs)": 20.0}, # 50 psig, 950 F
        {"Period Type": "Operational", "Pressure": 0.34474, "Pressure Unit": "MPa", "Temperature (C)": 454.44, "Duration (hrs)": 43800.0} # 50 psig, 850 F
    ]
}

example_4_component = {
    "Component Name": "Example Problem 4 (Crack Growth)",
    "Component Type": "Shell (동체)",
    "Material": "316 SS",
    "Inside Diameter (mm)": 1524.0,  # 60 in
    "Shell Thickness (mm)": 38.1,    # 1.5 in
    "Head Thickness (mm)": 0.0,
    "Future Corrosion Allowance (mm)": 0.0,
    "Weld Joint Efficiency (E)": 1.0,
    "Weld Seam Temp Adjustment": False,
    "Assessment Level": "API 579-1_ASME FFS-1 Level 3",
    "Crack Geometry": "RCSCLE2 (Cylinder, Outside Surface, Longitudinal)",
    "Flaw Depth a (mm)": 7.62,       # 0.30 in
    "Flaw Length 2c (mm)": 121.92,   # 4.80 in
    "Periods": [
        {"Period Type": "Operational", "Pressure": 3.44738, "Pressure Unit": "MPa", "Temperature (C)": 593.33, "Duration (hrs)": 7392.0} # 500 psig, 1100 F
    ]
}

example_3_component = {
    "Component Name": "Example Problem 3 (Heater Tube)",
    "Component Type": "Pipe (배관)",
    "Material": "2.25Cr-1Mo",
    "Inside Diameter (mm)": 202.7174,
    "Shell Thickness (mm)": 8.1788,
    "Head Thickness (mm)": 0.0,
    "Future Corrosion Allowance (mm)": 2.54,
    "Weld Joint Efficiency (E)": 1.0,
    "Weld Seam Temp Adjustment": False,
    "Assessment Level": "API 579-1_ASME FFS-1 Level 2",
    "Periods": [
        {"Period Type": "Operational", "Pressure": 1.4479, "Pressure Unit": "MPa", "Temperature (C)": 601.666, "Duration (hrs)": 131400.0},
        {"Period Type": "Operational", "Pressure": 1.4479, "Pressure Unit": "MPa", "Temperature (C)": 660.0, "Duration (hrs)": 336.0},
        {"Period Type": "Operational", "Pressure": 1.4479, "Pressure Unit": "MPa", "Temperature (C)": 601.666, "Duration (hrs)": 43800.0}
    ]
}

import copy

def on_level_change():
    idx = st.session_state.get('active_comp_idx', 0)
    level_val = st.session_state[f"level_sel_{idx}"]
    
    if "Level 1" in level_val:
        st.session_state['components'][idx] = copy.deepcopy(example_1_component)
    elif "Level 2" in level_val:
        st.session_state['components'][idx] = copy.deepcopy(example_3_component)
    elif "Level 3" in level_val:
        st.session_state['components'][idx] = copy.deepcopy(example_4_component)
        
    st.session_state['components'][idx]["Assessment Level"] = level_val

# --- Session State Initialization ---
if 'components' not in st.session_state:
    st.session_state['components'] = [example_1_component]


# --- Sidebar: Project Files ---
st.sidebar.header("📁 Project Files")

# 1. Load JSON State
uploaded_json = st.sidebar.file_uploader("Upload Session JSON", type=['json'])
if uploaded_json is not None:
    if st.session_state.get('last_uploaded_json_id') != uploaded_json.file_id:
        try:
            data = json.load(uploaded_json)
            if isinstance(data, list):
                st.session_state['components'] = data
                st.session_state['last_uploaded_json_id'] = uploaded_json.file_id
                st.sidebar.success("Session loaded successfully!")
        except Exception as e:
            st.sidebar.error("Error loading JSON file.")



# --- Main Content Tabs ---
tab1, tab2 = st.tabs(["📝 Input Data (Components)", "📊 Results & Report"])

with tab1:
    st.markdown("### Component Design & Operating Data")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        comp_names = [c.get("Component Name", f"Component {i+1}") for i, c in enumerate(st.session_state['components'])]
        selected_idx = st.selectbox("Select Component to Edit:", range(len(comp_names)), format_func=lambda x: comp_names[x])
    with col2:
        st.write("")
        st.write("")
        if st.button("➕ Add New Component"):
            new_comp = default_component.copy()
            new_comp["Component Name"] = f"New Component {len(st.session_state['components']) + 1}"
            st.session_state['components'].append(new_comp)
            st.rerun()

    if len(st.session_state['components']) > 0:
        active_comp = st.session_state['components'][selected_idx]
        
        with st.expander("⚙️ Component Design Data (설계 데이터)", expanded=True):
            c1, c2, c3 = st.columns(3)
            active_comp["Component Name"] = c1.text_input("Component Name", active_comp.get("Component Name", ""))
            
            comp_types = ["Combined (동체+경판)", "Shell (동체)", "Head (경판)", "Pipe (배관)"]
            ctype_val = active_comp.get("Component Type", "Combined (동체+경판)")
            active_comp["Component Type"] = c2.selectbox("Component Type (컴포넌트 유형)", comp_types, index=comp_types.index(ctype_val) if ctype_val in comp_types else 0)
            
            materials = ["Carbon Steel", "304 SS", "316 SS", "321 SS", "347 SS", "1.25Cr-0.5Mo", "2.25Cr-1Mo", "9Cr-1Mo"]
            mat_val = active_comp.get("Material", "Carbon Steel")
            mat_idx = materials.index(mat_val) if mat_val in materials else 0
            active_comp["Material"] = c3.selectbox("Material (재질)", materials, index=mat_idx)
            
            levels = [
                "API 579-1_ASME FFS-1 Level 1", 
                "API 579-1_ASME FFS-1 Level 2", 
                "API 579-1_ASME FFS-1 Level 3", 
                "ASME B31.3 Appendix V"
            ]
            level_val = active_comp.get("Assessment Level", "API 579-1_ASME FFS-1 Level 1")
            st.session_state['active_comp_idx'] = selected_idx
            active_comp["Assessment Level"] = st.selectbox(
                "Assessment Level (평가 레벨)", 
                levels, 
                index=levels.index(level_val) if level_val in levels else 0,
                key=f"level_sel_{selected_idx}",
                on_change=on_level_change
            )
            
            st.info("""
**Assessment Level Guide (평가 레벨 안내)**
- **API 579-1_ASME FFS-1 Level 1**: Basic assessment using conservative screening curves (LMP method). / 보수적인 스크리닝 곡선(LMP)을 사용하는 기본 평가
- **API 579-1_ASME FFS-1 Level 2**: Detailed assessment using the MPC Omega method. / MPC Omega 방식을 사용하는 상세 평가
- **API 579-1_ASME FFS-1 Level 3**: Advanced assessment requiring detailed stress analysis (e.g., FEA) and specific operational history. / 상세 응력해석(FEA 등) 및 특정 운전 이력이 요구되는 고급 평가
- **ASME B31.3 App. V**: Piping-specific assessment adding safety margins to LMP. / 배관 전용으로 LMP 방식에 안전 여유도를 추가한 평가
""")
            
            c4, c5, c6 = st.columns(3)
            active_comp["Inside Diameter (mm)"] = c4.number_input("Inside Diameter / 내경 (mm)", value=float(active_comp.get("Inside Diameter (mm)", 1900.0)))
            
            # Hide/disable thickness inputs based on type
            is_head_only = "Head" in active_comp["Component Type"]
            is_shell_pipe_only = "Shell" in active_comp["Component Type"] or "Pipe" in active_comp["Component Type"]
            
            shell_label = "Pipe Thickness / 배관 두께 (mm)" if "Pipe" in active_comp["Component Type"] else "Shell Thickness / 동체 두께 (mm)"
            
            active_comp["Shell Thickness (mm)"] = c5.number_input(shell_label, value=float(active_comp.get("Shell Thickness (mm)", 32.0)), disabled=is_head_only)
            active_comp["Head Thickness (mm)"] = c6.number_input("Head Thickness / 경판 두께 (mm)", value=float(active_comp.get("Head Thickness (mm)", 30.6)), disabled=is_shell_pipe_only)
            
            c7, c8, c9 = st.columns(3)
            active_comp["Future Corrosion Allowance (mm)"] = c7.number_input("FCA / 부식 여유 (mm)", value=float(active_comp.get("Future Corrosion Allowance (mm)", 3.0)))
            active_comp["Weld Joint Efficiency (E)"] = c8.number_input("Weld Joint Eff. / 용접 효율 (E)", value=float(active_comp.get("Weld Joint Efficiency (E)", 1.0)))
            active_comp["Weld Seam Temp Adjustment"] = c9.checkbox("Weld Seam Temp Adj. / 용접부 온도 보정 (+4°C)", value=bool(active_comp.get("Weld Seam Temp Adjustment", True)))
            
            c10, c11 = st.columns([1, 2])
            active_comp["Thermal Cycles"] = c10.number_input("Thermal Cycles / 열 반복 횟수", value=float(active_comp.get("Thermal Cycles", 0.0)), min_value=0.0, step=1.0, help="For Level 1: checks if <= 50. For Level 2/3: tracks operational cycles.")
            
        is_level3 = "Level 3" in active_comp["Assessment Level"]
        
        
        if is_level3:
            with st.expander("🛠️ Level 3 Flaw Dimensions & Geometry (Crack Growth)", expanded=True):
                geoms = [
                    "RCSCLE2 (Cylinder, Outside Surface, Longitudinal)",
                    "RCSCCI2 (Cylinder, Inside Surface, Circumferential)",
                    "RCSCCE2 (Cylinder, Outside Surface, Circumferential)",
                    "RSSCSE (Sphere, Surface Crack)"
                ]
                geom_val = active_comp.get("Crack Geometry", "RCSCLE2 (Cylinder, Outside Surface, Longitudinal)")
                active_comp["Crack Geometry"] = st.selectbox("Crack Geometry (균열 형상 모델)", geoms, index=geoms.index(geom_val) if geom_val in geoms else 0)
                
                c1, c2 = st.columns(2)
                active_comp["Flaw Depth a (mm)"] = c1.number_input("Flaw Depth (a) / 균열 깊이 (mm)", value=float(active_comp.get("Flaw Depth a (mm)", 7.62)))
                active_comp["Flaw Length 2c (mm)"] = c2.number_input("Flaw Length (2c) / 균열 길이 (mm)", value=float(active_comp.get("Flaw Length 2c (mm)", 121.92)))
                st.info("Note: Select the appropriate crack geometry. M_s (Reference Stress parameter) will be calculated dynamically.")

            with st.expander("📈 Time-Temperature-Stress Profile (Level 3)", expanded=True):
                st.write("Enter the startup, dwell, and shutdown history of the component.")
                
                profile_default = active_comp.get("Level 3 Profile Text", """# Time(hrs), Temperature(C), Stress(MPa)
0, 25, 0
10, 538, 150
50, 538, 120
100, 538, 110
110, 300, 150
120, 25, 0""")
                
                active_comp["Level 3 Profile Text"] = st.text_area(
                    "Time-Temperature-Stress Profile (Time(hrs), Temp(°C), Stress(MPa))",
                    value=profile_default,
                    height=200,
                    help="Enter data with one point per line, separated by commas, tabs, or spaces. Lines starting with # are comments."
                )
                
                active_comp["Level 3 Multiplier"] = st.number_input(
                    "Lifetime Cycles Multiplier (반복 횟수)",
                    value=float(active_comp.get("Level 3 Multiplier", 1.0)),
                    min_value=1.0,
                    step=1.0,
                    help="The number of times this transient profile repeats over the component's design life."
                )
        else:
            with st.expander("🕒 Operating Periods (운전 기간)", expanded=True):
                st.write("Define the operating conditions over the component's life.")
                periods_df = pd.DataFrame(active_comp.get("Periods", []))
                
                required_cols = ["Period Type", "Pressure", "Pressure Unit", "Temperature (C)", "Duration (hrs)", "Von Mises Stress (MPa)"]
                for col in required_cols:
                    if col not in periods_df.columns:
                        periods_df[col] = np.nan
                        
                column_order = ["Period Type", "Pressure", "Pressure Unit", "Temperature (C)", "Duration (hrs)"]
                if "Level 2" in active_comp["Assessment Level"]:
                    column_order.append("Von Mises Stress (MPa)")
                    
                edited_periods = st.data_editor(
                    periods_df,
                    num_rows="dynamic",
                    width="stretch",
                    column_order=column_order,
                    column_config={
                        "Period Type": st.column_config.SelectboxColumn("Period Type (운전 유형)", options=["Operational", "Maintenance"], default="Operational"),
                        "Pressure Unit": st.column_config.SelectboxColumn("Pressure Unit", options=["MPa", "kg/mm^2"]),
                        "Von Mises Stress (MPa)": st.column_config.NumberColumn("Von Mises Stress (MPa) [Optional]", min_value=0.0, step=1.0, help="If provided, overrides calculated nominal stress for Level 2.")
                    },
                    key=f"periods_editor_{selected_idx}"
                )
                active_comp["Periods"] = edited_periods.to_dict('records')
            
        st.session_state['components'][selected_idx] = active_comp
with tab2:
    st.markdown("### Assessment Execution")
    
    if st.button("▶ Run Assessment for Selected Component (현재 조건 계산)", type="primary"):
        with st.spinner("Calculating..."):
            results_summary = []
            html_reports = []
            
            idx = selected_idx
            comp = st.session_state['components'][idx]
            try:
                assessment = CreepAssessment(comp)
                res = assessment.assess()
                
                summary = {
                    "Component Name": comp.get("Component Name", f"Component {idx+1}"),
                    "Material": comp.get("Material", "Unknown"),
                    "Total Periods": len(comp.get("Periods", [])) if "Level 3" not in comp.get("Assessment Level", "") else f"Level 3 Profile ({len(res.get('level3_profile', []))} pts)",
                    "Total Damage": round(res['total_damage'], 6),
                    "Remaining Life (hrs)": "Infinite" if res['remaining_life'] == float('inf') else round(res['remaining_life'], 1),
                    "Status": res['status']
                }
                results_summary.append(summary)
                
                html_report = generate_html_report(comp, res)
                html_reports.append((idx, comp, html_report, res))
                
            except Exception as e:
                st.error(f"Error processing component {comp.get('Component Name', idx+1)}: {e}")
                
            if results_summary:
                df_summary = pd.DataFrame(results_summary)
                st.success("Calculations Complete!")
                
                st.dataframe(df_summary, width="stretch")
                
                st.markdown("### Detailed Calculation Trace & Reports")
                for idx, comp, html, res in html_reports:
                    comp_name = comp.get("Component Name", f"Component {idx+1}")
                    with st.expander(f"📄 Report for {comp_name} ({res['status']})"):
                        st.markdown("#### Calculation Details (Step-by-Step)")
                        formatted_trace = "<br>".join([line.replace("   ", "&nbsp;&nbsp;&nbsp;") for line in res['trace']])
                        st.markdown(f'<div style="color: var(--text-color); background-color: var(--secondary-background-color); padding: 20px; border-left: 4px solid #0056b3; font-family: \'Segoe UI\', Tahoma, Geneva, Verdana, sans-serif; font-size: 15px; line-height: 1.6; border-radius: 4px; max-height: 500px; overflow-y: auto; margin-bottom: 20px;">{formatted_trace}</div>', unsafe_allow_html=True)
                        
                        if res.get("graph_b64"):
                            st.markdown(f'<div style="text-align: center;"><img src="data:image/png;base64,{res["graph_b64"]}" style="max-width:600px; border: 1px solid #ddd; padding: 10px; border-radius: 4px;"></div>', unsafe_allow_html=True)
                        
                        if res.get("creep_life_graph_b64"):
                            st.markdown(f'<div style="text-align: center; margin-top: 15px;"><img src="data:image/png;base64,{res["creep_life_graph_b64"]}" style="max-width:600px; border: 1px solid #ddd; padding: 10px; border-radius: 4px;"></div>', unsafe_allow_html=True)
                        
                        if "cycle_table" in res and res["cycle_table"]:
                            st.markdown("#### 🔄 Rainflow Cycle Counting Results (Fatigue Analysis)")
                            df_cycles = pd.DataFrame(res["cycle_table"])
                            df_cycles.columns = ["Cycle Index", "Stress Range (MPa)", "Mean Stress (MPa)", "Cycle Count", "Stress Amplitude Sa (MPa)", "Allowable Cycles N", "Fatigue Damage (dDf)"]
                            st.dataframe(df_cycles, use_container_width=True)
                            
                        b64 = base64.b64encode(html.encode('utf-8')).decode('utf-8')
                        href = f'<a href="data:text/html;base64,{b64}" download="API579_Report_{comp_name}.html" style="display: inline-block; margin-top: 15px; padding: 0.5em 1em; color: white; background-color: #007bff; text-decoration: none; border-radius: 4px; font-weight: bold;">⬇ Download HTML Report</a>'
                        st.markdown(href, unsafe_allow_html=True)

# 3. Export JSON State (Placed at the bottom so it captures the latest session_state)
st.sidebar.markdown("---")
json_str = json.dumps(st.session_state['components'], indent=4)
st.sidebar.download_button(
    label="⬇ Save Session to JSON (세션 저장)",
    data=json_str,
    file_name="api579_session.json",
    mime="application/json"
)
