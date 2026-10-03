# Nahimic Linux — نسخه فارسی

افکت‌های صوتی Nahimic برای بلندگوی داخلی لپتاپ روی لینوکس. چهار پروفایل Music، Movie، Gaming و Communication، کنترل بم/صدا/ treble، صدای环绕، تثبیت ولوم و EQ ده‌باند. پروژه مستقل است و ارتباطی با Nahimic، A-Volute، SteelSeries یا سازندگان لپتاپ ندارد.

این فورک علاوه بر پشتیبانی **Realtek ALC256**، از **Realtek ALC274** (مثل MSI Stealth 14 Studio A13VF با Intel SOF) و اسکریپت نصب برای **Arch** و **Debian/Ubuntu** هم پشتیبانی می‌کند. متن اصلی پروژه انگلیسی است: [README.md](README.md).

## این پروژه چطور کار می‌کند

Nahimic روی ویندوز یک COM DLL به نام `NahimicAPO4.dll` است (نه یک درایور کرنلی). این پروژه همان DLL واقعی A-Volute را زیر Wine بارگذاری می‌کند، پارامترها را از API رسمی‌اش می‌خواند و صدا را بلوک‌به‌بلوک از `APOProcess()` عبور می‌دهد. یعنی **پردازش DSP واقعی ناهیمیک اجرا می‌شود**، نه بازپیاده‌سازی آن.

```
اپلیکیشن → PipeWire → pulse → Wine → NahimicAPO4.dll (DSP واقعی) → بلندگو
```

## پیش‌نیازها

- لپتاپ ۶۴ بیتی با PipeWire و WirePlumber 0.5+
- Wine، PySide6
- یک اسپیکر داخلی پشتیبانی‌شده (جدول `host/devices.json`)

## گام ۱: بررسی سخت‌افزار

هیچ تغییری در سیستم داده نمی‌شود. هدفون را جدا کنید، بلندگوی داخلی را به‌عنوان خروجی انتخاب کنید، بعد:

```sh
pactl list sinks | grep -E "Name:|alsa.components|Active Port"
```

روی همان سینک بلندگو باید داشته باشید:

| مورد | مقدار لازم |
|---|---|
| پورت | `[Out] Speaker` یا `analog-output-speaker` |
| سخت‌افزار | `HDA:10ec0274,146213c0,` (MSI Stealth 14 Studio A13VF) یا `HDA:10ec0256,...` (ALC256) یا `HDA:14f11f87,1d05e022,` (MECHREVO) |

روی لپتاپ‌های Intel SOF چند کدک در `alsa.components` فهرست می‌شود؛ مهم کدک آنالوگ است، نه HDMI.

## گام ۲: نصب

Arch:

```sh
git clone https://github.com/mahdishariatzade/nahimic-linux.git
cd nahimic-linux/packaging && makepkg -si
```

Debian / Ubuntu:

```sh
git clone https://github.com/mahdishariatzade/nahimic-linux.git
cd nahimic-linux
./packaging/install-ubuntu.sh
```

هر دو مسیر فایل‌های runtime را از Microsoft Update و سایت پشتیبانی Nahimic دانلود، SHA-256 آن‌ها را بررسی، پروژه را بیلد و زیر `/usr` نصب و سرویس کاربر را فعال می‌کنند.

اگر وابستگی‌ها را دستی نصب کرده‌اید: `SKIP_DEPS=1 ./packaging/install-ubuntu.sh`

## گام ۳: بررسی کارکرد

```sh
nahimic --status          # باید ready/enabled/active هر سه true باشند
systemctl --user status nahimic.service
journalctl --user -u nahimic.service -b
```

`active` فقط وقتی true است که صدایی واقعاً در حال پخش باشد.

## افزودن لپتاپ خودتان

جدول سخت‌افزار یک JSON ساده است و هنگام اجرا خوانده می‌شود؛ برای لپتاپ خودتان نیازی به بیلد مجدد نیست. فایل `~/.config/nahimic-linux/devices.json` بسازید (بر بیلد اصلی ارجاع دارد و با آپدیت پاک نمی‌شود):

```json
{
  "devices": [
    {
      "name": "My laptop",
      "codec": "10ec0274",
      "subsystem": "146213c0",
      "device_file": "/home/USER/146213C0_InternalSpeakers.nsx",
      "verified": false
    }
  ]
}
```

`tuning` واقعی مدل شما معمولاً در فایل‌های درایور ویندوز است:

```
C:\Windows\System32\DriverStore\FileRepository\...\NT3ProductSettings*.cab
  └── Devices/<SUBSYSTEM ID>_InternalSpeakers.nsx
```

کاب را با `cabextract` باز کنید و مسیر فایل را در `device_file` بگذارید، سپس:

```sh
systemctl --user stop nahimic.service
rm -rf ~/.local/share/nahimic-linux/runtime ~/.local/share/nahimic-linux/installation.json
nahimic --activate
```

## سخت‌افزار پشتیبانی‌شده

| مدل | کدک | subsystem | وضعیت |
|---|---|---|---|
| MECHREVO Wujie 14X Pro | `14f11f87` | `1d05e022` | verified |
| لپتاپ‌های ALC256 | `10ec0256` | `1c05c022` | آزمایشی |
| MSI Stealth 14 Studio A13VF | `10ec0274` | `146213c0` | آزمایشی |

`verified: false` یعنی روی آن سخت‌افزار تست نشده. برای MSI فایل تیونینگ واقعی همان مدل استفاده می‌شود (`Devices/146213C0_InternalSpeakers.nsx`)، ولی تا وقتی روی خود دستگاه تأیید نشود آزمایشی باقی می‌ماند.