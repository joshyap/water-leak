import pandas as pd

df = pd.read_csv("data/raw/Billing-Usage-for-0015929370.csv")
df = df.drop(columns=["Account Number", "Meter"])  # strip PII
df.to_csv("data/usage_clean.csv", index=False)