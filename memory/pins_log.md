
## 2026-02-26

- Pinů postováno: 12
- Pinů selhalo: 0
- Kie.ai obrázky: 0
- Placeholdery: 0

### Detaily:
- [PohadkoveTipyCZ] LEGO Disney Popelka: OK
- [PohadkoveTipyCZ] Interaktivní plyšák: OK
- [PohadkoveTipyCZ] Vzdělávací puzzle svět: OK
- [HomeDekorCZ] Makramé dekorace: OK
- [HomeDekorCZ] Aromatické svíčky: OK
- [HomeDekorCZ] Betonové misky: OK
- [FitnessMotivaceCZ] Rostlinný protein: OK
- [FitnessMotivaceCZ] Prémiová jógová podložka: OK
- [FitnessMotivaceCZ] Smart fitness hodinky: OK
- [TechGadgetsCZ] Mini projektor: OK
- [TechGadgetsCZ] Bezdrátová nabíječka 3v1: OK
- [TechGadgetsCZ] Smart LED pásky: OK

### Poznámky:
- Amazon tag: pohadkove-21 (placeholder)
- Awin API: chybí key
- AliExpress: čeká na API

## 2026-02-27 (pátek)

**@PohadkoveTipyCZ — 5 pinů zveřejněno**

| Produkt | Keyword | Cena | Status |
|---------|---------|------|--------|
| Crystal HD Transparent Magsafe Case | pohádková hračka | 59 Kč | ✅ |
| Mini Wooden Kong Ming Lock (puzzle) | puzzle pro děti | 31 Kč | ✅ |
| Montessori Wooden Animal Puzzle | puzzle pro děti | 48 Kč | ✅ |
| World Kid Cartoon Toys Stickers | fairy tale toys | 27 Kč | ✅ |
| Mini Retro Wigwam Fairy Garden | fairy tale toys | 3 Kč | ✅ |

**Opravy provedené dnes:**
- Fix: AliExpress API podpis (md5 místo hmac-sha256) → API teď vrací produkty
- Fix: Chrome profil kopírování (ignorovat Singleton sockety)

**Problém:** AliExpress tracking_id "pohadkovetipycz" vrací 402 error → affiliate linky jsou fallback (přímé URL, bez komise). Potřeba schválit tracking ID v AliExpress Portals dashboardu.

**Poznámka:** Produkty nejsou vždy perfektně v niche (phone case místo hračky) — API sortuje price_asc a vrací co odpovídá klíčovému slovu volně. Zvážit použití category_ids nebo jiné klíčové slovo.
