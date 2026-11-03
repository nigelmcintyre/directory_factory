import csv
from datetime import date

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Sum
from django.utils import timezone

from directory.models import ListingDailyStat

METRICS = [metric for metric, _ in ListingDailyStat.METRIC_CHOICES]


class Command(BaseCommand):
    help = "CSV of per-listing views, impressions and clicks for one month"

    def add_arguments(self, parser):
        parser.add_argument("--month", help="YYYY-MM (default: current month)")
        parser.add_argument("--listing", help="Only this listing slug")

    def handle(self, *args, **options):
        start = self._month_start(options["month"])
        end = date(start.year + start.month // 12, start.month % 12 + 1, 1)

        stats = ListingDailyStat.objects.filter(date__gte=start, date__lt=end)
        if options["listing"]:
            stats = stats.filter(listing__slug=options["listing"])

        rows = {}
        for stat in stats.values(
            "listing__slug", "listing__name", "listing__county", "listing__is_featured", "metric"
        ).annotate(total=Sum("count")):
            row = rows.setdefault(stat["listing__slug"], {
                "slug": stat["listing__slug"],
                "name": stat["listing__name"],
                "county": stat["listing__county"],
                "is_featured": int(stat["listing__is_featured"]),
                **dict.fromkeys(METRICS, 0),
            })
            row[stat["metric"]] = stat["total"]

        for row in rows.values():
            row["total_clicks"] = sum(row[metric] for metric in METRICS if metric.startswith("click_"))

        writer = csv.DictWriter(
            self.stdout,
            fieldnames=["slug", "name", "county", "is_featured", *METRICS, "total_clicks"],
        )
        writer.writeheader()
        writer.writerows(sorted(rows.values(), key=lambda row: (-row["total_clicks"], -row["view"])))

    def _month_start(self, month):
        if not month:
            return timezone.now().date().replace(day=1)
        try:
            year, month_number = (int(part) for part in month.split("-"))
            return date(year, month_number, 1)
        except ValueError:
            raise CommandError("--month must be YYYY-MM")
