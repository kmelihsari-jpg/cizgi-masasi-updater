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
17-22: saatte 1 (:05) | 22-05: 30 dk (:05, :35) | 05-17: kapali
Gunde 19 tetikleme (eskiden 39). Iddaa (17-20 :05) ve karne (18-20, :05 tikinden 10 dk sonra) saatleri degismedi.

## Bakim
- `STALE_DK`: icerik ayni kalsa bile D1'deki rapor saati bu kadar dakika geride kalirsa tetikler (0 = kapali).
- Test: `node tests/sakatlik_tetik.test.mjs` (ag ve Actions kullanmaz).
