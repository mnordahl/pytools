#!/bin/bash
echo "Installing git hooks..."
cp githooks/* .git/hooks/
chmod +x .git/hooks/*
echo "Done."
