#!/bin/bash
# Wrapper script to download photos for all listings
# Usage: ./download_photos.sh [--limit N] [--overwrite]

ARGS=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --limit)
            ARGS="$ARGS --limit $2"
            shift 2
            ;;
        --overwrite)
            ARGS="$ARGS --overwrite"
            shift
            ;;
        --max-width)
            ARGS="$ARGS --max-width $2"
            shift 2
            ;;
        --quality)
            ARGS="$ARGS --quality $2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: ./download_photos.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --limit N        Process only first N listings"
            echo "  --overwrite      Overwrite existing photos"
            echo "  --max-width N    Maximum image width (default: 800)"
            echo "  --quality N      WebP quality 1-100 (default: 85)"
            echo ""
            echo "Examples:"
            echo "  ./download_photos.sh                    # Download all missing photos"
            echo "  ./download_photos.sh --limit 10         # Download first 10"
            echo "  ./download_photos.sh --overwrite        # Redownload all photos"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Run ./download_photos.sh --help for usage"
            exit 1
            ;;
    esac
done

# Run the Django management command via docker-compose
docker-compose exec -T web python manage.py download_photos $ARGS