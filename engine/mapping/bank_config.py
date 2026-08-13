"""
bank_config.py - per-bank identification data.

Deliberate deviation from CIBIL_EXCEL's per-format regex parsers: bank
statements share one structural contract (date / narration / amount(s) /
running balance ledger) across dozens of banks, so one generic table engine
(engine/extract/statement_table.py) does the actual row extraction. What
varies bank to bank is small enough to be data, not code - a bank's display
name (for the report header) and the header/IFSC text that identifies it.

Column layout itself is *not* hand-mapped per bank here. statement_table.py
reads it structurally instead (see its module docstring): trailing numeric
cells are balance/withdrawal/deposit by position and count, with an explicit
DR/CR token or the running-balance delta resolving which single amount
column means what when a bank prints only one. That's what lets a 6th, 7th,
30th bank work without a new config entry - BANKS below only has to grow to
get a friendly name and IFSC prefix in the report, not a full column map.
"""

# key -> (display name, [detection tokens to look for in page-1 text, any match])
BANKS = {
    "SBI":       ("State Bank of India",        ["STATE BANK OF INDIA", "SBIN0", "sbi.co.in"]),
    "HDFC":      ("HDFC Bank",                   ["HDFC BANK", "HDFC0"]),
    "ICICI":     ("ICICI Bank",                   ["ICICI BANK", "ICIC0"]),
    "AXIS":      ("Axis Bank",                     ["AXIS BANK", "UTIB0"]),
    "KOTAK":     ("Kotak Mahindra Bank",            ["KOTAK MAHINDRA", "KKBK0"]),
    "PNB":       ("Punjab National Bank",            ["PUNJAB NATIONAL BANK", "PUNB0"]),
    "BOM":       ("Bank of Maharashtra",              ["BANK OF MAHARASHTRA", "MAHB0"]),
    "SIB":       ("South Indian Bank",                 ["SOUTH INDIAN BANK", "SIBL0"]),
    "TJSB":      ("TJSB Sahakari Bank",                 ["TJSB SAHAKARI BANK", "TJSB0"]),
    "BCCB":      ("Bassein Catholic Co-op Bank",         ["BASSEIN CATHOLIC", "BACB0"]),
    "PJSB":      ("Parshwanath Sahakari Bank",            ["PJSB0"]),
}

# Amount column mode, detected structurally per statement (not per bank) but
# named here for the summary sheet / debugging output.
AMOUNT_MODE_SPLIT = "split"                 # separate Withdrawal & Deposit columns
AMOUNT_MODE_SINGLE_INDICATOR = "single_dr_cr"   # one Amount column + a DR/CR cell
AMOUNT_MODE_SINGLE_SIGNED = "single_signed"     # one Amount column, direction inferred from balance delta


def identify_bank(text: str) -> tuple:
    """
    Best-effort bank identification from a page's text (page 1 is enough -
    every sample statement carries the bank name/IFSC prefix there).
    Returns (bank_key, display_name) or (None, "Unknown Bank") if nothing
    matched - the generic structural parser still runs either way.
    """
    upper = text.upper()
    for key, (display, tokens) in BANKS.items():
        if any(tok.upper() in upper for tok in tokens):
            return key, display
    return None, "Unknown Bank"
