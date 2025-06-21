# Cara Menjalankan Server dan Client
Berikut adalah langkah-langkah untuk menyiapkan dan menjalankan game ini.

## a. Prasyarat
	Pastikan Python 3 sudah terinstal. Anda juga perlu menginstal library pygame untuk client.
`pip install pygame`

## b. Langkah-langkah
### 1. Dapatkan Alamat IP Server:
- Buka Command Prompt (di Windows) atau Terminal (di macOS/Linux) pada komputer yang akan dijadikan server.
- Ketik perintah berikut untuk mengetahui alamat IP lokal Anda:
  - Windows: ipconfig (Cari alamat IPv4 di bawah koneksi Wi-Fi atau Ethernet Anda).
  - macOS/Linux: ifconfig atau ip a (Cari alamat inet).
  - Catat alamat IP ini (misalnya: 192.168.1.5).

### 2. Konfigurasi Client:
- Buka file client.py dengan editor teks.
- Ubah alamat IP di baris berikut dengan alamat IP yang Anda catat pada Langkah 1.
```
# Ubah '192.168.0.31' dengan IP server Anda
self.server_address = ('192.168.1.5', 55555)
```
- Simpan file tersebut. Lakukan ini pada semua file client.py jika Anda akan bermain dari beberapa komputer.

### 3. Jalankan Server:
Pada komputer server, navigasikan ke direktori tempat file-file game disimpan melalui terminal.
Jalankan server dengan perintah: 
`python server.py`

Anda akan melihat output yang menandakan server telah berjalan dan siap menerima koneksi.
```
==================================================
🎮 TUG OF WAR GAME SERVER STARTED
==================================================
📡 Listening on port 55555
🔗 Connect clients to: localhost:55555
==================================================
```

### 4. Jalankan Client:
- Pada setiap komputer client (atau di terminal baru pada komputer yang sama), navigasikan ke direktori game.
- Jalankan client dengan perintah: 
`python client.py`
- Sebuah window Pygame akan terbuka. Ulangi langkah ini untuk setiap pemain yang ingin bergabung. Server akan secara otomatis menyeimbangkan jumlah pemain di tim kiri dan kanan.

### 5. Mulai Bermain:
- Setelah ada minimal satu pemain di setiap tim, salah satu pemain dapat menekan tombol SPACE untuk memulai permainan.
- Pemain di tim kiri menekan tombol 'A' untuk menarik.
- Pemain di tim kanan menekan tombol 'D' untuk menarik.
- Permainan berakhir ketika salah satu tim berhasil menarik bar ke ujung atau ketika waktu habis. Game akan otomatis restart setelah 5 detik.

## Preview Aplikasi
### Client 1 
<img width="1101" alt="Screenshot 2025-06-21 at 12 17 48" src="https://github.com/user-attachments/assets/10d662b7-502f-4298-8ba5-e2370481db1d" /> <br> 
### Client 2
<img width="864" alt="Screenshot 2025-06-21 at 12 18 31" src="https://github.com/user-attachments/assets/797a1267-075f-46c7-ac94-f49543a38c2b" />


