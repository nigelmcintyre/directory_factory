#!/bin/bash
# Wrapper script to verify listing data quality
# Usage: ./verify_listings.sh [OPTIONS]

ARGS=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --fix)
            ARGS="$ARGS --fix"
            shift
            ;;
        --county-only)
            ARGS="$ARGS --county-only"
            shift
            ;;
        --limit)
            ARGS="$ARGS --limit $2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: ./verify_listings.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --fix            Automatically fix detected issues"
            echo "  --county-only    Only verify county information"
            echo "  --limit N        Check only first N listings (useful for testing)"
            echo ""
            echo "Examples:"
            echo "  ./verify_listings.sh                    # Check all, report only"
            echo "  ./verify_listings.sh --county-only      # Check only counties"
            echo "  ./verify_listings.sh --limit 10         # Check first 10 listings"
            echo "  ./verify_listings.sh --fix              # Check all and auto-fix"
            echo "  ./verify_listings.sh --county-only --fix # Fix only county issues"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Run ./verify_listings.sh --help for usage"
            exit 1
            ;;
    esac
done

# Run the Django management command via docker-compose
docker-compose exec -T web python manage.py verify_listings $ARGS
