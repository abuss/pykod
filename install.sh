#!/bin/bash

pacman -Syy

archlinux-keyring-wkd-sync

pacman -S git uv

git clone https://github.com/abuss/pykod

cd pykod

git switch reuse_home

uv sync

uv run example/configuration-vm.py install


