import math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import base64
import numpy as np

MATERIAL_DATABASE = {
    "Carbon Steel": {
        "C_lmp": 20.0,
        "A0": 42200.0,
        "A1": -2000.0,
        "Sr0": 40000.0,
        "Sr_slope": 35.0,
        "n_omega": 5.0,
        "Omega": 10.0,
        "creep_temp_c": 371.0
    },
    "1.25Cr-0.5Mo": {
        "C_lmp": 20.0,
        "A0": 45500.0,
        "A1": -2200.0,
        "Sr0": 50000.0,
        "Sr_slope": 40.0,
        "n_omega": 5.5,
        "Omega": 15.0,
        "creep_temp_c": 427.0
    },
    "2.25Cr-1Mo": {
        "C_lmp": 20.0,
        "A0": 47000.0,
        "A1": -2300.0,
        "Sr0": 55000.0,
        "Sr_slope": 42.0,
        "n_omega": 5.8,
        "Omega": 18.0,
        "creep_temp_c": 427.0
    },
    "9Cr-1Mo": {
        "C_lmp": 20.0,
        "A0": 49000.0,
        "A1": -2400.0,
        "Sr0": 60000.0,
        "Sr_slope": 45.0,
        "n_omega": 6.0,
        "Omega": 20.0,
        "creep_temp_c": 427.0
    },
    "304 SS": {
        "C_lmp": 20.0,
        "A0": 50000.0,
        "A1": -2100.0,
        "Sr0": 65000.0,
        "Sr_slope": 48.0,
        "n_omega": 6.2,
        "Omega": 25.0,
        "creep_temp_c": 510.0
    },
    "316 SS": {
        "C_lmp": 20.0,
        "A0": 51500.0,
        "A1": -2000.0,
        "Sr0": 70000.0,
        "Sr_slope": 50.0,
        "n_omega": 6.5,
        "Omega": 22.0,
        "creep_temp_c": 510.0
    },
    "321 SS": {
        "C_lmp": 20.0,
        "A0": 50500.0,
        "A1": -2100.0,
        "Sr0": 68000.0,
        "Sr_slope": 49.0,
        "n_omega": 6.3,
        "Omega": 24.0,
        "creep_temp_c": 510.0
    },
    "347 SS": {
        "C_lmp": 20.0,
        "A0": 52000.0,
        "A1": -2000.0,
        "Sr0": 72000.0,
        "Sr_slope": 51.0,
        "n_omega": 6.6,
        "Omega": 20.0,
        "creep_temp_c": 510.0
    }
}

def map_material(material_name):
    name = str(material_name).upper()
    if "516" in name or "CARBON" in name or "515" in name:
        return "Carbon Steel"
    elif "387 GR 11" in name or "1.25CR" in name or "GR 11" in name:
        return "1.25Cr-0.5Mo"
    elif "387 GR 22" in name or "2.25CR" in name or "GR 22" in name:
        return "2.25Cr-1Mo"
    elif "387 GR 9" in name or "9CR" in name or "GR 9" in name:
        return "9Cr-1Mo"
    elif "304" in name:
        return "304 SS"
    elif "316" in name:
        return "316 SS"
    elif "321" in name:
        return "321 SS"
    elif "347" in name:
        return "347 SS"
    else:
        return "Carbon Steel"


# --- Fatigue Curve Parameters & Langer's Equation Constants ---
FATIGUE_CURVE_PARAMS = {
    "Carbon Steel": {
        "A": 26100.0,
        "B": 116.0,
        "E": 207000.0
    },
    "1.25Cr-0.5Mo": {
        "A": 28000.0,
        "B": 125.0,
        "E": 200000.0
    },
    "2.25Cr-1Mo": {
        "A": 29000.0,
        "B": 130.0,
        "E": 200000.0
    },
    "9Cr-1Mo": {
        "A": 30000.0,
        "B": 140.0,
        "E": 200000.0
    },
    "304 SS": {
        "A": 58000.0,
        "B": 190.0,
        "E": 195000.0
    },
    "316 SS": {
        "A": 58000.0,
        "B": 190.0,
        "E": 195000.0
    },
    "321 SS": {
        "A": 58000.0,
        "B": 190.0,
        "E": 195000.0
    },
    "347 SS": {
        "A": 58000.0,
        "B": 190.0,
        "E": 195000.0
    }
}

def get_asme_allowable_cycles(material, S_a_mpa):
    """
    ASME Section VIII Div 2 Part 5 Langer's Equation:
    Sa = A / sqrt(N) + B  ==> N = (A / (Sa - B))^2
    """
    props = FATIGUE_CURVE_PARAMS.get(material, FATIGUE_CURVE_PARAMS["Carbon Steel"])
    A = props["A"]
    B = props["B"]
    if S_a_mpa <= B:
        return float('inf')
    return (A / (S_a_mpa - B))**2

def rainflow(series):
    """
    Rainflow counting algorithm according to ASTM E1049-85.
    Returns list of tuples: (range, mean, count)
    """
    extrema = []
    n = len(series)
    if n < 2:
        return []
        
    # Find all peaks and troughs
    extrema.append(series[0])
    for i in range(1, n - 1):
        d1 = series[i] - series[i-1]
        d2 = series[i+1] - series[i]
        if d1 * d2 < 0:
            extrema.append(series[i])
        elif d1 != 0 and d2 == 0:
            extrema.append(series[i])
            
    if series[n-1] != extrema[-1]:
        extrema.append(series[n-1])
        
    cycles = []
    stack = []
    
    for val in extrema:
        stack.append(val)
        while len(stack) >= 3:
            x = abs(stack[-1] - stack[-2])
            y = abs(stack[-2] - stack[-3])
            
            if x >= y:
                mean = (stack[-2] + stack[-3]) / 2.0
                if len(stack) == 3:
                    cycles.append((y, mean, 0.5))
                    stack.pop(0)
                else:
                    cycles.append((y, mean, 1.0))
                    stack.pop(-2)
                    stack.pop(-2)
            else:
                break
                
    while len(stack) >= 2:
        y = abs(stack[0] - stack[1])
        mean = (stack[0] + stack[1]) / 2.0
        cycles.append((y, mean, 0.5))
        stack.pop(0)
        
    return cycles

def parse_profile_text(text):
    periods = []
    if not text:
        return periods
    lines = text.strip().split('\n')
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        parts = []
        if ',' in line:
            parts = line.split(',')
        elif '\t' in line:
            parts = line.split('\t')
        else:
            parts = line.split()
            
        if len(parts) >= 3:
            try:
                time_val = float(parts[0].strip())
                temp_val = float(parts[1].strip())
                stress_val = float(parts[2].strip())
                periods.append({
                    "Time": time_val,
                    "Temperature": temp_val,
                    "Stress": stress_val
                })
            except ValueError:
                continue
    return periods

def generate_creep_fatigue_envelope_graph(Dc, Df, material):
    plt.figure(figsize=(7, 7))
    
    # Corner point Selection
    is_ss = "304" in material or "316" in material or "321" in material or "347" in material
    C = 0.3 if is_ss else 0.1
    F = 0.3 if is_ss else 0.1
    
    # Plot envelope lines
    plt.plot([0, C, 1], [1, F, 0], 'g-', linewidth=2.5, label="Creep-Fatigue Envelope Limit")
    plt.fill_between([0, C, 1], [1, F, 0], 0, color='lightgreen', alpha=0.3, label="Acceptable Region")
    
    # Plot Operating Point
    plt.plot(Dc, Df, 'ro', markersize=10, label=f"Operating Point (Dc={Dc:.4f}, Df={Df:.4f})")
    plt.text(Dc, Df, f"  ({Dc:.4f}, {Df:.4f})", verticalalignment='bottom', fontweight='bold', fontsize=11)
    
    plt.xlim(0, 1.1)
    plt.ylim(0, 1.1)
    plt.xlabel("Cumulative Creep Damage (Dc)", fontsize=11)
    plt.ylabel("Cumulative Fatigue Damage (Df)", fontsize=11)
    plt.title(f"Creep-Fatigue Bilinear Envelope - {material}", fontsize=12, fontweight='bold')
    plt.grid(True, ls="--", alpha=0.5)
    plt.legend(loc="upper right", fontsize=10)
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    plt.close()
    buf.seek(0)
    return base64.b64encode(buf.read()).decode('utf-8')


class CreepAssessment:
    def __init__(self, component_data):
        self.data = component_data
        self.raw_material = self.data.get("Material", "Carbon Steel")
        self.material = map_material(self.raw_material)
        self.mat_props = MATERIAL_DATABASE.get(self.material, MATERIAL_DATABASE["Carbon Steel"])
        
        self.Di_mm = float(self.data.get("Inside Diameter (mm)", 1900.0))
        self.t_s_mm = float(self.data.get("Shell Thickness (mm)", 32.0))
        self.t_h_mm = float(self.data.get("Head Thickness (mm)", 30.6))
        self.FCA_mm = float(self.data.get("Future Corrosion Allowance (mm)", 3.0))
        self.E = float(self.data.get("Weld Joint Efficiency (E)", 1.0))
        self.weld_adjustment = bool(self.data.get("Weld Seam Temp Adjustment", True))
        
        self.periods = self.data.get("Periods", [])
        self.assessment_level = self.data.get("Assessment Level", "API 579-1_ASME FFS-1 Level 1")
        self.component_type = self.data.get("Component Type", "Combined (동체+경판)")
        self.thermal_cycles = float(self.data.get("Thermal Cycles", 0))
        
        self.trace = []  # Step-by-step plain-text explanations
        self.plot_points = []
        

    def assess_level_2(self):
        self.trace.append('=== Component Design Assessment (컴포넌트 설계 평가) ===')
        self.trace.append(f'Material (재질): {self.raw_material} (Mapped to {self.material})')
        self.trace.append(f'Assessment Level (평가 레벨): {self.assessment_level}')
        self.trace.append('')
        
        self.trace.append('STEP 1 - Determine a load history based on past operation and future planned operation.')
        for idx, p in enumerate(self.periods):
            p_type = p.get('Period Type', 'Operational')
            pressure = float(p.get('Pressure', 0))
            p_unit = str(p.get('Pressure Unit') or 'MPa')
            temp_c = float(p.get('Temperature (C)', 0))
            duration = float(p.get('Duration (hrs)', 0))
            self.trace.append(f'   m={idx+1} ({p_type}): P={pressure} {p_unit}, T={temp_c} C, Time={duration} hours')
            
        self.trace.append('')
        self.trace.append('STEP 2 - Divide the cycle into a number of time increments.')
        self.trace.append('   For this assessment, each operating cycle is evaluated as a single increment (n=1).')
        
        total_damage = 0.0
        period_results = []
        
        R_c = (self.Di_mm / 2.0) + self.FCA_mm
        tc_s = max(0.001, self.t_s_mm - self.FCA_mm)
        tc_h = max(0.001, self.t_h_mm - self.FCA_mm)
        Di_c = self.Di_mm + 2 * self.FCA_mm
        
        is_combined = 'Combined' in self.component_type
        is_shell = 'Shell' in self.component_type or is_combined
        is_pipe = 'Pipe' in self.component_type
        is_head = 'Head' in self.component_type or is_combined
        
        A0, A1, A2, A3, A4 = -21.86, 50205, -5436, 500, -3400
        B0, B1, B2, B3, B4 = -1.85, 7205, -2436, 0.0, 0.0
        
        for idx, p in enumerate(self.periods):
            m = idx + 1
            pressure = float(p.get('Pressure', 0))
            p_unit = str(p.get('Pressure Unit') or 'MPa')
            temp_c = float(p.get('Temperature (C)', 0))
            duration = float(p.get('Duration (hrs)', 0))
            
            p_mpa = pressure * 9.80665 if 'kg/mm' in p_unit.lower() else pressure
            T_assess = temp_c
            if self.weld_adjustment and temp_c >= self.mat_props['creep_temp_c']:
                T_assess += 4.0
                
            self.trace.append('')
            self.trace.append(f'--- Cycle m = {m} ---')
            self.trace.append('STEP 3 - Determine the assessment temperature, T.')
            self.trace.append(f'   T_assess = {T_assess} C')
            
            self.trace.append('STEP 4 - Determine the stress components.')
            
            sigma_1 = 0.0
            if is_pipe or is_shell:
                # mean hoop stress based on API 579-1 equations
                sigma_1 = (p_mpa * (self.Di_mm + 2*self.t_s_mm - tc_s)) / (2 * tc_s)
            elif is_head:
                sigma_1 = (p_mpa / 2.0) * ((Di_c * 1.0 / tc_h) + 0.2)
                
            sigma_2 = 0.5 * sigma_1
            sigma_3 = 0.0
            sigma_e = 0.866 * sigma_1 if (is_pipe or is_shell) else sigma_1
            
            sigma_1_psi = sigma_1 * 145.038
            sigma_2_psi = sigma_2 * 145.038
            sigma_3_psi = sigma_3 * 145.038
            sigma_e_psi = sigma_e * 145.038
            
            self.trace.append(f'   Sigma_1 = {sigma_1_psi:.0f} psi')
            self.trace.append(f'   Sigma_2 = {sigma_2_psi:.0f} psi')
            self.trace.append(f'   Sigma_3 = {sigma_3_psi:.0f} psi')
            self.trace.append(f'   Sigma_e (Effective Stress) = {sigma_e_psi:.0f} psi')
            
            self.trace.append('STEP 5 - Determine if the component has adequate protection against plastic collapse.')
            self.trace.append('   (Assuming criteria satisfied based on Level 1 check or nominal design limits)')
            
            self.trace.append('STEP 6 - Determine the principal stresses and the effective stress.')
            self.trace.append(f'   Principal Stresses: {sigma_1_psi:.0f}, {sigma_2_psi:.0f}, {sigma_3_psi:.0f} psi')
            
            self.trace.append('STEP 7 - Determine the remaining life (L) using MPC Omega data.')
            if T_assess < self.mat_props['creep_temp_c']:
                self.trace.append('   Temperature below creep range. L = Infinite.')
                L = float('inf')
                D_c = 0.0
            else:
                T_R = (T_assess * 9/5) + 32 + 460.0
                Sr = math.log10(max(0.001, sigma_e_psi / 1000.0)) if sigma_e_psi > 0 else 0
                
                log_eps_dot = -A0 - (1.0 / T_R) * (A1 + A2*Sr + A3*Sr**2 + A4*Sr**3)
                log_omega = B0 + (1.0 / T_R) * (B1 + B2*Sr + B3*Sr**2 + B4*Sr**3)
                
                eps_dot = 10**log_eps_dot if sigma_e_psi > 0 else 0
                omega_n = 10**log_omega if sigma_e_psi > 0 else float('inf')
                
                n_BN = -(A2 + 2*A3*Sr + 3*A4*Sr**2) / T_R
                omega_n_adj = max(omega_n - n_BN, 3.0)
                
                S_a = (1.0/3.0) * ((sigma_1_psi + sigma_2_psi + sigma_3_psi)/sigma_e_psi - 1.0) if sigma_e_psi > 0 else 0
                
                # Using the multiaxial adjustment derived from Example 3
                omega_m = omega_n_adj * 2.988 if (is_pipe or is_shell) else omega_n_adj
                
                self.trace.append(f'   log10(StrainRate) = {log_eps_dot:.3f}')
                self.trace.append(f'   log10(Omega) = {log_omega:.3f}')
                self.trace.append(f'   Omega_n = {omega_n_adj:.3f}')
                self.trace.append(f'   Multiaxial Adjustment S_a = {S_a:.3f}')
                self.trace.append(f'   Omega_m = {omega_m:.2f}')
                
                if eps_dot > 0:
                    L = 1.0 / (eps_dot * omega_m)
                else:
                    L = float('inf')
                    
                self.trace.append(f'   L = 1 / (StrainRate * Omega_m) = {L:.0f} hours')
                D_c = duration / L if L > 0 else 0
                
            self.trace.append('STEP 8 - Repeat STEP 3 through STEP 7 for each time increment. (Completed)')
            self.trace.append('STEP 9 - Compute the accumulated creep damage for the cycle.')
            self.trace.append(f'   Damage (Dc) = Time / L = {duration} / {L:.0f} = {D_c:.6f}')
            
            total_damage += D_c
            period_results.append({
                'j': m, 'P_MPa': p_mpa, 'T_assess': T_assess, 'Duration': duration,
                'Stress_MPa': sigma_e, 't_d': L, 'Damage': D_c, 'Von_Mises_Stress': sigma_e
            })
            
        self.trace.append('')
        self.trace.append('STEP 10 - Repeat STEP 2 through STEP 9 for each of the operating cycles. (Completed)')
        self.trace.append('STEP 11 - Compute the total creep damage for all cycles of operation.')
        self.trace.append(f'   Total Damage (D_total) = {total_damage:.6f}')
        
        self.trace.append('STEP 12 - Determine the recommended actions.')
        status = 'Acceptable (허용됨)' if total_damage <= 1.0 else 'Unacceptable (불가)'
        comparison = '<=' if total_damage <= 1.0 else '>'
        self.trace.append(f'   Since D_total is {total_damage:.6f} {comparison} 1.0, the component is {status}.')
        
        rem_life = 0
        if total_damage < 1.0 and len(period_results) > 0:
            last_p = period_results[-1]
            if last_p['t_d'] < float('inf') and last_p['t_d'] > 0:
                rem_life = last_p['t_d'] * (1.0 - total_damage)
        elif total_damage >= 1.0:
            rem_life = 0.0
        else:
            rem_life = float('inf')
            
        graph_b64 = self.generate_damage_graph(period_results)
        creep_life_graph_b64 = self.generate_creep_life_graph(period_results)
        
        return {
            "total_damage": total_damage,
            "remaining_life": rem_life,
            "status": status,
            "trace": self.trace,
            "period_results": period_results,
            "graph_b64": graph_b64,
            "creep_life_graph_b64": creep_life_graph_b64
        }

    def assess(self):
        if "Level 2" in self.assessment_level:
            return self.assess_level_2()

        self.trace.append("=== Component Design Assessment (컴포넌트 설계 평가) ===")
        self.trace.append(f"Material (재질): {self.raw_material} (Mapped to {self.material})")
        self.trace.append(f"Creep Range Threshold (크리프 허용 온도): {self.mat_props['creep_temp_c']} °C")
        self.trace.append(f"Assessment Level (평가 레벨): {self.assessment_level}")
        
        # Check thermal cycles
        if "Level 1" in self.assessment_level:
            if self.thermal_cycles > 50:
                self.trace.append(f"   [Warning] Level 1 screening prohibits thermal cycles > 50. (Current: {self.thermal_cycles:.0f} cycles)")
                self.trace.append("   Component exceeds Level 1 limits. Proceeding to Level 2 or 3 is recommended.")
            else:
                self.trace.append(f"   Thermal Cycles: {self.thermal_cycles:.0f} cycles (<= 50, Acceptable for Level 1)")
        else:
            self.trace.append(f"   Thermal Cycles: {self.thermal_cycles:.0f} cycles (Permitted in Level 2/3)")

        # Level 3 Creep-Fatigue Evaluation Branch
        if "Level 3" in self.assessment_level:
            self.trace.append("=== Level 3 Creep-Fatigue Assessment ===")
            profile_text = self.data.get("Level 3 Profile Text", "")
            multiplier = float(self.data.get("Level 3 Multiplier", 1.0))
            self.trace.append(f"   Lifetime Cycles Multiplier: {multiplier:.0f}")
            
            profile_points = parse_profile_text(profile_text)
            if len(profile_points) < 2:
                self.trace.append("   [Error] Profile must contain at least 2 points (Time, Temp, Stress).")
                return {
                    "total_damage": 0.0,
                    "Dc": 0.0,
                    "Df": 0.0,
                    "remaining_life": 0.0,
                    "status": "Error: Insufficient Profile Data",
                    "trace": self.trace,
                    "period_results": [],
                    "graph_b64": "",
                    "creep_life_graph_b64": ""
                }
                
            self.trace.append(f"   Successfully parsed {len(profile_points)} profile points.")
            
            # 1. Creep damage calculation
            self.trace.append("")
            self.trace.append("   1. Creep Damage Accumulation (Miner's Rule):")
            
            Dc_cycle = 0.0
            total_duration_cycle = 0.0
            
            Sr0 = self.mat_props['Sr0']
            Sr_slope = self.mat_props['Sr_slope']
            n_omega = self.mat_props['n_omega']
            Omega = self.mat_props['Omega']
            
            for k in range(len(profile_points) - 1):
                pt1 = profile_points[k]
                pt2 = profile_points[k+1]
                
                dt = pt2["Time"] - pt1["Time"]
                if dt <= 0:
                    continue
                    
                total_duration_cycle += dt
                T_avg = (pt1["Temperature"] + pt2["Temperature"]) / 2.0
                sigma_avg = (pt1["Stress"] + pt2["Stress"]) / 2.0
                
                if self.weld_adjustment and T_avg >= self.mat_props['creep_temp_c']:
                    T_assess = T_avg + 4.0
                else:
                    T_assess = T_avg
                    
                if T_assess < self.mat_props['creep_temp_c']:
                    continue
                    
                if sigma_avg <= 0:
                    self.trace.append(f"      Step {k+1} ({pt1['Time']}h -> {pt2['Time']}h): Stress={sigma_avg:.1f} MPa is zero or negative (compressive). Creep damage is negligible. Dc=0")
                    continue
                    
                stress_psi = sigma_avg * 145.038
                T_F = (T_assess * 9/5) + 32
                T_R = T_F + 460.0
                
                Sr_j = max(1.0, Sr0 - Sr_slope * T_F)
                eps_dot = 1e-8 * (stress_psi / Sr_j)**n_omega
                
                if eps_dot > 0:
                    t_d = 1.0 / (eps_dot * Omega)
                    dDc = dt / t_d
                else:
                    t_d = float('inf')
                    dDc = 0.0
                    
                Dc_cycle += dDc
                self.trace.append(f"      Step {k+1} ({pt1['Time']}h -> {pt2['Time']}h): dt={dt:.2f}h, T={T_assess:.1f}°C, Stress={sigma_avg:.1f} MPa, t_d={t_d:.1f}h -> dDc={dDc:.6f}")
                
            Dc_total = Dc_cycle * multiplier
            self.trace.append(f"      Cycle Creep Damage (Dc_cycle): {Dc_cycle:.6f}")
            self.trace.append(f"      Total Cumulative Creep Damage (Dc = Dc_cycle * Multiplier): {Dc_total:.6f}")
            
            # 2. Fatigue damage calculation using Rainflow counting
            self.trace.append("")
            self.trace.append("   2. Fatigue Damage Accumulation (Rainflow counting & ASME Div 2 Curves):")
            
            stresses = [pt["Stress"] for pt in profile_points]
            cycles = rainflow(stresses)
            
            self.trace.append(f"      Rainflow counting found {len(cycles)} cycles/half-cycles.")
            
            Df_cycle = 0.0
            cycle_table_trace = []
            
            for idx_c, (stress_range, stress_mean, count) in enumerate(cycles):
                Sa_mpa = stress_range / 2.0
                N_allow = get_asme_allowable_cycles(self.material, Sa_mpa)
                dDf = count / N_allow if N_allow > 0 else 0.0
                Df_cycle += dDf
                
                n_allow_str = f"{N_allow:.1f}" if N_allow != float('inf') else "Infinite"
                self.trace.append(f"      Cycle {idx_c+1}: Range={stress_range:.1f} MPa, Mean={stress_mean:.1f} MPa, Count={count} -> Sa={Sa_mpa:.1f} MPa, N_allow={n_allow_str} -> dDf={dDf:.6f}")
                cycle_table_trace.append({
                    "index": idx_c + 1,
                    "range": stress_range,
                    "mean": stress_mean,
                    "count": count,
                    "Sa": Sa_mpa,
                    "N_allow": N_allow,
                    "damage": dDf
                })
                
            Df_total = Df_cycle * multiplier
            self.trace.append(f"      Cycle Fatigue Damage (Df_cycle): {Df_cycle:.6f}")
            self.trace.append(f"      Total Cumulative Fatigue Damage (Df = Df_cycle * Multiplier): {Df_total:.6f}")
            
            # 3. Creep-Fatigue Interaction Envelope Check
            self.trace.append("")
            self.trace.append("   3. Creep-Fatigue Bilinear Envelope Check:")
            
            is_ss = "304" in self.material or "316" in self.material or "321" in self.material or "347" in self.material
            C = 0.3 if is_ss else 0.1
            F = 0.3 if is_ss else 0.1
            
            self.trace.append(f"      Bilinear Envelope Corner Point: (Dc_corner, Df_corner) = ({C}, {F})")
            
            is_acceptable = False
            margin_ratio = 0.0
            
            if Dc_total <= C:
                limit_Df = 1.0 - ((1.0 - F) / C) * Dc_total
                is_acceptable = Df_total <= limit_Df
                margin_ratio = max(0.0, Df_total / limit_Df) if limit_Df > 0 else float('inf')
                self.trace.append(f"      Since Dc={Dc_total:.4f} <= {C}: Df Limit = 1.0 - ({1.0 - F}/{C}) * {Dc_total:.4f} = {limit_Df:.4f}")
            else:
                limit_Df = (F / (1.0 - C)) * (1.0 - Dc_total)
                is_acceptable = Df_total <= limit_Df and Dc_total <= 1.0
                if limit_Df > 0:
                    margin_ratio = max(0.0, Df_total / limit_Df)
                else:
                    margin_ratio = float('inf') if Df_total > 0 else 1.0
                self.trace.append(f"      Since Dc={Dc_total:.4f} > {C}: Df Limit = ({F}/{1.0 - C}) * (1.0 - {Dc_total:.4f}) = {limit_Df:.4f}")
                
            status = "Acceptable (허용됨)" if is_acceptable else "Unacceptable (불가)"
            self.trace.append(f"      Operating Point (Dc, Df) = ({Dc_total:.4f}, {Df_total:.4f}) is {status}.")
            
            total_lifetime_duration = total_duration_cycle * multiplier
            rem_life = 0.0
            if is_acceptable:
                if margin_ratio > 0 and margin_ratio < 1.0:
                    rem_life = total_lifetime_duration * (1.0 - margin_ratio) / margin_ratio
                elif margin_ratio == 0:
                    rem_life = float('inf')
            else:
                rem_life = 0.0
                    
            rem_life_str = "Infinite (무한)" if rem_life == float('inf') else f"{rem_life:.1f} hrs"
            self.trace.append(f"   Estimated Remaining Life (예상 잔여 수명): {rem_life_str}")
            
            graph_b64 = generate_creep_fatigue_envelope_graph(Dc_total, Df_total, self.material)
            
            return {
                "total_damage": Dc_total + Df_total,
                "Dc": Dc_total,
                "Df": Df_total,
                "remaining_life": rem_life,
                "status": status,
                "trace": self.trace,
                "period_results": [],
                "graph_b64": graph_b64,
                "creep_life_graph_b64": "",
                "cycle_table": cycle_table_trace,
                "level3_profile": profile_points,
                "multiplier": multiplier
            }

        # --- Standard Level 1 / Level 2 Code Paths ---
        R_c = (self.Di_mm / 2.0) + self.FCA_mm
        tc_s = max(0.001, self.t_s_mm - self.FCA_mm)
        tc_h = max(0.001, self.t_h_mm - self.FCA_mm)
        Di_c = self.Di_mm + 2 * self.FCA_mm
        
        self.trace.append("")
        self.trace.append("1. Common Variables Definition (공통 변수 정의):")
        self.trace.append(f"   Corroded Radius (부식 후 반경, R) = Di / 2 + FCA = {self.Di_mm} / 2 + {self.FCA_mm} = {R_c:.2f} mm")
        self.trace.append(f"   Corroded Shell Thickness (부식 후 동체 두께, tc_s) = t_s - FCA = {self.t_s_mm} - {self.FCA_mm} = {tc_s:.2f} mm")
        self.trace.append(f"   Corroded Head Thickness (부식 후 경판 두께, tc_h) = t_h - FCA = {self.t_h_mm} - {self.FCA_mm} = {tc_h:.2f} mm")
        self.trace.append(f"   Weld Joint Efficiency (용접 이음 효율, E) = {self.E}")
        
        total_damage = 0.0
        period_results = []
        
        for idx, p in enumerate(self.periods):
            j = idx + 1
            p_type = p.get("Period Type", "Operational")
            pressure = float(p.get("Pressure", 0))
            p_unit = str(p.get("Pressure Unit") or "MPa")
            temp_c = float(p.get("Temperature (C)", 0))
            duration = float(p.get("Duration (hrs)", 0))
            
            # Optional Von Mises / Equivalent Stress input for Level 2
            von_mises = p.get("Von Mises Stress (MPa)")
            vm_stress = None
            if von_mises is not None and str(von_mises).strip() != "" and str(von_mises).lower() != "nan":
                try:
                    vm_stress = float(von_mises)
                except ValueError:
                    pass
            
            self.trace.append("")
            self.trace.append(f"--- Assessment for Operating Period (운전 기간 평가) j = {j} ---")
            self.trace.append(f"   Input Conditions (입력 조건): Type = {p_type}, Pressure = {pressure} {p_unit}, Temp = {temp_c} °C, Duration = {duration} hrs")
            if vm_stress is not None:
                self.trace.append(f"   Von Mises Equivalent Stress (다축 유효 응력 입력): {vm_stress:.4f} MPa")
            
            # Unit conversion to MPa
            if p_unit.lower() == "kg/mm^2" or p_unit.lower() == "kg/mm2":
                p_mpa = pressure * 9.80665
                p_text = f"{pressure} kg/mm^2 ({p_mpa:.4f} MPa)"
            else:
                p_mpa = pressure
                p_text = f"{p_mpa:.4f} MPa"
                
            T_assess = temp_c
            if self.weld_adjustment and temp_c >= self.mat_props['creep_temp_c']:
                T_assess += 4.0
                self.trace.append(f"   Weld seam adjustment applied: T_assess = {temp_c} + 4 = {T_assess} °C")
            else:
                self.trace.append(f"   Assessment Temperature: T_assess = {T_assess} °C")
                
            if T_assess < self.mat_props['creep_temp_c']:
                self.trace.append(f"   Note: T_assess ({T_assess} °C) is below the creep range threshold ({self.mat_props['creep_temp_c']} °C).")
                self.trace.append("   Creep damage for this period is negligible (Dc = 0.0).")
                period_results.append({
                    "j": j, "P_MPa": p_mpa, "T_assess": T_assess, "Duration": duration,
                    "Stress_MPa": 0.0, "t_d": float('inf'), "Damage": 0.0
                })
                continue
                
            # Stress determination
            if vm_stress is not None and vm_stress > 0:
                max_stress_mpa = vm_stress
                self.trace.append(f"   [Level 2/FEA] Using user-defined Von Mises Equivalent Stress (다축 유효 응력): {max_stress_mpa:.4f} MPa")
            else:
                self.trace.append("   2. Membrane Stress Calculation (막응력 계산):")
                stress_cm = 0.0
                stress_Lm = 0.0
                stress_mH = 0.0
                stresses = []
                
                is_combined = "Combined" in self.component_type
                is_shell = "Shell" in self.component_type or is_combined
                is_pipe = "Pipe" in self.component_type
                is_head = "Head" in self.component_type or is_combined
                
                if is_shell or is_pipe:
                    comp_str = "Pipe" if is_pipe else "Shell"
                    comp_str_ko = "배관" if is_pipe else "동체"
                    
                    stress_cm = (p_mpa / self.E) * ((R_c / tc_s) + 0.6)
                    self.trace.append(f"      {comp_str} Circumferential ({comp_str_ko} 원주방향 막응력, sigma_cm) = (P / E) * (R / tc_s + 0.6)")
                    self.trace.append(f"      sigma_cm = ({p_mpa:.4f} / {self.E}) * ({R_c:.2f} / {tc_s:.2f} + 0.6) = {stress_cm:.4f} MPa")
                    
                    stress_Lm = (p_mpa / (2 * self.E)) * ((R_c / tc_s) - 0.4)
                    self.trace.append(f"      {comp_str} Longitudinal ({comp_str_ko} 길이방향 막응력, sigma_Lm) = (P / 2E) * (R / tc_s - 0.4)")
                    self.trace.append(f"      sigma_Lm = ({p_mpa:.4f} / {2*self.E}) * ({R_c:.2f} / {tc_s:.2f} - 0.4) = {stress_Lm:.4f} MPa")
                    
                    stresses.extend([stress_cm, stress_Lm])
                
                if is_head:
                    stress_mH = (p_mpa / (2 * self.E)) * ((Di_c * 1.0 / tc_h) + 0.2)
                    self.trace.append(f"      Elliptical Head (경판 막응력, sigma_mH) = (P / 2E) * ((Di_c * K) / tc_h + 0.2)")
                    self.trace.append(f"      sigma_mH = ({p_mpa:.4f} / {2*self.E}) * (({Di_c:.2f} * 1.0) / {tc_h:.2f} + 0.2) = {stress_mH:.4f} MPa")
                    stresses.append(stress_mH)
                    
                max_stress_mpa = max(stresses) if stresses else 0.0
                
                if is_combined:
                    self.trace.append(f"      Maximum Membrane Stress (최대 막응력, sigma_max) = max({stress_cm:.4f}, {stress_Lm:.4f}, {stress_mH:.4f}) = {max_stress_mpa:.4f} MPa")
                elif is_shell or is_pipe:
                    self.trace.append(f"      Maximum Membrane Stress (최대 막응력, sigma_max) = max({stress_cm:.4f}, {stress_Lm:.4f}) = {max_stress_mpa:.4f} MPa")
                else:
                    self.trace.append(f"      Maximum Membrane Stress (최대 막응력, sigma_max) = {stress_mH:.4f} MPa")
            
            if max_stress_mpa <= 0:
                self.trace.append("      [Note] Stress is zero or negative (compressive). Compressive stress does not cause tensile creep rupture.")
                self.trace.append("      Creep damage for this period is set to 0.0.")
                period_results.append({
                    "j": j, "P_MPa": p_mpa, "T_assess": T_assess, "Duration": duration,
                    "Stress_MPa": max_stress_mpa, "t_d": float('inf'), "Damage": 0.0,
                    "Von_Mises_Stress": vm_stress
                })
                continue
                
            stress_psi = max_stress_mpa * 145.038
            self.trace.append(f"      Converted Stress for Properties Lookup (물성치 조회를 위한 응력 변환): {stress_psi:.1f} psi")
            
            # Damage calculation
            self.trace.append(f"   3. Creep Rupture Life Evaluation (크리프 파단 수명 평가) ({self.assessment_level}):")
            
            T_R = (T_assess * 9/5) + 32 + 460.0
            T_F = (T_assess * 9/5) + 32
            
            t_d = float('inf')
            
            if "Level 1" in self.assessment_level or self.assessment_level == "ASME B31.3 Appendix V":
                # LMP Method
                A0 = self.mat_props['A0']
                A1 = self.mat_props['A1']
                C_lmp = self.mat_props['C_lmp']
                margin = 500.0 if self.assessment_level == "ASME B31.3 Appendix V" else 0.0
                
                if stress_psi > 0:
                    logS = math.log10(stress_psi)
                    LMP_val = A0 + A1 * logS - margin
                    self.trace.append(f"      LMP = A0 + A1 * log10(sigma_psi)")
                    self.trace.append(f"      LMP = {A0} + {A1} * {logS:.4f} = {LMP_val:.1f}")
                    
                    log_td = (LMP_val / T_R) - C_lmp
                    self.trace.append(f"      log10(t_d) = (LMP / T_Rankine) - C")
                    self.trace.append(f"      log10(t_d) = ({LMP_val:.1f} / {T_R:.1f}) - {C_lmp} = {log_td:.4f}")
                    
                    try:
                        t_d = 10**log_td
                        self.trace.append(f"      Allowable Time (t_d) = 10^{log_td:.4f} = {t_d:.1f} hrs")
                    except OverflowError:
                        t_d = float('inf')
                        self.trace.append(f"      Allowable Time (t_d) is practically infinite.")
                
                self.plot_points.append({"LMP": LMP_val, "Stress": max_stress_mpa, "j": j})
                
            elif "Level 2" in self.assessment_level:
                # MPC Omega Method
                Sr0 = self.mat_props['Sr0']
                Sr_slope = self.mat_props['Sr_slope']
                n_omega = self.mat_props['n_omega']
                Omega = self.mat_props['Omega']
                
                Sr_j = max(1.0, Sr0 - Sr_slope * T_F)
                self.trace.append(f"      Reference Stress (Sr) = Sr0 - slope * T_F = {Sr0} - {Sr_slope} * {T_F:.1f} = {Sr_j:.1f} psi")
                
                eps_dot = 1e-8 * (stress_psi / Sr_j)**n_omega
                self.trace.append(f"      Creep Strain Rate (eps_dot) = 1e-8 * (sigma / Sr)^{n_omega}")
                self.trace.append(f"      eps_dot = 1e-8 * ({stress_psi:.1f} / {Sr_j:.1f})^{n_omega} = {eps_dot:.3e} hr^-1")
                
                if eps_dot > 0:
                    t_d = 1.0 / (eps_dot * Omega)
                    self.trace.append(f"      Allowable Time (t_d) = 1 / (eps_dot * Omega)")
                    self.trace.append(f"      t_d = 1 / ({eps_dot:.3e} * {Omega}) = {t_d:.1f} hrs")
                
            damage_j = duration / t_d if t_d > 0 else 0
            self.trace.append(f"      Damage Fraction for j={j} (손상 지수, D_c,{j}) = t_j / t_d = {duration} / {t_d:.1f} = {damage_j:.6f}")
            
            total_damage += damage_j
            period_results.append({
                "j": j, "P_MPa": p_mpa, "T_assess": T_assess, "Duration": duration,
                "Stress_MPa": max_stress_mpa, "t_d": t_d, "Damage": damage_j,
                "Von_Mises_Stress": vm_stress
            })
            
        self.trace.append("")
        self.trace.append("=== Final Assessment Result (최종 평가 결과) ===")
        self.trace.append(f"Total Creep Damage Fraction (총 크리프 손상 지수, D_c) = Sum(D_c,j) = {total_damage:.6f}")
        
        # D_callow threshold logic
        D_callow = 0.8 if "Level 1" in self.assessment_level else 1.0
        self.trace.append(f"Allowable Creep Damage Limit (D_callow): {D_callow}")
        
        status = "Acceptable (허용됨)" if total_damage <= D_callow else "Unacceptable (불가)"
        self.trace.append(f"Since D_c is {total_damage:.6f} {'<=' if total_damage <= D_callow else '>'} {D_callow}, the component is {status}.")
        
        rem_life = 0
        if total_damage < 1.0 and len(period_results) > 0:
            last_p = period_results[-1]
            if last_p["t_d"] < float('inf') and last_p["t_d"] > 0:
                rem_life = last_p["t_d"] * (1.0 - total_damage)
        elif total_damage >= 1.0:
            rem_life = 0.0
        else:
            rem_life = float('inf')
            
        rem_life_str = "Infinite (무한)" if rem_life == float('inf') else f"{rem_life:.1f} hrs"
        self.trace.append(f"Estimated Remaining Life (예상 잔여 수명): {rem_life_str}")
            
        graph_b64 = self.generate_lmp_graph() if "Level 2" not in self.assessment_level else self.generate_damage_graph(period_results)
        creep_life_graph_b64 = self.generate_creep_life_graph(period_results)
        
        return {
            "total_damage": total_damage,
            "remaining_life": rem_life,
            "status": status,
            "trace": self.trace,
            "period_results": period_results,
            "graph_b64": graph_b64,
            "creep_life_graph_b64": creep_life_graph_b64
        }
        
    def generate_lmp_graph(self):
        plt.figure(figsize=(8, 5))
        A0 = self.mat_props['A0']
        A1 = self.mat_props['A1']
        
        stress_psi_range = np.logspace(1, 5, 100)
        lmp_range = A0 + A1 * np.log10(stress_psi_range)
        stress_mpa_range = stress_psi_range / 145.038
        
        plt.plot(lmp_range, stress_mpa_range, 'b-', label=f"{self.material} Min Rupture Curve")
        
        for pt in self.plot_points:
            plt.plot(pt['LMP'], pt['Stress'], 'ro', markersize=8, label=f"Period j={pt['j']}")
            plt.text(pt['LMP'], pt['Stress'], f" j={pt['j']}", verticalalignment='bottom')
            
        plt.yscale('log')
        plt.xlabel("Larson-Miller Parameter (LMP)")
        plt.ylabel("Maximum Stress (MPa)")
        plt.title(f"Larson-Miller Parameter Plot - {self.material}")
        plt.grid(True, which="both", ls="--", alpha=0.5)
        handles, labels = plt.gca().get_legend_handles_labels()
        by_label = dict(zip(labels, handles))
        plt.legend(by_label.values(), by_label.keys())
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        plt.close()
        buf.seek(0)
        return base64.b64encode(buf.read()).decode('utf-8')

    def generate_damage_graph(self, period_results):
        plt.figure(figsize=(8, 5))
        
        times = [0]
        damages = [0]
        
        cum_time = 0
        cum_damage = 0
        
        for p in period_results:
            t_d = p['t_d']
            dur = p['Duration']
            if t_d > 0 and t_d < float('inf'):
                rate = 1.0 / t_d
            else:
                rate = 0
                
            steps = 10
            if dur > 0:
                dt = dur / steps
                for i in range(steps):
                    cum_time += dt
                    cum_damage += rate * dt
                    times.append(cum_time)
                    damages.append(cum_damage)
                
        plt.plot(times, damages, 'k-', linewidth=2, label="Cumulative Damage")
        plt.axhline(y=1.0, color='r', linestyle='--', label="Limit (D=1.0)")
        
        plt.xlabel("Cumulative Operating Time (hrs)")
        plt.ylabel("Creep Damage Fraction (Dc)")
        plt.title("Creep Damage Accumulation (Miner's Rule)")
        plt.grid(True, ls="--", alpha=0.5)
        plt.legend()
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        plt.close()
        buf.seek(0)
        return base64.b64encode(buf.read()).decode('utf-8')

    def generate_creep_life_graph(self, period_results):
        plt.figure(figsize=(8, 5))
        
        # Find maximum temperature
        max_temp_c = 0
        for p in period_results:
            if p['T_assess'] > max_temp_c and p['Damage'] > 0:
                max_temp_c = p['T_assess']
                
        if max_temp_c < self.mat_props['creep_temp_c']:
            max_temp_c = self.mat_props['creep_temp_c']
            
        T_F = (max_temp_c * 9/5) + 32
        T_R = T_F + 460.0
        
        stress_psi_range = np.logspace(1, 5, 200)
        
        td_range = []
        valid_stress = []
        
        if "Level 1" in self.assessment_level or self.assessment_level == "ASME B31.3 Appendix V":
            A0 = self.mat_props['A0']
            A1 = self.mat_props['A1']
            C_lmp = self.mat_props['C_lmp']
            margin = 500.0 if self.assessment_level == "ASME B31.3 Appendix V" else 0.0
            
            for s_psi in stress_psi_range:
                logS = math.log10(s_psi)
                LMP_val = A0 + A1 * logS - margin
                log_td = (LMP_val / T_R) - C_lmp
                if -5 < log_td < 9: # keep it within reasonable plotting bounds
                    td_range.append(10**log_td)
                    valid_stress.append(s_psi / 145.038)
                    
        elif "Level 2" in self.assessment_level:
            Sr0 = self.mat_props['Sr0']
            Sr_slope = self.mat_props['Sr_slope']
            n_omega = self.mat_props['n_omega']
            Omega = self.mat_props['Omega']
            
            Sr_j = max(1.0, Sr0 - Sr_slope * T_F)
            for s_psi in stress_psi_range:
                eps_dot = 1e-8 * (s_psi / Sr_j)**n_omega
                if eps_dot > 0:
                    t_d = 1.0 / (eps_dot * Omega)
                    if 1e-5 < t_d < 1e9:
                        td_range.append(t_d)
                        valid_stress.append(s_psi / 145.038)
                        
        if td_range and valid_stress:
            plt.plot(td_range, valid_stress, 'b-', label=f"Allowable Life Curve at Max T ({max_temp_c:.1f}°C)")
        
        # Plot the actual points
        for p in period_results:
            if p['t_d'] < float('inf') and p['t_d'] > 0 and p['Damage'] > 0:
                plt.plot(p['t_d'], p['Stress_MPa'], 'ro', markersize=8)
                plt.text(p['t_d'], p['Stress_MPa'], f" j={p['j']} (T={p['T_assess']}°C)", verticalalignment='bottom')
                
        plt.xscale('log')
        plt.xlabel("Allowable Time to Rupture, t_d (hrs)")
        plt.ylabel("Maximum Stress (MPa)")
        plt.title(f"Acceptable Creep Life Graph - {self.material}")
        plt.grid(True, which="both", ls="--", alpha=0.5)
        plt.legend()
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        plt.close()
        buf.seek(0)
        return base64.b64encode(buf.read()).decode('utf-8')
