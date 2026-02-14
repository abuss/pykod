#!/bin/bash

pacman -Syy

archlinux-keyring-wkd-sync

pacman -S debootstrap uv git

git clone https://github.com/abuss/pykod

cd pykod

git switch multi_dist

uv sync

# uv run example/configuration-vm.py install
