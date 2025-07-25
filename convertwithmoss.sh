#!/bin/bash
# ConvertWithMoss Wrapper Script
# This script runs ConvertWithMoss with all required dependencies

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Set the classpath to include all JARs in the lib directory
CLASSPATH="$SCRIPT_DIR/ConvertWithMoss/target/lib/*"

# Run ConvertWithMoss with all arguments passed through
java -cp "$CLASSPATH" de.mossgrabers.convertwithmoss.ui.ConvertWithMossApp "$@"
