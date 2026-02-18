from django.core.management.base import BaseCommand
from blog.models import Post
from django.utils.text import slugify

class Command(BaseCommand):
    help = 'Populates the blog with initial content'

    def handle(self, *args, **kwargs):
        articles = [
            {
                "title": "Top 5 Health Benefits of Regular Sauna Use",
                "content": """Regular sauna bathing has been linked to numerous health benefits, backed by scientific research.

1. cardiovascular Health: Studies show that regular sauna use can lower blood pressure and improve heart function. The heat causes blood vessels to dilate, improving circulation.

2. Muscle Recovery: Athletes have long used saunas to recover from intense workouts. The heat helps relax muscles and reduce inflammation.

3. Stress Relief: The heat triggers the release of endorphins, the body's natural "feel-good" chemicals. A session can leave you feeling relaxed and rejuvenated.

4. Improved Sleep: The drop in body temperature after a sauna session can signal to the body that it's time to sleep.

5. Skin Health: Sweating helps flush out impurities and dead skin cells, leaving your skin glowing.

Remember to stay hydrated and listen to your body!""",
                "excerpt": "Discover how regular sauna sessions can improve your heart health, reduce stress, and boost recovery.",
                "cover_image_url": "https://images.unsplash.com/photo-1543489822-c495ebd9f3e9?ixlib=rb-1.2.1&auto=format&fit=crop&w=1350&q=80"
            },
            {
                "title": "Wood-Fired vs. Infrared: Which Sauna is Right for You?",
                "content": """Choosing between a traditional wood-fired sauna and a modern infrared sauna comes down to personal preference.

**Wood-Fired Saunas (Traditional)**
- **Heat Source:** Wood stove burning logs.
- **Experience:** Crackling fire, scent of wood smoke, very high heat (80-100°C).
- **Humidity:** You can throw water on the rocks ("löyly") to create steam.
- **Best For:** Purists who love the ritual and intense heat.

**Infrared Saunas**
- **Heat Source:** Infrared panels that heat your body directly, not just the air.
- **Experience:** Gentle heat, lower temperatures (45-60°C).
- **Humidity:** Dry heat, no steam.
- **Best For:** People who find high heat uncomfortable or want specific deep-tissue benefits.

Both offer excellent health benefits. Why not try both at local Irish saunas found on our directory?""",
                "excerpt": "Debating between traditional heat and modern infrared? We break down the differences to help you choose.",
                "cover_image_url": "https://images.unsplash.com/photo-1515362778563-6a8d0e44bc0b?ixlib=rb-1.2.1&auto=format&fit=crop&w=1350&q=80"
            },
            {
                "title": "The Rise of Sea Swimming & Sauna Culture in Ireland",
                "content": """Ireland has seen an explosion in mobile saunas popping up by beaches and lakes. This combination of cold water immersion and hot sauna therapy is more than just a trend—it's a movement.

**The Contrast Therapy Effect**
Moving from the freezing Irish Sea (often 10°C or lower) into a hot sauna (80°C+) creates a powerful physiological response. Your blood vessels constrict in the cold and dilate in the heat, pumping blood through your system.

**Community Connection**
Use our map to find saunas at popular spots like The Forty Foot, Salthill, or Garretstown. It's a fantastic way to meet people and embrace the outdoors in any weather.

**Tips for Beginners:**
- Start slow with short dips.
- Don't push your limits in the heat.
- Bring a warm hat and a flask of tea for afterwards!""",
                "excerpt": "Explore why thousands of Irish people are flocking to the coast for a freezing dip followed by a hot sauna.",
                "cover_image_url": "https://images.unsplash.com/photo-1544161515-4ab6ce6db48c?ixlib=rb-1.2.1&auto=format&fit=crop&w=1350&q=80"
            }
        ]

        for article_data in articles:
            post, created = Post.objects.get_or_create(
                slug=slugify(article_data['title']),
                defaults=article_data
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created article: {post.title}"))
            else:
                self.stdout.write(self.style.WARNING(f"Article already exists: {post.title}"))
