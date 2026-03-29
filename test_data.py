# test_esg.py
import joblib
import numpy as np

# Load the model
artifact = joblib.load("models/esg_model.joblib")
model_E = artifact["model_E"]
model_S = artifact["model_S"]
model_G = artifact["model_G"]
le      = artifact["sector_encoder"]
ind_map = artifact["industry_type_map"]

def predict(sector, gross_margin, operating_margin, rd_ratio, capex_ratio):
    sec_enc  = int(le.transform([sector])[0])
    ind_type = ind_map.get(sector, 2)

    E = model_E.predict([[sec_enc, ind_type, capex_ratio,   operating_margin]])[0]
    S = model_S.predict([[sec_enc, ind_type, gross_margin,  rd_ratio]])[0]
    G = model_G.predict([[sec_enc, ind_type, operating_margin, gross_margin]])[0]
    C = E * 0.7 + G * 0.3

    print(f"E={E:.1f}  S={S:.1f}  G={G:.1f}  Carbon={C:.1f}")

# Test with known stocks to verify consistency
predict("Oil & Gas",    0.38, 0.12, 0.00, 0.18)  # should be low E (~12)
predict("Clean Energy", 0.47, 0.22, 0.08, 0.05)  # should be high E (~97)
predict("Technology",   0.69, 0.44, 0.13, 0.02)  # should be high all (~MSFT)