[app]

title = MathLens
package.name = mathlens
package.domain = org.cimoopp

source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,json,npz,txt,md

version = 0.1.0

# python3 — рантайм, kivy — интерфейс, pillow+numpy — обработка снимка и инференс,
# sympy — точная математика (mpmath идёт как его зависимость)
requirements = python3,kivy,pillow,numpy,sympy,mpmath

orientation = portrait
fullscreen = 0

android.permissions = CAMERA,READ_MEDIA_IMAGES,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE
android.api = 34
android.minapi = 24
android.ndk = 25b
android.archs = arm64-v8a

android.allow_backup = True
android.accept_sdk_license = True

# сборка идёт с develop-ветки python-for-android: там свежие рецепты для numpy/sympy
p4a.branch = develop

[buildozer]

log_level = 2
warn_on_root = 1
