import re

REGEX_RULES = [
    ("PERIODIC_EARNINGS", [
        r"raport\s+trim", r"trimestrul", r"rezultate\s+financiare",
        r"trading\s+update", r"indicatori\s+operationali",
    ]),
    ("CORPORATE_GOVERNANCE", [
        r"convocar", r"hotarar", r"adunarea\s+generala", r"\baga\b",
        r"\bagea\b", r"\bagoa\b", r"consiliul\s+de\s+(administratie|supraveghere)",
        r"demisie", r"administrator\s+judiciar",
    ]),
    ("MATERIAL_CONTRACT", [
        r"contract\s+semnificativ", r"art\.\s*108", r"semnare",
        r"acord\s+achizitie", r"memorandum", r"finalizarea\s+tranzactiei",
    ]),
    ("LEGAL_REGULATORY", [
        r"litigiu", r"notificare\s+asf", r"sanctiune", r"decizie\s+asf",
        r"control\s+anaf", r"faliment", r"insolv", r"dizolvare",
        r"suspendare\s+tranzactionare", r"retragere\s+de\s+la\s+tranzactionare",
    ]),
    ("INSIDER_TRANSACTION", [
        r"persoane\s+initiate", r"notificare\s+insider", r"art\.\s*19",
        r"rascumparare\s+actiuni\s+proprii",
    ]),
    ("ADMINISTRATIVE_AMENDMENT", [
        r"calendar\s+financiar", r"erata", r"clarificare",
        r"perioada\s+inchisa", r"plata\s+(cupon|dividend)",
    ]),
]

def classify_title(title: str) -> str:
    t = title.lower()
    for event_type, patterns in REGEX_RULES:
        if any(re.search(p, t) for p in patterns):
            return event_type
    return "UNKNOWN"
