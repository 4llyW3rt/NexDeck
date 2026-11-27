# Testler

Gerçek ayarlara dokunmadan, geçici bir veri klasörüyle çalışır.

```powershell
python tests\smoke_test.py . $env:TEMP\nex-test $env:TEMP\nex-shots
python tests\sendinput_hook_test.py . $env:TEMP\nex-test
```

- `smoke_test.py`: thread-güvenli log, makro kuyruğu, bayat görev atma, çift sinyal engeli, firmware kimliği,
  profil geçişi, atomik config + yedekten dönüş, kopma/yeniden bağlanma, eklenti yükleme. Her sayfanın ekran görüntüsünü alır.
  Not: bozuk config testi `logs/error.log`'a bilerek bir Traceback yazar.
- `sendinput_hook_test.py`: F24 tuşunu gönderir, düşük seviye klavye hook'u ile scan code ve basılı kalma süresini ölçer.
