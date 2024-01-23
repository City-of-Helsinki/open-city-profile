#!/usr/bin/env bash

if [[ ! -z "$@" ]]; then
    apt-get remove -y "$@"
fi

apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false
apt-get clean
rm -rf /var/lib/apt/lists/*
