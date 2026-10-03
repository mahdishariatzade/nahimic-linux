PREFIX ?= /usr
DESTDIR ?=
CXX_WIN = x86_64-w64-mingw32-g++
CC_WIN = x86_64-w64-mingw32-gcc
WINFLAGS = -std=c++17 -Wall -Wextra -Werror -O2 -static -municode

all: bin/apo_probe.exe bin/apo_control.exe bin/seed3d.exe bin/pulse_state
bin:
	mkdir -p bin
bin/apo_probe.exe: host/apo_probe.cpp $(wildcard host/*.hpp) host/volume_state.h | bin
	$(CXX_WIN) $(WINFLAGS) $< -lpropsys -loleaut32 -lole32 -luuid -o $@
bin/apo_control.exe: host/apo_control.cpp $(wildcard host/*.hpp) | bin
	$(CXX_WIN) $(WINFLAGS) $< -loleaut32 -lole32 -luuid -o $@
bin/seed3d.exe: packaging/seed3d.c | bin
	$(CC_WIN) -std=c11 -Wall -Wextra -Werror -O2 -static $< -loleaut32 -ladvapi32 -o $@
bin/pulse_state: host/pulse_state.c host/volume_state.h | bin
	$(CC) $(CPPFLAGS) $(CFLAGS) -std=c11 -Wall -Wextra -Werror -O2 $< $$(pkg-config --cflags --libs libpulse) $(LDFLAGS) -o $@
install: all
	install -d $(DESTDIR)$(PREFIX)/lib/nahimic-linux/{app,host,bin}
	install -m644 app/*.py app/*.svg $(DESTDIR)$(PREFIX)/lib/nahimic-linux/app/
	install -d $(DESTDIR)$(PREFIX)/lib/nahimic-linux/app/assets
	install -m644 app/assets/* $(DESTDIR)$(PREFIX)/lib/nahimic-linux/app/assets/
	install -d $(DESTDIR)$(PREFIX)/lib/nahimic-linux/app/locales
	install -m644 app/locales/*.json $(DESTDIR)$(PREFIX)/lib/nahimic-linux/app/locales/
	install -m644 host/*.py host/devices.json $(DESTDIR)$(PREFIX)/lib/nahimic-linux/host/
	install -m755 bin/* $(DESTDIR)$(PREFIX)/lib/nahimic-linux/bin/
	install -Dm755 packaging/nahimic $(DESTDIR)$(PREFIX)/bin/nahimic
	install -Dm644 packaging/nahimic.service $(DESTDIR)$(PREFIX)/lib/systemd/user/nahimic.service
	install -Dm644 packaging/nahimic.desktop $(DESTDIR)$(PREFIX)/share/applications/nahimic.desktop
	install -Dm644 packaging/nahimic-autostart.desktop $(DESTDIR)/etc/xdg/autostart/nahimic.desktop
	install -Dm644 app/nahimic.svg $(DESTDIR)$(PREFIX)/share/icons/hicolor/scalable/apps/nahimic.svg
	install -Dm644 LICENSE $(DESTDIR)$(PREFIX)/share/licenses/nahimic-linux/LICENSE
	install -Dm644 packaging/LicenseRef-Nahimic $(DESTDIR)$(PREFIX)/share/licenses/nahimic-linux/LicenseRef-Nahimic
	install -Dm644 README.md $(DESTDIR)$(PREFIX)/share/doc/nahimic-linux/README.md
SHELL := /bin/bash
