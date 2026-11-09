# Historia zmian

Każde wydanie na GitHubie ma ten sam opis w zakładce Releases.

## Revo OS – ekran maszyny 1.4.0 · linia BELT

### Zmiany
- Ekran rozpoznaje typ maszyny (Belt / sztywny stół) i pokazuje pasujące elementy. Na Belcie wszystko działa jak w 1.3.0.
- Aktualizacje ekranu z gałęzi `belt`.

## Revo OS – ekran maszyny 1.4.0 · linia STÓŁ (600×600 / 1200×600, Z400 / Z600)

Pierwsze wydanie ekranu dla maszyn ze sztywnym stołem.

### W tej linii
- Kafelek **STÓŁ** zamiast PAS, rysunek maszyny ze sztywnym stołem na ekranie głównym.
- Bez sterowania pasem w panelu Ruch, bez wysuwania wydruku i bez serii wydruków.
- Test maszyny z obrazkami dla sztywnego stołu.
- Wszystko inne jak w linii Belt: przytrzymanie − / +, ekran po druku, wygaszacz, wersja angielska.

## Revo OS – ekran maszyny 1.3.0

### Nowe
- **Przytrzymanie − / + w oknie temperatury** – im dłużej trzymasz, tym szybciej się zmienia (1° → 5° → 10°).
- **Ekran po druku**: wynik (zakończony / anulowany / błąd), czas druku i zużyty filament oraz przyciski:
  - **WYSUŃ WYDRUK** – pas jedzie, dopóki trzymasz palec,
  - **DRUKUJ PONOWNIE**, **EKRAN GŁÓWNY**.
- **Wysuwanie pasa przytrzymaniem** także w panelu Ruch.
- **Wygaszacz** po 5 min: czarny ekran z przygaszoną godziną, stanem maszyny i temperaturami. Dotknięcie budzi.
- **Seria wydruków**: pole SZTUK przy starcie druku, licznik „w kolejce jeszcze N szt.” w trakcie druku.
- **Wersja angielska** ekranu Revo (Menu → Ustawienia ekranu → Język → English), wspólny słownik z Panelem Revo.

## Revo OS – ekran maszyny 1.2.0

### Nowe
- **Panel testu maszyny**: obrazek kroku, opis, pasek postępu, numer kroku, liczba pozostałych kroków i szacowany czas do końca, przyciski odpowiedzi (DZIAŁA / PROBLEM / PRZERWIJ, wybór przyczyny, POWTÓRZ / DALEJ).
- Ekran sam otwiera panel testu, gdy test zostanie uruchomiony z Panelu Revo lub konsoli.
- Podgląd temperatury na żywo w krokach grzania.

### Zmiany
- Menu: jedna pozycja „Test maszyny” zamiast testu szybkiego i fabrycznego.
