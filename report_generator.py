import jinja2
import datetime

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>API 579-1 Creep Assessment Report</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 40px; color: #333; line-height: 1.6; }
        .header { text-align: center; border-bottom: 2px solid #0056b3; padding-bottom: 20px; margin-bottom: 30px; }
        .header h1 { color: #0056b3; margin: 0; font-size: 28px; }
        .header p { color: #777; margin: 5px 0 0 0; }
        .section { margin-bottom: 40px; }
        .section-title { font-size: 20px; color: #0056b3; border-bottom: 1px solid #ccc; padding-bottom: 5px; margin-bottom: 15px; }
        .data-table { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
        .data-table th, .data-table td { padding: 10px; border: 1px solid #ddd; text-align: left; }
        .data-table th { background-color: #f4f7f6; width: 30%; font-weight: 600; }
        .period-table th { background-color: #e9ecef; }
        .math-trace { background-color: #f8f9fa; padding: 20px; border-left: 4px solid #0056b3; font-family: 'Courier New', Courier, monospace; overflow-x: auto; margin-bottom: 10px; font-size: 14px; white-space: pre-wrap; }
        .result-box { padding: 20px; background-color: #e9ecef; border-radius: 5px; font-size: 18px; margin-top: 20px; font-weight: bold; }
        .status-pass { color: #28a745; }
        .status-fail { color: #dc3545; }
        .footer { text-align: center; margin-top: 50px; font-size: 12px; color: #aaa; border-top: 1px solid #eee; padding-top: 20px; }
    </style>
</head>
<body>

    <div class="header">
        <h1>Fitness-For-Service Assessment Report</h1>
        <p>API 579-1 / ASME FFS-1 Part 10: Assessment of Components Operating in the Creep Range</p>
        <p>Generated on: {{ date }}</p>
    </div>

    <div class="section">
        <div class="section-title">1. Component Design Data (설계 데이터)</div>
        <table class="data-table">
            <tr><th>Component Type (컴포넌트 유형)</th><td>{{ comp_type }}</td></tr>
            <tr><th>Assessment Level (평가 레벨)</th><td>{{ level }}</td></tr>
            <tr><th>Material (재질)</th><td>{{ material }}</td></tr>
            <tr><th>Inside Diameter / 내경 (mm)</th><td>{{ diameter }}</td></tr>
            {% if "Head" not in comp_type %}
            <tr><th>Shell/Pipe Thickness / 동체/배관 두께 (mm)</th><td>{{ thickness_shell }}</td></tr>
            {% endif %}
            {% if "Shell" not in comp_type and "Pipe" not in comp_type %}
            <tr><th>Head Thickness / 경판 두께 (mm)</th><td>{{ thickness_head }}</td></tr>
            {% endif %}
            <tr><th>Future Corrosion Allowance / 부식 여유 (mm)</th><td>{{ fca }}</td></tr>
            <tr><th>Weld Joint Efficiency / 용접 효율 (E)</th><td>{{ weld_eff }}</td></tr>
            <tr><th>Weld Seam Temp Adj. / 용접부 온도 보정</th><td>{{ "Yes (+4&deg;C)" if weld_adj else "No" }}</td></tr>
            <tr><th>Thermal Cycles / 열 반복 횟수</th><td>{{ thermal_cycles }}</td></tr>
            {% if "Level 3" in level %}
            <tr><th>Lifetime Cycles Multiplier / 수명 반복 배수</th><td>{{ multiplier }}</td></tr>
            {% endif %}
        </table>
    </div>

    {% if "Level 3" in level %}
    <div class="section">
        <div class="section-title">2. Time-Temperature-Stress Profile (Level 3 입력 데이터)</div>
        <table class="data-table period-table">
            <thead>
                <tr>
                    <th>Point Index</th>
                    <th>Time (hrs)</th>
                    <th>Temperature (&deg;C)</th>
                    <th>Stress (MPa)</th>
                </tr>
            </thead>
            <tbody>
                {% for pt in level3_profile %}
                <tr>
                    <td>{{ loop.index }}</td>
                    <td>{{ "%.1f"|format(pt.Time) }}</td>
                    <td>{{ "%.1f"|format(pt.Temperature) }}</td>
                    <td>{{ "%.1f"|format(pt.Stress) }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    
    {% if cycle_table %}
    <div class="section">
        <div class="section-title">2b. Rainflow Cycle Counting Results (레인플로우 피로 분석)</div>
        <table class="data-table period-table">
            <thead>
                <tr>
                    <th>Cycle Index</th>
                    <th>Stress Range (MPa)</th>
                    <th>Mean Stress (MPa)</th>
                    <th>Count</th>
                    <th>Amplitude S<sub>a</sub> (MPa)</th>
                    <th>Allowable Cycles N</th>
                    <th>Fatigue Damage (dD<sub>f</sub>)</th>
                </tr>
            </thead>
            <tbody>
                {% for c in cycle_table %}
                <tr>
                    <td>{{ c.index }}</td>
                    <td>{{ "%.1f"|format(c.range) }}</td>
                    <td>{{ "%.1f"|format(c.mean) }}</td>
                    <td>{{ "%.1f"|format(c.count) }}</td>
                    <td>{{ "%.1f"|format(c.Sa) }}</td>
                    <td>{{ "%.1f"|format(c.N_allow) if c.N_allow != float('inf') else "Infinite" }}</td>
                    <td>{{ "%.6f"|format(c.damage) }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    {% endif %}

    {% else %}
    <div class="section">
        <div class="section-title">2. Operating Conditions / 운전 기간 (Periods)</div>
        <table class="data-table period-table">
            <thead>
                <tr>
                    <th>Period j</th>
                    <th>Type (운전 유형)</th>
                    <th>Pressure (압력)</th>
                    <th>Unit (단위)</th>
                    <th>Temperature (온도, &deg;C)</th>
                    <th>Duration (기간, hrs)</th>
                    {% if "Level 2" in level %}
                    <th>Von Mises Stress (MPa)</th>
                    {% endif %}
                </tr>
            </thead>
            <tbody>
                {% for p in periods %}
                <tr>
                    <td>{{ loop.index }}</td>
                    <td>{{ p.get('Period Type', 'Operational') }}</td>
                    <td>{{ p.get('Pressure', 0) }}</td>
                    <td>{{ p.get('Pressure Unit', 'MPa') }}</td>
                    <td>{{ p.get('Temperature (C)', 0) }}</td>
                    <td>{{ p.get('Duration (hrs)', 0) }}</td>
                    {% if "Level 2" in level %}
                    <td>{{ "%.1f"|format(p.get('Von Mises Stress (MPa)')) if p.get('Von Mises Stress (MPa)') is not none and p.get('Von Mises Stress (MPa)') >= 0 else "-" }}</td>
                    {% endif %}
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    {% endif %}

    <div class="section">
        <div class="section-title">3. Detailed Calculation Steps (상세 계산 과정)</div>
        <p>The following equations demonstrate the step-by-step calculation. (수식은 알아보기 쉽게 텍스트로 표현됩니다.)</p>
        <div class="math-trace">{% for line in math_trace %}
{{ line }}
{% endfor %}</div>
        <div style="text-align: center; margin-top: 20px;">
            <img src="data:image/png;base64,{{ graph_b64 }}" alt="Assessment Graph" style="max-width: 100%; border: 1px solid #ddd; padding: 10px; border-radius: 4px; margin-bottom: 10px;">
            {% if creep_life_graph_b64 %}
            <br>
            <img src="data:image/png;base64,{{ creep_life_graph_b64 }}" alt="Acceptable Creep Life Graph" style="max-width: 100%; border: 1px solid #ddd; padding: 10px; border-radius: 4px;">
            {% endif %}
        </div>
    </div>

    <div class="section">
        <div class="section-title">4. Final Assessment Result (최종 평가 결과)</div>
        <div class="result-box">
            {% if "Level 3" in level %}
            Cumulative Creep Damage / 누적 크리프 손상 (D<sub>c</sub>): {{ "%.6f"|format(Dc) }}<br>
            Cumulative Fatigue Damage / 누적 피로 손상 (D<sub>f</sub>): {{ "%.6f"|format(Df) }}<br>
            Total Interaction Damage Ratio / 총 상호작용 손상비: {{ "%.6f"|format(total_damage) }}<br>
            {% else %}
            Total Creep Damage Fraction / 총 크리프 손상 지수 (D<sub>c</sub>): {{ "%.6f"|format(total_damage) }}<br>
            {% endif %}
            Estimated Remaining Life / 예상 잔여 수명: {% if remaining_life == float('inf') %}Infinite (무한){% else %}{{ "%.1f"|format(remaining_life) }}{% endif %} hrs<br><br>
            Assessment Status / 평가 결과: <span class="{% if 'Acceptable' in status %}status-pass{% else %}status-fail{% endif %}">{{ status }}</span>
        </div>
    </div>

    <div class="footer">
        Software strictly follows API 579-1 Part 10 guidelines. Please verify calculations against engineering judgement and standard ASME PTB-14 examples.
    </div>

</body>
</html>
"""

def generate_html_report(component_data, result_data):
    template = jinja2.Template(HTML_TEMPLATE)
    
    comp_type = component_data.get('Component Type', 'Combined (동체+경판)')
    level = component_data.get('Assessment Level', 'Level 1')
    material = component_data.get('Material', 'Unknown')
    diameter = component_data.get('Inside Diameter (mm)', 0)
    thickness_shell = component_data.get('Shell Thickness (mm)', 0)
    thickness_head = component_data.get('Head Thickness (mm)', 0)
    fca = component_data.get('Future Corrosion Allowance (mm)', 0)
    weld_eff = component_data.get('Weld Joint Efficiency (E)', 1.0)
    weld_adj = component_data.get('Weld Seam Temp Adjustment', False)
    periods = component_data.get('Periods', [])
    thermal_cycles = component_data.get('Thermal Cycles', 0)
    
    html_content = template.render(
        date=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        comp_type=comp_type,
        level=level,
        material=material,
        diameter=diameter,
        thickness_shell=thickness_shell,
        thickness_head=thickness_head,
        fca=fca,
        weld_eff=weld_eff,
        weld_adj=weld_adj,
        periods=periods,
        thermal_cycles=thermal_cycles,
        multiplier=result_data.get('multiplier', 1.0),
        level3_profile=result_data.get('level3_profile', []),
        cycle_table=result_data.get('cycle_table', []),
        Dc=result_data.get('Dc', 0.0),
        Df=result_data.get('Df', 0.0),
        math_trace=result_data.get('trace', []),
        total_damage=result_data.get('total_damage', 0),
        remaining_life=result_data.get('remaining_life', float('inf')),
        status=result_data.get('status', 'Unknown'),
        graph_b64=result_data.get('graph_b64', ''),
        creep_life_graph_b64=result_data.get('creep_life_graph_b64', ''),
        float=float
    )
    return html_content
