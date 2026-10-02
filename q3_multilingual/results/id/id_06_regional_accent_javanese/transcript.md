# Call id-20261002-002142-5a06
- Market: id_multifinance · Channel: simulated · Customer: D001 (mock CRM)
- Disposition: **PTP_ON_TIME** · Verified: True · Tickets: -
- KB lookups: 0 · Guard interventions: 0

**Agent**: Selamat malam, saya Dewi, asisten virtual dari Pundi Mitra Finance. Percakapan ini direkam untuk menjaga kualitas layanan. Apakah saya berbicara dengan Pak Budi?
  - source: fixed_script
**Customer**: Gih, Leres, Kulobudi.
  - ASR: {'intended': 'Nggih, leres, kulo Budi.', 'ms': 267}
**Agent**: Untuk keamanan data, boleh saya konfirmasi tanggal lahir Bapak atau 4 digit terakhir nomor kontrak Bapak?
**Customer**: Lahir Kulo 17 Maret 1991, Mbak, nomor kontrak Kulo Sing Wing King 9.921.
  - ASR: {'intended': 'Lahir kulo 17 Maret 1991, mbak, nomer kontrak kulo sing wingking 9921.', 'ms': 335}
**Agent**: Pak Budi, terima kasih sudah mengonfirmasi. Ini pengingat angsuran pembiayaan motor Honda Vario 160. Angsuran ke-9 sebesar Rp1.250.000 jatuh tempo pada Selasa, 6 Oktober 2026. Apakah Bapak berencana membayar hari ini atau akan menggunakan metode pembayaran lain?
  - tools: verify_identity({"account_last4": "9921", "date_of_birth": "1991-03-17"}); get_loan_details({})
**Customer**: Angsuranipun sampun kulo siap ke, mangke tak bayar lewat Indomaret, sedinten sakderengipun jatuh tempongkih.
  - ASR: {'intended': 'Angsuranipun sampun kulo siapke, mangke tak bayar lewat Indomaret, sedinten sakderengipun jatuh tempo nggih.', 'ms': 437}
**Agent**: Baik Pak Budi, kami catat bahwa Bapak akan membayar angsuran Rp1.250.000 pada Senin, 5 Oktober 2026 lewat Indomaret. Terima kasih atas kesepakatan ini. Apakah ada hal lain yang bisa kami bantu?
  - tools: record_promise_to_pay({"date": "2026-10-05", "mode": "other"})
**Customer**: Maturnuun, Mbak.
  - ASR: {'intended': 'Matur nuwun, Mbak.', 'ms': 244}
**Agent**: Pak Budi, kami akan menunggu pembayaran pada Senin, 5 Oktober 2026 lewat Indomaret. Apakah ada pertanyaan lain atau hal yang ingin Bapak sampaikan?
  - tools: end_call({"disposition": "PTP_ON_TIME", "summary": "Pak Budi mengonfirmasi pembayaran angsuran Rp1.250.000 pada Senin, 5 Oktober 2026 lewat Indomaret."})
**Customer**: Boten-wonten malih, sampun cekap. Maturnuun, Mbak.
  - ASR: {'intended': 'Mboten wonten malih, sampun cekap. Matur nuwun, Mbak.', 'ms': 253}
**Agent**: Terima kasih, Pak Budi. Kami tutup percakapan ini. Selamat malam.

## ASR in the loop (customer voice `jv-ID-DimasNeural`) – WER 41.5%
- said: “Nggih, leres, kulo Budi.”  
  heard: “Gih, Leres, Kulobudi.”
- said: “Lahir kulo 17 Maret 1991, mbak, nomer kontrak kulo sing wingking 9921.”  
  heard: “Lahir Kulo 17 Maret 1991, Mbak, nomor kontrak Kulo Sing Wing King 9.921.”
- said: “Angsuranipun sampun kulo siapke, mangke tak bayar lewat Indomaret, sedinten sakderengipun jatuh tempo nggih.”  
  heard: “Angsuranipun sampun kulo siap ke, mangke tak bayar lewat Indomaret, sedinten sakderengipun jatuh tempongkih.”
- said: “Matur nuwun, Mbak.”  
  heard: “Maturnuun, Mbak.”
- said: “Mboten wonten malih, sampun cekap. Matur nuwun, Mbak.”  
  heard: “Boten-wonten malih, sampun cekap. Maturnuun, Mbak.”