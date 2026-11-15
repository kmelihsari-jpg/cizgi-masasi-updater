# iddaa barem arsivi (sadece-ekleme)

Her satir bir JSON dizisi: `[cekim_unix_sn, oyuncu_id, "MARKET", barem, oran, mac_baslama_unix_sn, "kaynak"]`.
Dosyalar `lines-YYYY-MM.ndjson` (ay basina bir tane). `log.ndjson` her ise yarayan calismanin ozetidir.

Kurallar:
- Mevcut satirlar degistirilmez ve silinmez; betik (`scripts/iddaa_archive.py`) yalnizca dosya sonuna ekler.
- Bir barem ilk goruldugunde ya da orani degistiginde yeni satir eklenir. Ayni oran tekrar gorulurse hicbir sey yazilmaz.
- Bir baremin o maca kadar gecen son satiri kapanis oranidir; ayni oyuncu/market/barem farkli gunlerde farkli `mac_baslama` ile ayri tutulur.
- Kaynak `import-*` olanlar sonradan eklenen eski goruntulerdir (13 Kasim: yuklenen dosya, 14 Kasim: artifact `inj/iddaa` belgesi, 15 Kasim: git goruntuleri).
- Not: 5-12 Kasim arasi ve 14 Kasim gunduzu icin goruntu bulunamadi.
- Senkron calismasi 18:30, 19:30, 20:30 (Istanbul) oldugu icin bu saatler arasindaki oran degisimleri kayda girmez.
