-- Schemat bazy flota_dronow (MySQL 8.0.16+), odtworzony z punktu 4
DROP DATABASE IF EXISTS flota_dronow;
CREATE DATABASE flota_dronow CHARACTER SET utf8mb4 COLLATE utf8mb4_polish_ci;
USE flota_dronow;

CREATE TABLE bazy (
  id_bazy INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  nazwa VARCHAR(80) NOT NULL UNIQUE,
  adres VARCHAR(150) NOT NULL,
  szerokosc_geo DECIMAL(9,6) NOT NULL,
  dlugosc_geo DECIMAL(9,6) NOT NULL,
  liczba_ladowisk TINYINT UNSIGNED NOT NULL CHECK (liczba_ladowisk > 0),
  liczba_stanowisk_ladowania TINYINT UNSIGNED NOT NULL
);

CREATE TABLE modele_dronow (
  id_modelu INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  producent VARCHAR(60) NOT NULL,
  nazwa_modelu VARCHAR(60) NOT NULL,
  max_udzwig_kg DECIMAL(5,2) NOT NULL CHECK (max_udzwig_kg > 0),
  zasieg_km DECIMAL(5,1) NOT NULL CHECK (zasieg_km > 0),
  predkosc_kmh SMALLINT UNSIGNED NOT NULL,
  limit_cykli_baterii SMALLINT UNSIGNED NOT NULL DEFAULT 300,
  UNIQUE (producent, nazwa_modelu)
);

CREATE TABLE drony (
  id_drona INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  id_modelu INT UNSIGNED NOT NULL,
  id_bazy INT UNSIGNED NOT NULL,
  numer_seryjny VARCHAR(40) NOT NULL UNIQUE,
  numer_rejestracyjny VARCHAR(20) NOT NULL UNIQUE,
  data_zakupu DATE NOT NULL,
  nalot_godziny DECIMAL(7,2) NOT NULL DEFAULT 0,
  status ENUM('dostepny','w_misji','w_serwisie','wycofany') NOT NULL DEFAULT 'dostepny',
  FOREIGN KEY (id_modelu) REFERENCES modele_dronow(id_modelu) ON DELETE RESTRICT,
  FOREIGN KEY (id_bazy) REFERENCES bazy(id_bazy) ON DELETE RESTRICT
);

CREATE TABLE baterie (
  id_baterii INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  id_modelu INT UNSIGNED NOT NULL,
  numer_seryjny VARCHAR(40) NOT NULL UNIQUE,
  pojemnosc_mah INT UNSIGNED NOT NULL CHECK (pojemnosc_mah > 0),
  liczba_cykli SMALLINT UNSIGNED NOT NULL DEFAULT 0,
  stan ENUM('sprawna','do_wymiany','wycofana') NOT NULL DEFAULT 'sprawna',
  FOREIGN KEY (id_modelu) REFERENCES modele_dronow(id_modelu) ON DELETE RESTRICT
);

CREATE TABLE pracownicy (
  id_pracownika INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  id_bazy INT UNSIGNED NOT NULL,
  imie VARCHAR(50) NOT NULL,
  nazwisko VARCHAR(60) NOT NULL,
  email VARCHAR(100) NOT NULL UNIQUE,
  telefon VARCHAR(20) NULL,
  stanowisko ENUM('operator','dyspozytor','technik') NOT NULL,
  data_zatrudnienia DATE NOT NULL,
  FOREIGN KEY (id_bazy) REFERENCES bazy(id_bazy) ON DELETE RESTRICT
);

CREATE TABLE uprawnienia_pracownikow (
  id_pracownika INT UNSIGNED NOT NULL,
  id_modelu INT UNSIGNED NOT NULL,
  data_uzyskania DATE NOT NULL,
  data_waznosci DATE NOT NULL,
  PRIMARY KEY (id_pracownika, id_modelu),
  CHECK (data_waznosci > data_uzyskania),
  FOREIGN KEY (id_pracownika) REFERENCES pracownicy(id_pracownika) ON DELETE CASCADE,
  FOREIGN KEY (id_modelu) REFERENCES modele_dronow(id_modelu) ON DELETE CASCADE
);

CREATE TABLE klienci (
  id_klienta INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  typ ENUM('firma','osoba') NOT NULL,
  nazwa VARCHAR(120) NOT NULL,
  nip CHAR(10) NULL UNIQUE,
  email VARCHAR(100) NOT NULL UNIQUE,
  telefon VARCHAR(20) NULL,
  adres VARCHAR(150) NOT NULL,
  data_rejestracji DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE przesylki (
  id_przesylki INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  id_klienta INT UNSIGNED NOT NULL,
  waga_kg DECIMAL(5,2) NOT NULL CHECK (waga_kg > 0),
  dlugosc_cm SMALLINT UNSIGNED NOT NULL,
  szerokosc_cm SMALLINT UNSIGNED NOT NULL,
  wysokosc_cm SMALLINT UNSIGNED NOT NULL,
  adres_odbioru VARCHAR(150) NOT NULL,
  odbior_szer_geo DECIMAL(9,6) NOT NULL,
  odbior_dl_geo DECIMAL(9,6) NOT NULL,
  adres_doreczenia VARCHAR(150) NOT NULL,
  dorecz_szer_geo DECIMAL(9,6) NOT NULL,
  dorecz_dl_geo DECIMAL(9,6) NOT NULL,
  priorytet ENUM('standard','ekspres','medyczna') NOT NULL DEFAULT 'standard',
  status ENUM('oczekuje','w_locie','doreczona','anulowana') NOT NULL DEFAULT 'oczekuje',
  data_nadania DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (id_klienta) REFERENCES klienci(id_klienta) ON DELETE RESTRICT
);

CREATE TABLE platnosci (
  id_platnosci INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  id_przesylki INT UNSIGNED NOT NULL UNIQUE,
  kwota_pln DECIMAL(8,2) NOT NULL CHECK (kwota_pln >= 0),
  metoda ENUM('karta','blik','przelew','faktura') NOT NULL,
  data_platnosci DATETIME NULL,
  status ENUM('oczekuje','oplacona','zwrocona') NOT NULL DEFAULT 'oczekuje',
  FOREIGN KEY (id_przesylki) REFERENCES przesylki(id_przesylki) ON DELETE RESTRICT
);

CREATE TABLE misje (
  id_misji INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  id_drona INT UNSIGNED NOT NULL,
  id_baterii INT UNSIGNED NOT NULL,
  id_operatora INT UNSIGNED NOT NULL,
  id_dyspozytora INT UNSIGNED NOT NULL,
  id_bazy_startowej INT UNSIGNED NOT NULL,
  planowany_start DATETIME NOT NULL,
  rzeczywisty_start DATETIME NULL,
  rzeczywiste_ladowanie DATETIME NULL,
  dystans_km DECIMAL(5,2) NULL,
  status ENUM('zaplanowana','w_trakcie','zakonczona','przerwana') NOT NULL DEFAULT 'zaplanowana',
  CHECK (rzeczywiste_ladowanie > rzeczywisty_start),
  FOREIGN KEY (id_drona) REFERENCES drony(id_drona) ON DELETE RESTRICT,
  FOREIGN KEY (id_baterii) REFERENCES baterie(id_baterii) ON DELETE RESTRICT,
  FOREIGN KEY (id_operatora) REFERENCES pracownicy(id_pracownika) ON DELETE RESTRICT,
  FOREIGN KEY (id_dyspozytora) REFERENCES pracownicy(id_pracownika) ON DELETE RESTRICT,
  FOREIGN KEY (id_bazy_startowej) REFERENCES bazy(id_bazy) ON DELETE RESTRICT
);

CREATE TABLE misje_przesylki (
  id_misji INT UNSIGNED NOT NULL,
  id_przesylki INT UNSIGNED NOT NULL,
  kolejnosc TINYINT UNSIGNED NOT NULL,
  numer_proby TINYINT UNSIGNED NOT NULL DEFAULT 1,
  wynik ENUM('w_drodze','doreczona','zwrocona') NOT NULL DEFAULT 'w_drodze',
  czas_doreczenia DATETIME NULL,
  PRIMARY KEY (id_misji, id_przesylki),
  FOREIGN KEY (id_misji) REFERENCES misje(id_misji) ON DELETE CASCADE,
  FOREIGN KEY (id_przesylki) REFERENCES przesylki(id_przesylki) ON DELETE CASCADE
);

CREATE TABLE przeglady (
  id_przegladu INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  id_drona INT UNSIGNED NOT NULL,
  id_technika INT UNSIGNED NOT NULL,
  data_przegladu DATE NOT NULL,
  typ ENUM('okresowy','po_incydencie','naprawa') NOT NULL,
  wynik ENUM('pozytywny','negatywny') NOT NULL,
  uwagi TEXT NULL,
  nastepny_przeglad DATE NOT NULL,
  CHECK (nastepny_przeglad > data_przegladu),
  FOREIGN KEY (id_drona) REFERENCES drony(id_drona) ON DELETE RESTRICT,
  FOREIGN KEY (id_technika) REFERENCES pracownicy(id_pracownika) ON DELETE RESTRICT
);

CREATE TABLE incydenty (
  id_incydentu INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  id_misji INT UNSIGNED NOT NULL,
  czas_wystapienia DATETIME NOT NULL,
  typ ENUM('utrata_gps','twarde_ladowanie','niska_bateria','kolizja','inny') NOT NULL,
  waznosc ENUM('niska','srednia','wysoka','krytyczna') NOT NULL,
  opis TEXT NULL,
  FOREIGN KEY (id_misji) REFERENCES misje(id_misji) ON DELETE CASCADE
);
