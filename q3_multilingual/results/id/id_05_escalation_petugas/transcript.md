# Call id-20261001-223325-a703
- Market: id_multifinance · Channel: simulated · Customer: D002 (mock CRM)
- Disposition: **ESCALATED** · Verified: True · Tickets: ['ESC-DC0DA5', 'CB-B434D6']
- KB lookups: 0 · Guard interventions: 1

**Agent**: Selamat malam, saya Dewi, asisten virtual dari Pundi Mitra Finance. Percakapan ini direkam untuk menjaga kualitas layanan. Apakah saya berbicara dengan Bu Siti?
  - source: fixed_script
**Customer**: Ya, ini Bu Siti Rahayu.
  - ASR: {'intended': 'Ya, ini Bu Siti Rahayu.', 'ms': 246}
**Agent**: Baik, Bu Siti. Untuk keamanan data, boleh saya konfirmasi tanggal lahir Ibu, atau 4 digit terakhir nomor kontrak?
**Customer**: Tanggal lahir saya 25 Agustus 1993, dan 4 digi terakhir nomor kontrak 1178.
  - ASR: {'intended': 'Tanggal lahir saya 25 Agustus 1993, dan 4 digit terakhir nomor kontrak 1178.', 'ms': 405}
**Agent**: Baik, Bu. Saya verifikasi dulu ya.
**Customer**: Baik, terima kasih. Saya mau bicara langsung sama petugas, Mbak. Minta di telepon besok jam 10 pagi.
  - ASR: {'intended': 'Baik, terima kasih. Saya mau bicara langsung sama petugas, Mbak. Minta ditelepon besok jam 10 pagi.', 'ms': 336}
**Agent**: Baik, Bu Siti, kami akan menghubungi kembali Ibu pada hari kerja berikutnya. Apakah Ibu ingin menentukan jam spesifik untuk panggilan kembali?
  - tools: verify_identity({"account_last4": "1178", "date_of_birth": "1993-08-25"}); escalate_to_human({"details": "Bu Siti meminta berbicara dengan petugas pada besok jam 10 pagi", "reason": "human_request"})
**Customer**: Ya, tolong hubungi saya besok jam 10 pagi. Terima kasih.
  - ASR: {'intended': 'Ya, tolong hubungi saya besok jam\u202f10\u202fpagi. Terima kasih.', 'ms': 267}
**Agent**: Kami sudah jadwalkan panggilan kembali pada Sabtu, 3 Oktober 2026 pukul 10 pagi; terima kasih atas waktunya, selamat malam.
  - tools: schedule_callback({"date": "2026-10-03", "reason": "Minta bicara dengan petugas", "time": "10:00"}); end_call({"disposition": "CALLBACK_SCHEDULED", "summary": "Bu Siti meminta bicara dengan petugas; callback dijadwalkan Sabtu, 3 Oktober 2026 jam 10:00 (tiket ESC-DC0DA5, CB-B434D6)."})

## Grounding guard interventions
- ungrounded numbers: ['10.00', '1000'] → regenerate  (draft: “Terima kasih, Bu Siti, data Ibu sudah terverifikasi. Saya catat permintaan Ibu untuk dihubungi petugas besok, Sabtu, 3 Oktober pukul 10.00 pagi ya.”)

## ASR in the loop (customer voice `id-ID-ArdiNeural`) – WER 6.8%
- said: “Ya, ini Bu Siti Rahayu.”  
  heard: “Ya, ini Bu Siti Rahayu.”
- said: “Tanggal lahir saya 25 Agustus 1993, dan 4 digit terakhir nomor kontrak 1178.”  
  heard: “Tanggal lahir saya 25 Agustus 1993, dan 4 digi terakhir nomor kontrak 1178.”
- said: “Baik, terima kasih. Saya mau bicara langsung sama petugas, Mbak. Minta ditelepon besok jam 10 pagi.”  
  heard: “Baik, terima kasih. Saya mau bicara langsung sama petugas, Mbak. Minta di telepon besok jam 10 pagi.”
- said: “Ya, tolong hubungi saya besok jam 10 pagi. Terima kasih.”  
  heard: “Ya, tolong hubungi saya besok jam 10 pagi. Terima kasih.”