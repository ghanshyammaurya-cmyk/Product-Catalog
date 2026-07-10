"""Apply client-provided requirements to PS-001 (Advantech UNO-258) in Excel."""
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "testdata", "partner_products.xlsx")

CLIENT_CATEGORIES = """Edge Feature: Extended Temperature, Real-time
Vertical: Manufacturing; Robotics
Open Software Platform: Robotics AI Suite, Manufacturing AI Suite
Intel Processors: Intel Core Ultra Series 3 processors
Geo Availability: Worldwide; US/Canada; Latin America Region; Europe, Middle East, and Africa; Asia Pacific, Japan, Australia & New Zealand; PRC; India
AI Edge System Sizing: TBC
Target Audience: SI (System Integrators)"""

CLIENT_FEATURES = """1. High-performance Computing
2. Integrated AI Acceleration
3. Compact Fanless Design
4. Rich I/O & Fast Connectivity"""

CLIENT_DESCRIPTION = (
    "The UNO-258 is Advantech's next-generation fanless Edge AI Box PC designed to accelerate "
    "real-time AI applications in smart manufacturing, machine vision, and industrial automation. "
    "Powered by Intel® Core™ Ultra Series 3 processors, the system delivers up to 180 TOPS AI "
    "performance through integrated CPU, GPU, and NPU architecture, enabling low-latency AI "
    "inference directly at the edge. As industrial environments increasingly demand real-time "
    "inspection, autonomous operation, and AI-driven analytics, traditional systems often struggle "
    "with thermal limitations, unstable operation, and complex deployment. UNO-258 addresses these "
    "challenges with a rugged fanless design, wide-temperature operation, and industrial-grade "
    "reliability for harsh environments. The compact platform supports high-speed connectivity, "
    "multiple vision and industrial I/O interfaces, and flexible expansion capabilities, making it "
    "ideal for Vision AI, robotics, smart transportation, and edge automation applications. "
    "Compared with conventional industrial PCs, UNO-258 combines high AI computing performance, "
    "fanless durability, and simplified deployment into a compact edge-ready platform optimized "
    "for next-generation Edge AI workloads."
)

CLIENT_RESOURCE_URL = (
    "https://www.advantech.com/en/products/9a0cc561-8fc2-4e22-969c-9df90a3952b5/"
    "uno-258/mod_d527f9c1-6844-48ed-a512-e10c146dbea0"
)

df = pd.read_excel(PATH)
mask = df["test_id"].astype(str) == "PS-001"
if not mask.any():
    raise SystemExit("PS-001 row not found in Excel")

if "expected_resource_url" not in df.columns:
    df["expected_resource_url"] = ""

if "partner_dropdown_label" not in df.columns:
    df["partner_dropdown_label"] = ""

df.loc[mask, "partner_name"] = "Advantech"
df.loc[mask, "partner_dropdown_label"] = "Advantech Co. Ltd."
df.loc[mask, "product_name"] = "Advantech UNO-258"
df.loc[mask, "application_name"] = "Advantech UNO-258"
df.loc[mask, "search_term"] = "Advantech UNO-258"
df.loc[mask, "expected_title"] = "Advantech UNO-258"
df.loc[mask, "expected_short_description"] = "Fanless Edge AI Box PC for Smart Manufacturing"
df.loc[mask, "expected_description"] = CLIENT_DESCRIPTION
df.loc[mask, "expected_contact_url"] = "https://www.advantech.com/en/contact"
df.loc[mask, "expected_resource_url"] = CLIENT_RESOURCE_URL
df.loc[mask, "expected_features"] = CLIENT_FEATURES
df.loc[mask, "category_subcategory"] = CLIENT_CATEGORIES
df.loc[mask, "expected_categories"] = CLIENT_CATEGORIES
df.loc[mask, "expected_meta_description"] = (
    "The UNO-258 is Advantech's next-generation fanless Edge AI Box PC designed to accelerate "
    "real-time AI applications in smart manufacturing, machine"
)
df.loc[mask, "validate_pdf"] = False

with pd.ExcelWriter(PATH, engine="openpyxl") as writer:
    df.to_excel(writer, sheet_name="PartnerProducts", index=False)

print("Updated PS-001 with client requirements")
print("  - Product details, features (4 items), resource URL, categories (7 groups)")
