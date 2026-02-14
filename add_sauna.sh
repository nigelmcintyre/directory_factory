#!/bin/bash
# Wrapper script to add a sauna from Google Maps URL
# Usage: ./add_sauna.sh "<google_maps_url>"
# Or: ./add_sauna.sh "<place_id>"
# Or: ./add_sauna.sh --search "<sauna name>"

SEARCH_FLAG=""
INPUT=""

# Parse arguments
if [ "$1" == "--search" ]; then
    SEARCH_FLAG="--search"
    INPUT="$2"
elif [ -n "$1" ]; then
    INPUT="$1"
else
    echo "Usage: ./add_sauna.sh [--search] \"<google_maps_url_or_place_id_or_name>\""
    echo ""
    echo "Examples:"
    echo "  ./add_sauna.sh \"https://www.google.com/maps/place/...\""
    echo "  ./add_sauna.sh \"ChIJpVTwYrEfbEgRs8L59OUk56g\""
    echo "  ./add_sauna.sh --search \"The Barrel Sauna Dublin\""
    echo ""
    echo "Options:"
    echo "  --search    Search by place name instead of place_id/URL"
    echo ""
    echo "Tip: To get a place_id, open Google Maps, click on the place,"
    echo "     and look for 'place_id' in the URL or page info"
    exit 1
fi

# Run the Django management command via docker-compose
if [ -n "$SEARCH_FLAG" ]; then
    docker-compose exec -T web python manage.py add_sauna "$INPUT" --search
else
    docker-compose exec -T web python manage.py add_sauna "$INPUT"
fi
