#!/usr/bin/env zsh

source ./pipeline/vars.sh

cd $BASE_DIR/src/frontend
pnpm i
pnpm build
cp -r ./dist ../backend/dist
