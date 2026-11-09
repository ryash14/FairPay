"""What the (fictional) company knows: the rates its PDFs publish.

Only the devkit generators read this file. It plays the part of Kestrel's
payroll office writing its own documents. The application never imports it:
the application reads every rate back out of the PDFs.
"""
RATE_WINDOWS = {
    "Front of House": [("01 Jul", "27.20", "2.50"), ("18 Jan", "29.30", "2.87")],
    "Front of House Trainee": [("01 Jul", "23.40", "2.10"), ("01 Feb", "23.95", "2.15")],
    "Kitchen": [("01 Jul", "26.10", "2.30"), ("01 Oct", "26.80", "2.30"), ("01 Mar", "27.45", "2.40")],
    "Kitchen Trainee": [("01 Jul", "22.30", "1.90"), ("01 Dec", "22.90", "1.95")],
    "Night Audit": [("01 Jul", "28.60", "34.30", "3.10"), ("15 Jan", "29.40", "35.25", "3.20")],
}
MOVES_ONTO = {"Front of House Trainee": "Front of House", "Kitchen Trainee": "Kitchen"}
COMMITMENT_PAYMENTS = {"PC1": "150.00", "PC2": "85.00", "PC3": "60.00"}
WORKED_EXAMPLE_REFERENCE = "PQR-SYD-0041927"
