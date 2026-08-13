"""
password.py - password-protected bank statement PDFs.

Indian bank e-statements are routinely locked by default (SBI/HDFC/ICICI all
do this), so this has to be handled from day one, not bolted on later. Before
prompting the user, we auto-try the handful of conventions banks actually use
(PAN, DOB in a couple of common orderings) - if the caller has that data on
hand (e.g. carried over from the CIBIL/ITR legs of the suite for the same
borrower), the upload never needs to interrupt them at all.
"""

import re


def candidate_passwords(pan: str = None, dob: str = None, name: str = None) -> list:
    """
    Build an ordered list of password candidates from borrower identity data
    the caller already has. `dob` may be any parseable date string; `pan` is
    the 10-character PAN; `name` is the account holder's full name.

    Returns [] if no identity data was supplied - the caller falls back to
    prompting the user directly.
    """
    candidates = []

    dob_digits = None
    if dob:
        digits = re.sub(r"\D", "", dob)
        if len(digits) == 8:
            dob_digits = digits

    pan_upper = pan.strip().upper() if pan else None

    if pan_upper and dob_digits:
        # ddmmyyyy
        candidates.append(pan_upper + dob_digits)
        # ddmmyy
        candidates.append(pan_upper + dob_digits[:4] + dob_digits[6:])

    if pan_upper:
        candidates.append(pan_upper)

    if name and dob_digits:
        first4 = re.sub(r"[^A-Za-z]", "", name)[:4].upper()
        if first4:
            candidates.append(first4 + dob_digits)

    if dob_digits:
        candidates.append(dob_digits)          # ddmmyyyy alone
        candidates.append(dob_digits[:4] + dob_digits[6:])  # ddmmyy

    # de-dupe, preserve order
    seen, out = set(), []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out


def unlock(doc, explicit_password: str = None, pan: str = None,
           dob: str = None, name: str = None) -> bool:
    """
    Try to authenticate an open (but locked) fitz.Document in place.
    Returns True if unlocked, False if every attempt failed.

    Order: explicit user-supplied password first, then auto-try candidates
    built from any identity data supplied.
    """
    if not doc.needs_pass:
        return True

    if explicit_password and doc.authenticate(explicit_password):
        return True

    for candidate in candidate_passwords(pan=pan, dob=dob, name=name):
        if doc.authenticate(candidate):
            return True

    return False
