name: Build APK

on:
  push:
    branches: [ main, master ]
  workflow_dispatch:

jobs:
  build:
    runs-on: ubuntu-22.04

    steps:
    - name: Checkout code
      uses: actions/checkout@v4

    - name: Setup Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.10'

    - name: Install System Dependencies
      run: |
        sudo apt-get update
        sudo apt-get install -y \
            build-essential git unzip zip openjdk-17-jdk \
            autoconf libtool pkg-config zlib1g-dev \
            libncurses5-dev libncursesw5-dev libtinfo5 \
            cmake libffi-dev libssl-dev automake \
            libltdl-dev libfreetype6-dev

    - name: Install Buildozer
      run: |
        pip install --upgrade pip setuptools wheel
        pip install cython==0.29.36 buildozer

    - name: Accept Android Licenses & Build APK
      run: |
        yes | buildozer android debug > build.log 2>&1 || (cat build.log && exit 1)

    - name: Upload Build Log (Always)
      uses: actions/upload-artifact@v4
      if: always()
      with:
        name: full-build-log
        path: build.log

    - name: Upload Ready APK
      uses: actions/upload-artifact@v4
      with:
        name: WallCrusher-APK
        path: bin/*.apk
