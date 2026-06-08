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
        
        self.trace = []  # Step-by-step plain-text explanations
        self.plot_points = []
        
    def assess(self):
        self.trace.append("=== Component Design Assessment (컴포넌트 설계 평가) ===")
        self.trace.append(f"Material (재질): {self.raw_material} (Mapped to {self.material})")
        self.trace.append(f"Creep Range Threshold (크리프 허용 온도): {self.mat_props['creep_temp_c']} °C")
        
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
            
            self.trace.append("")
            self.trace.append(f"--- Assessment for Operating Period (운전 기간 평가) j = {j} ---")
            self.trace.append(f"   Input Conditions (입력 조건): Type = {p_type}, Pressure = {pressure} {p_unit}, Temp = {temp_c} °C, Duration = {duration} hrs")
            
            # Unit conversion to MPa
            if p_unit.lower() == "kg/mm^2" or p_unit.lower() == "kg/mm2":
                p_mpa = pressure * 9.80665
                p_text = f"{pressure} kg/mm^2 ({p_mpa:.4f} MPa)"
            else:
                p_mpa = pressure
                p_text = f"{p_mpa:.4f} MPa"
                
            # Temperature adjustment
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
                
                # Shell circumferential
                stress_cm = (p_mpa / self.E) * ((R_c / tc_s) + 0.6)
                self.trace.append(f"      {comp_str} Circumferential ({comp_str_ko} 원주방향 막응력, sigma_cm) = (P / E) * (R / tc_s + 0.6)")
                self.trace.append(f"      sigma_cm = ({p_mpa:.4f} / {self.E}) * ({R_c:.2f} / {tc_s:.2f} + 0.6) = {stress_cm:.4f} MPa")
                
                # Shell longitudinal
                stress_Lm = (p_mpa / (2 * self.E)) * ((R_c / tc_s) - 0.4)
                self.trace.append(f"      {comp_str} Longitudinal ({comp_str_ko} 길이방향 막응력, sigma_Lm) = (P / 2E) * (R / tc_s - 0.4)")
                self.trace.append(f"      sigma_Lm = ({p_mpa:.4f} / {2*self.E}) * ({R_c:.2f} / {tc_s:.2f} - 0.4) = {stress_Lm:.4f} MPa")
                
                stresses.extend([stress_cm, stress_Lm])
            
            if is_head:
                # Head stress (K=1 for 2:1 elliptical)
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
                
                # If B31.3, apply a safety margin (e.g. subtract 500 from LMP)
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
                "Stress_MPa": max_stress_mpa, "t_d": t_d, "Damage": damage_j
            })
            
        self.trace.append("")
        self.trace.append("=== Final Assessment Result (최종 평가 결과) ===")
        self.trace.append(f"Total Creep Damage Fraction (총 크리프 손상 지수, D_c) = Sum(D_c,j) = {total_damage:.6f}")
        
        status = "Acceptable (허용됨)" if total_damage <= 1.0 else "Unacceptable (불가)"
        self.trace.append(f"Since D_c is {total_damage:.6f} {'<=' if total_damage <= 1.0 else '>'} 1.0, the component is {status}.")
        
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
