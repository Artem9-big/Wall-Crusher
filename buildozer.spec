[app]
title = Wall Crusher
package.name = wallcrusher
package.domain = org.wallcrusher
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
version = 1.0
icon.filename = %(source.dir)s/icon.jpg
requirements = python3,pygame,sdl2_image,sdl2_mixer,sdl2_ttf,sdl2
orientation = portrait
fullscreen = 1
android.archs = arm64-v8a, armeabi-v7a
android.allow_backup = True

[buildozer]
log_level = 2
warn_on_root = 1
