import pandas as pd

file_path = "Assessment of components operating in the creep range_MFC.xlsx"
xls = pd.ExcelFile(file_path)

with open("excel_structure.txt", "w", encoding="utf-8") as f:
    for sheet_name in xls.sheet_names:
        f.write(f"\n==========================================\n")
        f.write(f"SHEET: {sheet_name}\n")
        f.write(f"==========================================\n")
        df = pd.read_excel(file_path, sheet_name=sheet_name, header=None)
        for r_idx, row in df.iterrows():
            row_vals = []
            for c_idx, val in enumerate(row):
                if pd.notna(val):
                    row_vals.append(f"Col {c_idx} ({val})")
            if row_vals:
                f.write(f"Row {r_idx:2d}: " + " | ".join(row_vals) + "\n")
print("Done writing to excel_structure.txt")
