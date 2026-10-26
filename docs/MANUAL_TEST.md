# Manual test checklist (R1)

Run `python bot.py`, then go through this in Telegram. Each line maps to a PRD acceptance criterion.
Unit tests (`pytest`) cover the rules themselves: BR-02 to BR-05, formatting, and the database.

## FR-01 Owner only
- [ ] From a second account (or a friend): `/start`, `/catat`, and random text get **no reply**
- [ ] From my account: every command below works
- [ ] Remove `OWNER_ID` from `.env`, then run `python bot.py`. It exits with "OWNER_ID belum diisi". Put it back.

## FR-05 Start and help
- [ ] `/start` and `/help` list every command
- [ ] Typing `/` shows the command menu (restart Telegram if it doesn't show up right away)

## FR-02 `/catat`
- [ ] `/catat` asks "Kategori?" with 6 category buttons (category comes first)
- [ ] Typing text instead of tapping says "Pilih dari tombol di atas ya."
- [ ] Tapping a category asks "Apa yang kamu beli?"
- [ ] An item over 100 characters is rejected, and I stay on the item step
- [ ] A valid item shows the account buttons, then the account tap asks "Berapa?"
- [ ] `abc`, `25rb`, `25.000`, `0`, `-5`, `100000001` are each rejected, and I stay on the amount step
- [ ] `25000` saves and replies `✅ <item> (<category>) Rp25.000`
- [ ] Start `/catat`, wait 5 minutes: "Waktu habis" message, nothing saved, next text gets the `/help` hint

## FR-03 `/batal`
- [ ] `/catat` → item → `/batal` replies "Dibatalkan." and `/total` is unchanged

## FR-04 Totals
- [ ] `/total` opens the `/bulan` report

## FR-06 `/hapus`
- [ ] `/hapus` shows the newest entry with "Ya, hapus" and "Batal"
- [ ] "Batal" deletes nothing
- [ ] "Ya, hapus" deletes it and confirms
- [ ] Tapping "Ya, hapus" on an **old** `/hapus` message after adding a new entry says "Catatan terakhir sudah berubah"
- [ ] With no entries: "Belum ada catatan untuk dihapus."

## FR-07 Unknown input
- [ ] Random text or `/xyz` outside a flow gets the `/help` hint
- [ ] Inside `/catat`, item text is NOT answered with the hint

## Logging
- [ ] The terminal never shows the token (look for `bot<digits>:` in any URL)

# R2: Real tracker

## FR-08 Accounts
- [ ] `/akun` → `CIMB` → current balance → "✅ Akun CIMB ditambahkan"
- [ ] `/akun` → `cimb` again → "sudah ada"
- [ ] Add all accounts I use (SeaBank, GoPay, Cash, …) with their **real** balances
- [ ] `/saldo` matches each real app

## FR-09 `/catat` with account
- [ ] After the item, account buttons appear; the last-used account comes first
- [ ] Reply shows `(Kategori, Akun)`; `/saldo` drops by that amount

## FR-10 / FR-11 Income and transfer
- [ ] `/masuk` → `Gaji` → CIMB → amount: CIMB goes up
- [ ] `/pindah` → CIMB → GoPay (CIMB is not in the second list) → amount: CIMB down, GoPay up, total unchanged
- [ ] `/bulan` does NOT count the transfer as spending

## FR-12 / FR-13 Cycle and budget
- [ ] `/bulan` title is the current cycle (e.g. `27 Okt - 26 Nov 2026`)
- [ ] ◀ shows the previous cycle, ▶ comes back; no ▶ on the current cycle
- [ ] `/budget Makan 1500000` → bar at 0%; a `/catat` Makan shows the bar under the ✅
- [ ] Past 80% shows ⚠️, past 100% shows 🚨
- [ ] `/budget Makan 0` removes it

## FR-14 Undo any kind
- [ ] After a `/pindah`, `/hapus` shows the transfer; "Ya, hapus" restores both balances

# R2.5: Keep the numbers right

## FR-15 `/riwayat`
- [ ] Shows my latest entries, newest first; "Lebih lama ▶" after 8
- [ ] Tap an entry → change the amount → `/saldo` and `/bulan` follow
- [ ] Change the category and the account with buttons
- [ ] Delete an **old** entry (not the last) after confirming

## FR-16 `/sesuaikan`
- [ ] Pick CIMB, type the real balance from the CIMB app → `/saldo` now matches; `/bulan` spending unchanged

## FR-17 `/hutang`
- [ ] "Aku pinjamkan / talangi" → new name → account → amount → "X berutang ke kamu"
- [ ] "Dia bayar ke aku" shows only people who owe me and how much is left; paying it all says "Lunas"
- [ ] "Aku pinjam" and "Aku bayar hutang" work the other way
- [ ] `/bulan` does not count any of these as spending or income

## FR-18 `/langganan`
- [ ] ➕ Tambah: Netflix → Hiburan → CIMB → 54000 → day
- [ ] On the due day (or when the laptop wakes up after it) the reminder arrives once
- [ ] ✅ Sudah bayar logs it; tapping again says "Sudah dicatat"
- [ ] ✏️ Jumlahnya beda asks the amount (for bills like listrik)
- [ ] 🗑 removes it from the list
