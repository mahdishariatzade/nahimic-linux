/* Seed Nahimic binary settings into the Wine prefix of the installed product.
 *
 * The values are handed over by nahimic-settings, which reads them from a
 * Windows installation or from an exported registry file. Nothing proprietary
 * is stored in this repository.
 */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define SETTINGS_SUB_KEY \
    "Software\\Nahimic\\NahimicAPO4\\A-Voluteinternal\\NahimicSettings\\GlobalControl\\Store"

static int put_binary(HKEY root, const char *name, const void *data, DWORD size) {
    HKEY key;
    LONG r = RegCreateKeyExA(root, SETTINGS_SUB_KEY, 0, NULL, 0, KEY_ALL_ACCESS, NULL, &key, NULL);
    if (r != ERROR_SUCCESS) {
        fprintf(stderr, "seed3d: cannot open %s (%ld)\n", SETTINGS_SUB_KEY, r);
        return 1;
    }
    r = RegSetValueExA(key, name, 0, REG_BINARY, (const BYTE *)data, size);
    if (r != ERROR_SUCCESS)
        fprintf(stderr, "seed3d: cannot set %s (%ld)\n", name, r);
    RegCloseKey(key);
    return r != ERROR_SUCCESS;
}

static int put_dword(HKEY root, const char *name, DWORD value) {
    HKEY key;
    LONG r = RegCreateKeyExA(root, SETTINGS_SUB_KEY, 0, NULL, 0, KEY_ALL_ACCESS, NULL, &key, NULL);
    if (r != ERROR_SUCCESS) {
        fprintf(stderr, "seed3d: cannot open %s (%ld)\n", SETTINGS_SUB_KEY, r);
        return 1;
    }
    r = RegSetValueExA(key, name, 0, REG_DWORD, (const BYTE *)&value, sizeof value);
    if (r != ERROR_SUCCESS)
        fprintf(stderr, "seed3d: cannot set %s (%ld)\n", name, r);
    RegCloseKey(key);
    return r != ERROR_SUCCESS;
}

static unsigned char *read_file(const char *path, DWORD *size) {
    FILE *file = fopen(path, "rb");
    if(!file) {
        fprintf(stderr, "seed3d: cannot open %s\n", path);
        return NULL;
    }
    fseek(file, 0, SEEK_END);
    long length = ftell(file);
    fseek(file, 0, SEEK_SET);
    if(length <= 0) {
        fclose(file);
        fprintf(stderr, "seed3d: %s is empty\n", path);
        return NULL;
    }
    unsigned char *data = (unsigned char *)malloc((size_t)length);
    if(!data || fread(data, 1, (size_t)length, file) != (size_t)length) {
        fclose(file);
        free(data);
        fprintf(stderr, "seed3d: cannot read %s\n", path);
        return NULL;
    }
    fclose(file);
    *size = (DWORD)length;
    return data;
}

int main(int argc, char **argv) {
    if(argc != 3) {
        fprintf(stderr, "usage: seed3d <3d-database-file> <count>\n");
        return 2;
    }
    DWORD size = 0;
    unsigned char *data = read_file(argv[1], &size);
    if(!data) return 2;
    int failed = 0;
    failed |= put_binary(HKEY_LOCAL_MACHINE, "kSet_Hp3DDatabaseFilter", data, size);
    failed |= put_dword(HKEY_LOCAL_MACHINE, "kSet_Hp3DDatabaseFilterCount",
                        (DWORD)strtoul(argv[2], NULL, 10));
    failed |= put_dword(HKEY_LOCAL_MACHINE, "kSet_Hp3DDatabaseFilterId", 1);
    failed |= put_dword(HKEY_LOCAL_MACHINE, "kSet_Hp3DDatabaseFilterState", 1);
    failed |= put_dword(HKEY_LOCAL_MACHINE, "kSet_Spk3DDatabaseFilterId", 3);
    failed |= put_dword(HKEY_LOCAL_MACHINE, "kSet_Spk3DDatabaseFilterState", 0);
    free(data);
    if(!failed) fprintf(stderr, "seed3d: wrote %lu bytes\n", (unsigned long)size);
    return failed;
}