# generuj_dane.py – generator danych syntetycznych dla bazy flota_dronow
# Uruchomienie:  pip install faker   →   python generuj_dane.py   →   powstaje plik dane.sql
# Dane spełniają reguły biznesowe z punktu 4 (te same, które w punkcie 10 wymuszą triggery):
#   - dron leci tylko z ważnym przeglądem, operator tylko z ważnymi uprawnieniami na model,
#   - bateria pasuje do modelu drona, waga paczek ≤ udźwig, trasa ≤ zasięg,
#   - paczka zwrócona do bazy trafia do kolejnej misji z numerem próby + 1.

import random
from datetime import date, datetime, timedelta
from faker import Faker

fake = Faker("pl_PL")
Faker.seed(2026)                      # stałe ziarno → za każdym razem te same dane
random.seed(2026)

DZIS = date(2026, 11, 13)             # „dziś” w projekcie
POCZATEK = date(2026, 9, 1)           # od tego dnia generujemy loty
KRAKOW = (50.0614, 19.9366)           # środek miasta, wokół niego losujemy punkty

tabele = {}                           # nazwa tabeli → (lista kolumn, lista wierszy)

# ---------------------------------------------------------------- bazy
# 4 huby w różnych dzielnicach Krakowa
bazy = [
    (1, "Hub Krowodrza",   "ul. Racławicka 56, Kraków",  50.077214, 19.915530, 6, 8),
    (2, "Hub Podgórze",    "ul. Wielicka 28, Kraków",    50.040871, 19.965312, 5, 6),
    (3, "Hub Nowa Huta",   "os. Zgody 7, Kraków",        50.071905, 20.037118, 4, 6),
    (4, "Hub Bronowice",   "ul. Balicka 18, Kraków",     50.081322, 19.882041, 4, 5),
]
tabele["bazy"] = (["id_bazy", "nazwa", "adres", "szerokosc_geo", "dlugosc_geo",
                   "liczba_ladowisk", "liczba_stanowisk_ladowania"], bazy)

# ---------------------------------------------------------------- modele_dronow
# (id, producent, model, udźwig kg, zasięg km, prędkość km/h, limit cykli baterii)
modele = [
    (1, "Matternet", "M2",            2.00, 20.0,  70, 300),
    (2, "Wingcopter", "198",          5.00, 75.0, 110, 400),
    (3, "Zipline",   "P2 Zip",        3.50, 24.0, 100, 350),
    (4, "DJI",       "FlyCart 30",   30.00, 28.0,  72, 250),
]
tabele["modele_dronow"] = (["id_modelu", "producent", "nazwa_modelu", "max_udzwig_kg",
                            "zasieg_km", "predkosc_kmh", "limit_cykli_baterii"], modele)
model_po_id = {m[0]: m for m in modele}

# ---------------------------------------------------------------- drony
# 28 dronów: po 7 w każdej bazie, modele rozłożone równo (każda baza ma każdy model)
drony = []
for id_drona in range(1, 29):
    id_bazy = (id_drona - 1) // 7 + 1
    id_modelu = (id_drona - 1) % 4 + 1
    data_zakupu = fake.date_between(date(2024, 3, 1), date(2025, 12, 31))
    drony.append([id_drona, id_modelu, id_bazy,
                  f"SN-{model_po_id[id_modelu][1][:3].upper()}-{random.randint(100000, 999999)}",
                  f"PL-UAS-{id_drona:04d}",
                  data_zakupu,
                  round(random.uniform(20, 180), 2),   # nalot sprzed września, potem dodamy loty
                  "dostepny"])
# trzy drony z ciekawszym statusem (przydadzą się w zapytaniach SELECT):
drony[6][7] = "wycofany"      # dron 7  – wycofany, nie lata od lipca
drony[13][7] = "w_serwisie"   # dron 14 – przegląd wygasł 2026-11-01
drony[20][7] = "w_serwisie"   # dron 21 – przegląd wygasł 2026-10-20

# ---------------------------------------------------------------- baterie
# 2 baterie na drona, zawsze tego samego modelu co dron + 2 zużyte w magazynie
baterie = []
baterie_drona = {}            # id_drona → [id_baterii, id_baterii]
id_baterii = 1
for d in drony:
    baterie_drona[d[0]] = []
    for _ in range(2):
        baterie.append([id_baterii, d[1], f"BAT-{d[1]}-{random.randint(1000000, 9999999)}",
                        random.choice([5200, 8000, 9500, 14000, 29000])
                        if d[1] == 4 else random.choice([4000, 5200, 6000]),
                        random.randint(10, 120),      # cykle sprzed września
                        "sprawna"])
        baterie_drona[d[0]].append(id_baterii)
        id_baterii += 1
for id_modelu in (1, 3):
    limit = model_po_id[id_modelu][6]
    baterie.append([id_baterii, id_modelu, f"BAT-{id_modelu}-{random.randint(1000000, 9999999)}",
                    5200, limit - random.randint(0, 5), "do_wymiany"])
    id_baterii += 1

# ---------------------------------------------------------------- pracownicy
# w każdej bazie: 4 operatorów, 2 dyspozytorów, 2 techników
pracownicy = []
uzyte_emaile = set()
id_pracownika = 1
for id_bazy in range(1, 5):
    for stanowisko, ile in (("operator", 4), ("dyspozytor", 2), ("technik", 2)):
        for _ in range(ile):
            imie = fake.first_name()
            nazwisko = fake.last_name()
            bez_ogonkow = str.maketrans("ąćęłńóśźżĄĆĘŁŃÓŚŹŻ", "acelnoszzACELNOSZZ")
            email = (imie + "." + nazwisko).translate(bez_ogonkow).lower() + "@wirnik-express.pl"
            while email in uzyte_emaile:
                email = email.replace("@", str(random.randint(1, 9)) + "@")
            uzyte_emaile.add(email)
            pracownicy.append((id_pracownika, id_bazy, imie, nazwisko, email,
                               fake.phone_number() if random.random() < 0.9 else None,
                               stanowisko,
                               fake.date_between(date(2023, 1, 1), date(2025, 6, 30))))
            id_pracownika += 1
tabele["pracownicy"] = (["id_pracownika", "id_bazy", "imie", "nazwisko", "email", "telefon",
                         "stanowisko", "data_zatrudnienia"], pracownicy)

# ---------------------------------------------------------------- uprawnienia_pracownikow
# k-ty operator w bazie ma zawsze ważne uprawnienia na model k → każda baza obsłuży każdy model.
# Dodatkowo losowe uprawnienia na inne modele; część z nich wygasła (do zapytań i triggera).
uprawnienia = []
for p in pracownicy:
    if p[6] != "operator":
        continue
    numer_w_bazie = (p[0] - 1) % 8 + 1                       # 1..4 to operatorzy
    glowny_model = numer_w_bazie
    uzyskane = fake.date_between(date(2025, 1, 1), date(2025, 8, 31))
    uprawnienia.append((p[0], glowny_model, uzyskane, uzyskane + timedelta(days=730)))
    for id_modelu in random.sample([m for m in range(1, 5) if m != glowny_model], random.randint(0, 2)):
        uzyskane = fake.date_between(date(2024, 6, 1), date(2025, 10, 31))
        waznosc = uzyskane + timedelta(days=random.choice([365, 730]))   # część wygasa przed DZIS
        uprawnienia.append((p[0], id_modelu, uzyskane, waznosc))
tabele["uprawnienia_pracownikow"] = (["id_pracownika", "id_modelu", "data_uzyskania",
                                      "data_waznosci"], uprawnienia)

# ---------------------------------------------------------------- przeglady (okresowe)
# Co 90 dni od zakupu, zawsze pozytywne → dron ma ciągłą ważność przeglądu.
# Wyjątki: dron 7 (ostatni przegląd 2026-04, wygasł), 14 (wygasł 2026-11-01), 21 (wygasł 2026-10-20).
technicy_bazy = {b: [p[0] for p in pracownicy if p[1] == b and p[6] == "technik"] for b in range(1, 5)}
przeglady = []
koniec_waznosci = {}          # id_drona → data, po której dron nie ma już ważnego przeglądu
id_przegladu = 1
for d in drony:
    if d[0] == 7:
        ostatni = date(2026, 4, 15)
    elif d[0] == 14:
        ostatni = date(2026, 11, 1) - timedelta(days=90)
    elif d[0] == 21:
        ostatni = date(2026, 10, 20) - timedelta(days=90)
    else:
        ostatni = DZIS
    dzien = d[5] + timedelta(days=random.randint(0, 5))
    while dzien <= ostatni:
        nastepny = dzien + timedelta(days=90)
        przeglady.append([id_przegladu, d[0], random.choice(technicy_bazy[d[2]]), dzien,
                          "okresowy", "pozytywny",
                          random.choice([None, None, "Bez uwag", "Wymieniono śmigła",
                                         "Kalibracja kompasu", "Aktualizacja firmware"]),
                          nastepny])
        koniec_waznosci[d[0]] = nastepny
        id_przegladu += 1
        dzien = nastepny - timedelta(days=random.randint(0, 3))   # kolejny przegląd tuż przed terminem
    if d[0] == 7:
        koniec_waznosci[d[0]] = date(2026, 7, 14)   # wycofany – po tej dacie nie lata

# ---------------------------------------------------------------- klienci
klienci = []
uzyte_emaile = set()
for id_klienta in range(1, 121):
    if id_klienta <= 40:
        typ = "firma"
        nazwa = random.choice(["Apteka ", "Laboratorium ", "Restauracja ", "Kwiaciarnia ", ""]) + fake.company()
        nip = fake.nip()
        email = "kontakt" + str(id_klienta) + "@" + fake.domain_name()
    else:
        typ = "osoba"
        nazwa = fake.name()
        nip = None
        email = fake.free_email()
    while email in uzyte_emaile:
        email = str(random.randint(1, 9)) + email
    uzyte_emaile.add(email)
    klienci.append((id_klienta, typ, nazwa[:120], nip, email,
                    fake.phone_number() if random.random() < 0.85 else None,
                    fake.street_address() + ", Kraków",
                    fake.date_time_between(datetime(2025, 1, 1), datetime(2026, 8, 31))))
tabele["klienci"] = (["id_klienta", "typ", "nazwa", "nip", "email", "telefon", "adres",
                      "data_rejestracji"], klienci)

# ---------------------------------------------------------------- przesylki
# 650 paczek nadanych od 1.09 do 13.11; punkty odbioru i doręczenia w promieniu ~7 km od centrum
przesylki = []
for id_przesylki in range(1, 651):
    nadanie = fake.date_time_between(datetime(2026, 9, 1, 7, 0), datetime(2026, 11, 13, 12, 0))
    nadanie = nadanie.replace(hour=random.randint(7, 17))         # po 15:00 → poleci następnego dnia
    id_klienta = random.randint(1, 120)
    priorytet = random.choices(["standard", "ekspres", "medyczna"], [70, 22, 8])[0]
    if id_klienta <= 40 and random.random() < 0.3:
        priorytet = "medyczna"                                     # apteki i laboratoria
    waga = round(random.choices([random.uniform(0.1, 1.9), random.uniform(2, 4.9), random.uniform(5, 25)],
                                [70, 25, 5])[0], 2)
    odbior_szer = round(KRAKOW[0] + random.uniform(-0.05, 0.05), 6)
    odbior_dl = round(KRAKOW[1] + random.uniform(-0.09, 0.09), 6)
    if waga > 5:     # ciężkie paczki (tylko DJI FlyCart) – krótkie trasy, doręczenie do ~2 km od odbioru
        dorecz_szer = round(odbior_szer + random.uniform(-0.015, 0.015), 6)
        dorecz_dl = round(odbior_dl + random.uniform(-0.02, 0.02), 6)
    else:
        dorecz_szer = round(KRAKOW[0] + random.uniform(-0.05, 0.05), 6)
        dorecz_dl = round(KRAKOW[1] + random.uniform(-0.09, 0.09), 6)
    przesylki.append([id_przesylki, id_klienta, waga,
                      random.randint(10, 45), random.randint(8, 35), random.randint(4, 30),
                      fake.street_address() + ", Kraków", odbior_szer, odbior_dl,
                      fake.street_address() + ", Kraków", dorecz_szer, dorecz_dl,
                      priorytet, "oczekuje", nadanie])
przesylki.sort(key=lambda p: p[14])                                # po dacie nadania
for i, p in enumerate(przesylki):
    p[0] = i + 1                                                   # id rosną razem z datą
# ok. 2% paczek klient anuluje przed lotem
for p in random.sample(przesylki, 13):
    p[13] = "anulowana"

# ---------------------------------------------------------------- misje + misje_przesylki + incydenty
# Symulacja dzień po dniu. Kolejka = paczki nadane do tego dnia (i zwrócone z wcześniejszych lotów).
# Dla pierwszej paczki w kolejce szukamy drona, który: ma udźwig, ważny przegląd, jest wolny;
# potem dokładamy kolejne paczki, dopóki pasuje udźwig, zasięg i max 3 paczki.
operatorzy_bazy = {b: [p[0] for p in pracownicy if p[1] == b and p[6] == "operator"] for b in range(1, 5)}
dyspozytorzy_bazy = {b: [p[0] for p in pracownicy if p[1] == b and p[6] == "dyspozytor"] for b in range(1, 5)}
baza_po_id = {b[0]: b for b in bazy}

misje = []
misje_przesylki = []
incydenty = []
proby = {}                     # id_przesylki → ile razy już leciała
kolejka = []
wskaznik = 0                   # następna paczka z listy, która jeszcze nie weszła do kolejki
uzycia_baterii = {}            # id_baterii → ile zakończonych lotów
nalot_dodany = {}              # id_drona → godziny dodane w symulacji
id_misji = 1
id_incydentu = 1

dzien = POCZATEK
while dzien <= DZIS + timedelta(days=1):
    # dorzuć do kolejki paczki nadane przed końcem tego dnia
    while wskaznik < len(przesylki) and przesylki[wskaznik][14].date() <= dzien:
        if przesylki[wskaznik][13] != "anulowana":
            kolejka.append(przesylki[wskaznik])
        wskaznik += 1
    # medyczne i ekspresowe najpierw
    kolejka.sort(key=lambda p: ({"medyczna": 0, "ekspres": 1, "standard": 2}[p[12]], p[14]))

    wolny_od = {d[0]: datetime.combine(dzien, datetime.min.time()).replace(hour=8) for d in drony}
    planowane = dzien > DZIS          # jutro (14.11) → misje tylko zaplanowane
    dzisiaj = dzien == DZIS
    nieobsluzone = []

    while kolejka:
        pierwsza = kolejka.pop(0)
        if pierwsza[14].date() == dzien and pierwsza[14].hour >= 15 and not planowane:
            nieobsluzone.append(pierwsza)          # późno nadana – poleci następnego dnia
            continue
        # drony zdolne do lotu tego dnia: ważny przegląd, udźwig i zasięg na trasę z tą paczką
        kandydaci = []
        for d in drony:
            if d[7] == "wycofany" or koniec_waznosci.get(d[0], date.min) <= dzien:
                continue
            if model_po_id[d[1]][3] < float(pierwsza[2]) or wolny_od[d[0]].hour >= 19:
                continue
            b = baza_po_id[d[2]]
            trasa = [(b[3], b[4]), (pierwsza[7], pierwsza[8]), (pierwsza[10], pierwsza[11]), (b[3], b[4])]
            dystans = 0
            for a, c in zip(trasa, trasa[1:]):
                dystans += (((c[0] - a[0]) * 111.2) ** 2 + ((c[1] - a[1]) * 71.5) ** 2) ** 0.5
            if dystans <= model_po_id[d[1]][4] * 0.9:
                kandydaci.append(d)
        if not kandydaci:
            nieobsluzone.append(pierwsza)
            continue
        dron = min(kandydaci, key=lambda d: (wolny_od[d[0]], model_po_id[d[1]][3]))
        model = model_po_id[dron[1]]
        baza = baza_po_id[dron[2]]

        # operator z bazy drona z ważnymi uprawnieniami na ten model w tym dniu
        operatorzy = [u[0] for u in uprawnienia
                      if u[1] == dron[1] and u[0] in operatorzy_bazy[dron[2]] and u[2] <= dzien < u[3]]
        if not operatorzy:
            nieobsluzone.append(pierwsza)
            continue

        # dokładanie paczek: udźwig, zasięg (trasa baza → odbiór → doręczenie → … → baza), max 3
        ladunek = [pierwsza]
        for kandydatka in list(kolejka):
            if len(ladunek) == 3:
                break
            if kandydatka[14].date() == dzien and kandydatka[14].hour >= 15 and not planowane:
                continue
            proba = ladunek + [kandydatka]
            if sum(float(p[2]) for p in proba) > model[3]:
                continue
            punkty = [(baza[3], baza[4])]
            for p in proba:
                punkty += [(p[7], p[8]), (p[10], p[11])]
            punkty.append((baza[3], baza[4]))
            dystans = 0
            for a, b in zip(punkty, punkty[1:]):
                dystans += (((b[0] - a[0]) * 111.2) ** 2 + ((b[1] - a[1]) * 71.5) ** 2) ** 0.5
            if dystans <= model[4] * 0.9:
                ladunek.append(kandydatka)
                kolejka.remove(kandydatka)

        punkty = [(baza[3], baza[4])]
        for p in ladunek:
            punkty += [(p[7], p[8]), (p[10], p[11])]
        punkty.append((baza[3], baza[4]))
        dystans = 0
        for a, b in zip(punkty, punkty[1:]):
            dystans += (((b[0] - a[0]) * 111.2) ** 2 + ((b[1] - a[1]) * 71.5) ** 2) ** 0.5
        if dystans > model[4] * 0.9:                 # nawet jedna paczka za daleko dla tego modelu
            nieobsluzone.append(pierwsza)
            continue

        najpozniej_nadana = max(p[14] for p in ladunek)
        planowany_start = max(wolny_od[dron[0]], najpozniej_nadana + timedelta(minutes=30))
        planowany_start = planowany_start.replace(second=0, microsecond=0)
        if planowany_start.hour >= 20 or planowany_start.date() != dzien:
            nieobsluzone.extend(ladunek)
            continue
        minuty_lotu = dystans / model[5] * 60 + 4 * len(ladunek)     # +4 min na każde doręczenie
        bateria = baterie_drona[dron[0]][id_misji % 2]
        operator = random.choice(operatorzy)
        dyspozytor = random.choice(dyspozytorzy_bazy[dron[2]])

        # wynik lotu
        los = random.random()
        if planowane:
            status = "zaplanowana"
        elif dzisiaj and planowany_start.hour >= 13:
            status = "zaplanowana" if planowany_start.hour >= 15 else "w_trakcie"
        elif los < 0.04:
            status = "przerwana"
        else:
            status = "zakonczona"

        rzeczywisty_start = None
        ladowanie = None
        dystans_zapis = None
        if status in ("zakonczona", "przerwana", "w_trakcie"):
            rzeczywisty_start = planowany_start + timedelta(minutes=random.randint(0, 12))
        if status == "zakonczona":
            ladowanie = rzeczywisty_start + timedelta(minutes=round(minuty_lotu + random.uniform(-2, 6)))
            dystans_zapis = round(dystans, 2)
        if status == "przerwana":
            ladowanie = rzeczywisty_start + timedelta(minutes=round(minuty_lotu * random.uniform(0.2, 0.5)) + 1)
            dystans_zapis = round(dystans * random.uniform(0.2, 0.5), 2)

        misje.append([id_misji, dron[0], bateria, operator, dyspozytor, dron[2],
                      planowany_start, rzeczywisty_start, ladowanie, dystans_zapis, status])

        # przydziały paczek do misji
        czas = rzeczywisty_start
        for kolejnosc, p in enumerate(ladunek, start=1):
            proby[p[0]] = proby.get(p[0], 0) + 1
            if status == "zakonczona":
                czas = czas + timedelta(minutes=round(minuty_lotu / (len(ladunek) + 1)))
                wynik = "zwrocona" if random.random() < 0.05 else "doreczona"   # np. brak odbiorcy
            elif status == "przerwana":
                wynik = "zwrocona"
            else:
                wynik = "w_drodze"
            misje_przesylki.append((id_misji, p[0], kolejnosc, proby[p[0]], wynik,
                                    czas if wynik == "doreczona" else None))
            if wynik == "doreczona":
                p[13] = "doreczona"
            elif wynik == "zwrocona":
                p[13] = "oczekuje"
                nieobsluzone.append(p)                  # wraca do kolejki na następny dzień
            elif status == "w_trakcie":
                p[13] = "w_locie"
            # zaplanowana → paczka dalej „oczekuje”

        # incydenty: zawsze przy przerwanej misji, czasem przy udanej (drobne)
        if status == "przerwana" or (status == "zakonczona" and random.random() < 0.05):
            if status == "przerwana":
                typ = random.choice(["utrata_gps", "niska_bateria", "kolizja", "inny"])
                waznosc = random.choice(["srednia", "wysoka", "wysoka", "krytyczna"])
            else:
                typ = random.choice(["twarde_ladowanie", "utrata_gps", "niska_bateria"])
                waznosc = random.choice(["niska", "niska", "srednia", "wysoka"])
            opisy = {
                "utrata_gps": "Chwilowa utrata sygnału GNSS, dron przeszedł w tryb zawisu",
                "niska_bateria": "Napięcie baterii spadło poniżej progu krytycznego",
                "kolizja": "Kontakt śmigła z gałęzią drzewa podczas zniżania",
                "twarde_ladowanie": "Lądowanie z prędkością pionową powyżej normy",
                "inny": "Silny podmuch wiatru, operator przerwał misję",
            }
            koniec = ladowanie or rzeczywisty_start
            incydenty.append((id_incydentu, id_misji,
                              rzeczywisty_start + (koniec - rzeczywisty_start) * random.uniform(0.3, 0.9),
                              typ, waznosc, opisy[typ]))
            id_incydentu += 1
            # incydent wysoki/krytyczny → przegląd po incydencie następnego dnia
            if waznosc in ("wysoka", "krytyczna") and dzien < DZIS:
                przeglady.append([id_przegladu, dron[0], random.choice(technicy_bazy[dron[2]]),
                                  dzien + timedelta(days=1), "po_incydencie", "pozytywny",
                                  "Przegląd po incydencie #" + str(id_incydentu - 1),
                                  dzien + timedelta(days=91)])
                id_przegladu += 1

        if status == "zakonczona":
            uzycia_baterii[bateria] = uzycia_baterii.get(bateria, 0) + 1
            nalot_dodany[dron[0]] = nalot_dodany.get(dron[0], 0) + (ladowanie - rzeczywisty_start).seconds / 3600
        if status == "przerwana":
            nalot_dodany[dron[0]] = nalot_dodany.get(dron[0], 0) + (ladowanie - rzeczywisty_start).seconds / 3600
        if status == "w_trakcie":
            dron[7] = "w_misji"
        wolny_od[dron[0]] = planowany_start + timedelta(minutes=minuty_lotu + 30)   # +30 min na wymianę baterii
        id_misji += 1

    kolejka = nieobsluzone
    dzien += timedelta(days=1)

# ---------------------------------------------------------------- liczniki po symulacji
# liczba_cykli baterii i nalot drona zawierają też loty z symulacji (tak samo zrobi trigger)
for b in baterie:
    b[4] += uzycia_baterii.get(b[0], 0)
for d in drony:
    d[6] = round(d[6] + nalot_dodany.get(d[0], 0), 2)

tabele["drony"] = (["id_drona", "id_modelu", "id_bazy", "numer_seryjny", "numer_rejestracyjny",
                    "data_zakupu", "nalot_godziny", "status"], drony)
tabele["baterie"] = (["id_baterii", "id_modelu", "numer_seryjny", "pojemnosc_mah", "liczba_cykli",
                      "stan"], baterie)
tabele["przeglady"] = (["id_przegladu", "id_drona", "id_technika", "data_przegladu", "typ", "wynik",
                        "uwagi", "nastepny_przeglad"], przeglady)
tabele["przesylki"] = (["id_przesylki", "id_klienta", "waga_kg", "dlugosc_cm", "szerokosc_cm",
                        "wysokosc_cm", "adres_odbioru", "odbior_szer_geo", "odbior_dl_geo",
                        "adres_doreczenia", "dorecz_szer_geo", "dorecz_dl_geo", "priorytet",
                        "status", "data_nadania"], przesylki)
tabele["misje"] = (["id_misji", "id_drona", "id_baterii", "id_operatora", "id_dyspozytora",
                    "id_bazy_startowej", "planowany_start", "rzeczywisty_start",
                    "rzeczywiste_ladowanie", "dystans_km", "status"], misje)
tabele["misje_przesylki"] = (["id_misji", "id_przesylki", "kolejnosc", "numer_proby", "wynik",
                              "czas_doreczenia"], misje_przesylki)
tabele["incydenty"] = (["id_incydentu", "id_misji", "czas_wystapienia", "typ", "waznosc", "opis"],
                       incydenty)

# ---------------------------------------------------------------- platnosci (1:1 z przesylki)
platnosci = []
for p in przesylki:
    kwota = 12 + 3.5 * float(p[2]) + {"standard": 0, "ekspres": 10, "medyczna": 20}[p[12]]
    firma = p[1] <= 40
    metoda = random.choice(["faktura", "przelew"]) if firma else random.choice(["karta", "blik", "blik"])
    if p[13] == "anulowana":
        status, data_platnosci = "zwrocona", p[14] + timedelta(minutes=5)
    elif metoda == "faktura" and p[14].date() > DZIS - timedelta(days=14):
        status, data_platnosci = "oczekuje", None       # faktura z 14-dniowym terminem jeszcze nieopłacona
    else:
        status = "oplacona"
        data_platnosci = p[14] + timedelta(minutes=random.randint(1, 10)) if not firma \
            else p[14] + timedelta(days=random.randint(1, 13))
    platnosci.append((p[0], p[0], round(kwota, 2), metoda, data_platnosci, status))
tabele["platnosci"] = (["id_platnosci", "id_przesylki", "kwota_pln", "metoda", "data_platnosci",
                        "status"], platnosci)

# ---------------------------------------------------------------- zapis do dane.sql
# Kolejność tabel = kolejność kluczy obcych (najpierw rodzice, potem dzieci).
kolejnosc = ["bazy", "modele_dronow", "drony", "baterie", "pracownicy", "uprawnienia_pracownikow",
             "klienci", "przesylki", "platnosci", "misje", "misje_przesylki", "przeglady", "incydenty"]
with open("dane.sql", "w", encoding="utf-8") as plik:
    plik.write("-- Dane syntetyczne wygenerowane przez generuj_dane.py (Faker, locale pl_PL)\n")
    plik.write("USE flota_dronow;\nSET NAMES utf8mb4;\n\n")
    for nazwa in kolejnosc:
        kolumny, wiersze = tabele[nazwa]
        plik.write(f"-- {nazwa}: {len(wiersze)} wierszy\n")
        for start in range(0, len(wiersze), 100):              # INSERT po 100 wierszy
            plik.write(f"INSERT INTO {nazwa} ({', '.join(kolumny)}) VALUES\n")
            linie = []
            for wiersz in wiersze[start:start + 100]:
                wartosci = []
                for w in wiersz:
                    if w is None:
                        wartosci.append("NULL")
                    elif isinstance(w, datetime):
                        wartosci.append("'" + w.strftime("%Y-%m-%d %H:%M:%S") + "'")
                    elif isinstance(w, (date, str)):
                        wartosci.append("'" + str(w).replace("'", "''") + "'")
                    else:
                        wartosci.append(str(w))
                linie.append("  (" + ", ".join(wartosci) + ")")
            plik.write(",\n".join(linie) + ";\n")
        plik.write("\n")

for nazwa in kolejnosc:
    print(f"{nazwa:25} {len(tabele[nazwa][1]):5} wierszy")
