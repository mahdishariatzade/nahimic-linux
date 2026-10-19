# Nahimic Linux — نسخه فارسی

افکت‌های صوتی حرفه‌ای Nahimic برای بلندگوی داخلی لپ‌تاپ روی لینوکس. دارای چهار پروفایل (Music، Movie، Gaming و Communication)، تقویت باس و تریبل، وضوح صدا، صدای فراگیر (Surround)، تثبیت ولوم و اکولایزر ۱۰ بانده. این پروژه مستقل است و ارتباطی با Nahimic، A-Volute یا سازندگان لپ‌تاپ ندارد.

این فورک با هدف **پایداری حداکثری و پشتیبانی همگانی** توسعه داده شده است:
- **پایداری صوتی بی‌نقص:** بافر ۱ مگابایتی برای پایپ‌های صدا (`fcntl.F_SETPIPE_SZ`) و اولویت پردازش بلادرنگ (`Nice=-11`, RT Limits) جهت حذف هرگونه لگ، بریدگی یا خش‌خش صدا زیر بار سنگین پردازنده.
- **مهلت زمانی جابجایی (Grace Period):** جلوگیری از کرش سرویس هنگام اتصال/قطع هدفون، بلوتوث یا نمایشگرهای HDMI.
- **پشتیبانی گسترده سخت‌افزاری:** شناسایی خودکار بیش از ۱۰۰۰ مدل لپ‌تاپ (MSI، ASUS، Lenovo، Dell، Acer و...) و استخراج تیونینگ کارخانه‌ای درایور ویندوز، با پشتیبانی تأییدشده از **Realtek ALC274** (مانند MSI Stealth 14 Studio) و **ALC256**.
- **نصب آسان دوگانه:** اسکریپت‌های نصب و یکپارچه‌سازی کامل برای **Arch Linux** و **Debian / Ubuntu**.
- **همزیستی بدون تداخل:** تمرکز کامل بر پردازش باکیفیت اسپیکرها در کنار امکان استفاده موازی از ابزارهای بومی (مانند EasyEffects / DeepFilterNet برای میکروفون).

متن انگلیسی پروژه: [README.md](README.md).

## این پروژه چطور کار می‌کند

Nahimic روی ویندوز یک COM DLL به نام `NahimicAPO4.dll` است (نه یک درایور کرنلی). این پروژه همان DLL واقعی A-Volute را زیر Wine بارگذاری می‌کند، پارامترها را از API رسمی‌اش می‌خواند و صدا را بلوک‌به‌بلوک از `APOProcess()` عبور می‌دهد. یعنی **پردازش DSP واقعی ناهیمیک اجرا می‌شود**، نه بازپیاده‌سازی آن.

```
اپلیکیشن → PipeWire → pulse → Wine → NahimicAPO4.dll (DSP واقعی) → بلندگو
```

## راهنمای نصب سریع

### نصب خودکار با یک دستور (پیشنهادی)
اسکریپت ستاپ خودکار، توزیع لینوکس شما (آرچ، مانجارو، اوبونتو، دبیان و...)، پیش‌نیازها و سخت‌افزار صدا را شناسایی کرده و ناهیمیک را به‌طور کامل نصب و فعال می‌کند:

```sh
git clone https://github.com/mahdishariatzade/nahimic-linux.git
cd nahimic-linux
./setup.sh
```

### نصب دستی بر اساس توزیع

**Arch / EndeavourOS / Manjaro (بسته رسمی pacman):**
```sh
cd packaging && makepkg -si
```

**Debian / Ubuntu:**
```sh
./packaging/install-ubuntu.sh
```

### دستورات مدیریت
```sh
./setup.sh --status       # بررسی وضعیت سرویس و پردازش صدا
./setup.sh --restart      # راه‌اندازی مجدد سرویس صوتی
./setup.sh --uninstall    # حذف کامل و پاک‌سازی فایل‌های ناهیمیک
```

## اختیاری: فیلتر فضایی ناهیمیک

Virtual Surround و صدای فضایی هدفون ناهیمیک با یک دیتابیس فیلتر کار می‌کنند که اپ ویندوز در زمان اجرا به درایور می‌دهد، پس داخل بسته‌ی درایور نیست. بدون آن سرویس کار می‌کند و همه‌ی افکت‌ها اعمال می‌شوند؛ فقط فیلتر فضایی همان چیزی می‌ماند که بسته‌ی درایور دارد.

اگر یک نصب ویندوز داری که رویش ناهیمیک نصب است:

```sh
python3 packaging/nahimic-settings.py extract --windows /mnt/win11
python3 packaging/nahimic-settings.py seed
systemctl --user restart nahimic.service
```

دستور اول به `reged` از پکیج `chntpw` نیاز دارد و `extra/3d-database.bin` را همراه با یک dump کامل از تنظیمات می‌نویسد. هیچ داده‌ی اختصاصی‌ای در این مخزن ذخیره نمی‌شود، به همین دلیل `extra/` در git نادیده گرفته می‌شود. اسکریپت‌های نصب، اگر `extra/3d-database.bin` موجود باشد، خودکار این مرحله را اجرا می‌کنند.

اگر بعد از تزریق، سرویس خطای `Original APO initialization failed` داد، یعنی یک import ناموفق محصول را نیمه‌initialized رها کرده؛ ریست کنید:

```sh
systemctl --user stop nahimic.service
rm -rf ~/.local/share/nahimic-linux/runtime ~/.local/share/nahimic-linux/installation.json
nahimic --activate
```

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

## حذف کامل

اول پنل و سرویس را متوقف کنید تا چیزی prefix واین را در اختیار نداشته باشد:

```sh
pkill -f '[a]pp/main.py'
systemctl --user disable --now nahimic.service
WINEPREFIX=~/.local/share/nahimic-linux/runtime/prefix wineserver -k   # اختیاری، برای باقی‌مانده‌ها
```

آرچ با پکیج و وابستگی‌هایش حذف می‌شود:

```sh
sudo pacman -Rns nahimic-linux
```

دبیان/اوبونتو پکیج ندارد، پس درخت نصب‌شده را پاک کنید:

```sh
sudo rm -rf /usr/lib/nahimic-linux /usr/share/nahimic-linux /usr/bin/nahimic \
    /usr/lib/systemd/user/nahimic.service /usr/share/applications/nahimic.desktop \
    /usr/share/icons/hicolor/scalable/apps/nahimic.svg /etc/xdg/autostart/nahimic.desktop
systemctl --user daemon-reload
systemctl --user reset-failed nahimic.service 2>/dev/null || true
```

بعد تنظیمات، فیلتر فضایی استخراج‌شده و محیط واین را حذف کنید — کل prefix از جمله دیتابیس تزریق‌شده داخل آن است:

```sh
rm -rf ~/.local/share/nahimic-linux ~/.config/nahimic-linux
rm -rf extra                             # داخل مخزن، اگر آنجا استخراج کرده‌اید
```

بررسی نهایی:

```sh
systemctl --user status nahimic.service   # انتظار: Unit nahimic.service could not be found
pgrep -af '[n]ahimic-linux/host'            # انتظار: بدون خروجی
```

پکیج‌هایی که برای آن نصب شدند باقی می‌مانند، چون ممکن است نرم‌افزار دیگری هم ازشان استفاده کند. در دبیان/اوبونتو: `wine`، `mingw-w64`، `cabextract`، `python3-pyside6.qtcore`، `python3-pyside6.qtgui`، `python3-pyside6.qtwidgets` و `python3-pyside6.qtnetwork`. در آرچ: `wine`، `mingw-w64-gcc` و `cabextract`. هرکدام را که لازم ندارید با `apt remove` یا `pacman -R` حذف کنید.

## پشتیبانی سخت‌افزار

بیشتر لپتاپ‌ها هیچ کاری لازم ندارند: نصب‌کننده همه‌ی کاب‌های سازنده‌ها را در بسته‌ی درایور ناهیمیک باز می‌کند، تیونینگ اسپیکرشان را برمی‌دارد و جدول تطبیق می‌سازد. با بسته‌ی فعلی بیش از هزار لپتاپ بدون هیچ تنظیمی کار می‌کنند.

جدول curated در `host/devices.json` فقط سخت‌افزار تست‌شده را نگه می‌دارد و بر جدول تولیدشده مقدم است، چون ورودی‌های تولیدشده فقط subsystem دارند و کدک را در خود فایل تیونینگ ثبت نمی‌کنند. برای اینکه یک لپتاپ با کدک و نام واقعی و پرچم verified شناسایی شود، ورودی‌اش را آنجا اضافه کنید.

اگر لپتاپی در هیچ جدولی نبود ولی خودش تیونینگ دارد، از طریق `~/.config/nahimic-linux/devices.json` کار می‌کند و نیازی به بیلد مجدد ندارد.

## سخت‌افزار پشتیبانی‌شده

| مدل | کدک | subsystem | وضعیت |
|---|---|---|---|
| MECHREVO Wujie 14X Pro | `14f11f87` | `1d05e022` | تأییدشده (verified) |
| MSI Stealth 14 Studio A13VF | `10ec0274` | `146213c0` | تأییدشده (verified) |
| لپ‌تاپ‌های ALC256 | `10ec0256` | `1c05c022` | آزمایشی |

وضعیت `تأییدشده` به این معنی است که تطبیق سخت‌افزار، اتصال پورت‌ها و پخش بدون نقص صدا مستقیماً روی دستگاه فیزیکی آزمایش و اعتبارسنجی شده است. سایر مدل‌های لپ‌تاپ از طریق جدول خودکار و فایل‌های تیونینگ رسمی پشتیبانی می‌شوند.