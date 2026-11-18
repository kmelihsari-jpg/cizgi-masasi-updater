# cizgi-sakatlik-tetik: degisim kontrollu tetikleme

`sakatlik-tetik.js` mevcut `cizgi-sakatlik-tetik` Worker'inin yerine gecer. Cron saatleri, iddaa ve karne
tetiklemeleri aynidir. Tek fark: sakatlik workflow'u artik yalniz NBA raporunun ICERIGI degistiyse
(ya da emin olunamiyorsa) tetiklenir. Okuma/D1/resmi kaynak onceligi `nba-official-sync.yml`'de ayni kalir.

## Guvenli gecis (eski Worker'a dokunmadan test)
1. Cloudflare > Workers > Create > yeni Worker: `cizgi-sakatlik-tetik-v2`. Kodu `sakatlik-tetik.js` ile degistir.
2. Settings > Bindings: KV namespace `cizgi-sakatlik-durum` -> degisken adi `SAKATLIK_KV`.
   Secret'lar: eskisinden `GITHUB_TOKEN` ve `TEST_KEY` degerlerini kopyala. (Istege bagli: `STALE_DK`, varsayilan 60.)
3. Test (GitHub'a dokunmaz): `https://cizgi-sakatlik-tetik-v2.<hesap>.workers.dev/?k=TEST_KEY&is=kontrol`
   - "ATLANDI: ..." ya da "TETIKLENIRDI: ilk calisma" gibi bir metin donmeli.
   - "Error 1102 / Worker exceeded resource limits" donerse CPU limiti asildi: GECME, eski Worker'da kal.
   - Birkac kez dene; Dashboard > Metrics'te CPU time 10 ms altinda olmali.
4. Gecis: v2'ye TEK cron ekle: `5,20,35,50 * * * *` (UTC). Saat plani kodda (`SAKATLIK_SLOTLARI`), cron'da degil.
   SONRA eski Worker'dan tum cron'lari sil (ikisi ayni anda calismasin). Ucretsiz planda hesap basina 5 cron siniri var; bu 3 yerine 1 slot kullanir.
5. Geri donus: eski Worker'a cron'lari geri ekle, v2'den sil.

## Sakatlik saat plani (Istanbul)
17-22: saatte 1 (:05) | 22-00: 30 dk (:05, :35) | 00-03: 15 dk (:05, :20, :35, :50) | 03-05: 30 dk | 05-17: kapali
Gunde 25 tetikleme (18 Kasim 2026'dan beri; once 19, en basta 39). Iddaa (17-20 :05) ve karne (18-20, :05 tikinden 10 dk sonra) saatleri degismedi.

## Parmak izi (VARSAYILAN KAPALI)
Workers ucretsiz planinda olcum: P50 ~7.9 ms, P99 ~13 ms (sinir 10 ms). Bu yuzden kod varsayilan olarak parmak izi KULLANMAZ;
sakatlik workflow'u her sakatlik slotunda kosulsuz tetiklenir. Takvim tasarrufu (39 -> 19 tetik/gun) bundan bagimsiz gecerlidir.
Acmak icin ortam degiskeni `PARMAK_IZI=1` (KV baglamasi `SAKATLIK_KV` gerekir). Ucretsiz planda ACMA.

## Bakim
- `STALE_DK`: icerik ayni kalsa bile D1'deki rapor saati bu kadar dakika geride kalirsa tetikler (0 = kapali).
- Test: `node tests/sakatlik_tetik.test.mjs` (ag ve Actions kullanmaz).
