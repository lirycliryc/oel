"""
Heizöl-Preisüberwachung Schweiz
Holt den aktuellen Preis für eine PLZ und gibt eine Kaufempfehlung.
Installation: pip install requests beautifulsoup4
"""
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime


def get_heizoelpreis(plz: str, menge_l: int = 3000) -> dict:
    """
    Holt den aktuellen Heizölpreis für eine Schweizer PLZ
    von heizoel24.ch (Preisvergleich).
    """
    url = f"https://www.heizoel24.ch/heizoelpreise/{plz}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # Preis extrahieren – mehrere Selektoren für Robustheit
        price_element = (
            soup.find("span", class_="price")
            or soup.find("div", class_="heizoelpreis")
            or soup.find("td", class_="price")
            or soup.find(string=re.compile(r"\d{2,3},\d{2}\s*CHF"))
        )

        if price_element:
            price_text = price_element.get_text(strip=True) if hasattr(price_element, "get_text") else str(price_element)
            numbers = re.findall(r"\d{2,3}[.,]\d{2}", price_text)
            if numbers:
                price_100l = float(numbers[0].replace(",", "."))
            else:
                price_100l = None
        else:
            price_100l = None

        return {
            "plz": plz,
            "menge_l": menge_l,
            "preis_pro_100l_chf": price_100l,
            "preis_gesamt_chf": price_100l * (menge_l / 100) if price_100l else None,
            "quelle": url,
            "abgerufen_am": datetime.now().strftime("%d.%m.%Y %H:%M"),
        }

    except requests.RequestException as e:
        return {"error": f"Netzwerkfehler: {e}"}


def get_trenddaten() -> dict:
    """
    Holt die übergeordneten Trenddaten von heizoel24.ch.
    """
    url = "https://www.heizoel24.ch/preise-statistik"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        text = soup.get_text()

        trend_7d = None
        trend_30d = None
        trend_1y = None

        match_7 = re.search(r"7 Tage:\s*([+\-][\d.,]+)\s*%", text)
        match_30 = re.search(r"30 Tage:\s*([+\-][\d.,]+)\s*%", text)
        match_1y = re.search(r"1 Jahr:\s*([+\-][\d.,]+)\s*%", text)

        if match_7:
            trend_7d = float(match_7.group(1).replace(",", "."))
        if match_30:
            trend_30d = float(match_30.group(1).replace(",", "."))
        if match_1y:
            trend_1y = float(match_1y.group(1).replace(",", "."))

        return {
            "trend_7_tage_prozent": trend_7d,
            "trend_30_tage_prozent": trend_30d,
            "trend_1_jahr_prozent": trend_1y,
        }

    except requests.RequestException as e:
        return {"error": f"Netzwerkfehler: {e}"}


def kaufempfehlung(
    trend_7d: float, trend_30d: float, tankfuellung_prozent: int = 50
) -> str:
    """
    Gibt eine einfache Kaufempfehlung basierend auf Trends.
    """
    if tankfuellung_prozent < 20:
        return "SOFORT BESTELLEN – Tank kritisch leer, Preisrisiko zweitrangig."

    if trend_7d is not None and trend_30d is not None:
        if trend_7d < -3 and trend_30d < -3:
            return "WARTEN – Starker Abwärtstrend. Preis dürfte weiter sinken."
        elif trend_7d < 0 and trend_30d < 0:
            return "BEOBACHTEN – Leichter Abwärtstrend. Warten lohnt sich wahrscheinlich."
        elif trend_7d > 3 and trend_30d > 3:
            return "ZUSCHLAGEN – Starker Aufwärtstrend. Preis könnte weiter steigen."
        elif trend_7d > 0 and trend_30d > 0:
            return "ABWÄGEN – Leichter Aufwärtstrend. Bei <40% Tankfüllung bestellen."
        else:
            return "NEUTRAL – Kein klarer Trend. Bei Bedarf bestellen."

    return "Keine Trenddaten verfügbar. Bitte manuell prüfen."


def main():
    PLZ = "4143"
    MENGE = 3000
    TANKFUELLUNG = 50  # <-- ANPASSEN: aktueller Tankfüllstand in %

    print("=" * 55)
    print(f"  HEIZÖL-PREISÜBERWACHUNG – PLZ {PLZ}")
    print(f"  Abnahmemenge: {MENGE:,} Liter".replace(",", "'"))
    print("=" * 55)

    # Preis abrufen
    print("\n[1] Preis wird abgerufen...")
    preis_daten = get_heizoelpreis(PLZ, MENGE)

    if "error" in preis_daten:
        print(f"    FEHLER: {preis_daten['error']}")
        print("    Hinweis: heizoel24.ch könnte das Scraping blockieren.")
        print("    Alternative: https://www.heizoel24.ch direkt besuchen.")
    elif preis_daten["preis_pro_100l_chf"] is None:
        print("    WARNUNG: Preis konnte nicht erkannt werden.")
        print("    Die HTML-Struktur der Seite hat sich vermutlich geändert.")
        print(f"    Manuell prüfen: {preis_daten['quelle']}")
    else:
        preis = preis_daten["preis_pro_100l_chf"]
        gesamt = preis_daten["preis_gesamt_chf"]
        print(f"    Preis/100L:   {preis:.2f} CHF")
        print(f"    Gesamt {MENGE}L: {gesamt:,.0f} CHF".replace(",", "'"))

    # Trend abrufen
    print("\n[2] Trenddaten werden abgerufen...")
    trend = get_trenddaten()

    if "error" not in trend:
        t7 = trend.get("trend_7_tage_prozent")
        t30 = trend.get("trend_30_tage_prozent")
        t1y = trend.get("trend_1_jahr_prozent")

        print(f"    7-Tage-Trend:   {t7:+.1f} %" if t7 is not None else "    7-Tage-Trend:   n/a")
        print(f"    30-Tage-Trend:  {t30:+.1f} %" if t30 is not None else "    30-Tage-Trend:  n/a")
        print(f"    1-Jahr-Trend:   {t1y:+.1f} %" if t1y is not None else "    1-Jahr-Trend:   n/a")

        print("\n" + "=" * 55)
        empfehlung = kaufempfehlung(t7, t30, TANKFUELLUNG)
        print(f"  EMPFEHLUNG: {empfehlung}")
        print("=" * 55)
    else:
        print(f"    FEHLER: {trend['error']}")

    print(f"\n  Hinweis: Keine Anlageberatung. Preis = Richtwert.")
    print(f"  Für verbindliche Angebote: heizoel24.ch / toptank.ch")
    print()


if __name__ == "__main__":
    main()
